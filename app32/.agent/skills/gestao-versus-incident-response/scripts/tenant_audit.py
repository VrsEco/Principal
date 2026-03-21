from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _resolve_model_and_fields(object_type: str):
    from models import ProcessInstance, ProjectTask, Process, Project, Employee

    mapping = {
        'process-instance': (ProcessInstance, ['id', 'company_id', 'process_id', 'status', 'executor_id', 'responsible_id', 'owner_employee_id']),
        'project-task': (ProjectTask, ['id', 'project_id', 'responsible_id', 'executor_id', 'status']),
        'process': (Process, ['id', 'company_id', 'macro_id', 'name']),
        'project': (Project, ['id', 'company_id', 'title', 'status']),
        'employee': (Employee, ['id', 'company_id', 'user_id', 'name']),
    }
    return mapping[object_type]


def _dump_fields(obj, fields: list[str]) -> dict:
    data = {}
    for field in fields:
        value = getattr(obj, field, None)
        if hasattr(value, 'isoformat'):
            try:
                value = value.isoformat()
            except Exception:
                value = str(value)
        data[field] = value
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description='Auditoria objetiva de tenant/contexto para incidentes.')
    parser.add_argument('--env', default='production')
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--company-id', type=int, required=True)
    parser.add_argument('--object-type', choices=['process-instance', 'project-task', 'process', 'project', 'employee'], required=True)
    parser.add_argument('--object-id', type=int, required=True)
    args = parser.parse_args()

    from app import create_app
    from models import Employee, User
    from utils.permissions import can_access_company, has_permission

    app = create_app(args.env)
    with app.app_context():
        user = User.query.get(args.user_id)
        if not user:
            print(json.dumps({'error': f'user {args.user_id} não encontrado'}, ensure_ascii=False, indent=2))
            return 1

        employee = Employee.query.filter_by(user_id=args.user_id, company_id=args.company_id).first()
        model, fields = _resolve_model_and_fields(args.object_type)
        obj = model.query.get(args.object_id)

        payload = {
            'user': {
                'id': user.id,
                'email': getattr(user, 'email', None),
                'role': getattr(user, 'role', None),
            },
            'company_id': args.company_id,
            'object_type': args.object_type,
            'object_id': args.object_id,
            'user_can_access_company': can_access_company(args.company_id),
            'permissions': {
                'processes_view': has_permission(args.company_id, 'processes', 'view'),
                'processes_edit': has_permission(args.company_id, 'processes', 'edit'),
                'projects_view': has_permission(args.company_id, 'projects', 'view'),
                'projects_edit': has_permission(args.company_id, 'projects', 'edit'),
            },
            'employee_in_company': _dump_fields(employee, ['id', 'company_id', 'user_id', 'name']) if employee else None,
            'target_object': _dump_fields(obj, fields) if obj else None,
        }

        if obj is not None and hasattr(obj, 'company_id'):
            payload['object_company_matches_requested_company'] = getattr(obj, 'company_id', None) == args.company_id

        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
