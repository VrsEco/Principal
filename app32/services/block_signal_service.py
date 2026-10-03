"""Sinais por bloco da Agenda (Fase 2): capacidade, consumo e sinal.

Funcao pura sobre dados ja carregados: nao acessa banco, nao bloqueia nada.
Regras: docs/spec/agenda_unificada_blocos_pessoa_v1.md, secoes 5.4 e 8.
"""

from __future__ import annotations

from typing import Any, Iterable

DEFAULT_IDLE_THRESHOLD_MINUTES = 30

SIGNAL_OVER = "over"
SIGNAL_FREE = "free"
SIGNAL_FULL = "full"
SIGNAL_NONE = "none"  # bloco nao operacional: nao recebe sinal

OPERATIONAL_MODE = "operational"


def union_minutes(intervals: Iterable[tuple[int, int]]) -> int:
    """Minutos da uniao dos intervalos (cada hora conta uma vez)."""
    total, cur_start, cur_end = 0, None, None
    for start, end in sorted((a, b) for a, b in intervals if b > a):
        if cur_end is None or start > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    if cur_end is not None:
        total += cur_end - cur_start
    return total


def fmt_minutes(minutes: int) -> str:
    """90 -> '1h30', 120 -> '2h', 30 -> '30min'."""
    minutes = max(int(minutes), 0)
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours}h{rest:02d}"
    if hours:
        return f"{hours}h"
    return f"{rest}min"


def signal_for(capacity: int, consumed: int, idle_threshold: int = DEFAULT_IDLE_THRESHOLD_MINUTES) -> dict[str, Any]:
    """Sinal de um bloco operacional: Acima / Livre / Completo."""
    capacity = max(int(capacity), 0)
    consumed = max(int(consumed), 0)
    if consumed > capacity:
        diff = consumed - capacity
        return {"state": SIGNAL_OVER, "minutes": diff, "label": f"Acima {fmt_minutes(diff)}"}
    free = capacity - consumed
    if free >= max(int(idle_threshold), 1):
        return {"state": SIGNAL_FREE, "minutes": free, "label": f"Livre {fmt_minutes(free)}"}
    return {"state": SIGNAL_FULL, "minutes": free, "label": "Completo"}


def _block_window(block: dict[str, Any]) -> tuple[int, int]:
    return int(block["start_minutes"]), int(block["end_minutes"])


def compute_block_signals(
    blocks: Iterable[dict[str, Any]],
    items: Iterable[dict[str, Any]],
    timed_events: Iterable[dict[str, Any]],
    idle_threshold: int = DEFAULT_IDLE_THRESHOLD_MINUTES,
) -> dict[str, Any]:
    """Calcula capacidade, consumo e sinal de cada bloco de UM dia de UMA pessoa.

    blocks: {id, name, mode, start_minutes, end_minutes}
    items: {block_id, estimated_minutes, completed?, title?, id?}  (atribuidos a bloco)
    timed_events: {start_minutes, duration_minutes}  (reunioes/eventos com horario)

    - Concluidos nao consomem (RF-SIN-2).
    - Estimativa 0/ausente fica fora da conta e e contada em `without_estimate` (RF-SIN-5).
    - Evento com horario consome o bloco em que COMECA (secao 5.4).
    - Apenas blocos operacionais recebem sinal e entram na capacidade do dia.
    """
    blocks = sorted((dict(b) for b in blocks), key=lambda b: (b["start_minutes"], b["end_minutes"]))
    state: dict[Any, dict[str, Any]] = {}
    for block in blocks:
        start, end = _block_window(block)
        state[block["id"]] = {
            "id": block["id"],
            "name": block.get("name"),
            "mode": block.get("mode") or OPERATIONAL_MODE,
            "start_minutes": start,
            "end_minutes": end,
            "capacity_minutes": max(end - start, 0),
            "consumed_minutes": 0,
            "item_count": 0,
            "event_count": 0,
            "without_estimate": 0,
        }

    unassigned_without_estimate = 0
    for item in items:
        if item.get("completed"):
            continue
        minutes = int(item.get("estimated_minutes") or 0)
        entry = state.get(item.get("block_id"))
        if entry is None:
            if minutes <= 0:
                unassigned_without_estimate += 1
            continue
        entry["item_count"] += 1
        if minutes <= 0:
            entry["without_estimate"] += 1
            continue
        entry["consumed_minutes"] += minutes

    for event in timed_events:
        start = int(event["start_minutes"])
        duration = max(int(event.get("duration_minutes") or 0), 0)
        owner = next((b for b in blocks if b["start_minutes"] <= start < b["end_minutes"]), None)
        if owner is None:
            continue
        entry = state[owner["id"]]
        entry["event_count"] += 1
        entry["consumed_minutes"] += duration

    result_blocks: list[dict[str, Any]] = []
    operational_windows: list[tuple[int, int]] = []
    day_consumed = 0
    for block in blocks:
        entry = state[block["id"]]
        if entry["mode"] == OPERATIONAL_MODE:
            entry["signal"] = signal_for(entry["capacity_minutes"], entry["consumed_minutes"], idle_threshold)
            operational_windows.append((entry["start_minutes"], entry["end_minutes"]))
            day_consumed += entry["consumed_minutes"]
        else:
            entry["signal"] = {"state": SIGNAL_NONE, "minutes": 0, "label": ""}
        result_blocks.append(entry)

    # Capacidade do dia = UNIAO dos intervalos: blocos sobrepostos nao contam a mesma hora duas vezes (RF-BLO-5).
    day_capacity = union_minutes(operational_windows)
    if day_capacity <= 0:
        day = {"state": SIGNAL_NONE, "minutes": 0, "label": "Sem expediente"}
    else:
        day = signal_for(day_capacity, day_consumed, idle_threshold)
    day.update({"capacity_minutes": day_capacity, "consumed_minutes": day_consumed})

    return {
        "blocks": result_blocks,
        "day": day,
        "unassigned_without_estimate": unassigned_without_estimate,
    }
