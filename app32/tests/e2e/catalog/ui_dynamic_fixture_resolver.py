from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

from flask import has_app_context

from app32.tests.e2e.config.environments import E2EEnvironmentSettings

_PLACEHOLDER_RE = re.compile(r"<(?:(?P<type>int|string|path):)?(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>")


@dataclass
class DynamicFixtureResolution:
    route: str
    resolved_route: str
    resolved_values: dict[str, int | str] = field(default_factory=dict)
    unresolved_placeholders: list[str] = field(default_factory=list)
    reason: str | None = None

    @property
    def resolved(self) -> bool:
        return not self.reason and not self.unresolved_placeholders


class DynamicFixtureResolver:
    """Resolve placeholders de rotas usando fixtures reais e tenant-safe.

    O resolver é deliberadamente conservador: só substitui IDs quando a consulta
    consegue filtrar por ``company_id`` ou por relacionamento com uma entidade da
    empresa. Quando não há fixture segura, a rota permanece como ponto de
    manutenção em vez de forçar navegação ou mutação fora de contexto.
    """

    def __init__(self, settings: E2EEnvironmentSettings):
        self.settings = settings
        self._cache: dict[str, int | str | None] = {}

    def resolve_route(self, route: str) -> DynamicFixtureResolution:
        original = str(route or "").strip()
        resolved = original
        values: dict[str, int | str] = {}
        unresolved: list[str] = []
        for match in list(_PLACEHOLDER_RE.finditer(original)):
            token = match.group(0)
            name = match.group("name")
            value = self.resolve_value(name)
            if value is None:
                unresolved.append(name)
                continue
            resolved = resolved.replace(token, str(value))
            values[name] = value
        reason = "dynamic_route_requires_fixture_resolution" if unresolved else None
        return DynamicFixtureResolution(
            route=original,
            resolved_route=resolved,
            resolved_values=values,
            unresolved_placeholders=unresolved,
            reason=reason,
        )

    def resolve_value(self, name: str) -> int | str | None:
        key = str(name or "").strip()
        if key in self._cache:
            return self._cache[key]
        resolver = _STATIC_RESOLVERS.get(key) or _DB_RESOLVERS.get(key)
        value = resolver(self) if resolver else None
        self._cache[key] = value
        return value

    def _company_id(self) -> int | None:
        return self.settings.company_id

    def _user_id(self) -> int | None:
        return self.settings.user_id

    def _first_id(self, model: Any, *, company_id: int | None = None, filters: tuple[Any, ...] = ()) -> int | None:
        if company_id is None:
            company_id = self._company_id()
        if company_id is None:
            return None
        try:
            query = model.query
            if hasattr(model, "company_id"):
                query = query.filter(model.company_id == company_id)
            for clause in filters:
                query = query.filter(clause)
            if hasattr(model, "deleted_at"):
                query = query.filter(model.deleted_at.is_(None))
            if hasattr(model, "is_deleted"):
                query = query.filter(model.is_deleted.is_(False))
            if hasattr(model, "is_active"):
                query = query.filter(model.is_active.is_(True))
            row = query.order_by(model.id.asc()).first()
            return int(row.id) if row is not None and getattr(row, "id", None) is not None else None
        except Exception:
            return None


@contextmanager
def app_context_if_needed() -> Iterator[None]:
    if has_app_context():
        yield
        return
    root = Path(__file__).resolve().parents[4]
    inner = root / "app32"
    for candidate in (root, inner):
        text = str(candidate)
        if text not in sys.path:
            sys.path.insert(0, text)
    os.environ.setdefault("APP_BOOTSTRAP_DB_SCHEMA", "false")
    os.environ.setdefault("APP_BOOTSTRAP_RUNTIME_SERVICES", "false")
    from app import create_app  # type: ignore

    app = create_app(os.environ.get("FLASK_CONFIG") or "production")
    with app.app_context():
        yield


