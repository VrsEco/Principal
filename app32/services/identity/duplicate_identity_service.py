from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, inspect

from models import db
from models.employee import Employee
from models.meeting import Meeting
from models.occurrence import Occurrence
from models.process import ProcessInstance
from models.user import User
from models.user_employee_assignment import UserEmployeeAssignment
from services.identity.identity_normalizer import (
    normalize_email,
    normalize_name,
    normalize_phone,
)


EMPLOYEE_JSON_COLUMNS = {
    "occurrences": ("collaborators_ids",),
    "process_instances": ("collaborators_json",),
    "meetings": (
        "guests_json",
        "participants_json",
        "discussions_json",
        "activities_json",
    ),
}


@dataclass
class MergeSummary:
    entity_type: str
    keep_id: int
    merge_id: int
    company_id: int | None = None
    updated_references: dict[str, int] | None = None
    json_updates: dict[str, int] | None = None
    dry_run: bool = True
    deactivated: bool = False
    deduplicated_rows: dict[str, int] | None = None
    field_updates: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "keep_id": self.keep_id,
            "merge_id": self.merge_id,
            "company_id": self.company_id,
            "updated_references": dict(self.updated_references or {}),
            "json_updates": dict(self.json_updates or {}),
            "dry_run": self.dry_run,
            "deactivated": self.deactivated,
            "deduplicated_rows": dict(self.deduplicated_rows or {}),
            "field_updates": list(self.field_updates or []),
        }


