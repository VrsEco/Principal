"""New isolated portable PostgreSQL cluster; never uses application DB URLs."""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import uuid


def main():
    package = Path(__file__).resolve().parents[2]
    binaries = package / 'tmp/audit_p0_pg_lab/portable/pgsql/bin'
    root = package / 'tmp/financial_concurrency_lab' / ('run_' + uuid.uuid4().hex)
    root.mkdir(parents=True)
    cluster = root / 'cluster'
    password = secrets.token_urlsafe(32)
    pwfile = root / 'password.tmp'
    pwfile.write_text(password)
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    env = os.environ.copy()
    for key in ('DATABASE_URL', 'DEV_DATABASE_URL', 'APP32_AUDIT_P0_TEST_URL'):
        env.pop(key, None)
    env.update(PYTHONPATH=str(package), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONIOENCODING='utf-8', APP_BOOTSTRAP_DB_SCHEMA='0',
               APP_BOOTSTRAP_RUNTIME_SERVICES='0', TELEGRAM_SETUP_WEBHOOK='0')
    def run(args, name, timeout):
        with (root / name).open('w', encoding='utf-8') as log:
            result = subprocess.run(args, cwd=package.parent, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        output = (root / name).read_text(encoding='utf-8', errors='replace').replace(password, '[REDACTED]')
        (root / name).write_text(output, encoding='utf-8')
        print(output, flush=True)
        return result.returncode
    started = False
    code = 1
    try:
        assert run([str(binaries/'initdb.exe'), '-D', str(cluster), '-U', 'financial_lab',
                    '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C', '--pwfile', str(pwfile)], 'init.log', 90) == 0
        pwfile.unlink()
        assert run([str(binaries/'pg_ctl.exe'), '-D', str(cluster), '-l', str(root/'postgres.log'),
                    '-o', f'-h 127.0.0.1 -p {port} -c max_connections=20', '-w', 'start'], 'start.log', 60) == 0
        started = True
        import psycopg2
        conn = psycopg2.connect(host='127.0.0.1', port=port, user='financial_lab', password=password, dbname='postgres')
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute('CREATE DATABASE app32_financial_concurrency_lab')
        finally:
            conn.close()
        env['APP32_FINANCIAL_LAB_URL'] = f'postgresql+psycopg2://financial_lab:{password}@127.0.0.1:{port}/app32_financial_concurrency_lab'
        code = run([sys.executable, '-m', 'pytest', 'app32/tests/test_financial_concurrency_postgresql.py',
                    '-q', '--tb=short'], 'tests.log', 150)
    finally:
        if pwfile.exists():
            pwfile.unlink()
        stopped = not started or run([str(binaries/'pg_ctl.exe'), '-D', str(cluster), '-m', 'fast', '-w', 'stop'], 'stop.log', 30) == 0
        result = {'tests_exit_code': code, 'listener_stopped': stopped, 'scope': 'local synthetic data, real financial service and models', 'evidence_dir': str(root)}
        (root/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result), flush=True)
    sys.exit(code)


if __name__ == '__main__':
    main()
