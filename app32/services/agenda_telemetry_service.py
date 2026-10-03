"""Telemetria de uso da Agenda: só nome da ação e detalhe curto, nunca títulos nem dados dos itens."""
from __future__ import annotations

from typing import Any, Iterable

from models import AgendaUiEvent, db

MAX_EVENTS_PER_CALL = 20
DEVICES = {"mobile", "desktop"}
# evento -> valores aceitos em `detail` (None = detail livre curto, apenas [a-z0-9_-])
ALLOWED_EVENTS: dict[str, set[str] | None] = {
    "agenda_open": {"day", "week", "month"},
    "view_change": {"day", "week", "month"},
    "create_open": None,
    "create_choose": {"meeting", "project_task", "process_instance", "manual"},
    "late_open": None,
    "late_sort": {"old", "new", "type", "source"},
    "late_filter": {"project_task", "process_instance"},
    "item_open": {"meeting", "project_task", "process_instance", "manual", "google_event"},
    "legacy_open": None,
    "google_open": None,
    "blocks_toggle": {"on", "off"},
    "estimate_open": None,
    "estimate_save": None,
    "move_open": None,
    "move_confirm": {"same_day", "other_day"},
    "suggest_open": None,
    "suggest_apply": None,
    "suggest_accept": None,
    "suggest_undo": None,
    "blocks_edit_open": None,
    "blocks_edit_save": {"create", "update", "delete"},
    "migration_open": None,
    "migration_apply": None,
    "migration_revert": None,
}


def _clean_detail(value: Any, allowed: set[str] | None) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()[:40]
    if allowed is not None:
        return text if text in allowed else None
    return text if all(c.isalnum() or c in "_-" for c in text) else None


def record_events(company_id: int, user_id: int | None, device: str | None, events: Iterable[dict[str, Any]]) -> int:
    """Grava até MAX_EVENTS_PER_CALL eventos válidos; ignora silenciosamente o que não está na lista permitida."""
    device = device if device in DEVICES else None
    rows = []
    for item in list(events or [])[:MAX_EVENTS_PER_CALL]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("event") or "").strip().lower()
        if name not in ALLOWED_EVENTS:
            continue
        rows.append(AgendaUiEvent(
            company_id=company_id, user_id=user_id, event=name, device=device,
            detail=_clean_detail(item.get("detail"), ALLOWED_EVENTS[name]),
        ))
    if rows:
        db.session.add_all(rows)
        db.session.commit()
    return len(rows)
