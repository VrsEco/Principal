"""Linux-only synthetic transport lab. No APP32 imports, DB or financial writes.

Run with production virtualenv Python; uses the installed uWSGI executable but
never its configuration. All HTTP listeners bind loopback, on temporary ports.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request


def stop_owned(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def main():
    assert sys.platform == 'linux', 'Requires Linux uWSGI'
    executable = None
    for proc in Path('/proc').iterdir():
        try:
            argv = (proc / 'cmdline').read_bytes().split(b'\0')
            if argv[0].endswith(b'/uwsgi') and b'appgestaoversuscombr.45a4cd4b.configr.cloud.ini' in argv:
                executable = argv[0].decode()
                break
        except OSError:
            pass
    assert executable and Path(executable).is_file(), 'uWSGI binary not found'
    result = {'scope': 'synthetic Flask only; no APP32, auth, tenant or financial validation', 'cases': []}
    clean_env = {k: os.environ[k] for k in ('PATH', 'HOME', 'LANG', 'LD_LIBRARY_PATH') if k in os.environ}
    with tempfile.TemporaryDirectory(prefix='gv-wsgi-lab-') as directory:
        root = Path(directory)
        app = root / 'fixture.py'
        app.write_text("""from flask import Flask, jsonify
from pathlib import Path
import os,time
application=Flask(__name__)
@application.get('/fast')
def fast():return jsonify(pid=os.getpid())
@application.get('/slow')
def slow():
 Path(__file__).with_suffix('.started').write_text(str(os.getpid()))
 time.sleep(4)
 return jsonify(pid=os.getpid())
""")
        for workers in (1, 2):
            with socket.socket() as s:
                s.bind(('127.0.0.1', 0))
                port = s.getsockname()[1]
            marker = app.with_suffix('.started')
            marker.unlink(missing_ok=True)
            command = [executable, '--home', sys.prefix, '--master', '--workers', str(workers), '--threads', '1',
                       '--http-socket', f'127.0.0.1:{port}', '--wsgi-file', str(app),
                       '--callable', 'application', '--need-app', '--die-on-term',
                       '--vacuum', '--disable-logging', '--harakiri', '8',
                       '--logto', str(root / f'uwsgi-{workers}.log')]
            error_file = (root / 'stderr.log').open('w+')
            process = subprocess.Popen(command, cwd=root, env=clean_env, start_new_session=True,
                                       stdin=subprocess.DEVNULL, stdout=error_file, stderr=error_file)
            def get(route):
                start = time.monotonic()
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/{route}', timeout=9) as response:
                    data = json.load(response)
                return {'seconds': round(time.monotonic() - start, 3), **data}
            try:
                deadline = time.monotonic() + 12
                while True:
                    if process.poll() is not None:
                        error_file.flush()
                        log = root / f'uwsgi-{workers}.log'
                        detail = log.read_text() if log.exists() else (root / 'stderr.log').read_text()
                        raise RuntimeError('Synthetic uWSGI failed to start: ' + detail[-1200:])
                    try:
                        get('fast')
                        break
                    except OSError:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(.1)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    slow_future = pool.submit(get, 'slow')
                    deadline = time.monotonic() + 3
                    while not marker.exists():
                        assert time.monotonic() < deadline, 'Slow request never started'
                        time.sleep(.02)
                    fast = get('fast')
                    slow = slow_future.result(timeout=9)
                passed = fast['seconds'] > 3 if workers == 1 else fast['seconds'] < 1.5 and fast['pid'] != slow['pid']
                result['cases'].append({'workers': workers, 'fast': fast, 'slow': slow, 'passed': passed})
            finally:
                stop_owned(process)
                error_file.close()
            assert passed, 'Concurrency expectation failed'
        # EOF contract of installed FastMCP transport; deliberately not APP32 server.
        start = time.monotonic()
        process = subprocess.Popen([sys.executable, '-c',
            "from mcp.server.fastmcp import FastMCP; FastMCP('isolated-eof-test').run(transport='stdio')"],
            cwd=root, env=clean_env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True)
        try:
            _, stderr = process.communicate(input=b'', timeout=12)
            result['fastmcp_eof'] = {'returncode': process.returncode, 'seconds': round(time.monotonic()-start, 3), 'passed': process.returncode == 0}
            if process.returncode:
                result['fastmcp_eof']['error_tail'] = stderr.decode(errors='replace')[-700:]
        finally:
            stop_owned(process)
        result['owned_processes_stopped'] = True
    print(json.dumps(result, indent=2))
    assert result['fastmcp_eof']['passed'], 'EOF test failed'


if __name__ == '__main__':
    main()
