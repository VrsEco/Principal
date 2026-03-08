from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, List

from .channel_presenter import sanitize_for_channel
from .conversation_presenter import build_key_value_lines, build_next_step_block, build_presenter_header, build_status_callout


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

    lines: List[str] = build_presenter_header(
        "Ocupacao do Colaborador",
        f"{collaborator_name} | {company_label}",
        channel=channel,
    )
    lines.extend(
        [
            "",
            build_status_callout(
                "info",
                f"Periodo analisado: {format_date_br(start_date)} a {format_date_br(end_date)}",
                channel=channel,
            ),
            "",
        ]
    )
    lines.extend(
        build_key_value_lines(
            [
                ("Horas disponiveis", f"{available_hours:.2f}h"),
                ("Horas tomadas com processos", f"{process_hours_taken:.2f}h"),
                ("Horas registradas em projetos", f"{project_hours_taken:.2f}h"),
                ("Horas comprometidas com projetos", f"{project_hours_committed:.2f}h"),
                ("Consumo total do periodo", f"{total_consumption:.2f}h"),
                ("Saldo estimado", f"{balance_hours:.2f}h"),
                ("Ocupacao estimada", f"{utilization:.1f}%"),
            ],
            channel=channel,
        )
    )
    lines.extend(
        [
            "",
            sanitize_for_channel(
                "Observacao: o compromisso em projetos considera horas estimadas de atividades abertas do colaborador no periodo.",
                channel,
            ),
            "",
            *build_next_step_block(
                "Use esse panorama para verificar capacidade disponivel no periodo.",
                "Se quiser, solicite outro periodo ou outro colaborador.",
                channel=channel,
            ),
        ]
    )
    return "\n".join(lines)
