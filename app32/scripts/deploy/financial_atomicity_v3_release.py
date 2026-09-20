"""Bounded surgical release of the reviewed six-file financial package."""
import hashlib
import json
import pathlib
import shlex
import subprocess
import sys
import time

from configr_remote_helper import connect_ssh, APP_DIR, BASE_DIR

ROOT = pathlib.Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / 'app32/docs/harnesses/screen_performance_inventory_v1'
WORKTREE = pathlib.Path('C:/Users/mff20/.codex/worktrees/financial-atomicity-v3/app32')
COMMIT = '77355c063b9c391b26d88f0095733295ca612dc4'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(ssh, command):
    _, out, err = ssh.exec_command(command, timeout=30)
    output, errors = out.read().decode(), err.read().decode()
    if out.channel.recv_exit_status():
        raise RuntimeError(errors[:500] or output[:500])
    return output


def prepare():
    manifest = json.loads((EVIDENCE / 'financial_atomicity_candidate_v3_manifest.json').read_text(encoding='utf-8'))
    baseline = json.loads((EVIDENCE / 'financial_atomicity_deploy_preflight.json').read_text(encoding='utf-8'))
    expected = {r['path']: r for r in baseline['files']}
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/codex/financial-atomicity-v3'], cwd=WORKTREE, text=True).split()[0]
    assert remote == COMMIT
    snapshot = BASE_DIR + '/predeploy_snapshots/financial_atomicity_v3_' + str(int(time.time()))
    plan = {'commit': COMMIT, 'snapshot': snapshot, 'app': APP_DIR, 'files': []}
    ssh = connect_ssh()
    try:
        run(ssh, 'mkdir -p ' + shlex.quote(snapshot + '/originals/services') + ' ' + shlex.quote(snapshot + '/staged/services'))
        with ssh.open_sftp() as sftp:
            for rec in manifest['files']:
                rel = rec['path'].removeprefix('app32/')
                assert rel.startswith('services/') and '/' not in rel[len('services/'):]
                content = subprocess.check_output(['git', 'show', COMMIT + ':' + rec['path']], cwd=WORKTREE).replace(b'\r\n', b'\n')
                assert sha(content) == rec['candidate_sha256']
                compile(content, rel, 'exec')
                try:
                    with sftp.open(APP_DIR + '/' + rel, 'rb') as f:
                        old = f.read()
                except FileNotFoundError:
                    old = None
                assert (old is not None) == expected[rec['path']]['exists']
                if old is not None:
                    assert sha(old.replace(b'\r\n', b'\n')) == expected[rec['path']]['sha256'], 'Remote drift: ' + rel
                    with sftp.open(snapshot + '/originals/' + rel, 'wb') as f:
                        f.write(old)
                    with sftp.open(snapshot + '/originals/' + rel, 'rb') as f:
                        assert sha(f.read()) == sha(old)
                with sftp.open(snapshot + '/staged/' + rel, 'wb') as f:
                    f.write(content)
                with sftp.open(snapshot + '/staged/' + rel, 'rb') as f:
                    assert sha(f.read()) == sha(content)
                plan['files'].append({'path': rel, 'old_sha256': sha(old) if old is not None else None, 'new_sha256': sha(content)})
            with sftp.open(snapshot + '/plan.json', 'w') as f:
                f.write(json.dumps(plan))
    finally:
        ssh.close()
    (EVIDENCE / 'financial_atomicity_deploy_plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    print(json.dumps(plan, indent=2))


REMOTE_APPLY = r'''
import hashlib,json,os,pathlib,signal,socket,subprocess,time,urllib.request
plan=json.loads(pathlib.Path(PLAN_PATH).read_text()); app=pathlib.Path(plan['app']); snap=pathlib.Path(plan['snapshot'])
result={'commit':plan['commit'],'snapshot':str(snap),'events':[],'deployed':False}
paused=[]; replaced=[]; stopped=False
def report(event):
 result['events'].append(event);(snap/'result.json').write_text(json.dumps(result,indent=2));print(event,flush=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats():
 s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect(str(app.parents[1]/'etc/uwsgi/stats'));data=b''
 while True:
  b=s.recv(65536)
  if not b:break
  data+=b
 s.close();return json.loads(data)
def manager(name,action):
 with (snap/(name+'_'+action+'.log')).open('w') as log:
  r=subprocess.run(['bash',str(app/'scripts'/('manage_'+name+'.sh')),action],stdout=log,stderr=subprocess.STDOUT,timeout=300)
 if r.returncode:raise RuntimeError(name+' '+action+' failed; see snapshot log')
 report(name+' '+action+' succeeded')
def signal_safe(pid,sig):
 try:os.kill(pid,sig)
 except ProcessLookupError:pass
def thaw_restart():
 for pid in paused:signal_safe(pid,signal.SIGTERM)
 for pid in paused:signal_safe(pid,signal.SIGCONT)
 paused.clear()
def health(url,host=None,attempts=45):
 for _ in range(attempts):
  try:
   req=urllib.request.Request(url,headers={'Host':host} if host else {})
   with urllib.request.urlopen(req,timeout=3) as r:
    if r.status==200:return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('health failed: '+url)
try:
 for f in plan['files']:
  target=app/f['path'];assert target.exists()==(f['old_sha256'] is not None)
  if target.exists():assert digest(target)==f['old_sha256'],'drift '+f['path']
  assert digest(snap/'staged'/f['path'])==f['new_sha256'];compile((snap/'staged'/f['path']).read_bytes(),f['path'],'exec')
 before=stats();assert len(before['workers'])==1,'unexpected worker count';assert before.get('listen_queue',0)==0
 assert all(not c.get('in_request') for w in before['workers'] for c in w.get('cores',[])),'web request active'
 # Refuse deployment while a known long-lived stdio MCP writer exists.
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:args=(proc/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  assert not any(a.endswith(b'/mcp_server.py') or a==b'mcp_server.py' for a in args),'active MCP stdio writer'
 report('hashes and idle single-worker preflight confirmed')
 stopped=True
 manager('scheduler','stop');manager('mcp_http','stop')
 before=stats();assert before.get('listen_queue',0)==0
 assert all(not c.get('in_request') for w in before['workers'] for c in w.get('cores',[]))
 for pid in [before['pid']]+[w['pid'] for w in before['workers']]:
  os.kill(pid,signal.SIGSTOP);paused.append(pid)
 report('APP32 master and worker paused briefly for file switch')
 # New dependency first; each destination replacement is atomic.
 files=sorted(plan['files'],key=lambda f:f['path']!='services/financial_transaction.py')
 for f in files:
  target=app/f['path'];tmp=target.with_name(target.name+'.financial_v3_tmp')
  tmp.write_bytes((snap/'staged'/f['path']).read_bytes());tmp.chmod(target.stat().st_mode & 0o777 if target.exists() else 0o644)
  os.replace(tmp,target);replaced.append(f)
  assert digest(target)==f['new_sha256']
 report('six versioned files installed and hashes verified')
 thaw_restart();report('old APP32 processes terminated; emperor will respawn')
 health('http://127.0.0.1/healthz','app.gestaoversus.com.br')
 # uWSGI can re-exec the master with the same PID. Verify replacement of
 # the actual HTTP worker, rather than requiring a different master PID.
 old_workers={w['pid'] for w in before['workers']}
 for _ in range(30):
  after=stats()
  if len(after['workers'])==1 and old_workers.isdisjoint({w['pid'] for w in after['workers']}):break
  time.sleep(1)
 else:raise RuntimeError('HTTP worker replacement not confirmed')
 result['web_before']={'master':before['pid'],'workers':[w['pid'] for w in before['workers']]}
 result['web_after']={'master':after['pid'],'workers':[w['pid'] for w in after['workers']]}
 manager('scheduler','start');manager('scheduler','health');manager('mcp_http','start')
 health('http://127.0.0.1:8101/healthz');health('https://app.gestaoversus.com.br/mcp/healthz',attempts=5)
 for f in plan['files']:assert digest(app/f['path'])==f['new_sha256']
 result['deployed']=True;report('web scheduler MCP healthy; single worker retained')
except Exception as exc:
 result['error']=type(exc).__name__+': '+str(exc);report('deployment failed; restoring snapshot')
 for f in reversed(replaced):
  target=app/f['path']
  if f['old_sha256'] is None:target.unlink(missing_ok=True)
  else:
   tmp=target.with_name(target.name+'.financial_v3_rollback');tmp.write_bytes((snap/'originals'/f['path']).read_bytes());os.replace(tmp,target)
 thaw_restart()
 if replaced:
  try:
   current=stats()
   for pid in [current['pid']]+[w['pid'] for w in current['workers']]:signal_safe(pid,signal.SIGTERM)
  except Exception:pass
 if stopped:
  for name in ['scheduler','mcp_http']:
   try:manager(name,'start')
   except Exception as recovery:report('recovery warning: '+str(recovery))
 report('rollback attempted; verify runtime before reopening');raise
finally:
 for pid in paused:signal_safe(pid,signal.SIGCONT)
 (snap/'result.json').write_text(json.dumps(result,indent=2))
'''


def apply():
    plan = json.loads((EVIDENCE / 'financial_atomicity_deploy_plan.json').read_text(encoding='utf-8'))
    ssh = connect_ssh()
    try:
        code = 'PLAN_PATH=' + repr(plan['snapshot'] + '/plan.json') + '\n' + REMOTE_APPLY
        stdin, stdout, stderr = ssh.exec_command(BASE_DIR + '/.virtualenv/3.12/bin/python -u -', timeout=420)
        stdin.write(code)
        stdin.channel.shutdown_write()
        for line in stdout:
            print(line.rstrip(), flush=True)
        errors = stderr.read().decode()
        status = stdout.channel.recv_exit_status()
        with ssh.open_sftp() as sftp:
            with sftp.open(plan['snapshot'] + '/result.json') as f:
                result = f.read()
        (EVIDENCE / 'financial_atomicity_deploy_result.json').write_bytes(result)
        print(errors[-1500:] if errors else '')
        print(result.decode())
        if status:
            raise SystemExit(status)
    finally:
        ssh.close()


if __name__ == '__main__':
    {'prepare': prepare, 'apply': apply}[sys.argv[1]]()
