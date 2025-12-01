"""
Migração de dados de atividades (JSON) para tabelas normalizadas.

Uso:
    python scripts/migrate_my_work_data.py --company-id 30 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

import sqlalchemy as sa

os.environ.setdefault("FLASK_ENV", "development")
import sys

sys.path.append(os.getcwd())

from app_pev import app  # noqa: E402
from models import db  # noqa: E402
from models.employee import Employee  # noqa: E402


CompanyProject = None
ProjectActivity = None
ProcessInstanceCollaborator = None
process_instances = None


def _to_decimal(value: Optional[str]) -> Optional[Decimal]:
    if value in (None, "", "null"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _resolve_employee(company_id: int, who: Optional[str]) -> Optional[int]:
    if not who:
        return None
    who = who.strip()
    if not who:
        return None

    employee = None
    query = Employee.query.filter(
        Employee.company_id == company_id, sa.func.lower(Employee.name) == who.lower()
    )
    employee = query.first()

    if employee:
        return employee.id

    query = Employee.query.filter(
        Employee.company_id == company_id, sa.func.lower(Employee.email) == who.lower()
    )
    employee = query.first()
    return employee.id if employee else None


def _resolve_employee_for_process(
    session, company_id: Optional[int], identifier: Any
) -> Optional[int]:
    if identifier in (None, "", "null"):
        return None

    # Tentar ID direto
    try:
        candidate = int(identifier)
        row = session.execute(
            sa.text(
                "SELECT id FROM employees WHERE id = :id"
                + (" AND company_id = :company_id" if company_id else "")
            ),
            {"id": candidate, "company_id": company_id},
        ).first()
        if row:
            return candidate
    except (ValueError, TypeError):
        pass

    text_value = str(identifier).strip()
    if not text_value:
        return None

    params = {"text": text_value}
    sql = """
        SELECT id
        FROM employees
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(:text))
    """
    if company_id:
        sql += " AND company_id = :company_id"
        params["company_id"] = company_id
    row = session.execute(sa.text(sql + " LIMIT 1"), params).first()
    if row:
        return row[0]

    params = {"text": text_value}
    sql = """
        SELECT id
        FROM employees
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(:text))
    """
    if company_id:
        sql += " AND company_id = :company_id"
        params["company_id"] = company_id
    row = session.execute(sa.text(sql + " LIMIT 1"), params).first()
    return row[0] if row else None


def _upsert_project_activity(
    session,
    project_id: int,
    company_id: int,
    payload: Dict,
    dry_run: bool = False,
):
    code = payload.get("code")
    title = payload.get("what") or payload.get("title") or "Atividade"
    description = payload.get("how") or payload.get("description")
    observations = payload.get("observations")
    if observations:
        description = f"{description or ''}\n\n{observations}".strip()

    status = (payload.get("status") or "planned").lower()
    stage = payload.get("stage")
    priority = (payload.get("priority") or "normal").lower()
    deadline = _parse_date(payload.get("when") or payload.get("deadline"))
    amount = _to_decimal(payload.get("amount"))
    estimated_hours = _to_decimal(payload.get("estimated_hours"))
    worked_hours = _to_decimal(payload.get("worked_hours"))
    responsible_id = _resolve_employee(company_id, payload.get("who"))
    executor_id = responsible_id

    metadata = {
        "legacy_id": payload.get("id"),
        "logs": payload.get("logs"),
        "raw": payload,
    }

    select_stmt = sa.select(ProjectActivity.c.id).where(
        ProjectActivity.c.project_id == project_id,
        sa.or_(
            sa.and_(ProjectActivity.c.code.is_(None), code is None),
            ProjectActivity.c.code == code,
        ),
    )
    existing_id = session.execute(select_stmt).scalar()

    if existing_id:
        update_stmt = (
            ProjectActivity.update()
            .where(ProjectActivity.c.id == existing_id)
            .values(
                title=title,
                description=description,
                status=status,
                stage=stage,
                priority=priority,
                deadline=deadline,
                amount=amount,
                estimated_hours=estimated_hours or 0,
                worked_hours=worked_hours or 0,
                responsible_id=responsible_id,
                executor_id=executor_id,
                metadata=metadata,
                is_deleted=False,
            )
        )
        if not dry_run:
            session.execute(update_stmt)
        return existing_id

    insert_stmt = ProjectActivity.insert().values(
        project_id=project_id,
        code=code,
        title=title,
        description=description,
        status=status,
        stage=stage,
        priority=priority,
        deadline=deadline,
        amount=amount,
        estimated_hours=estimated_hours or 0,
        worked_hours=worked_hours or 0,
        responsible_id=responsible_id,
        executor_id=executor_id,
        metadata=metadata,
    )
    if dry_run:
        return None
    result = session.execute(insert_stmt)
    return result.inserted_primary_key[0]


def _migrate_project_activities(session, company_id: Optional[int], dry_run: bool):
    stmt = sa.select(CompanyProject)
    if company_id:
        stmt = stmt.where(CompanyProject.c.company_id == company_id)

    rows = session.execute(stmt).mappings().all()

    migrated = 0
    for project in rows:
        activities_value = project.get("activities")
        if not activities_value:
            continue
        try:
            activities = (
                json.loads(activities_value)
                if isinstance(activities_value, str)
                else activities_value
            )
        except json.JSONDecodeError:
            continue

        if not isinstance(activities, list):
            continue

        for activity in activities:
            _upsert_project_activity(
                session,
                project_id=project["id"],
                company_id=project["company_id"],
                payload=activity,
                dry_run=dry_run,
            )
            migrated += 1

    if not dry_run:
        session.commit()
    return migrated


def _migrate_process_collaborators(session, company_id: Optional[int], dry_run: bool):
    stmt = sa.select(process_instances)
    if company_id:
        stmt = stmt.where(process_instances.c.company_id == company_id)

    instances = session.execute(stmt).fetchall()
    migrated = 0

    for instance in instances:
        payload = instance.assigned_collaborators
        if not payload:
            continue

        try:
            collaborators = (
                json.loads(payload) if isinstance(payload, str) else payload
            )
        except json.JSONDecodeError:
            continue

        if not isinstance(collaborators, list):
            continue

        existing_rows = session.execute(
            sa.select(
                ProcessInstanceCollaborator.c.id,
                ProcessInstanceCollaborator.c.employee_id,
                ProcessInstanceCollaborator.c.role,
            ).where(ProcessInstanceCollaborator.c.process_instance_id == instance.id)
        ).all()
        existing_map = {
            (row.employee_id, row.role): row.id
            for row in existing_rows
            if row.employee_id
        }
        seen = set()

        primary_executor = None
        primary_responsible = None
        owner_employee = None

        for collab in collaborators:
            employee_id = _resolve_employee_for_process(
                session, instance.company_id, collab.get("id") or collab.get("name")
            )
            if not employee_id:
                continue

            hours = _to_decimal(collab.get("hours")) or Decimal("0")
            role = (collab.get("role") or "executor").lower()
            if role not in ("executor", "responsible", "owner"):
                role = "executor"

            if role == "executor" and not primary_executor:
                primary_executor = employee_id
            if role == "responsible" and not primary_responsible:
                primary_responsible = employee_id
            if role == "owner" and not owner_employee:
                owner_employee = employee_id

            key = (employee_id, role)
            values = dict(
                process_instance_id=instance.id,
                employee_id=employee_id,
                role=role,
                estimated_hours=hours,
                worked_hours=Decimal("0"),
                notes=collab.get("notes"),
                is_deleted=False,
            )

            if key in existing_map:
                seen.add(existing_map[key])
                if not dry_run:
                    session.execute(
                        ProcessInstanceCollaborator.update()
                        .where(ProcessInstanceCollaborator.c.id == existing_map[key])
                        .values(**values)
                    )
            else:
                if not dry_run:
                    result = session.execute(
                        ProcessInstanceCollaborator.insert().values(**values)
                    )
                    seen.add(result.inserted_primary_key[0])
                migrated += 1

        obsolete_ids = [
            row.id for row in existing_rows if row.id not in seen
        ]
        if obsolete_ids and not dry_run:
            session.execute(
                ProcessInstanceCollaborator.update()
                .where(ProcessInstanceCollaborator.c.id.in_(obsolete_ids))
                .values(is_deleted=True)
            )

        update_values = {}
        if primary_responsible:
            update_values["responsible_id"] = primary_responsible
        if primary_executor:
            update_values["executor_id"] = primary_executor
        if owner_employee:
            update_values["owner_employee_id"] = owner_employee

        if update_values and not dry_run:
            update_values["updated_at"] = sa.func.now()
            session.execute(
                process_instances.update()
                .where(process_instances.c.id == instance.id)
                .values(**update_values)
            )

    if not dry_run:
        session.commit()
    return migrated


def run(company_id: Optional[int], dry_run: bool):
    with app.app_context():
        global CompanyProject, ProjectActivity, ProcessInstanceCollaborator, process_instances

        metadata = sa.MetaData()
        engine = db.engine

        CompanyProject = sa.Table(
            "company_projects",
            metadata,
            autoload_with=engine,
        )
        ProjectActivity = sa.Table(
            "project_activities",
            metadata,
            autoload_with=engine,
        )
        ProcessInstanceCollaborator = sa.Table(
            "process_instance_collaborators",
            metadata,
            autoload_with=engine,
        )
        process_instances = sa.Table(
            "process_instances",
            metadata,
            autoload_with=engine,
        )

        session = db.session
        migrated_projects = _migrate_project_activities(session, company_id, dry_run)
        migrated_process_collabs = _migrate_process_collaborators(
            session, company_id, dry_run
        )
        output = {
            "dry_run": dry_run,
            "company_id": company_id,
            "project_activities": migrated_projects,
            "process_collaborators": migrated_process_collabs,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migra atividades JSON para tabelas normalizadas"
    )
    parser.add_argument("--company-id", type=int, help="Filtrar por empresa específica")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa sem gravar alterações no banco",
    )
    args = parser.parse_args()
    run(args.company_id, args.dry_run)