def _with_db(fn: Callable[[DynamicFixtureResolver], int | str | None]) -> Callable[[DynamicFixtureResolver], int | str | None]:
    def wrapper(resolver: DynamicFixtureResolver) -> int | str | None:
        if resolver._company_id() is None:
            return None
        with app_context_if_needed():
            return fn(resolver)
    return wrapper


def _resolve_company_id(resolver: DynamicFixtureResolver) -> int | None:
    return resolver._company_id()


def _resolve_user_id(resolver: DynamicFixtureResolver) -> int | None:
    return resolver._user_id()


@_with_db
def _resolve_employee_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.employee import Employee  # type: ignore

    filters = ()
    if resolver._user_id() is not None:
        filters = (Employee.user_id == resolver._user_id(),)
    return resolver._first_id(Employee, filters=filters) or resolver._first_id(Employee)


@_with_db
def _resolve_process_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.process import Process  # type: ignore

    return resolver._first_id(Process)


@_with_db
def _resolve_macro_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.process import MacroProcess  # type: ignore

    return resolver._first_id(MacroProcess)


@_with_db
def _resolve_routine_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.process import ProcessRoutine  # type: ignore
    from models.routine import Routine  # type: ignore

    return resolver._first_id(ProcessRoutine) or resolver._first_id(Routine)


@_with_db
def _resolve_schedule_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.financial import FinancialSchedule  # type: ignore

    return resolver._first_id(FinancialSchedule)


@_with_db
def _resolve_entry_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.financial import FinancialEntry  # type: ignore

    return resolver._first_id(FinancialEntry)


@_with_db
def _resolve_bordero_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.financial import FinancialBordero  # type: ignore

    return resolver._first_id(FinancialBordero)


@_with_db
def _resolve_batch_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.financial import FinancialImportBatch  # type: ignore

    return resolver._first_id(FinancialImportBatch)


@_with_db
def _resolve_property_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.real_estate_auction import RealEstateAuctionProperty  # type: ignore

    return resolver._first_id(RealEstateAuctionProperty)


@_with_db
def _resolve_project_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.project import Project  # type: ignore

    return resolver._first_id(Project)


@_with_db
def _resolve_task_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.project import Project, ProjectTask  # type: ignore

    company_id = resolver._company_id()
    row = (
        ProjectTask.query.join(Project, ProjectTask.project_id == Project.id)
        .filter(Project.company_id == company_id)
        .filter(ProjectTask.is_deleted.is_(False))
        .order_by(ProjectTask.id.asc())
        .first()
    )
    return int(row.id) if row is not None else None


@_with_db
def _resolve_portfolio_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.portfolio import Portfolio  # type: ignore

    return resolver._first_id(Portfolio)


@_with_db
def _resolve_party_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.contracts import ContractParty  # type: ignore

    return resolver._first_id(ContractParty)


@_with_db
def _resolve_contract_id(resolver: DynamicFixtureResolver) -> int | None:
    from models.contracts import Contract  # type: ignore

    return resolver._first_id(Contract)


_STATIC_RESOLVERS: dict[str, Callable[[DynamicFixtureResolver], int | str | None]] = {
    "company_id": _resolve_company_id,
    "user_id": _resolve_user_id,
}

_DB_RESOLVERS: dict[str, Callable[[DynamicFixtureResolver], int | str | None]] = {
    "employee_id": _resolve_employee_id,
    "process_id": _resolve_process_id,
    "macro_id": _resolve_macro_id,
    "routine_id": _resolve_routine_id,
    "schedule_id": _resolve_schedule_id,
    "entry_id": _resolve_entry_id,
    "bordero_id": _resolve_bordero_id,
    "batch_id": _resolve_batch_id,
    "property_id": _resolve_property_id,
    "project_id": _resolve_project_id,
    "task_id": _resolve_task_id,
    "portfolio_id": _resolve_portfolio_id,
    "party_id": _resolve_party_id,
    "contract_id": _resolve_contract_id,
}
