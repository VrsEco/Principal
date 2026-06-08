from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

from models import (
    Company,
    Indicator,
    IndicatorData,
    IndicatorGoal,
    MacroProcess,
    Process,
    ProcessBpmnDiagram,
    ProcessRoutine,
    Routine,
    db,
)
from utils.indicator_filters import PROCESS_SOURCE_MODULES, indicator_supports_source_context


KANBAN_STAGE_LABELS = {
    "inbox": "Fora de escopo",
    "designing": "Desenho",
    "deploying": "Implantação",
    "stabilizing": "Estabilização",
    "stable": "Estável",
}

STRUCTURING_LABELS = {
    "inbox": "Inbox",
    "initiated": "Iniciado",
    "in_progress": "Em estruturação",
    "structured": "Estruturado",
    "stabilized": "Estabilizado",
    "stable": "Estável",
}

PERFORMANCE_LABELS = {
    "critical": "Crítico",
    "below": "Abaixo do esperado",
    "satisfactory": "Satisfatório",
}

SCHEDULE_LABELS = {
    "daily": "Diária",
    "weekly": "Semanal",
    "monthly": "Mensal",
    "quarterly": "Trimestral",
    "yearly": "Anual",
    "specific": "Data específica",
}


@dataclass(frozen=True)
class MacroProcessBookContext:
    company: Company
    macro: MacroProcess
    generated_at: str
    first_page: dict[str, Any]
    sipoc: dict[str, Any]
    processes: list[dict[str, Any]]
    routines: list[dict[str, Any]]
    indicators: list[dict[str, Any]]
    safe_delivery: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "macro": self.macro,
            "generated_at": self.generated_at,
            "first_page": self.first_page,
            "sipoc": self.sipoc,
            "processes": self.processes,
            "routines": self.routines,
            "indicators": self.indicators,
            "safe_delivery": self.safe_delivery,
        }


def build_macro_process_book_context(
    *,
    macro_id: int,
    company_id: int,
    request_root: str | None = None,
) -> dict[str, Any]:
    """Monta contexto cliente-safe do Book do Macroprocesso.

    Guardrail: o macroprocesso e todos os agregados são filtrados por
    `company_id`. A versão inicial não expõe contratos de execução,
    matriz analítica de riscos/gaps ou anexo AI-readable.
    """

    macro = (
        MacroProcess.query.options(joinedload(MacroProcess.area))
        .filter(MacroProcess.id == macro_id, MacroProcess.company_id == company_id)
        .first()
    )
    if not macro:
        raise ValueError("Macroprocesso não encontrado para a empresa ativa.")

    company = Company.query.filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Empresa não encontrada para o macroprocesso informado.")

    processes = _load_processes(macro_id=macro.id, company_id=company_id)
    process_ids = [process.id for process in processes]
    pop_counts = _load_pop_counts(process_ids=process_ids, company_id=company_id)
    routine_counts = _load_routine_counts(process_ids=process_ids, company_id=company_id)
    indicator_counts = _load_indicator_counts(process_ids=process_ids, company_id=company_id)
    published_flow_ids = _load_published_flow_ids(process_ids=process_ids, company_id=company_id)
    indicators = _load_macro_indicators(process_ids=process_ids, company_id=company_id)
    routines = _load_macro_routines(process_ids=process_ids, company_id=company_id)
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    root_url = (request_root or "").rstrip("/")

    process_payload = [
        _serialize_process(
            process,
            pop_count=pop_counts.get(process.id, 0),
            routine_count=routine_counts.get(process.id, 0),
            indicator_count=indicator_counts.get(process.id, 0),
            has_published_flow=process.id in published_flow_ids,
            root_url=root_url,
        )
        for process in processes
    ]

    context = MacroProcessBookContext(
        company=company,
        macro=macro,
        generated_at=generated_at,
        first_page=_build_first_page(
            company=company,
            macro=macro,
            generated_at=generated_at,
            process_count=len(process_payload),
            pop_count=sum(pop_counts.values()),
            routine_count=sum(routine_counts.values()),
            indicator_count=len(indicators),
            published_flow_count=len(published_flow_ids),
        ),
        sipoc=_build_sipoc_context(macro=macro, processes=process_payload),
        processes=process_payload,
        routines=routines,
        indicators=indicators,
        safe_delivery=_build_safe_delivery_context(),
    )
    return context.to_dict()


