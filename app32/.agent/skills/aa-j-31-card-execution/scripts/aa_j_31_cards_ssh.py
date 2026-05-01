from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app32.scripts.deploy.configr_remote_helper import APP_DIR, BASE_DIR, connect_ssh, run_command

DEFAULT_PROJECT_CODE = 'AA.J.31'
DEFAULT_COMPANY_CODE = 'AA'
DEFAULT_RESPONSIBLE = 'Codex'
REMOTE_PYTHON = f"{BASE_DIR}/.virtualenv/3.12/bin/python"


class RemoteExecutionError(RuntimeError):
    pass


def _default_key_path() -> Path:
    return Path(__file__).resolve().parents[4] / '.codex_temp_deploy_key'


def _ensure_key_env() -> None:
    if os.environ.get('GV_DEPLOY_KEY_PATH'):
        return
    candidate = _default_key_path()
    if candidate.exists():
        os.environ['GV_DEPLOY_KEY_PATH'] = str(candidate)


def _build_remote_script() -> str:
    return r'''
import argparse
import json
from datetime import datetime, date

from app import create_app
from models import db
from models.company import Company
from models.project import Project, ProjectTask

DEFAULT_PROJECT_CODE = "AA.J.31"
DEFAULT_COMPANY_CODE = "AA"
DEFAULT_RESPONSIBLE = "Codex"


def parse_due_date(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError("Data inválida. Use YYYY-MM-DD ou DD/MM/YYYY.")


def extract_id(code_or_id: str):
    raw = str(code_or_id or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return int(raw)
    parts = [p for p in raw.replace('[', '.').replace(']', '.').split('.') if p.isdigit()]
    if parts:
        return int(parts[-1])
    return None


def resolve_project(project_code: str):
    project_id = extract_id(project_code)
    if project_id:
        project = Project.query.filter(Project.id == project_id).first()
        if project:
            return project
    company_code = (project_code or DEFAULT_PROJECT_CODE).split('.J.')[0].strip().upper()
    return (
        Project.query.join(Company, Company.id == Project.company_id)
        .filter(Project.id == 31 if project_code == DEFAULT_PROJECT_CODE else True)
        .filter(Company.client_code == company_code)
        .order_by(Project.id.asc())
        .first()
    )


def project_payload(project):
    company = Company.query.get(project.company_id)
    return {
        'project_id': project.id,
        'project_code': project.code,
        'project_name': project.name,
        'company_id': project.company_id,
        'company_code': getattr(company, 'client_code', None),
        'company_name': getattr(company, 'name', None),
    }


def task_payload(task):
    return {
        'task_id': task.id,
        'task_code': task.code if getattr(task, 'id', None) else None,
        'project_id': task.project_id,
        'title': task.what,
        'responsible': task.who,
        'status': task.status,
        'stage': task.stage,
        'priority': task.priority,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'completion_date': task.completion_date.isoformat() if task.completion_date else None,
        'notes': task.notes,
    }


def list_tasks(project_code: str, open_only: bool, contains: str | None):
    project = resolve_project(project_code)
    if not project:
        return {'ok': False, 'error': f'Projeto {project_code} não encontrado.'}
    query = ProjectTask.query.filter(ProjectTask.project_id == project.id)
    if open_only:
        query = query.filter(ProjectTask.stage != 'completed')
    if contains:
        query = query.filter(ProjectTask.what.ilike(f'%{contains}%'))
    tasks = query.order_by(ProjectTask.id.asc()).all()
    return {'ok': True, 'project': project_payload(project), 'tasks': [task_payload(t) for t in tasks]}


def create_task(project_code: str, title: str, due_date_raw: str | None, responsible: str | None, notes: str | None, priority: str, dry_run: bool):
    project = resolve_project(project_code)
    if not project:
        return {'ok': False, 'error': f'Projeto {project_code} não encontrado.'}
    parsed_due_date = parse_due_date(due_date_raw)
    task = ProjectTask(
        project_id=project.id,
        what=title.strip(),
        who=(responsible or DEFAULT_RESPONSIBLE).strip(),
        due_date=parsed_due_date,
        status='planned',
        stage='inbox',
        priority=(priority or 'normal').strip() or 'normal',
        notes=(notes or '').strip() or None,
    )
    if dry_run:
        return {'ok': True, 'dry_run': True, 'project': project_payload(project), 'task': task_payload(task)}
    db.session.add(task)
    db.session.flush()
    project.update_progress()
    db.session.commit()
    return {'ok': True, 'project': project_payload(project), 'task': task_payload(task)}


def complete_task(identifier: str, completion_date_raw: str | None, evidence: str | None, dry_run: bool):
    task_id = extract_id(identifier)
    task = None
    if task_id:
        task = ProjectTask.query.filter(ProjectTask.id == task_id).first()
    if task is None:
        task = ProjectTask.query.filter(ProjectTask.what == identifier).order_by(ProjectTask.id.desc()).first()
    if not task:
        return {'ok': False, 'error': f'Atividade {identifier} não encontrada.'}
    final_date = parse_due_date(completion_date_raw) or date.today()
    current_notes = (task.notes or '').strip()
    evidence_text = (evidence or '').strip()
    merged_notes = current_notes
    if evidence_text:
        merged_notes = f"{current_notes}\n\nConclusão: {evidence_text}".strip() if current_notes else f"Conclusão: {evidence_text}"
    updated = task_payload(task)
    updated['completion_date'] = final_date.isoformat()
    updated['status'] = 'completed'
    updated['stage'] = 'completed'
    updated['notes'] = merged_notes or None
    if dry_run:
        return {'ok': True, 'dry_run': True, 'task': updated}
    task.status = 'completed'
    task.stage = 'completed'
    task.completion_date = final_date
    task.notes = merged_notes or None
    if task.project:
        task.project.update_progress()
    db.session.commit()
    return {'ok': True, 'task': task_payload(task)}


def ensure_steps(project_code: str, stage_name: str, total_steps: int, titles: list[str], due_date_raw: str | None, responsible: str | None, dry_run: bool):
    project = resolve_project(project_code)
    if not project:
        return {'ok': False, 'error': f'Projeto {project_code} não encontrado.'}
    parsed_due_date = parse_due_date(due_date_raw)
    expected_titles = titles or [f'[{stage_name} - Passo {idx} de {total_steps}]' for idx in range(1, total_steps + 1)]
    existing = {
        row.what: row
        for row in ProjectTask.query.filter(ProjectTask.project_id == project.id, ProjectTask.what.in_(expected_titles)).all()
    }
    created = []
    reused = []
    for title in expected_titles:
        if title in existing:
            reused.append(task_payload(existing[title]))
            continue
        task = ProjectTask(
            project_id=project.id,
            what=title,
            who=(responsible or DEFAULT_RESPONSIBLE).strip(),
            due_date=parsed_due_date,
            status='planned',
            stage='inbox',
            priority='normal',
        )
        if dry_run:
            created.append(task_payload(task))
        else:
            db.session.add(task)
            db.session.flush()
            created.append(task_payload(task))
    if not dry_run and created:
        project.update_progress()
        db.session.commit()
    return {
        'ok': True,
        'project': project_payload(project),
        'created': created,
        'existing': reused,
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)

    list_parser = sub.add_parser('list')
    list_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    list_parser.add_argument('--contains')
    list_parser.add_argument('--all', action='store_true')

    create_parser = sub.add_parser('create')
    create_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    create_parser.add_argument('--title', required=True)
    create_parser.add_argument('--due-date')
    create_parser.add_argument('--responsible')
    create_parser.add_argument('--notes')
    create_parser.add_argument('--priority', default='normal')
    create_parser.add_argument('--dry-run', action='store_true')

    complete_parser = sub.add_parser('complete')
    complete_parser.add_argument('--identifier', required=True)
    complete_parser.add_argument('--completion-date')
    complete_parser.add_argument('--evidence')
    complete_parser.add_argument('--dry-run', action='store_true')

    ensure_parser = sub.add_parser('ensure-steps')
    ensure_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    ensure_parser.add_argument('--stage-name', required=True)
    ensure_parser.add_argument('--total-steps', type=int, required=True)
    ensure_parser.add_argument('--titles', nargs='*')
    ensure_parser.add_argument('--due-date')
    ensure_parser.add_argument('--responsible')
    ensure_parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    app = create_app('production')
    with app.app_context():
        if args.command == 'list':
            payload = list_tasks(args.project_code, open_only=not args.all, contains=args.contains)
        elif args.command == 'create':
            payload = create_task(args.project_code, args.title, args.due_date, args.responsible, args.notes, args.priority, args.dry_run)
        elif args.command == 'complete':
            payload = complete_task(args.identifier, args.completion_date, args.evidence, args.dry_run)
        elif args.command == 'ensure-steps':
            payload = ensure_steps(args.project_code, args.stage_name, args.total_steps, args.titles or [], args.due_date, args.responsible, args.dry_run)
        else:
            payload = {'ok': False, 'error': f'Comando inválido: {args.command}'}

    print(json.dumps(payload, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
'''


