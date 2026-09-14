from __future__ import annotations

from datetime import datetime
from typing import Any

from models import Company, MacroProcess
from services.macro_process_sipoc_service import get_macro_process_sipoc_bundle


LANES = (
    ("supplier", "Fornecedores"),
    ("input", "Entradas"),
    ("process", "Processos filhos"),
    ("output", "Saídas"),
    ("customer", "Clientes"),
)


def build_macro_process_sipoc_report_context(*, macro_id: int, company_id: int) -> dict[str, Any]:
    """Monta a emissão client-safe do snapshot SIPOC publicado.

    A leitura parte do `company_id` da empresa ativa e nunca usa um snapshot de
    rascunho: o PDF sempre representa a versão publicada do macroprocesso.
    """
    macro = MacroProcess.query.filter_by(id=macro_id, company_id=company_id).first()
    if not macro:
        raise ValueError("Macroprocesso não encontrado para a empresa ativa.")

    company = Company.query.filter_by(id=company_id).first()
    if not company:
        raise ValueError("Empresa não encontrada para o macroprocesso informado.")

    bundle = get_macro_process_sipoc_bundle(
        macro_process_id=macro.id,
        company_id=company_id,
    )
    snapshot = bundle.get("published_snapshot")
    if not snapshot:
        raise ValueError("Este macroprocesso não possui um SIPOC publicado para emissão.")

    return {
        "company": company,
        "macro": macro,
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "sipoc": _serialize_report_sipoc(snapshot),
    }


def _serialize_report_sipoc(snapshot: dict[str, Any]) -> dict[str, Any]:
    items_by_lane = snapshot.get("items") or {}
    return {
        "title": snapshot.get("title") or "SIPOC de Macroprocesso",
        "objective": snapshot.get("objective") or "Objetivo não informado.",
        "version": snapshot.get("version") or 1,
        "published_at": _format_published_at(snapshot.get("published_at")),
        "boundaries": [
            ("Início", snapshot.get("start_boundary") or "Não informado."),
            ("Fim", snapshot.get("end_boundary") or "Não informado."),
        ],
        "details": [
            ("Evento disparador", snapshot.get("trigger_event")),
            ("Requisitos do cliente", snapshot.get("customer_requirements")),
            ("Restrições", snapshot.get("constraints_notes")),
            ("Medidas / indicadores", snapshot.get("measures_notes")),
        ],
        "lanes": [
            {
                "key": key,
                "label": label,
                "items": items_by_lane.get(key) or [{"title": "Não informado.", "description": None}],
            }
            for key, label in LANES
        ],
    }


def _format_published_at(value: str | None) -> str:
    if not value:
        return "Não informado"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(value)
