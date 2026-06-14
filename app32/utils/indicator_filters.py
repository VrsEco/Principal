from __future__ import annotations

from functools import lru_cache

from sqlalchemy import and_, exists, inspect, or_

from models import Indicator, IndicatorEntityLink, db

PROCESS_SOURCE_MODULES = ("processo", "process")
PROJECT_SOURCE_MODULES = ("projeto", "project")


@lru_cache(maxsize=1)
def get_indicator_table_columns() -> frozenset[str]:
    try:
        inspector = inspect(db.engine)
        columns = {column["name"] for column in inspector.get_columns("indicators")}
        if columns:
            return frozenset(columns)
    except Exception:
        pass
    return frozenset(column.name for column in Indicator.__table__.columns)


def indicator_supports_source_context() -> bool:
    columns = get_indicator_table_columns()
    return "source_module" in columns and "source_id" in columns


def build_indicator_process_filter(process_id: int):
    clauses = [Indicator.process_id == process_id]
    clauses.append(
        exists().where(
            and_(
                IndicatorEntityLink.company_id == Indicator.company_id,
                IndicatorEntityLink.indicator_id == Indicator.id,
                IndicatorEntityLink.target_type == "process",
                IndicatorEntityLink.target_ref == str(process_id),
                IndicatorEntityLink.is_active.is_(True),
            )
        )
    )
    if indicator_supports_source_context():
        clauses.append(
            and_(
                Indicator.source_module.in_(PROCESS_SOURCE_MODULES),
                Indicator.source_id == process_id,
            )
        )
    return or_(*clauses)


def build_indicator_project_filter(project_id: int):
    clauses = [Indicator.project_id == project_id]
    clauses.append(
        exists().where(
            and_(
                IndicatorEntityLink.company_id == Indicator.company_id,
                IndicatorEntityLink.indicator_id == Indicator.id,
                IndicatorEntityLink.target_type == "project",
                IndicatorEntityLink.target_ref == str(project_id),
                IndicatorEntityLink.is_active.is_(True),
            )
        )
    )
    if indicator_supports_source_context():
        clauses.append(
            and_(
                Indicator.source_module.in_(PROJECT_SOURCE_MODULES),
                Indicator.source_id == project_id,
            )
        )
    return or_(*clauses)
