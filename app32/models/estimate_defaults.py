"""Politica de estimativa da Agenda (SPEC agenda unificada, RF-EST-1).

Atividades e instancias NOVAS, sem tempo informado, nascem com 30 min. Registros
existentes nao sao alterados (RF-EST-2): so o INSERT dispara a regra.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import event

from . import db
from .process import ProcessInstance
from .project import ProjectTask

DEFAULT_ESTIMATED_HOURS = Decimal("0.50")


def _apply_default(_mapper, _connection, target) -> None:
    if not target.estimated_hours:
        target.estimated_hours = DEFAULT_ESTIMATED_HOURS


event.listen(ProjectTask, "before_insert", _apply_default)
event.listen(ProcessInstance, "before_insert", _apply_default)
