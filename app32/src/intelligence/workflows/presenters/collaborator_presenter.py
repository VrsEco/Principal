from __future__ import annotations

from datetime import date
from typing import Any, Callable

from .chat_contract import ChatMessageBlock, make_list_block
from .conversation_presenter import build_chat_contract_message, build_status_callout


def build_collaborator_occupancy_report(
    *,
    collaborator_name: str,
    company_label: str,
    start_date: date,
    end_date: date,
    available_hours: float,
    process_hours_taken: float,
    project_hours_taken: float,
    project_hours_committed: float,
    channel: str,
    format_date_br: Callable[[Any], str],
) -> str:
    total_consumption = process_hours_taken + project_hours_committed
    balance_hours = available_hours - total_consumption
    utilization = (total_consumption / available_hours * 100.0) if available_hours > 0 else 0.0

    return build_chat_contract_message(
        "Ocupacao do Colaborador",
        subtitle=f"{collaborator_name} | {company_label}",
        channel=channel,
        blocks=[
            ChatMessageBlock(
                kind="status",
                text=build_status_callout(
                    "info",
                    f"Periodo analisado: {format_date_br(start_date)} a {format_date_br(end_date)}",
                    channel=channel,
                ),
            ),
            make_list_block(
                [
                    f"Horas disponiveis: {available_hours:.2f}h",
                    f"Horas tomadas com processos: {process_hours_taken:.2f}h",
                    f"Horas registradas em projetos: {project_hours_taken:.2f}h",
                    f"Horas comprometidas com projetos: {project_hours_committed:.2f}h",
                    f"Consumo total do periodo: {total_consumption:.2f}h",
                    f"Saldo estimado: {balance_hours:.2f}h",
                    f"Ocupacao estimada: {utilization:.1f}%",
                ]
            ),
            ChatMessageBlock(
                kind="body",
                text="Observacao: o compromisso em projetos considera horas estimadas de atividades abertas do colaborador no periodo.",
            ),
            ChatMessageBlock(
                kind="next_step",
                items=[
                    "Use esse panorama para verificar capacidade disponivel no periodo.",
                    "Se quiser, solicite outro periodo ou outro colaborador.",
                ],
            ),
        ],
    )