def _run_remote(command: str, args: List[str]) -> Dict[str, Any]:
    _ensure_key_env()
    remote_script = _build_remote_script()
    quoted_script = shlex.quote(remote_script)
    quoted_args = ' '.join(shlex.quote(arg) for arg in args)
    remote_command = (
        f"cd {APP_DIR} && {REMOTE_PYTHON} -c {quoted_script} {shlex.quote(command)} {quoted_args}"
    )
    ssh = connect_ssh()
    try:
        code, out, err = run_command(ssh, remote_command)
    finally:
        ssh.close()
    if code != 0:
        raise RemoteExecutionError(err or out or f'Falha remota sem saída útil. Código={code}')
    output = (out or '').strip()
    if not output:
        raise RemoteExecutionError('A execução remota não retornou payload JSON.')
    last_line = output.splitlines()[-1]
    return json.loads(last_line)


def cmd_list(args: argparse.Namespace) -> None:
    payload = _run_remote('list', [
        '--project-code', args.project_code,
        *(['--contains', args.contains] if args.contains else []),
        *( ['--all'] if args.all else []),
    ])
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_create(args: argparse.Namespace) -> None:
    payload = _run_remote('create', [
        '--project-code', args.project_code,
        '--title', args.title,
        *(['--due-date', args.due_date] if args.due_date else []),
        *(['--responsible', args.responsible] if args.responsible else []),
        *(['--notes', args.notes] if args.notes else []),
        '--priority', args.priority,
        *( ['--dry-run'] if args.dry_run else []),
    ])
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_complete(args: argparse.Namespace) -> None:
    payload = _run_remote('complete', [
        '--identifier', args.identifier,
        *(['--completion-date', args.completion_date] if args.completion_date else []),
        *(['--evidence', args.evidence] if args.evidence else []),
        *( ['--dry-run'] if args.dry_run else []),
    ])
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_ensure_steps(args: argparse.Namespace) -> None:
    cli_args: List[str] = [
        '--project-code', args.project_code,
        '--stage-name', args.stage_name,
        '--total-steps', str(args.total_steps),
    ]
    if args.titles:
        cli_args.append('--titles')
        cli_args.extend(args.titles)
    if args.due_date:
        cli_args.extend(['--due-date', args.due_date])
    if args.responsible:
        cli_args.extend(['--responsible', args.responsible])
    if args.dry_run:
        cli_args.append('--dry-run')
    payload = _run_remote('ensure-steps', cli_args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
parser = argparse.ArgumentParser(description='Opera cards do projeto AA.J.1 via SSH no app Gestão Versus.')
    sub = parser.add_subparsers(dest='command', required=True)

    list_parser = sub.add_parser('list')
    list_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    list_parser.add_argument('--contains')
    list_parser.add_argument('--all', action='store_true')
    list_parser.set_defaults(func=cmd_list)

    create_parser = sub.add_parser('create')
    create_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    create_parser.add_argument('--title', required=True)
    create_parser.add_argument('--due-date')
    create_parser.add_argument('--responsible')
    create_parser.add_argument('--notes')
    create_parser.add_argument('--priority', default='normal')
    create_parser.add_argument('--dry-run', action='store_true')
    create_parser.set_defaults(func=cmd_create)

    complete_parser = sub.add_parser('complete')
    complete_parser.add_argument('--identifier', required=True)
    complete_parser.add_argument('--completion-date')
    complete_parser.add_argument('--evidence')
    complete_parser.add_argument('--dry-run', action='store_true')
    complete_parser.set_defaults(func=cmd_complete)

    ensure_parser = sub.add_parser('ensure-steps')
    ensure_parser.add_argument('--project-code', default=DEFAULT_PROJECT_CODE)
    ensure_parser.add_argument('--stage-name', required=True)
    ensure_parser.add_argument('--total-steps', type=int, required=True)
    ensure_parser.add_argument('--titles', nargs='*')
    ensure_parser.add_argument('--due-date')
    ensure_parser.add_argument('--responsible')
    ensure_parser.add_argument('--dry-run', action='store_true')
    ensure_parser.set_defaults(func=cmd_ensure_steps)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