def _load_processes(*, macro_id: int, company_id: int) -> list[Process]:
    return (
        Process.query.filter(
            Process.company_id == company_id,
            Process.macro_id == macro_id,
            or_(Process.is_active.is_(True), Process.is_active.is_(None)),
        )
        .order_by(Process.order_index.asc(), Process.code.asc(), Process.id.asc())
        .all()
    )


def _load_pop_counts(*, process_ids: list[int], company_id: int) -> dict[int, int]:
    if not process_ids:
        return {}
    rows = (
        db.session.query(ProcessRoutine.process_id, db.func.count(ProcessRoutine.id))
        .filter(ProcessRoutine.company_id == company_id)
        .filter(ProcessRoutine.process_id.in_(process_ids))
        .filter(or_(ProcessRoutine.is_active.is_(True), ProcessRoutine.is_active.is_(None)))
        .group_by(ProcessRoutine.process_id)
        .all()
    )
    return _rows_to_int_dict(rows)


def _load_routine_counts(*, process_ids: list[int], company_id: int) -> dict[int, int]:
    if not process_ids:
        return {}
    rows = (
        db.session.query(Routine.process_id, db.func.count(Routine.id))
        .filter(Routine.company_id == company_id)
        .filter(Routine.process_id.in_(process_ids))
        .filter(or_(Routine.is_active.is_(True), Routine.is_active.is_(None)))
        .group_by(Routine.process_id)
        .all()
    )
    return _rows_to_int_dict(rows)


def _load_indicator_counts(*, process_ids: list[int], company_id: int) -> dict[int, int]:
    if not process_ids:
        return {}
    rows = (
        db.session.query(Indicator.process_id, db.func.count(Indicator.id))
        .filter(Indicator.company_id == company_id)
        .filter(Indicator.is_active.is_(True))
        .filter(Indicator.process_id.in_(process_ids))
        .group_by(Indicator.process_id)
        .all()
    )
    payload = _rows_to_int_dict(rows)
    if indicator_supports_source_context():
        source_rows = (
            db.session.query(Indicator.source_id, db.func.count(Indicator.id))
            .filter(Indicator.company_id == company_id)
            .filter(Indicator.is_active.is_(True))
            .filter(Indicator.source_module.in_(PROCESS_SOURCE_MODULES))
            .filter(Indicator.source_id.in_(process_ids))
            .group_by(Indicator.source_id)
            .all()
        )
        for process_id, total in _rows_to_int_dict(source_rows).items():
            payload[process_id] = max(payload.get(process_id, 0), total)
    return payload


def _load_published_flow_ids(*, process_ids: list[int], company_id: int) -> set[int]:
    if not process_ids:
        return set()
    return {
        int(process_id)
        for (process_id,) in (
            db.session.query(ProcessBpmnDiagram.process_id)
            .filter(ProcessBpmnDiagram.company_id == company_id)
            .filter(ProcessBpmnDiagram.status == "published")
            .filter(ProcessBpmnDiagram.process_id.in_(process_ids))
            .distinct()
            .all()
        )
        if process_id is not None
    }