class DuplicateIdentityService:
    """Auditoria e merge seguro de usuários/colaboradores duplicados."""

    @staticmethod
    def audit_duplicate_users() -> list[dict[str, Any]]:
        grouped: dict[str, list[User]] = defaultdict(list)
        for user in User.query.order_by(User.id.asc()).all():
            key = normalize_email(user.email)
            if key:
                grouped[key].append(user)

        duplicates = []
        for normalized_email, users in grouped.items():
            if len(users) < 2:
                continue
            duplicates.append(
                {
                    "normalized_email": normalized_email,
                    "count": len(users),
                    "users": [
                        {
                            "id": user.id,
                            "email": user.email,
                            "name": user.name,
                            "is_active": bool(getattr(user, "is_active", True)),
                            "company_ids": [
                                employee.company_id
                                for employee in Employee.query.filter_by(user_id=user.id).all()
                            ],
                        }
                        for user in users
                    ],
                }
            )
        return duplicates

    @staticmethod
    def audit_duplicate_employees(company_id: int | None = None) -> list[dict[str, Any]]:
        query = Employee.query.order_by(Employee.company_id.asc(), Employee.id.asc())
        if company_id is not None:
            query = query.filter_by(company_id=company_id)
        employees = query.all()

        grouped_by_email: dict[tuple[int, str], list[Employee]] = defaultdict(list)
        grouped_by_name_phone: dict[tuple[int, str, str], list[Employee]] = defaultdict(list)

        for employee in employees:
            email_key = normalize_email(employee.email)
            if email_key:
                grouped_by_email[(employee.company_id, email_key)].append(employee)
            else:
                name_key = normalize_name(employee.name)
                phone_key = normalize_phone(employee.phone or employee.whatsapp)
                if name_key and phone_key:
                    grouped_by_name_phone[(employee.company_id, name_key, phone_key)].append(employee)

        duplicates: list[dict[str, Any]] = []
        for (company_key, normalized_email), items in grouped_by_email.items():
            if len(items) < 2:
                continue
            duplicates.append(
                {
                    "company_id": company_key,
                    "strategy": "email",
                    "normalized_email": normalized_email,
                    "count": len(items),
                    "employees": [DuplicateIdentityService._employee_snapshot(item) for item in items],
                }
            )
        for (company_key, normalized_name, normalized_phone), items in grouped_by_name_phone.items():
            if len(items) < 2:
                continue
            duplicates.append(
                {
                    "company_id": company_key,
                    "strategy": "name_phone",
                    "normalized_name": normalized_name,
                    "normalized_phone": normalized_phone,
                    "count": len(items),
                    "employees": [DuplicateIdentityService._employee_snapshot(item) for item in items],
                }
            )
        return duplicates

    @staticmethod
    def _validate_user_merge_conflicts(*, keep_user_id: int, merge_user_id: int) -> str | None:
        keep_employees = Employee.query.filter_by(user_id=keep_user_id).all()
        merge_employees = Employee.query.filter_by(user_id=merge_user_id).all()
        keep_by_company = {employee.company_id: employee for employee in keep_employees}
        for employee in merge_employees:
            existing = keep_by_company.get(employee.company_id)
            if existing and existing.id != employee.id:
                return (
                    "Conflito: os dois usuários possuem colaboradores diferentes na empresa "
                    f"{employee.company_id}. Faça o merge de colaboradores antes do merge de usuários."
                )
        return None

    @staticmethod
    def merge_users(*, keep_user_id: int, merge_user_id: int, dry_run: bool = True) -> dict[str, Any]:
        if keep_user_id == merge_user_id:
            return {"success": False, "error": "keep_user_id e merge_user_id devem ser diferentes"}

        keep_user = User.query.get(keep_user_id)
        merge_user = User.query.get(merge_user_id)
        if not keep_user or not merge_user:
            return {"success": False, "error": "Usuário principal ou duplicado não encontrado"}
        conflict_message = DuplicateIdentityService._validate_user_merge_conflicts(
            keep_user_id=keep_user_id,
            merge_user_id=merge_user_id,
        )
        if conflict_message:
            return {"success": False, "error": conflict_message}

        summary = MergeSummary(
            entity_type="user",
            keep_id=keep_user_id,
            merge_id=merge_user_id,
            dry_run=dry_run,
            updated_references={},
            json_updates={},
            deduplicated_rows={},
            field_updates=[],
        )

        try:
            ref_counts = DuplicateIdentityService._update_foreign_keys(
                target_table_name="users",
                keep_id=keep_user_id,
                merge_id=merge_user_id,
                dry_run=dry_run,
                skip_tables={"users"},
            )
            summary.updated_references.update(ref_counts)

            dedup_counts = DuplicateIdentityService._deduplicate_user_assignments(
                keep_user_id=keep_user_id,
                merge_user_id=merge_user_id,
                dry_run=dry_run,
            )
            summary.deduplicated_rows.update(dedup_counts)

            field_updates = DuplicateIdentityService._merge_user_fields(
                keep_user=keep_user,
                merge_user=merge_user,
                dry_run=dry_run,
            )
            summary.field_updates.extend(field_updates)

            if not dry_run:
                merge_user.is_active = False
                merge_user.email = f"merged+user-{merge_user.id}__{merge_user.email}"
                summary.deactivated = True
                db.session.commit()
            else:
                db.session.rollback()

            return {"success": True, "summary": summary.to_dict()}
        except Exception as exc:
            db.session.rollback()
            return {"success": False, "error": str(exc)}

    @staticmethod
    def merge_employees(
        *,
        company_id: int,
        keep_employee_id: int,
        merge_employee_id: int,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        if keep_employee_id == merge_employee_id:
            return {"success": False, "error": "keep_employee_id e merge_employee_id devem ser diferentes"}

        keep_employee = Employee.query.filter_by(id=keep_employee_id, company_id=company_id).first()
        merge_employee = Employee.query.filter_by(id=merge_employee_id, company_id=company_id).first()
        if not keep_employee or not merge_employee:
            return {"success": False, "error": "Colaborador principal ou duplicado não encontrado na empresa"}

        if keep_employee.user_id and merge_employee.user_id and keep_employee.user_id != merge_employee.user_id:
            return {
                "success": False,
                "error": (
                    "Conflito: ambos os colaboradores possuem usuários diferentes vinculados. "
                    "Unifique os usuários antes do merge de colaboradores."
                ),
            }

        summary = MergeSummary(
            entity_type="employee",
            keep_id=keep_employee_id,
            merge_id=merge_employee_id,
            company_id=company_id,
            dry_run=dry_run,
            updated_references={},
            json_updates={},
            deduplicated_rows={},
            field_updates=[],
        )

        try:
            ref_counts = DuplicateIdentityService._update_foreign_keys(
                target_table_name="employees",
                keep_id=keep_employee_id,
                merge_id=merge_employee_id,
                dry_run=dry_run,
                skip_tables={"employees"},
            )
            summary.updated_references.update(ref_counts)

            json_counts = DuplicateIdentityService._update_employee_json_references(
                keep_employee_id=keep_employee_id,
                merge_employee_id=merge_employee_id,
                company_id=company_id,
                dry_run=dry_run,
            )
            summary.json_updates.update(json_counts)

            dedup_counts = DuplicateIdentityService._deduplicate_employee_rows(
                keep_employee_id=keep_employee_id,
                merge_employee_id=merge_employee_id,
                dry_run=dry_run,
            )
            summary.deduplicated_rows.update(dedup_counts)

            field_updates = DuplicateIdentityService._merge_employee_fields(
                keep_employee=keep_employee,
                merge_employee=merge_employee,
                dry_run=dry_run,
            )
            summary.field_updates.extend(field_updates)

            if not dry_run:
                merge_employee.user_id = None
                merge_employee.status = "inactive"
                if merge_employee.email and normalize_email(merge_employee.email) == normalize_email(keep_employee.email):
                    merge_employee.email = (
                        f"merged+employee-{merge_employee.id}__{merge_employee.email}"
                    )
                summary.deactivated = True
                db.session.commit()
            else:
                db.session.rollback()

            return {"success": True, "summary": summary.to_dict()}
        except Exception as exc:
            db.session.rollback()
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _employee_snapshot(employee: Employee) -> dict[str, Any]:
        return {
            "id": employee.id,
            "company_id": employee.company_id,
            "user_id": employee.user_id,
            "name": employee.name,
            "email": employee.email,
            "phone": employee.phone,
            "whatsapp": employee.whatsapp,
            "status": employee.status,
        }

    @staticmethod
    def _update_foreign_keys(
        *,
        target_table_name: str,
        keep_id: int,
        merge_id: int,
        dry_run: bool,
        skip_tables: set[str] | None = None,
    ) -> dict[str, int]:
        inspector = inspect(db.engine)
        skip_tables = set(skip_tables or set())
        updated: dict[str, int] = {}

        for table_name in inspector.get_table_names():
            if table_name in skip_tables:
                continue
            table = db.metadata.tables.get(table_name)
            if table is None:
                continue
            for fk in inspector.get_foreign_keys(table_name):
                referred_table = fk.get("referred_table")
                constrained = fk.get("constrained_columns") or []
                referred = fk.get("referred_columns") or []
                if referred_table != target_table_name or len(constrained) != 1 or referred != ["id"]:
                    continue
                column_name = constrained[0]
                column = table.c.get(column_name)
                if column is None:
                    continue
                count = db.session.execute(
                    db.select(db.func.count()).select_from(table).where(column == merge_id)
                ).scalar_one()
                if count:
                    updated[f"{table_name}.{column_name}"] = int(count)
                    if not dry_run:
                        if DuplicateIdentityService._column_has_unique_constraint(
                            inspector=inspector,
                            table_name=table_name,
                            column_name=column_name,
                        ):
                            DuplicateIdentityService._update_unique_constrained_foreign_key_rows(
                                inspector=inspector,
                                table_name=table_name,
                                column_name=column_name,
                                keep_id=keep_id,
                                merge_id=merge_id,
                            )
                        else:
                            db.session.execute(
                                table.update().where(column == merge_id).values({column_name: keep_id})
                            )
        return updated

    @staticmethod
    def _column_has_unique_constraint(*, inspector, table_name: str, column_name: str) -> bool:
        for item in inspector.get_unique_constraints(table_name):
            columns = item.get("column_names") or []
            if column_name in columns:
                return True
        return False

    @staticmethod
    def _update_unique_constrained_foreign_key_rows(
        *,
        inspector,
        table_name: str,
        column_name: str,
        keep_id: int,
        merge_id: int,
    ) -> None:
        table = db.metadata.tables.get(table_name)
        if table is None:
            return
        unique_constraints = [
            tuple(item.get("column_names") or [])
            for item in inspector.get_unique_constraints(table_name)
            if column_name in (item.get("column_names") or [])
        ]
        rows = db.session.execute(
            db.select(table).where(table.c[column_name] == merge_id)
        ).mappings().all()
        for row in rows:
            conflict_row_id = None
            for unique_columns in unique_constraints:
                filters = []
                for unique_column in unique_columns:
                    expected = keep_id if unique_column == column_name else row.get(unique_column)
                    filters.append(table.c[unique_column] == expected)
                candidate = db.session.execute(
                    db.select(table.c.id).where(and_(*filters), table.c.id != row["id"])
                ).first()
                if candidate:
                    conflict_row_id = getattr(candidate, "id", None) or candidate[0]
                    break
            if conflict_row_id:
                DuplicateIdentityService._resolve_unique_constraint_conflict(
                    table_name=table_name,
                    source_row_id=row["id"],
                    conflict_row_id=conflict_row_id,
                    keep_id=keep_id,
                )
            else:
                db.session.execute(
                    table.update().where(table.c.id == row["id"]).values({column_name: keep_id})
                )

    @staticmethod
    def _resolve_unique_constraint_conflict(
        *,
        table_name: str,
        source_row_id: int,
        conflict_row_id: int,
        keep_id: int,
    ) -> None:
        table = db.metadata.tables.get(table_name)
        if table is None:
            return
        if table_name == "work_journey_agendas":
            agenda_items = db.metadata.tables.get("work_journey_agenda_items")
            if agenda_items is not None:
                db.session.execute(
                    agenda_items.update()
                    .where(agenda_items.c.agenda_id == source_row_id)
                    .values({"agenda_id": conflict_row_id, "employee_id": keep_id})
                )
        db.session.execute(table.delete().where(table.c.id == source_row_id))

    @staticmethod
    def _deduplicate_user_assignments(*, keep_user_id: int, merge_user_id: int, dry_run: bool) -> dict[str, int]:
        # Após reatribuir FKs, podem sobrar assignments redundantes do mesmo user/employee.
        counts = {"user_employee_assignments_removed": 0}
        assignments = (
            UserEmployeeAssignment.query.filter_by(user_id=keep_user_id)
            .order_by(UserEmployeeAssignment.employee_id.asc(), UserEmployeeAssignment.id.asc())
            .all()
        )
        grouped: dict[int, list[UserEmployeeAssignment]] = defaultdict(list)
        for assignment in assignments:
            grouped[assignment.employee_id].append(assignment)

        for _, items in grouped.items():
            if len(items) < 2:
                continue
            keeper = next((item for item in items if item.is_active), items[0])
            for item in items:
                if item.id == keeper.id:
                    continue
                counts["user_employee_assignments_removed"] += 1
                if not dry_run:
                    db.session.delete(item)
        return counts

    @staticmethod
    def _deduplicate_employee_rows(*, keep_employee_id: int, merge_employee_id: int, dry_run: bool) -> dict[str, int]:
        counts = {
            "user_employee_assignments_removed": 0,
            "project_activity_collaborators_removed": 0,
            "process_instance_collaborators_removed": 0,
            "team_members_removed": 0,
        }

        assignments = (
            UserEmployeeAssignment.query.filter_by(employee_id=keep_employee_id)
            .order_by(UserEmployeeAssignment.user_id.asc(), UserEmployeeAssignment.id.asc())
            .all()
        )
        grouped_assignments: dict[int, list[UserEmployeeAssignment]] = defaultdict(list)
        for assignment in assignments:
            grouped_assignments[assignment.user_id].append(assignment)
        for _, items in grouped_assignments.items():
            if len(items) < 2:
                continue
            keeper = next((item for item in items if item.is_active), items[0])
            for item in items:
                if item.id == keeper.id:
                    continue
                counts["user_employee_assignments_removed"] += 1
                if not dry_run:
                    db.session.delete(item)

        counts["project_activity_collaborators_removed"] += DuplicateIdentityService._delete_duplicate_rows(
            table_name="project_activity_collaborators",
            business_keys=("activity_id", "employee_id", "role"),
            dry_run=dry_run,
            filter_column="employee_id",
            filter_value=keep_employee_id,
        )
        counts["process_instance_collaborators_removed"] += DuplicateIdentityService._delete_duplicate_rows(
            table_name="process_instance_collaborators",
            business_keys=("process_instance_id", "employee_id", "role"),
            dry_run=dry_run,
            filter_column="employee_id",
            filter_value=keep_employee_id,
        )
        counts["team_members_removed"] += DuplicateIdentityService._delete_duplicate_rows(
            table_name="team_members",
            business_keys=("team_id", "employee_id"),
            dry_run=dry_run,
            filter_column="employee_id",
            filter_value=keep_employee_id,
        )
        return counts

    @staticmethod
    def _delete_duplicate_rows(
        *,
        table_name: str,
        business_keys: tuple[str, ...],
        dry_run: bool,
        filter_column: str,
        filter_value: int,
    ) -> int:
        table = db.metadata.tables.get(table_name)
        if table is None:
            return 0
        rows = db.session.execute(
            db.select(table).where(table.c[filter_column] == filter_value)
        ).mappings().all()
        seen: set[tuple[Any, ...]] = set()
        duplicates: list[int] = []
        for row in rows:
            key = tuple(row.get(field) for field in business_keys)
            if key in seen:
                duplicates.append(row["id"])
            else:
                seen.add(key)
        if duplicates and not dry_run:
            db.session.execute(table.delete().where(table.c.id.in_(duplicates)))
        return len(duplicates)

    @staticmethod
    def _merge_user_fields(*, keep_user: User, merge_user: User, dry_run: bool) -> list[str]:
        updated_fields: list[str] = []
        candidate_fields = (
            "whatsapp",
            "telegram",
            "instagram",
            "summary_delivery_channels",
        )
        for field in candidate_fields:
            keep_value = getattr(keep_user, field, None)
            merge_value = getattr(merge_user, field, None)
            if not keep_value and merge_value:
                updated_fields.append(field)
                if not dry_run:
                    setattr(keep_user, field, merge_value)
        if not keep_user.name and merge_user.name:
            updated_fields.append("name")
            if not dry_run:
                keep_user.name = merge_user.name
        return updated_fields

    @staticmethod
    def _merge_employee_fields(*, keep_employee: Employee, merge_employee: Employee, dry_run: bool) -> list[str]:
        updated_fields: list[str] = []
        candidate_fields = (
            "email",
            "phone",
            "whatsapp",
            "telegram",
            "department",
            "hire_date",
            "weekly_hours",
            "notes",
            "role_id",
        )
        for field in candidate_fields:
            keep_value = getattr(keep_employee, field, None)
            merge_value = getattr(merge_employee, field, None)
            if not keep_value and merge_value:
                updated_fields.append(field)
                if not dry_run:
                    setattr(keep_employee, field, merge_value)
        if not keep_employee.name and merge_employee.name:
            updated_fields.append("name")
            if not dry_run:
                keep_employee.name = merge_employee.name
        if keep_employee.user_id is None and merge_employee.user_id is not None:
            updated_fields.append("user_id")
            if not dry_run:
                keep_employee.user_id = merge_employee.user_id
        return updated_fields

    @staticmethod
    def _update_employee_json_references(
        *,
        keep_employee_id: int,
        merge_employee_id: int,
        company_id: int,
        dry_run: bool,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        for occurrence in Occurrence.query.filter_by(company_id=company_id).all():
            changed = False
            payload = occurrence.collaborators_ids
            new_payload, changed = DuplicateIdentityService._replace_value_recursive(
                payload,
                old_value=merge_employee_id,
                new_value=keep_employee_id,
            )
            if changed:
                counts["occurrences.collaborators_ids"] = counts.get("occurrences.collaborators_ids", 0) + 1
                if not dry_run:
                    occurrence.collaborators_ids = new_payload

        for instance in ProcessInstance.query.filter_by(company_id=company_id).all():
            new_payload, changed = DuplicateIdentityService._replace_value_recursive(
                instance.collaborators_json,
                old_value=merge_employee_id,
                new_value=keep_employee_id,
            )
            if changed:
                counts["process_instances.collaborators_json"] = counts.get("process_instances.collaborators_json", 0) + 1
                if not dry_run:
                    instance.collaborators_json = new_payload

        for meeting in Meeting.query.filter_by(company_id=company_id).all():
            for column_name in EMPLOYEE_JSON_COLUMNS["meetings"]:
                raw_value = getattr(meeting, column_name, None)
                if not raw_value:
                    continue
                try:
                    parsed = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
                except Exception:
                    continue
                new_payload, changed = DuplicateIdentityService._replace_value_recursive(
                    parsed,
                    old_value=merge_employee_id,
                    new_value=keep_employee_id,
                )
                if changed:
                    counts[f"meetings.{column_name}"] = counts.get(f"meetings.{column_name}", 0) + 1
                    if not dry_run:
                        setattr(meeting, column_name, json.dumps(new_payload, ensure_ascii=False))
        return counts

    @staticmethod
    def _replace_value_recursive(payload: Any, *, old_value: int, new_value: int) -> tuple[Any, bool]:
        changed = False

        if isinstance(payload, list):
            new_list = []
            for item in payload:
                new_item, item_changed = DuplicateIdentityService._replace_value_recursive(
                    item,
                    old_value=old_value,
                    new_value=new_value,
                )
                new_list.append(new_item)
                changed = changed or item_changed
            return new_list, changed

        if isinstance(payload, dict):
            new_dict = {}
            for key, value in payload.items():
                if isinstance(value, str) and value == f"employee:{old_value}":
                    new_dict[key] = f"employee:{new_value}"
                    changed = True
                    continue
                new_value_item, item_changed = DuplicateIdentityService._replace_value_recursive(
                    value,
                    old_value=old_value,
                    new_value=new_value,
                )
                new_dict[key] = new_value_item
                changed = changed or item_changed
            return new_dict, changed

        if isinstance(payload, str) and payload == f"employee:{old_value}":
            return f"employee:{new_value}", True

        if payload == old_value:
            return new_value, True

        return payload, False
