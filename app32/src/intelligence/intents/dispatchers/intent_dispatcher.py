from __future__ import annotations

from typing import Dict, Optional

from ..schemas.operational_form import OperationalIntentForm


class OperationalIntentDispatcher:
    def __init__(self, routing_table: Optional[Dict[str, str]] = None):
        self._routing_table = dict(routing_table or {})

    def resolve_action_key(self, form: OperationalIntentForm) -> Optional[str]:
        return self._routing_table.get(form.intent_code)