def _load_macro_indicators(*, process_ids: list[int], company_id: int) -> list[dict[str, Any]]:
    if not process_ids:
        return []

    indicator_filter = Indicator.process_id.in_(process_ids)
    if indicator_supports_source_context():
        indicator_filter = or_(
            Indicator.process_id.in_(process_ids),
            and_(
                Indicator.source_module.in_(PROCESS_SOURCE_MODULES),
                Indicator.source_id.in_(process_ids),
            ),
        )

    indicators = (
        Indicator.query.filter(Indicator.company_id == company_id)
        .filter(Indicator.is_active.is_(True))
        .filter(indicator_filter)
        .order_by(Indicator.code.asc(), Indicator.id.asc())
        .limit(18)
        .all()
    )

    payload = []
    for indicator in indicators:
        process_id = getattr(indicator, "process_id", None) or getattr(indicator, "source_id", None)
        latest_goal = (
            IndicatorGoal.query.filter(
                IndicatorGoal.company_id == company_id,
                IndicatorGoal.indicator_id == indicator.id,
            )
            .order_by(IndicatorGoal.goal_date.desc(), IndicatorGoal.created_at.desc())
            .first()
        )
        latest_record = (
            IndicatorData.query.filter(
                IndicatorData.company_id == company_id,
                IndicatorData.indicator_id == indicator.id,
            )
            .order_by(IndicatorData.measured_date.desc(), IndicatorData.created_at.desc())
            .first()
        )
        payload.append(
            {
                "id": indicator.id,
                "code": indicator.code or "-",
                "name": indicator.name,
                "process_id": process_id,
                "unit": indicator.unit,
                "current_value": _format_indicator_value(
                    latest_record.measured_value if latest_record else None,
                    indicator.unit,
                ),
                "goal_value": _format_indicator_value(
                    latest_goal.goal_value if latest_goal else None,
                    indicator.unit,
                ),
                "last_record_date": latest_record.measured_date.strftime("%d/%m/%Y")
                if latest_record and latest_record.measured_date
                else None,
            }
        )
    return payload


def _load_macro_routines(*, process_ids: list[int], company_id: int) -> list[dict[str, Any]]:
    if not process_ids:
        return []
    routines = (
        Routine.query.filter(
            Routine.company_id == company_id,
            Routine.process_id.in_(process_ids),
            or_(Routine.is_active.is_(True), Routine.is_active.is_(None)),
        )
        .order_by(Routine.process_id.asc(), Routine.order_index.asc(), Routine.id.asc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": routine.id,
            "process_id": routine.process_id,
            "code": routine.code or "-",
            "name": routine.name,
            "description": routine.description,
            "schedule_label": SCHEDULE_LABELS.get(
                (routine.schedule_type or "").lower(),
                routine.schedule_type or "Não definido",
            ),
            "schedule_value": routine.schedule_value,
            "start_time": routine.start_time,
        }
        for routine in routines
    ]


def _serialize_process(
    process: Process,
    *,
    pop_count: int,
    routine_count: int,
    indicator_count: int,
    has_published_flow: bool,
    root_url: str,
) -> dict[str, Any]:
    return {
        "id": process.id,
        "code": process.code or "-",
        "name": process.name,
        "display_name": _compose_title(process.code, process.name),
        "description": process.description,
        "responsible": process.responsible or "Não definido",
        "structuring_label": STRUCTURING_LABELS.get(
            (process.structuring_level or "").lower(),
            "Não informado",
        ),
        "performance_label": PERFORMANCE_LABELS.get(
            (process.performance_level or "").lower(),
            "Não informado",
        ),
        "stage_label": KANBAN_STAGE_LABELS.get(
            (process.kanban_stage or "").lower(),
            process.kanban_stage or "Não informado",
        ),
        "book_url": f"{root_url}/processes/{process.id}/book" if root_url else f"/processes/{process.id}/book",
        "stats": {
            "pop_count": int(pop_count or 0),
            "routine_count": int(routine_count or 0),
            "indicator_count": int(indicator_count or 0),
            "has_published_flow": bool(has_published_flow),
        },
    }


def _build_first_page(
    *,
    company: Company,
    macro: MacroProcess,
    generated_at: str,
    process_count: int,
    pop_count: int,
    routine_count: int,
    indicator_count: int,
    published_flow_count: int,
) -> dict[str, Any]:
    area = getattr(macro, "area", None)
    return {
        "title": _compose_title(macro.code, macro.name),
        "subtitle": macro.description
        or "Book executivo do macroprocesso, incluindo escopo, mapa integrado, processos, rotinas e indicadores.",
        "generated_at": generated_at,
        "company_name": company.name,
        "area_name": _compose_title(getattr(area, "code", None), getattr(area, "name", None), fallback="Não definido"),
        "owner_name": macro.owner or "Não definido",
        "stats": [
            {"label": "Processos", "value": process_count},
            {"label": "Fluxos publicados", "value": published_flow_count},
            {"label": "Atividades POP", "value": pop_count},
            {"label": "Rotinas", "value": routine_count},
            {"label": "Indicadores", "value": indicator_count},
        ],
    }


