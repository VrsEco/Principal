from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import aa_j_31_cards_ssh as cards


def _card_title(stage_name: str, step_number: int, total_steps: int) -> str:
    return f'[{stage_name} - Passo {step_number} de {total_steps}]'


def _run(command: str, args: List[str]) -> Dict[str, Any]:
    return cards._run_remote(command, args)


def cmd_materialize(args: argparse.Namespace) -> None:
    total_steps = len(args.steps)
    if total_steps < 3:
        raise SystemExit('Esta automação exige 3 ou mais etapas.')

    payload = _run('list', ['--project-code', args.project_code, '--contains', args.stage_name, '--all'])
    existing_by_title = {task['title']: task for task in payload.get('tasks', [])}

    created: List[Dict[str, Any]] = []
    reused: List[Dict[str, Any]] = []
    for idx, step_description in enumerate(args.steps, start=1):
        title = _card_title(args.stage_name, idx, total_steps)
        if title in existing_by_title:
            reused.append(existing_by_title[title])
            continue
        notes = f'Passo {idx} de {total_steps}: {step_description.strip()}'
        create_args = [
            '--project-code', args.project_code,
            '--title', title,
            '--notes', notes,
            '--priority', args.priority,
        ]
        if args.due_date:
            create_args.extend(['--due-date', args.due_date])
        if args.responsible:
            create_args.extend(['--responsible', args.responsible])
        created.append(_run('create', create_args)['task'])

    result = {
        'ok': True,
        'project_code': args.project_code,
        'stage_name': args.stage_name,
        'total_steps': total_steps,
        'created': created,
        'reused': reused,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_complete_step(args: argparse.Namespace) -> None:
    if args.total_steps < 3:
        raise SystemExit('Esta automação exige 3 ou mais etapas.')
    title = _card_title(args.stage_name, args.step_number, args.total_steps)
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
        description='Wrapper operacional para materializar e concluir passos em AA.J.31.'
    )
    sub = parser.add_subparsers(dest='command', required=True)

    materialize = sub.add_parser('materialize')
    materialize.add_argument('--project-code', default='AA.J.31')
    materialize.add_argument('--stage-name', required=True)
    materialize.add_argument('--steps', nargs='+', required=True)
    materialize.add_argument('--due-date')
    materialize.add_argument('--responsible', default='Codex')
    materialize.add_argument('--priority', default='normal')
    materialize.set_defaults(func=cmd_materialize)

    complete = sub.add_parser('complete-step')
    complete.add_argument('--stage-name', required=True)
    complete.add_argument('--step-number', type=int, required=True)
    complete.add_argument('--total-steps', type=int, required=True)
    complete.add_argument('--evidence', required=True)
    complete.add_argument('--completion-date')
    complete.set_defaults(func=cmd_complete_step)

    status = sub.add_parser('status')
    status.add_argument('--project-code', default='AA.J.31')
    status.add_argument('--stage-name', required=True)
    status.set_defaults(func=cmd_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
