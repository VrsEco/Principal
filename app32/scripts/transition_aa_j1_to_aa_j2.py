"""Consolida o backlog do AA.J.1 em um card por entrega no AA.J.2.

Dry-run é o padrão. A mutação exige ``--execute`` e ocorre em uma transação.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from typing import Iterable

from app import create_app
from models import db
from models.company import Company
from models.project import Project, ProjectTask


COMPANY_ID = 9
SOURCE_SEQUENCE = 1
TARGET_SEQUENCE = 2
TRANSITION_TITLE_FRAGMENT = "Reestruturar governanca e performance AA.J.1"
STEP_RE = re.compile(r"^\s*\[(?P<delivery>.*?)\s*-\s*Passo\s+\d+\s+de\s+\d+\]\s*(?P<suffix>.*)$", re.I)


def _normalized(value: str | None) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _task_code(task: ProjectTask) -> str:
    return task.code


def _group_key(task: ProjectTask) -> tuple[str, str]:
    title = str(task.what or "").strip()
    match = STEP_RE.match(title)
    if match:
        return "delivery", _normalized(match.group("delivery"))
    return "card", _normalized(title)


def _delivery_title(tasks: list[ProjectTask]) -> str:
    first_title = str(tasks[0].what or "").strip()
    match = STEP_RE.match(first_title)
    if match:
        return f"[{match.group('delivery').strip()}]"
    return first_title


def _migration_key(group_key: tuple[str, str]) -> str:
    raw = f"{group_key[0]}:{group_key[1]}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:20]


def _priority(tasks: Iterable[ProjectTask]) -> str:
    weights = {"low": 1, "normal": 2, "medium": 2, "high": 3, "alta": 3, "urgent": 4, "urgente": 4}
    return max((str(task.priority or "normal") for task in tasks), key=lambda value: weights.get(value.casefold(), 2))


def _stage(tasks: Iterable[ProjectTask]) -> str:
    values = {str(task.stage or "inbox") for task in tasks}
    for candidate in ("executing", "pending", "suspended", "waiting", "inbox"):
        if candidate in values:
            return candidate
    return "inbox"


def _build_notes(tasks: list[ProjectTask], group_key: tuple[str, str]) -> str:
    marker = _migration_key(group_key)
    lines = [
        f"AAJ1_MIGRATION_KEY={marker}",
        "Consolidado automaticamente do histórico AA.J.1 em 13/08/2026.",
        "",
        "Cards de origem:",
    ]
    for task in tasks:
        lines.append(f"- {_task_code(task)} — {str(task.what or '').strip()}")
    lines.extend(["", "Checklist/evidências preservadas:"])
    for index, task in enumerate(tasks, start=1):
        description = (task.notes or task.how or task.what or "Etapa sem descrição").strip()
        lines.append(f"- [ ] {index}. {description}")
    return "\n".join(lines)


def _resolve_projects() -> tuple[Project, Project | None]:
    source = Project.query.filter_by(
        company_id=COMPANY_ID,
        code_sequence=SOURCE_SEQUENCE,
        is_deleted=False,
    ).first()
    if not source:
        raise RuntimeError("Projeto fonte AA.J.1 não encontrado para company_id=9.")
    target = Project.query.filter_by(
        company_id=COMPANY_ID,
        code_sequence=TARGET_SEQUENCE,
        is_deleted=False,
    ).first()
    return source, target


def _open_source_tasks(source_id: int) -> list[ProjectTask]:
    return (
        ProjectTask.query.filter(
            ProjectTask.project_id == source_id,
            ProjectTask.is_deleted.is_(False),
            ProjectTask.stage != "completed",
            ~ProjectTask.what.ilike(f"%{TRANSITION_TITLE_FRAGMENT}%"),
        )
        .order_by(ProjectTask.id.asc())
        .all()
    )


def build_plan() -> dict:
    source, target = _resolve_projects()
    tasks = _open_source_tasks(source.id)
    grouped: dict[tuple[str, str], list[ProjectTask]] = defaultdict(list)
    for task in tasks:
        grouped[_group_key(task)].append(task)
    planned = []
    existing_markers = set()
    if target:
        for notes, in ProjectTask.query.with_entities(ProjectTask.notes).filter(
            ProjectTask.project_id == target.id,
            ProjectTask.is_deleted.is_(False),
            ProjectTask.notes.ilike("%AAJ1_MIGRATION_KEY=%"),
        ):
            match = re.search(r"AAJ1_MIGRATION_KEY=([a-f0-9]{20})", notes or "")
            if match:
                existing_markers.add(match.group(1))
    for key, rows in grouped.items():
        marker = _migration_key(key)
        planned.append({
            "migration_key": marker,
            "title": _delivery_title(rows),
            "source_count": len(rows),
            "source_codes": [_task_code(row) for row in rows],
            "already_migrated": marker in existing_markers,
        })
    return {
        "company_id": COMPANY_ID,
        "source": {"id": source.id, "code": source.code, "status": source.status},
        "target": {"id": target.id, "code": target.code, "status": target.status} if target else None,
        "source_open_considered": len(tasks),
        "consolidated_deliveries": len(grouped),
        "cards_to_create": sum(1 for row in planned if not row["already_migrated"]),
        "groups": planned,
    }


def execute_transition(*, archive_source: bool) -> dict:
    company = Company.query.filter_by(id=COMPANY_ID).first()
    if not company:
        raise RuntimeError("Empresa company_id=9 não encontrada.")
    source, target = _resolve_projects()
    if not target:
        target = Project(
            company_id=COMPANY_ID,
            code_sequence=TARGET_SEQUENCE,
            name="DEV APP Gestão Versus — Ciclo 2",
            description="Projeto operacional enxuto, regido por um card por entrega.",
            owner=source.owner,
            status="in_progress",
            start_date=date.today(),
            priority=source.priority,
            portfolio_id=source.portfolio_id,
            notes="Sucessor operacional do AA.J.1. Backlog consolidado em 13/08/2026.",
        )
        db.session.add(target)
        db.session.flush()

    tasks = _open_source_tasks(source.id)
    grouped: dict[tuple[str, str], list[ProjectTask]] = defaultdict(list)
    for task in tasks:
        grouped[_group_key(task)].append(task)

    created = []
    reused = []
    for key, rows in grouped.items():
        marker = _migration_key(key)
        existing = ProjectTask.query.filter(
            ProjectTask.project_id == target.id,
            ProjectTask.is_deleted.is_(False),
            ProjectTask.notes.ilike(f"%AAJ1_MIGRATION_KEY={marker}%"),
        ).first()
        if existing:
            reused.append(existing.code)
            continue
        stage = _stage(rows)
        due_dates = [row.due_date for row in rows if row.due_date]
        task = ProjectTask(
            project_id=target.id,
            what=_delivery_title(rows),
            who=rows[0].who,
            employee_id=rows[0].employee_id,
            due_date=min(due_dates) if due_dates else None,
            how="Execução consolidada por entrega; usar checklist nas notas.",
            status="planned" if stage in {"inbox", "waiting"} else "in_progress",
            stage=stage,
            priority=_priority(rows),
            notes=_build_notes(rows, key),
            estimated_hours=sum(float(row.estimated_hours or 0) for row in rows),
            worked_hours=sum(float(row.worked_hours or 0) for row in rows),
        )
        db.session.add(task)
        db.session.flush()
        created.append(task.code)

    if archive_source:
        source.status = "archived"
        suffix = "Arquivado em 13/08/2026 após consolidação do backlog no AA.J.2."
        source.notes = f"{(source.notes or '').strip()}\n\n{suffix}".strip()
    target.status = "in_progress"
    target.update_progress()
    db.session.commit()
    return {
        "ok": True,
        "company_id": COMPANY_ID,
        "source": {"id": source.id, "code": source.code, "status": source.status},
        "target": {"id": target.id, "code": target.code, "status": target.status},
        "created_count": len(created),
        "reused_count": len(reused),
        "created_codes": created,
        "reused_codes": reused,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--archive-source", action="store_true")
    args = parser.parse_args()

    app = create_app("production")
    with app.app_context():
        try:
            payload = execute_transition(archive_source=args.archive_source) if args.execute else build_plan()
            payload["dry_run"] = not args.execute
            print(json.dumps(payload, ensure_ascii=False, default=str))
        except Exception:
            db.session.rollback()
            raise


if __name__ == "__main__":
    main()
