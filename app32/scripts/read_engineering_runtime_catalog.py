"""Explicit opt-in read from an existing Codex daemon; never starts a daemon or turn."""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.engineering_runtime_catalog_service import read_codex_catalog


def main():
    process=None
    worker=None
    cleanup_failed=False
    try:
        executable=shutil.which('codex')
        if not executable:
            raise ValueError('Codex unavailable')
        process=subprocess.Popen([executable,'app-server','proxy'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        messages=queue.Queue(maxsize=128)
        def reader():
            try:
                while True:
                    line=process.stdout.readline(1048577)
                    if not line or len(line)>1048576:
                        messages.put_nowait(None)
                        return
                    messages.put_nowait(json.loads(line))
            except Exception:
                try:messages.put_nowait(None)
                except queue.Full:pass
        worker=threading.Thread(target=reader,daemon=True)
        worker.start()
        deadline=time.monotonic()+20
        sequence=0
        def rpc(method,params,notification=False):
            nonlocal sequence
            if method not in ('initialize','initialized','model/list'):
                raise ValueError('Method not allowed')
            if time.monotonic()>=deadline:
                raise ValueError('Runtime timeout')
            sequence+=1
            payload={'method':method,'params':params}
            if not notification:payload['id']=sequence
            process.stdin.write(json.dumps(payload)+'\n');process.stdin.flush()
            if notification:return None
            while True:
                response=messages.get(timeout=max(0.01,deadline-time.monotonic()))
                if time.monotonic()>deadline or not isinstance(response,dict):
                    raise ValueError('Runtime unavailable')
                if response.get('id')==sequence:
                    if 'error' in response or 'result' not in response:
                        raise ValueError('RPC rejected')
                    return response['result']
        result=read_codex_catalog(rpc)
        output={'success':True,'catalog':result}
        code=0
    except (OSError,ValueError,queue.Empty):
        output={'success':False,'error':'runtime_catalog_unavailable','fallback':'manual_selection_in_runtime'}
        code=2
    finally:
        if process is not None:
            try:
                if process.poll() is None:process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            except (OSError,subprocess.TimeoutExpired):
                cleanup_failed=True
            if worker is not None:
                worker.join(timeout=1)
                cleanup_failed=cleanup_failed or worker.is_alive()
            # Avoid closing a pipe while its reader still holds the stream lock.
            if not cleanup_failed:
                for stream in (process.stdin,process.stdout):
                    if stream is not None:
                        try:stream.close()
                        except OSError:cleanup_failed=True
    if cleanup_failed:
        output={'success':False,'error':'runtime_catalog_cleanup_failed','fallback':'manual_selection_in_runtime'}
        code=2
    print(json.dumps(output))
    return code


if __name__=='__main__':
    raise SystemExit(main())
