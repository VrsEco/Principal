from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from markupsafe import Markup

from models import db
from models.ui_catalog import UiCatalog


def format_ui_code(screen_code: int, object_code: int) -> str:
    """Return the canonical UI code in the format '<screen>-<object>'."""
    return f"{screen_code}-{object_code}"


def escape_attr(value: str) -> str:
    """Escape attribute values to avoid HTML injection."""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def get_screen_entries(screen_code: int, include_inactive: bool = False) -> List[UiCatalog]:
    """Fetch catalog entries for a specific screen."""
    query = UiCatalog.query.filter_by(screen_code=screen_code, is_deleted=False)
    if not include_inactive:
        query = query.filter(UiCatalog.is_active.is_(True))
    return query.order_by(UiCatalog.object_code.asc()).all()


def get_screen_attr_map(screen_code: int) -> Dict[str, Markup]:
    """Return a dict mapping object codes to HTML data attributes."""
    entries = get_screen_entries(screen_code)
    return build_attr_map(entries)


def build_attr_map(entries: Iterable[UiCatalog]) -> Dict[str, Markup]:
    """Build attribute map for a collection of catalog entries."""
    attr_map: Dict[str, Markup] = {}
    for entry in entries:
        attributes = [f'data-ui-code="{escape_attr(entry.ui_code)}"']
        if entry.name:
            attributes.append(f'data-ui-name="{escape_attr(entry.name)}"')
        if entry.object_type:
            attributes.append(f'data-ui-type="{escape_attr(entry.object_type)}"')
        if entry.route:
            attributes.append(f'data-ui-route="{escape_attr(entry.route)}"')
        attr_map[str(entry.object_code)] = Markup(" ".join(attributes))
    return attr_map


def serialize_screen_catalog(screen_code: int) -> Dict[str, Dict[str, Optional[str]]]:
    """Return serializable payload keyed by object code."""
    entries = get_screen_entries(screen_code)
    payload: Dict[str, Dict[str, Optional[str]]] = {}
    for entry in entries:
        payload[str(entry.object_code)] = {
            "object_code": entry.object_code,
            "ui_code": entry.ui_code,
            "name": entry.name,
            "description": entry.description,
            "object_type": entry.object_type,
            "route": entry.route,
        }
    return payload


def get_by_code(ui_code: str) -> Optional[UiCatalog]:
    """Return a catalog entry for a given UI code."""
    return UiCatalog.query.filter_by(ui_code=ui_code, is_deleted=False).first()


def ensure_entry(
    screen_code: int,
    object_code: int,
    name: str,
    description: Optional[str] = None,
    object_type: Optional[str] = None,
    route: Optional[str] = None,
) -> UiCatalog:
    """
    Idempotently create or update a catalog entry.

    Useful for scripting or tests to guarantee codes exist.
    """
    ui_code = format_ui_code(screen_code, object_code)
    entry = UiCatalog.query.filter_by(ui_code=ui_code).first()
    if entry is None:
        entry = UiCatalog(
            screen_code=screen_code,
            object_code=object_code,
            ui_code=ui_code,
            name=name,
            description=description,
            object_type=object_type,
            route=route,
            is_active=True,
        )
        db.session.add(entry)
    else:
        entry.name = name
        entry.description = description
        entry.object_type = object_type
        entry.route = route
        entry.is_active = True
        entry.is_deleted = False
    db.session.commit()
    return entry










