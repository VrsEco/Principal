from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable


def run_step(label: str, command: list[str]) -> int:
    print(f'\n=== {label} ===')
    print('CMD:', ' '.join(command))
    result = subprocess.run(command, check=False)
    print(f'EXIT_CODE: {result.returncode}')
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description='Atalho operacional para manutenção e investigação de erros.')
    parser.add_argument('--env', default='production')
    parser.add_argument('--files', nargs='*', default=['app.py', 'api/resources/process.py', 'api/routes/my_work.py', 'templates/modules/my_work/my_work_v2.html', 'static/js/my-work.js', 'models/__init__.py'])
    parser.add_argument('--git-status', action='store_true')
    parser.add_argument('--smoke', action='store_true', help='Executa smoke_create_app.py')
    parser.add_argument('--user-id', type=int)
    parser.add_argument('--company-id', type=int)
    parser.add_argument('--object-type', choices=['process-instance', 'project-task', 'process', 'project', 'employee'])
    parser.add_argument('--object-id', type=int)
    parser.add_argument('--suggest-only', action='store_true', help='Não executa nada; apenas mostra a sequência recomendada')
    args = parser.parse_args()

    integrity_cmd = [
        PYTHON,
        str(SCRIPT_DIR / 'integrity_snapshot.py'),
        '--files',
        *args.files,
    ]
    if args.git_status:
        integrity_cmd.append('--git-status')

    smoke_cmd = [
        PYTHON,
        str(SCRIPT_DIR / 'smoke_create_app.py'),
        '--env',
        args.env,
    ]

    tenant_ready = all([
        args.user_id is not None,
        args.company_id is not None,
        args.object_type is not None,
        args.object_id is not None,
    ])
    tenant_cmd = [
        PYTHON,
        str(SCRIPT_DIR / 'tenant_audit.py'),
        '--env',
        args.env,
        '--user-id',
        str(args.user_id or ''),
        '--company-id',
        str(args.company_id or ''),
        '--object-type',
        str(args.object_type or ''),
        '--object-id',
        str(args.object_id or ''),
    ]

    print('### Gestão Versus - Manutenção de Erro ###')
    print('Sequência recomendada:')
    print('1. Snapshot de integridade local')
    print('2. Smoke de boot da aplicação')
    print('3. Auditoria de tenant/contexto')
    print('4. Se necessário: prod_file_probe.py e prod_request_probe.py')

    print('\nComandos sugeridos:')
    print(' -', ' '.join(integrity_cmd))
    print(' -', ' '.join(smoke_cmd))
    if tenant_ready:
        print(' -', ' '.join(tenant_cmd))
    else:
        print(' - tenant_audit.py requer --user-id --company-id --object-type --object-id')

    if args.suggest_only:
        return 0

    exit_codes = []
    exit_codes.append(run_step('INTEGRITY SNAPSHOT', integrity_cmd))

    if args.smoke:
        exit_codes.append(run_step('SMOKE CREATE_APP', smoke_cmd))

    if tenant_ready:
        exit_codes.append(run_step('TENANT AUDIT', tenant_cmd))

    failed = [code for code in exit_codes if code != 0]
    if failed:
        print('\n[RESULT] Há falhas nos checks iniciais. Priorize ambiente/runtime/tenant antes de editar código.')
        return 1

    print('\n[RESULT] Checks iniciais concluídos sem falha. Se o bug persistir, avance para contrato HTTP e probes de produção.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
