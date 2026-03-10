import os
import sys
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
os.environ.setdefault('FLASK_CONFIG', 'production')

from sqlalchemy import func
from app import create_app
from models import db
from models.activity_work_log import ActivityWorkLog
from models.project import Project, ProjectTask, ProjectActivityCollaborator, ProjectTaskHoursSummary
from models.employee import Employee

app = create_app('production')
entries = [
    {
        'task_id': 195,
        'employee_id': 23,
        'hours': Decimal('1.0'),
        'description': 'DEV APP Gestão Versus - Fase 6 - fechamento do fluxo de rejeição e auditoria conversacional [commit 2829a50a][Fabiano]',
    },
    {
        'task_id': 195,
        'employee_id': 45,
        'hours': Decimal('1.0'),
        'description': 'DEV APP Gestão Versus - Fase 6 - implementação da rejeição operacional e logging conversacional [commit 2829a50a][Codex]',
    },
    {
        'task_id': 196,
        'employee_id': 23,
        'hours': Decimal('0.5'),
        'description': 'DEV APP Gestão Versus - Fase 7 - validação e deploy do fechamento da Fase 6 [commit 2829a50a][Fabiano]',
    },
    {
        'task_id': 196,
        'employee_id': 45,
        'hours': Decimal('0.5'),
        'description': 'DEV APP Gestão Versus - Fase 7 - testes, deploy e validação do fluxo de rejeição [commit 2829a50a][Codex]',
    },
]

with app.app_context():
    project = db.session.get(Project, 31)
    affected_tasks = set()
    created = []
    skipped = []

    for entry in entries:
        task = db.session.get(ProjectTask, entry['task_id'])
        employee = db.session.get(Employee, entry['employee_id'])
        if not task or not employee:
            raise RuntimeError(f"Task/employee invalido: {entry}")

        existing = ActivityWorkLog.query.filter_by(
            activity_type='project',
            activity_id=entry['task_id'],
            employee_id=entry['employee_id'],
            description=entry['description'],
        ).first()
        if existing:
            skipped.append(existing.id)
            affected_tasks.add(task.id)
            continue

        log = ActivityWorkLog(
            activity_type='project',
            activity_id=entry['task_id'],
            employee_id=entry['employee_id'],
            employee_name=employee.name,
            work_date=date.today(),
            hours_worked=entry['hours'],
            description=entry['description'],
            created_at=datetime.utcnow(),
        )
        db.session.add(log)
        db.session.flush()
        created.append(log.id)
        affected_tasks.add(task.id)

    for task_id in affected_tasks:
        task = db.session.get(ProjectTask, task_id)
        total_hours = (
            db.session.query(func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0))
            .filter(
                ActivityWorkLog.activity_type == 'project',
                ActivityWorkLog.activity_id == task_id,
            )
            .scalar()
        ) or Decimal('0')
        task.worked_hours = total_hours

        summary = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
        if not summary:
            summary = ProjectTaskHoursSummary(
                task_id=task_id,
                total_estimated_hours=task.estimated_hours or Decimal('0'),
                total_worked_hours=total_hours,
            )
            db.session.add(summary)
        else:
            summary.total_estimated_hours = task.estimated_hours or Decimal('0')
            summary.total_worked_hours = total_hours

        employee_totals = (
            db.session.query(
                ActivityWorkLog.employee_id,
                func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0),
            )
            .filter(
                ActivityWorkLog.activity_type == 'project',
                ActivityWorkLog.activity_id == task_id,
            )
            .group_by(ActivityWorkLog.employee_id)
            .all()
        )
        totals_map = {employee_id: hours for employee_id, hours in employee_totals}
        for employee_id, employee_hours in totals_map.items():
            collaborator = ProjectActivityCollaborator.query.filter(
                ProjectActivityCollaborator.activity_id == task_id,
                ProjectActivityCollaborator.employee_id == employee_id,
                ProjectActivityCollaborator.is_deleted.is_(False),
            ).first()
            if not collaborator:
                collaborator = ProjectActivityCollaborator(
                    activity_id=task_id,
                    employee_id=employee_id,
                    role='executor',
                    estimated_hours=Decimal('0'),
                    worked_hours=employee_hours,
                    notes='Criado/sincronizado automaticamente no apontamento do projeto DEV APP Gestão Versus.',
                )
                db.session.add(collaborator)
            else:
                collaborator.worked_hours = employee_hours

    phase6 = db.session.get(ProjectTask, 195)
    if phase6.stage != 'completed':
        phase6.stage = 'completed'
    if phase6.status != 'completed':
        phase6.status = 'completed'
    if not phase6.completion_date:
        phase6.completion_date = date.today()
    note = 'Fase 6 concluída em 08/03/2026: hardening do contexto, policy guard, approval gating, rejeição operacional e retomada segura pós-aprovação implantados.'
    if note not in (phase6.notes or ''):
        phase6.notes = ((phase6.notes or '').strip() + ('\n\n' if phase6.notes else '') + note).strip()

    if project:
        project.update_progress()
        project.status = 'in_progress'

    db.session.commit()
    print(f'CREATED_LOG_IDS={created}')
    print(f'SKIPPED_LOG_IDS={skipped}')
    for task_id in sorted(affected_tasks):
        task = db.session.get(ProjectTask, task_id)
        summary = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
        print(f'TASK_{task_id}_HOURS={float(task.worked_hours or 0):.2f}')
        print(f'TASK_{task_id}_SUMMARY={float(summary.total_worked_hours or 0):.2f}')
    print(f'PHASE6={(phase6.stage, phase6.status, str(phase6.completion_date), float(phase6.worked_hours or 0))}')
    print(f'PROJECT={(project.id, project.progress, project.status)}')
