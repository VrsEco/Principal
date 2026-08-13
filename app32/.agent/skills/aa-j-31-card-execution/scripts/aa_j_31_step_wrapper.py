from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

import aa_j_31_cards_ssh as cards


def _card_title(stage_name: str) -> str:
    return f'[{stage_name}]'


def _checklist(steps: List[str], completed_step: int = 0, evidence: str | None = None) -> str:
    lines = ['Checklist da entrega:']
    for idx, description in enumerate(steps, start=1):
        marker = 'x' if idx <= completed_step else ' '
        lines.append(f'- [{marker}] Passo {idx} de {len(steps)}: {description.strip()}')
    if evidence:
        lines.extend(['', 'Evidências:', f'- Passo {completed_step}: {evidence.strip()}'])
    return '\n'.join(lines)


def _run(command: str, args: List[str]) -> Dict[str, Any]:
    return cards._run_remote(command, args)


def cmd_materialize(args: argparse.Namespace) -> None:
    total_steps = len(args.steps)
    if total_steps < 3:
        raise SystemExit('Esta automação exige 3 ou mais etapas.')

    payload = _run('list', ['--project-code', args.project_code, '--contains', args.stage_name, '--all'])
    title = _card_title(args.stage_name)
    existing_by_title = {task['title']: task for task in payload.get('tasks', [])}
    created: List[Dict[str, Any]] = []
    reused: List[Dict[str, Any]] = []

    if title in existing_by_title:
        reused.append(existing_by_title[title])
    else:
        create_args = [
            '--project-code', args.project_code,
            '--title', title,
            '--notes', _checklist(args.steps),
            '--priority', args.priority,
        ]
        if args.due_date:
            create_args.extend(['--due-date', args.due_date])
        if args.responsible:
            create_args.extend(['--responsible', args.responsible])
        created.append(_run('create', create_args)['task'])

    print(json.dumps({
        'ok': True,
        'project_code': args.project_code,
        'stage_name': args.stage_name,
        'total_steps': total_steps,
        'created': created,
        'reused': reused,
    }, ensure_ascii=False, indent=2))


def cmd_complete_step(args: argparse.Namespace) -> None:
    if args.total_steps < 3:
        raise SystemExit('Esta automação exige 3 ou mais etapas.')
    if len(args.steps) != args.total_steps:
        raise SystemExit('--steps deve conter exatamente total-steps itens.')
    if not 1 <= args.step_number <= args.total_steps:
        raise SystemExit('step-number fora do intervalo da entrega.')

    title = _card_title(args.stage_name)
    notes = _checklist(args.steps, completed_step=args.step_number, evidence=args.evidence)
    payload = _run('update-notes', ['--identifier', title, '--notes', notes])
    if args.step_number == args.total_steps:
        cli_args = ['--identifier', title, '--evidence', args.evidence]
        if args.completion_date:
            cli_args.extend(['--completion-date', args.completion_date])
        payload = _run('complete', cli_args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_status(args: argparse.Namespace) -> None:
    payload = _run('list', ['--project-code', args.project_code, '--contains', args.stage_name, '--all'])
    tasks = payload.get('tasks', [])
    tasks.sort(key=lambda item: item.get('task_id') or 0)
    print(json.dumps({
        'ok': True,
        'project': payload.get('project'),
        'stage_name': args.stage_name,
        'tasks': tasks,
    }, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Wrapper operacional para manter um card por entrega com checklist.'
    )
    sub = parser.add_subparsers(dest='command', required=True)

    materialize = sub.add_parser('materialize')
    materialize.add_argument('--project-code', default='AA.ENGINEERING.CURRENT')
    materialize.add_argument('--stage-name', required=True)
    materialize.add_argument('--steps', nargs='+', required=True)
    materialize.add_argument('--due-date')
    materialize.add_argument('--responsible', default='Codex')
    materialize.add_argument('--priority', default='normal')
    materialize.set_defaults(func=cmd_materialize)

    complete = sub.add_parser('complete-step')
    complete.add_argument('--project-code', default='AA.ENGINEERING.CURRENT')
    complete.add_argument('--stage-name', required=True)
    complete.add_argument('--step-number', type=int, required=True)
    complete.add_argument('--total-steps', type=int, required=True)
    complete.add_argument('--steps', nargs='+', required=True)
    complete.add_argument('--evidence', required=True)
    complete.add_argument('--completion-date')
    complete.set_defaults(func=cmd_complete_step)

    status = sub.add_parser('status')
    status.add_argument('--project-code', default='AA.ENGINEERING.CURRENT')
    status.add_argument('--stage-name', required=True)
    status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