def _build_sipoc_context(*, macro: MacroProcess, processes: list[dict[str, Any]]) -> dict[str, Any]:
    area = getattr(macro, "area", None)
    process_items = [
        {"title": item["display_name"], "description": item.get("description")}
        for item in processes[:7]
    ]
    if len(processes) > 7:
        process_items.append(
            {
                "title": f"+ {len(processes) - 7} processo(s) adicional(is)",
                "description": "Ver portfólio de processos do macroprocesso.",
            }
        )
    return {
        "title": f"SIPOC executivo - {_compose_title(macro.code, macro.name)}",
        "objective": macro.description or "Enquadrar o macroprocesso em visão executiva cliente-safe.",
        "start_boundary": "Demanda, evento ou rotina que inicia algum processo do macroprocesso.",
        "end_boundary": "Resultado do macroprocesso entregue, registrado e acompanhado por indicadores.",
        "lanes": [
            {
                "key": "supplier",
                "label": "Fornecedores",
                "items": [
                    {"title": getattr(area, "name", None) or "Área responsável"},
                    {"title": macro.owner or "Dono do macroprocesso"},
                    {"title": "Equipes executoras"},
                ],
            },
            {
                "key": "input",
                "label": "Entradas",
                "items": [
                    {"title": "Demandas operacionais"},
                    {"title": "Dados mínimos do cliente/processo"},
                    {"title": "Critérios de execução e acompanhamento"},
                ],
            },
            {
                "key": "process",
                "label": "Macroetapas",
                "items": process_items or [{"title": "Nenhum processo ativo cadastrado"}],
            },
            {
                "key": "output",
                "label": "Saídas",
                "items": [
                    {"title": "Entrega operacional"},
                    {"title": "Rotinas e registros atualizados"},
                    {"title": "Indicadores de acompanhamento"},
                ],
            },
            {
                "key": "customer",
                "label": "Clientes",
                "items": [
                    {"title": "Cliente interno ou externo"},
                    {"title": "Gestor responsável"},
                    {"title": "Diretoria e equipes envolvidas"},
                ],
            },
        ],
    }


def _build_safe_delivery_context() -> dict[str, Any]:
    return {
        "title": "Regra de entrega cliente-safe",
        "summary": (
            "Esta versão do Book do Macroprocesso é executiva e operacional. "
            "Ela não expõe a camada interna de arquitetura, automação e agentes."
        ),
        "excluded_items": [
            "matriz consolidada processo x rotina x indicador x risco x evidência x contrato de execução",
            "riscos, controles, gaps e plano de melhoria em nível analítico",
            "contratos de execução por atividade",
            "anexo AI-readable para MCP/Sapiens",
        ],
    }


def _rows_to_int_dict(rows: list[tuple[int | None, int]]) -> dict[int, int]:
    payload: dict[int, int] = {}
    for key, value in rows:
        if key is None:
            continue
        payload[int(key)] = int(value or 0)
    return payload


def _compose_title(code: str | None, name: str | None, fallback: str = "Não definido") -> str:
    safe_code = (code or "").strip()
    safe_name = (name or "").strip()
    if safe_code and safe_name:
        return f"{safe_code} - {safe_name}"
    if safe_name:
        return safe_name
    if safe_code:
        return safe_code
    return fallback


def _format_number(value: Any) -> str:
    if value is None:
        return "0"
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}".replace(".", ",")
    return str(value)


def _format_indicator_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "Não informado"
    formatted = _format_number(value)
    if unit:
        return f"{formatted} {unit}"
    return formatted
