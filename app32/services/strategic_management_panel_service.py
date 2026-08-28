from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from models import (
    Employee,
    Indicator,
    IndicatorData,
    IndicatorEntityLink,
    IndicatorGoal,
    IndicatorLineOfSight,
    Meeting,
    Process,
    ProcessStrategyProfile,
    Project,
    ProjectTask,
    db,
)
from services.efficiency_collaborators_service import build_team_efficiency_summary
from services.indicator_service import goal_is_effective
from services.structuring_journey_service import StructuringJourneyService
from utils.indicator_ranges import normalize_performance_ranges


GROUP_DEFINITIONS = {
    "strategic": {
        "label": "Indicadores Estratégicos",
        "short_label": "Estratégicos",
        "subtitle": "Resultado, direção e objetivos corporativos",
        "color": "#ef4444",
    },
    "processes": {
        "label": "Indicadores de Processos",
        "short_label": "Processos",
        "subtitle": "Rotina, BPMN, SLA e maturidade operacional",
        "color": "#f59e0b",
    },
    "projects": {
        "label": "Indicadores de Projetos",
        "short_label": "Projetos",
        "subtitle": "Execução fora da rotina e iniciativas corretivas",
        "color": "#3b82f6",
    },
    "team_efficiency": {
        "label": "Eficiência da Equipe",
        "short_label": "Equipe",
        "subtitle": "Eficiência, capacidade e entrega do time",
        "color": "#10b981",
    },
    "webs": {
        "label": "Indicadores de Teia",
        "short_label": "Teias",
        "subtitle": "Conexões, dependências e alinhamentos críticos",
        "color": "#7c3aed",
    },
}


def build_strategic_management_panel(
    company_id: int,
    *,
    period: str | None = None,
    audience: str | None = "consultant",
) -> dict[str, Any]:
    """Monta a visão executiva tenant-safe do Painel de Gestão Estratégica.

    A service não cria cadastros nem altera estado: apenas consolida dados já
    existentes do tenant para leitura e acionamento gerencial pela UI.
    """
    if not company_id:
        raise ValueError("company_id é obrigatório.")

    period_context = _resolve_period(period)
    today = date.today()
    normalized_audience = _normalize_audience(audience)

    indicators = (
        Indicator.query.filter(Indicator.company_id == company_id)
        .filter(Indicator.is_active.is_(True))
        .order_by(Indicator.name.asc())
        .all()
    )
    indicator_ids = [indicator.id for indicator in indicators]
    latest_data = _latest_indicator_data(company_id, indicator_ids, period_context)
    goals = _latest_indicator_goals(company_id, indicator_ids, period_context)

    projects_by_id = {
        project.id: project
        for project in Project.query.filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .all()
    }
    project_task_stats = _project_task_stats(company_id)
    indicator_task_links = _indicator_task_links(company_id)
    employees_by_id = {
        employee.id: employee
        for employee in Employee.query.filter(Employee.company_id == company_id).all()
    }

    groups: dict[str, dict[str, Any]] = {
        key: {
            **definition,
            "key": key,
            "total": 0,
            "semaphore": Counter({"green": 0, "yellow": 0, "red": 0, "blue": 0, "gray": 0}),
            "alerts": [],
            "subgroups": defaultdict(list),
            "items": [],
        }
        for key, definition in GROUP_DEFINITIONS.items()
    }

    for indicator in indicators:
        group_key = _classify_indicator(indicator)
        latest = latest_data.get(indicator.id)
        goal = goals.get(indicator.id)
        status = _evaluate_indicator_status(indicator, latest, goal)
        goal_routines = _goal_routines_payload(goal)
        responsible = employees_by_id.get(indicator.responsible_id)
        project = projects_by_id.get(indicator.project_id) if indicator.project_id else None
        project_status = _project_execution_status(project, project_task_stats.get(indicator.project_id or 0))

        item = {
            "id": indicator.id,
            "code": indicator.full_code or indicator.code,
            "name": indicator.name,
            "description": indicator.description,
            "group": group_key,
            "subgroup": _infer_subgroup(indicator, group_key),
            "semaphore": status["semaphore"],
            "situation": status["label"],
            "objective": indicator.description or indicator.notes or "Objetivo não informado no cadastro do indicador.",
            "unit": indicator.unit or "",
            "polarity": indicator.polarity or "positive",
            "goal": _decimal_to_float(getattr(goal, "goal_value", None)),
            "goal_id": getattr(goal, "id", None),
            "goal_name": getattr(goal, "name", None),
            "goal_type": getattr(goal, "goal_type", None),
            "goal_kind": getattr(goal, "goal_kind", None),
            "goal_scope": getattr(goal, "goal_scope", None),
            "goal_period_start": _date_to_iso(getattr(goal, "period_start", None)),
            "goal_period_end": _date_to_iso(
                getattr(goal, "period_end", None) or getattr(goal, "goal_date", None)
            ),
            "goal_date": _date_to_iso(
                getattr(goal, "period_end", None) or getattr(goal, "goal_date", None)
            ),
            "routine_ids": [routine["id"] for routine in goal_routines],
            "measurement_routines": goal_routines,
            "current_value": _decimal_to_float(getattr(latest, "measured_value", None)),
            "measured_date": _date_to_iso(getattr(latest, "measured_date", None)),
            "responsible": {
                "id": responsible.id,
                "name": responsible.name,
                "email": responsible.email,
            }
            if responsible
            else None,
            "project": _project_payload(project, project_status),
            "activities": _merged_activity_payload(
                project,
                project_task_stats.get(indicator.project_id or 0),
                indicator_task_links.get(indicator.id, []),
            ),
            "status_detail": status["detail"],
            "next_charge": "Próxima reunião de gestão do período",
        }

        group = groups[group_key]
        group["total"] += 1
        group["semaphore"][item["semaphore"]] += 1
        group["items"].append(item)
        group["subgroups"][item["subgroup"]].append(item)
        if item["semaphore"] in {"red", "yellow"}:
            group["alerts"].append(item)

    _enrich_web_group(groups["webs"], company_id, indicators, projects_by_id, project_task_stats)
    _enrich_team_efficiency_group(groups["team_efficiency"], company_id, period_context)
    _enrich_group_monitoring_coverage(
        groups["processes"],
        company_id=company_id,
        indicators=indicators,
        target_type="process",
    )
    _enrich_group_monitoring_coverage(
        groups["projects"],
        company_id=company_id,
        indicators=indicators,
        target_type="project",
    )
    structuring_trail = _build_structuring_trail(
        company_id=company_id,
        audience=normalized_audience,
        indicators=indicators,
        active_projects=list(projects_by_id.values()),
        meetings=_upcoming_meetings(company_id, today),
    )

    ordered_groups = []
    for key in ("strategic", "processes", "projects", "team_efficiency", "webs"):
        group = groups[key]
        group["semaphore"] = dict(group["semaphore"])
        group["alerts_count"] = len(group["alerts"])
        group["subgroups"] = [
            {"name": name, "total": len(items), "items": items}
            for name, items in sorted(group["subgroups"].items())
        ]
        ordered_groups.append(group)

    return {
        "company_id": company_id,
        "audience": normalized_audience,
        "period": period_context,
        "structuring_trail": structuring_trail,
        "groups": ordered_groups,
        "meetings": structuring_trail["meetings"],
        "form_options": _form_options(company_id, employees_by_id, projects_by_id),
        "actions": {
            "new_meeting_url": f"/meetings/company/{company_id}",
            "new_activity_project_url": "/projects/new",
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def _normalize_audience(audience: str | None) -> str:
    raw = str(audience or "consultant").strip().lower()
    return raw if raw in {"client", "consultant"} else "consultant"


def _build_structuring_trail(
    *,
    company_id: int,
    audience: str,
    indicators: list[Indicator],
    active_projects: list[Project],
    meetings: list[dict[str, Any]],
) -> dict[str, Any]:
    journey = StructuringJourneyService.get_journey(company_id=company_id, audience=audience, scope="company")
    blocks_by_key = {block["key"]: block for block in journey.get("blocks", [])}

    process_indicators = [item for item in indicators if _classify_indicator(item) == "processes"]
    strategic_indicators = [item for item in indicators if _classify_indicator(item) == "strategic"]
    active_projects = [project for project in active_projects if getattr(project, "is_deleted", False) is False]
    process_profiles = {
        int(profile.process_id): profile
        for profile in ProcessStrategyProfile.query.filter(ProcessStrategyProfile.company_id == company_id).all()
        if getattr(profile, "process_id", None) is not None
    }
    finalistic_process_ids = {
        process_id for process_id, profile in process_profiles.items() if _is_finalistic_profile(profile)
    }
    scoped_finalistic_indicators = [
        indicator for indicator in process_indicators if getattr(indicator, "process_id", None) in finalistic_process_ids
    ]
    finalistic_scope_mode = "explicit_finalistic_profiles" if scoped_finalistic_indicators else "fallback_all_process_indicators"
    if not scoped_finalistic_indicators:
        scoped_finalistic_indicators = list(process_indicators)

    indicator_ids = [int(item.id) for item in process_indicators if getattr(item, "id", None) is not None]
    measurement_rows = _load_indicator_measurements(company_id, indicator_ids)
    goals_by_indicator = _load_indicator_goals_history(company_id, indicator_ids)

    phase_00_deliverables = [
        _phase_deliverable(
            key="process_architecture",
            label="Arquitetura de processos",
            source_block=blocks_by_key.get("processes"),
            detail="Mapa com áreas, macroprocessos, processos essenciais e donos.",
        ),
        _phase_deliverable(
            key="basic_indicators",
            label="Árvore de indicadores básicos",
            ready=bool(strategic_indicators),
            maturity_pct=100 if strategic_indicators else 0,
            detail=f"{len(strategic_indicators)} indicador(es) corporativo(s)/estratégico(s) ativo(s).",
            missing_message="Cadastre indicadores básicos/vitais da empresa para fechar a fase 00.",
        ),
        _phase_deliverable(
            key="project_engine",
            label="Motor de projetos operante",
            ready=bool(active_projects),
            maturity_pct=100 if active_projects else 0,
            detail=f"{len(active_projects)} projeto(s) ativo(s) disponível(is) para follow-up e ação corretiva.",
            missing_message="Falta evidência de motor de projetos operante no tenant.",
        ),
        _phase_deliverable(
            key="organogram",
            label="Organograma",
            ready=False,
            maturity_pct=0,
            detail="Dependência conhecida: módulo de organograma ainda não existe no APP32.",
            missing_message="Spike/build do organograma é obrigatório para fechar a fase 00.",
            dependency=True,
        ),
    ]

    modeling_block = blocks_by_key.get("processes") or {}
    phase_01_deliverables = [
        _phase_deliverable(
            key="finalistic_modeling",
            label="Processos finalísticos modelados",
            source_block=modeling_block,
            detail="MVP usa a cobertura de modelagem existente; classificação explícita de finalísticos ainda é lacuna de dados.",
        ),
        _phase_deliverable(
            key="finalistic_indicators",
            label="Indicadores por processo",
            ready=bool(process_indicators),
            maturity_pct=100 if process_indicators else 0,
            detail=f"{len(process_indicators)} indicador(es) de processo ativo(s).",
            missing_message="Associe indicadores aos processos modelados para sustentar a fase 01.",
        ),
        _phase_deliverable(
            key="stable_cycles",
            label="Gate estável (N ciclos)",
            stable_gate=_build_stability_gate_payload(
                indicators=scoped_finalistic_indicators,
                measurement_rows=measurement_rows,
                goals_by_indicator=goals_by_indicator,
                scope_label="processos finalísticos",
                scope_mode=finalistic_scope_mode,
            ),
        ),
    ]

    phase_02_deliverables = [
        _phase_deliverable(
            key="all_process_modeling",
            label="Todos os processos modelados",
            source_block=modeling_block,
            detail="Expansão da modelagem para Gestão + Apoio com o mesmo motor BPMN/POP.",
        ),
        _phase_deliverable(
            key="all_process_indicators",
            label="Cobertura de indicadores por processo",
            ready=bool(process_indicators),
            maturity_pct=100 if process_indicators else 0,
            detail="Cobertura atual reaproveita indicadores ligados a processos existentes.",
            missing_message="Amplie a linha de visada dos indicadores para todos os processos.",
        ),
        _phase_deliverable(
            key="stable_all_cycles",
            label="Gate estável em todos os processos",
            stable_gate=_build_stability_gate_payload(
                indicators=process_indicators,
                measurement_rows=measurement_rows,
                goals_by_indicator=goals_by_indicator,
                scope_label="todos os processos",
                scope_mode="all_process_indicators",
            ),
        ),
    ]

    phase_03_deliverables = [
        _phase_deliverable(
            key="strategic_identity",
            label="Identidade e alinhamento estratégico",
            source_block=blocks_by_key.get("identity"),
            detail="Identidade aprofundada, pilares, objetivos e elementos de cenário/alinhamento.",
        ),
        _phase_deliverable(
            key="strategic_cycle",
            label="Ciclo de gestão estratégica rodando",
            ready=bool(meetings),
            maturity_pct=100 if meetings else 0,
            detail=f"{len(meetings)} reunião(ões) futura(s) já aparecem no cockpit estratégico.",
            missing_message="Agende/reforce a cadência de revisão estratégica para fechar a fase 03.",
        ),
    ]

    phases = [
        _build_phase(
            code="00",
            key="phase_00",
            label="Básico",
            promise="Coloca a casa em ordem para executar com donos, arquitetura mínima e rotina gerencial.",
            gate_name="Funcionando",
            gate_rule="indicadores básicos alimentados e revisados na rotina; donos definidos; motor de projetos operante",
            deliverables=phase_00_deliverables,
        ),
        _build_phase(
            code="01",
            key="phase_01",
            label="Processos Finalísticos",
            promise="Foca o que gera valor ao cliente primeiro, com modelagem e indicador por processo.",
            gate_name="Estável",
            gate_rule="indicador na meta/trajetória por N ciclos consecutivos (default 3, configurável por indicador)",
            deliverables=phase_01_deliverables,
        ),
        _build_phase(
            code="02",
            key="phase_02",
            label="Todos os Processos",
            promise="Expande a governança para Gestão + Apoio e tira a operação do improviso.",
            gate_name="Estável",
            gate_rule="mesmo critério de estabilidade, aplicado a todos os processos modelados",
            deliverables=phase_02_deliverables,
        ),
        _build_phase(
            code="03",
            key="phase_03",
            label="Plan. e Gestão Estratégicos",
            promise="Transforma a estrutura em ciclo estratégico recorrente, com direção e revisão.",
            gate_name="Rodando",
            gate_rule="ciclo de gestão estratégica ativo, com revisão periódica acontecendo",
            deliverables=phase_03_deliverables,
        ),
    ]

    current_index = next((index for index, phase in enumerate(phases) if not phase["gate"]["ready"]), len(phases) - 1)
    if all(phase["gate"]["ready"] for phase in phases):
        current_index = len(phases) - 1

    for index, phase in enumerate(phases):
        phase["state"] = "completed" if index < current_index else "current" if index == current_index else "future"
        phase["is_completed"] = phase["state"] == "completed"
        phase["is_current"] = phase["state"] == "current"
        phase["is_future"] = phase["state"] == "future"

    current_phase = phases[current_index]
    next_phase = phases[current_index + 1] if current_index + 1 < len(phases) else None
    hero_title = (
        f"Fase atual: {current_phase['code']} — {current_phase['maturity_pct']}% até o gate"
        + (f" · Próximo nível: {next_phase['code']}" if next_phase else " · Jornada completa")
    )
    hero_subtitle = (
        current_phase["client_pulse"]
        if audience == "client"
        else f"Próximo item faltante: {current_phase['next_missing_label']}"
    )

    return {
        "audience": audience,
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "current_phase_key": current_phase["key"],
        "current_phase_code": current_phase["code"],
        "next_phase_code": next_phase["code"] if next_phase else None,
        "phases": phases,
        "journey_source": {
            "read_model": journey.get("read_model"),
            "journey_key": journey.get("journey_key"),
            "gate_policy": journey.get("gate_policy"),
        },
        "meetings": meetings,
    }


def _phase_deliverable(
    *,
    key: str,
    label: str,
    source_block: dict[str, Any] | None = None,
    stable_gate: dict[str, Any] | None = None,
    ready: bool | None = None,
    maturity_pct: int | None = None,
    detail: str | None = None,
    missing_message: str | None = None,
    dependency: bool = False,
) -> dict[str, Any]:
    if stable_gate is not None:
        ready = bool(stable_gate.get("ready"))
        maturity_pct = int(stable_gate.get("maturity_pct") or 0)
        dependency = bool(stable_gate.get("dependency"))
        return {
            "key": key,
            "label": label,
            "ready": ready,
            "maturity_pct": maturity_pct,
            "detail": stable_gate.get("detail") or "",
            "dependency": dependency,
            "status": "ready" if ready else "dependency" if dependency else "pending",
            "next_missing_label": stable_gate.get("next_missing_label") or "Sem pendência operacional.",
            "source_block_key": None,
            "missing_items": list(stable_gate.get("missing_items") or []),
            "subblocks": [],
            "stable_gate": stable_gate,
        }

    if source_block is not None:
        source_gate = source_block.get("gate") or {}
        ready = bool(source_gate.get("ready"))
        maturity_pct = int(source_block.get("maturity_pct") or 0)
        missing_items = list(source_gate.get("missing_essentials") or [])
        missing_messages = [item.get("missing_to_ready", [None])[0] for item in source_block.get("subblocks", []) if item.get("missing_to_ready")]
        next_missing_label = ", ".join(item.get("label") for item in missing_items if item.get("label")) or (
            next((message for message in missing_messages if message), None) or missing_message or "Sem pendência operacional."
        )
        return {
            "key": key,
            "label": label,
            "ready": ready,
            "maturity_pct": maturity_pct,
            "detail": detail or source_gate.get("message") or "",
            "dependency": dependency,
            "status": "ready" if ready else "dependency" if dependency else "pending",
            "next_missing_label": next_missing_label,
            "source_block_key": source_block.get("key"),
            "missing_items": missing_items,
            "subblocks": source_block.get("subblocks") or [],
        }

    return {
        "key": key,
        "label": label,
        "ready": bool(ready),
        "maturity_pct": int(maturity_pct or 0),
        "detail": detail or "",
        "dependency": dependency,
        "status": "ready" if ready else "dependency" if dependency else "pending",
        "next_missing_label": missing_message or "Sem pendência operacional.",
        "source_block_key": None,
        "missing_items": [],
        "subblocks": [],
    }


def _build_phase(
    *,
    code: str,
    key: str,
    label: str,
    promise: str,
    gate_name: str,
    gate_rule: str,
    deliverables: list[dict[str, Any]],
) -> dict[str, Any]:
    scores = [int(item.get("maturity_pct") or 0) for item in deliverables]
    maturity_pct = round(sum(scores) / len(scores)) if scores else 0
    next_missing = next((item for item in deliverables if not item.get("ready")), None)
    return {
        "code": code,
        "key": key,
        "label": label,
        "promise": promise,
        "deliverables": deliverables,
        "maturity_pct": maturity_pct,
        "next_missing_label": next_missing.get("next_missing_label") if next_missing else "Todos os entregáveis desta fase já estão prontos.",
        "client_pulse": "Você já tem base para subir de nível." if maturity_pct >= 60 else "Ainda faltam bases importantes para consolidar este nível.",
        "gate": {
            "name": gate_name,
            "rule": gate_rule,
            "ready": all(bool(item.get("ready")) for item in deliverables),
            "policy": "soft",
        },
    }


def _load_indicator_measurements(company_id: int, indicator_ids: list[int]) -> dict[int, list[IndicatorData]]:
    if not indicator_ids:
        return {}
    rows = (
        IndicatorData.query.filter(IndicatorData.company_id == company_id)
        .filter(IndicatorData.indicator_id.in_(indicator_ids))
        .order_by(IndicatorData.indicator_id.asc(), IndicatorData.measured_date.desc(), IndicatorData.id.desc())
        .all()
    )
    by_indicator: dict[int, list[IndicatorData]] = {}
    for row in rows:
        by_indicator.setdefault(int(row.indicator_id), []).append(row)
    return by_indicator


def _load_indicator_goals_history(company_id: int, indicator_ids: list[int]) -> dict[int, list[IndicatorGoal]]:
    if not indicator_ids:
        return {}
    rows = (
        IndicatorGoal.query.filter(IndicatorGoal.company_id == company_id)
        .filter(IndicatorGoal.indicator_id.in_(indicator_ids))
        .filter(IndicatorGoal.status == "active")
        .order_by(
            IndicatorGoal.indicator_id.asc(),
            IndicatorGoal.period_end.desc().nullslast(),
            IndicatorGoal.goal_date.desc().nullslast(),
            IndicatorGoal.period_start.desc().nullslast(),
            IndicatorGoal.id.desc(),
        )
        .all()
    )
    by_indicator: dict[int, list[IndicatorGoal]] = {}
    for row in rows:
        by_indicator.setdefault(int(row.indicator_id), []).append(row)
    return by_indicator


def _is_finalistic_profile(profile: ProcessStrategyProfile | None) -> bool:
    customer_type = _slug_text(getattr(profile, "customer_type", None))
    customer_description = _slug_text(getattr(profile, "customer_description", None))
    combined = f"{customer_type} {customer_description}".strip()
    if not combined:
        return False
    internal_markers = {"interno", "internal", "apoio", "support", "suporte", "gestao", "management", "backoffice"}
    if any(marker in combined for marker in internal_markers):
        return False
    external_markers = {"cliente", "customer", "externo", "external", "mercado", "usuario", "venda", "comercial"}
    return any(marker in combined for marker in external_markers)


def _slug_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _build_stability_gate_payload(
    *,
    indicators: list[Indicator],
    measurement_rows: dict[int, list[IndicatorData]],
    goals_by_indicator: dict[int, list[IndicatorGoal]],
    scope_label: str,
    scope_mode: str,
) -> dict[str, Any]:
    if not indicators:
        return {
            "ready": False,
            "maturity_pct": 0,
            "dependency": True,
            "detail": f"Sem indicadores vinculados a {scope_label} para avaliar estabilidade.",
            "next_missing_label": f"Cadastre indicadores por processo para medir estabilidade em {scope_label}.",
            "missing_items": [{"reason": "no_indicators", "label": scope_label}],
            "scope_mode": scope_mode,
            "indicator_summaries": [],
        }

    summaries = []
    ratios: list[float] = []
    missing = []
    for indicator in indicators:
        summary = _indicator_stability_summary(
            indicator=indicator,
            measurements=measurement_rows.get(int(indicator.id), []),
            goals=goals_by_indicator.get(int(indicator.id), []),
        )
        summaries.append(summary)
        ratios.append(summary["completion_ratio"])
        if not summary["ready"]:
            missing.append(summary)

    maturity_pct = int(round((sum(ratios) / len(ratios)) * 100)) if ratios else 0
    ready = not missing
    required_cycles = max((int(item["required_cycles"]) for item in summaries), default=3)
    missing_count = len(missing)
    scope_text = "processos finalísticos" if scope_mode == "explicit_finalistic_profiles" else scope_label
    if ready:
        next_missing_label = f"Todos os indicadores de {scope_text} fecharam o gate estável."
    else:
        next_missing_label = f"Faltam {missing_count} indicador(es) de {scope_text} com estabilidade em {required_cycles} ciclos."
    detail = (
        f"{len(summaries)} indicador(es) avaliados em {scope_text}; "
        f"{sum(1 for item in summaries if item['ready'])} prontos; "
        f"critério: meta ou trajetória clara por N ciclos consecutivos."
    )
    if scope_mode == "fallback_all_process_indicators":
        detail += " Fallback aplicado: não há marcação explícita de finalístico no domínio; usando todos os indicadores de processo."

    return {
        "ready": ready,
        "maturity_pct": maturity_pct,
        "dependency": False,
        "detail": detail,
        "next_missing_label": next_missing_label,
        "missing_items": [
            {
                "indicator_id": item["indicator_id"],
                "label": item["indicator_name"],
                "reason": item["reason"],
                "stable_cycles": item["stable_cycles"],
                "required_cycles": item["required_cycles"],
            }
            for item in missing
        ],
        "scope_mode": scope_mode,
        "indicator_summaries": summaries,
    }


def _indicator_stability_summary(
    *,
    indicator: Indicator,
    measurements: list[IndicatorData],
    goals: list[IndicatorGoal],
) -> dict[str, Any]:
    required_cycles = _indicator_required_stable_cycles(indicator)
    cycle_rows = _dedupe_measurements_by_cycle(measurements)
    evaluated_cycles = []
    stable_cycles = 0
    last_ratio = 0.0

    for row in cycle_rows:
        goal = _resolve_goal_for_measurement(row, goals)
        evaluation = _evaluate_measurement_against_goal(indicator, row, goal)
        if evaluation["is_good"]:
            stable_cycles += 1
        else:
            break
        evaluated_cycles.append(evaluation)
        if len(evaluated_cycles) >= required_cycles:
            break

    if evaluated_cycles:
        last_ratio = min(stable_cycles, required_cycles) / float(required_cycles)
    reason = "ok"
    if not cycle_rows:
        reason = "no_measurements"
    elif not goals:
        reason = "no_goals"
    elif stable_cycles < required_cycles:
        reason = "insufficient_stable_cycles"

    return {
        "indicator_id": int(indicator.id),
        "indicator_name": indicator.name,
        "indicator_code": indicator.full_code or indicator.code,
        "required_cycles": required_cycles,
        "stable_cycles": stable_cycles,
        "ready": stable_cycles >= required_cycles,
        "completion_ratio": last_ratio,
        "reason": reason,
        "cycles_evaluated": evaluated_cycles,
    }


def _indicator_required_stable_cycles(indicator: Indicator) -> int:
    source_config = getattr(indicator, "source_config", None) or {}
    for key in ("required_stable_cycles", "stable_cycles", "gate_cycles"):
        value = source_config.get(key) if isinstance(source_config, dict) else None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = None
        if parsed and parsed > 0:
            return parsed
    return 3


def _dedupe_measurements_by_cycle(measurements: list[IndicatorData]) -> list[IndicatorData]:
    unique: list[IndicatorData] = []
    seen = set()
    for row in sorted(measurements, key=lambda item: ((item.period_end or item.measured_date), item.id), reverse=True):
        cycle_key = (
            getattr(row, "period_start", None) or getattr(row, "measured_date", None),
            getattr(row, "period_end", None) or getattr(row, "measured_date", None),
        )
        if cycle_key in seen:
            continue
        seen.add(cycle_key)
        unique.append(row)
    return unique


def _resolve_goal_for_measurement(measurement: IndicatorData, goals: list[IndicatorGoal]) -> IndicatorGoal | None:
    measurement_date = getattr(measurement, "measured_date", None)
    if getattr(measurement, "goal_id", None):
        for goal in goals:
            if int(goal.id) == int(measurement.goal_id):
                return goal
    for goal in goals:
        period_start = getattr(goal, "period_start", None)
        period_end = getattr(goal, "period_end", None) or getattr(goal, "goal_date", None)
        if period_start and period_end and measurement_date and period_start <= measurement_date <= period_end:
            return goal
    dated_goals = [goal for goal in goals if getattr(goal, "goal_date", None) and measurement_date and goal.goal_date <= measurement_date]
    if dated_goals:
        dated_goals.sort(key=lambda item: (item.goal_date, item.id), reverse=True)
        return dated_goals[0]
    return goals[0] if goals else None


def _evaluate_measurement_against_goal(indicator: Indicator, measurement: IndicatorData, goal: IndicatorGoal | None) -> dict[str, Any]:
    value = _to_float(getattr(measurement, "measured_value", None))
    goal_value = _to_float(getattr(goal, "goal_value", None))
    if value is None or goal_value is None or goal_value == 0:
        return {
            "measured_date": _date_to_iso(getattr(measurement, "measured_date", None)),
            "status": "no_goal",
            "is_good": False,
            "value": value,
            "goal_value": goal_value,
        }

    status = _classify_measurement_status(indicator, value=value, goal=goal)
    return {
        "measured_date": _date_to_iso(getattr(measurement, "measured_date", None)),
        "status": status,
        "is_good": status in {"on_target", "exceeded", "alert"},
        "value": value,
        "goal_value": goal_value,
    }


def _classify_measurement_status(indicator: Indicator, *, value: float, goal: IndicatorGoal) -> str:
    goal_value = _to_float(getattr(goal, "goal_value", None))
    if goal_value in (None, 0):
        return "no_goal"
    ranges = normalize_performance_ranges(getattr(goal, "performance_ranges", None))
    red_max = float(ranges.get("red", 80))
    yellow_max = float(ranges.get("yellow", 90))
    green_max = float(ranges.get("green", 110))
    polarity = str(getattr(indicator, "polarity", "positive") or "positive").strip().lower()
    if polarity == "negative":
        if value <= goal_value * (red_max / 100):
            return "on_target"
        if value <= goal_value * (yellow_max / 100):
            return "alert"
        return "below"

    performance_pct = (value / goal_value) * 100
    if performance_pct >= green_max:
        return "exceeded"
    if performance_pct >= yellow_max:
        return "on_target"
    if performance_pct >= red_max:
        return "alert"
    return "below"


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_period(period: str | None) -> dict[str, Any]:
    today = date.today()
    raw = (period or "month").strip().lower()
    if raw == "quarter":
        quarter = ((today.month - 1) // 3) + 1
        start_month = ((quarter - 1) * 3) + 1
        start = date(today.year, start_month, 1)
        end_month = start_month + 2
        next_month = date(today.year + (1 if end_month == 12 else 0), 1 if end_month == 12 else end_month + 1, 1)
        label = f"{quarter}º trimestre/{today.year}"
    elif raw == "year":
        start = date(today.year, 1, 1)
        next_month = date(today.year + 1, 1, 1)
        label = f"Ano/{today.year}"
    else:
        start = date(today.year, today.month, 1)
        next_month = date(today.year + (1 if today.month == 12 else 0), 1 if today.month == 12 else today.month + 1, 1)
        label = today.strftime("%B/%Y").capitalize()
        raw = "month"
    end = next_month - timedelta(days=1)
    return {"key": raw, "label": label, "start": start.isoformat(), "end": end.isoformat()}


def _latest_indicator_data(company_id: int, indicator_ids: list[int], period: dict[str, Any]) -> dict[int, IndicatorData]:
    if not indicator_ids:
        return {}
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    rows = (
        IndicatorData.query.filter(IndicatorData.company_id == company_id)
        .filter(IndicatorData.indicator_id.in_(indicator_ids))
        .filter(IndicatorData.measured_date >= start)
        .filter(IndicatorData.measured_date <= end)
        .order_by(IndicatorData.indicator_id.asc(), IndicatorData.measured_date.desc(), IndicatorData.id.desc())
        .all()
    )
    latest: dict[int, IndicatorData] = {}
    for row in rows:
        latest.setdefault(row.indicator_id, row)
    return latest


def _latest_indicator_goals(company_id: int, indicator_ids: list[int], period: dict[str, Any]) -> dict[int, IndicatorGoal]:
    if not indicator_ids:
        return {}
    reference_date = date.fromisoformat(period["end"])
    rows = (
        IndicatorGoal.query.filter(IndicatorGoal.company_id == company_id)
        .filter(IndicatorGoal.indicator_id.in_(indicator_ids))
        .order_by(IndicatorGoal.indicator_id.asc(), IndicatorGoal.period_start.desc().nullslast(), IndicatorGoal.id.desc())
        .all()
    )
    grouped: dict[int, list[IndicatorGoal]] = defaultdict(list)
    for row in rows:
        grouped[int(row.indicator_id)].append(row)
    return {
        indicator_id: selected
        for indicator_id, goals in grouped.items()
        if (selected := _select_effective_goal(goals, reference_date)) is not None
    }


def _select_effective_goal(goals: list[IndicatorGoal], reference_date: date) -> IndicatorGoal | None:
    """Seleciona a meta-base vigente, priorizando o escopo corporativo/equipe."""
    effective = [goal for goal in goals if goal_is_effective(goal, reference_date)]
    if not effective:
        return None
    return max(
        effective,
        key=lambda goal: (
            1 if getattr(goal, "goal_kind", "base") == "base" else 0,
            1 if getattr(goal, "goal_scope", "team") == "team" else 0,
            getattr(goal, "period_start", None) or date.min,
            getattr(goal, "id", 0) or 0,
        ),
    )


def _goal_routines_payload(goal: IndicatorGoal | None) -> list[dict[str, Any]]:
    if not goal:
        return []
    routines_by_id: dict[int, dict[str, Any]] = {}
    for link in getattr(goal, "routine_links", []) or []:
        routine = getattr(link, "routine", None)
        routine_id = int(getattr(link, "routine_id", 0) or 0)
        if not routine_id:
            continue
        routines_by_id[routine_id] = {
            "id": routine_id,
            "code": getattr(routine, "code", None),
            "name": getattr(routine, "name", None) or f"Rotina {routine_id}",
        }
    legacy_id = getattr(goal, "routine_id", None)
    if legacy_id and int(legacy_id) not in routines_by_id:
        routines_by_id[int(legacy_id)] = {
            "id": int(legacy_id),
            "code": None,
            "name": f"Rotina {legacy_id}",
        }
    return sorted(
        routines_by_id.values(),
        key=lambda item: ((item.get("code") or ""), item.get("name") or "", item["id"]),
    )


def _project_task_stats(company_id: int) -> dict[int, dict[str, Any]]:
    today = date.today()
    rows = (
        db.session.query(ProjectTask, Project)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .filter(ProjectTask.is_deleted.is_(False))
        .all()
    )
    stats: dict[int, dict[str, Any]] = defaultdict(lambda: {"total": 0, "late": 0, "open": 0, "completed": 0, "items": []})
    for task, project in rows:
        bucket = stats[project.id]
        bucket["total"] += 1
        is_completed = task.stage == "completed" or task.status == "completed"
        due_date = _date_only(task.due_date)
        if is_completed:
            bucket["completed"] += 1
        else:
            bucket["open"] += 1
            if due_date and due_date < today:
                bucket["late"] += 1
        bucket["items"].append(
            {
                "id": task.id,
                "code": task.code,
                "what": task.what,
                "responsible": task.employee_name,
                "due_date": _date_to_iso(due_date),
                "stage": task.stage,
                "status": task.status,
                "late": bool(due_date and due_date < today and not is_completed),
            }
        )
    return stats


def _indicator_task_links(company_id: int) -> dict[int, list[dict[str, Any]]]:
    marker = "APP32_INDICATOR_LINK:"
    rows = (
        db.session.query(ProjectTask, Project)
        .join(Project, Project.id == ProjectTask.project_id)
        .filter(Project.company_id == company_id)
        .filter(Project.is_deleted.is_(False))
        .filter(ProjectTask.is_deleted.is_(False))
        .filter(ProjectTask.notes.ilike(f"%{marker}%"))
        .all()
    )
    links: dict[int, list[dict[str, Any]]] = defaultdict(list)
    today = date.today()
    for task, project in rows:
        indicator_id = _extract_indicator_link(task.notes)
        if not indicator_id:
            continue
        due_date = _date_only(task.due_date)
        is_completed = task.stage == "completed" or task.status == "completed"
        links[indicator_id].append(
            {
                "id": task.id,
                "code": task.code,
                "what": task.what,
                "responsible": task.employee_name,
                "due_date": _date_to_iso(due_date),
                "stage": task.stage,
                "status": task.status,
                "late": bool(due_date and due_date < today and not is_completed),
                "project_id": project.id,
                "project_code": project.code,
                "project_name": project.name,
                "linked_by_indicator": True,
            }
        )
    return links


def _extract_indicator_link(notes: str | None) -> int | None:
    if not notes:
        return None
    marker = "APP32_INDICATOR_LINK:"
    for line in str(notes).splitlines():
        if marker not in line:
            continue
        try:
            return int(line.split(marker, 1)[1].strip().split()[0])
        except (TypeError, ValueError, IndexError):
            return None
    return None


def _classify_indicator(indicator: Indicator) -> str:
    source = (indicator.source_module or "").lower()
    text = " ".join(
        str(value or "").lower()
        for value in [indicator.name, indicator.code, indicator.full_code, indicator.indicator_type, indicator.okr_reference, source]
    )
    if indicator.project_id or source in {"project", "projects", "projetos"}:
        return "projects"
    if indicator.process_id or indicator.routine_id or source in {"process", "processes", "routine", "routines", "bpmn"}:
        return "processes"
    if any(token in text for token in ["teia", "conex", "depend", "rede", "network"]):
        return "webs"
    return "strategic"


def _infer_subgroup(indicator: Indicator, group_key: str) -> str:
    text = f"{indicator.name} {indicator.code} {indicator.full_code or ''}".lower()
    if group_key == "strategic":
        if any(token in text for token in ["comercial", "venda", "cliente", "proposta"]):
            return "Comerciais"
        if any(token in text for token in ["finance", "receita", "custo", "margem", "caixa"]):
            return "Financeiros"
        if any(token in text for token in ["operac", "produção", "produtiv"]):
            return "Operacionais"
        return "Corporativos"
    if group_key == "processes":
        return "Rotina, BPMN e SLA"
    if group_key == "projects":
        return "Projetos e iniciativas"
    return "Conexões e dependências"


def _evaluate_indicator_status(indicator: Indicator, latest: IndicatorData | None, goal: IndicatorGoal | None) -> dict[str, str]:
    current = _to_decimal(getattr(latest, "measured_value", None))
    target = _to_decimal(getattr(goal, "goal_value", None))
    if current is None:
        return {"semaphore": "gray", "label": "Sem medição no período", "detail": "Inclua medição no menu de indicadores."}
    if target is None or target == 0:
        return {"semaphore": "gray", "label": "Sem meta ativa", "detail": "Cadastre meta no menu específico de indicadores."}

    ratio = current / target if (indicator.polarity or "positive") == "positive" else target / current if current else Decimal("0")
    if ratio >= Decimal("1.10"):
        return {"semaphore": "blue", "label": "Acima do range", "detail": "Resultado acima da meta de referência."}
    if ratio >= Decimal("1.00"):
        return {"semaphore": "green", "label": "Dentro do range", "detail": "Indicador dentro da meta."}
    if ratio >= Decimal("0.90"):
        return {"semaphore": "yellow", "label": "Atenção", "detail": "Desvio moderado exige acompanhamento."}
    return {"semaphore": "red", "label": "Fora do range", "detail": "Desvio crítico exige ação corretiva governada."}


def _project_execution_status(project: Project | None, stats: dict[str, Any] | None) -> dict[str, Any] | None:
    if not project:
        return None
    stats = stats or {"total": 0, "late": 0, "open": 0, "completed": 0}
    if stats.get("late", 0) > 0:
        label = "Atividades atrasadas"
        semaphore = "red"
    elif project.status in {"completed", "done"}:
        label = "Concluído"
        semaphore = "green"
    elif stats.get("open", 0) > 0:
        label = "Em execução"
        semaphore = "blue"
    else:
        label = "Sem atividades abertas"
        semaphore = "gray"
    return {"label": label, "semaphore": semaphore, **stats}


def _project_payload(project: Project | None, status: dict[str, Any] | None) -> dict[str, Any] | None:
    if not project:
        return None
    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "owner": project.owner,
        "status": project.status,
        "deadline": _date_to_iso(project.end_date),
        "execution": status,
    }


def _project_activity_payload(project: Project | None, stats: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not project or not stats:
        return []
    return stats.get("items", [])[:5]


def _merged_activity_payload(project: Project | None, stats: dict[str, Any] | None, linked_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    seen = set()
    for item in _project_activity_payload(project, stats) + list(linked_items or []):
        key = int(item.get("id") or 0)
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items[:8]


def _form_options(company_id: int, employees_by_id: dict[int, Employee], projects_by_id: dict[int, Project]) -> dict[str, Any]:
    processes = (
        Process.query.filter(Process.company_id == company_id)
        .order_by(Process.name.asc())
        .all()
    )
    active_projects = [
        project
        for project in projects_by_id.values()
        if project.status not in {"completed", "cancelled", "archived"}
    ]
    return {
        "projects": [
            {"id": project.id, "code": project.code, "name": project.name}
            for project in sorted(active_projects, key=lambda item: item.name or "")
        ],
        "processes": [
            {"id": process.id, "code": process.code, "name": process.name}
            for process in processes
        ],
        "employees": [
            {"id": employee.id, "name": employee.name, "email": employee.email}
            for employee in sorted(employees_by_id.values(), key=lambda item: item.name or "")
        ],
    }


def _enrich_team_efficiency_group(group: dict[str, Any], company_id: int, period: dict[str, Any]) -> None:
    start = date.fromisoformat(period["start"])
    end = date.fromisoformat(period["end"])
    summary = build_team_efficiency_summary(
        company_id=company_id,
        start_date=start,
        end_date=end,
    )

    group["total"] = summary["total"]
    group["card_title"] = summary.get("card_title")
    group["card_subtitle"] = summary.get("card_subtitle")
    group["value_label"] = summary["value_label"]
    group["alert_label"] = summary["alert_label"]
    group["detail_url"] = f"/companies/{company_id}/efficiency-analysis"
    group["summary"] = summary.get("summary") or {}
    group["semaphore"].update(summary["semaphore"])
    group["items"] = list(summary["items"])

    for item in group["items"]:
        group["subgroups"][item["subgroup"]].append(item)
        if item["semaphore"] in {"red", "yellow"}:
            group["alerts"].append(item)


def _enrich_group_monitoring_coverage(
    group: dict[str, Any],
    *,
    company_id: int,
    indicators: list[Indicator],
    target_type: str,
) -> None:
    if target_type == "process":
        total_existing = (
            Process.query.filter(Process.company_id == company_id)
            .filter(Process.is_active.is_(True))
            .count()
        )
        legacy_attr = "process_id"
        source_modules = {"process", "processes", "processo"}
        singular_label = "processo"
        plural_label = "processos"
    elif target_type == "project":
        total_existing = (
            Project.query.filter(Project.company_id == company_id)
            .filter(Project.is_deleted.is_(False))
            .filter(Project.status.notin_(("completed", "cancelled", "archived")))
            .count()
        )
        legacy_attr = "project_id"
        source_modules = {"project", "projects", "projeto", "projetos"}
        singular_label = "projeto"
        plural_label = "projetos"
    else:
        return

    monitored_ids: set[int] = set()
    active_indicator_ids = {int(indicator.id) for indicator in indicators}

    for indicator in indicators:
        legacy_id = getattr(indicator, legacy_attr, None)
        if legacy_id:
            monitored_ids.add(int(legacy_id))
        source_module = str(getattr(indicator, "source_module", "") or "").strip().lower()
        source_id = getattr(indicator, "source_id", None)
        if source_id and source_module in source_modules:
            monitored_ids.add(int(source_id))

    link_rows = (
        IndicatorEntityLink.query.filter(IndicatorEntityLink.company_id == company_id)
        .filter(IndicatorEntityLink.target_type == target_type)
        .filter(IndicatorEntityLink.is_active.is_(True))
        .all()
    )
    for link in link_rows:
        if int(link.indicator_id) not in active_indicator_ids:
            continue
        if link.target_id:
            monitored_ids.add(int(link.target_id))
            continue
        try:
            monitored_ids.add(int(str(link.target_ref or "").strip()))
        except (TypeError, ValueError):
            continue

    monitored_total = min(len(monitored_ids), total_existing)
    coverage_percent = round((monitored_total / total_existing) * 100) if total_existing else 0
    existing_label = singular_label if total_existing == 1 else plural_label
    monitored_label = singular_label if monitored_total == 1 else plural_label

    group["coverage"] = {
        "target_type": target_type,
        "total_existing": total_existing,
        "monitored_total": monitored_total,
        "coverage_percent": coverage_percent,
        "label": f"{total_existing} {existing_label} · {monitored_total} monitorados · {coverage_percent}%",
        "summary": f"{total_existing} {existing_label} cadastrados; {monitored_total} {monitored_label} com indicadores.",
    }


def _enrich_web_group(group: dict[str, Any], company_id: int, indicators: list[Indicator], projects: dict[int, Project], task_stats: dict[int, dict[str, Any]]) -> None:
    unlinked_indicators = [indicator for indicator in indicators if not indicator.responsible_id or (indicator.project_id is None and _classify_indicator(indicator) != "processes")]
    late_projects = [project for project_id, project in projects.items() if task_stats.get(project_id, {}).get("late", 0) > 0]
    score = len(unlinked_indicators) + len(late_projects)
    semaphore = "green" if score == 0 else "yellow" if score < 3 else "red"
    synthetic = {
        "id": "web-health",
        "code": "TEIA",
        "name": "Saúde das teias de conexão",
        "group": "webs",
        "subgroup": "Conexões e dependências",
        "semaphore": semaphore,
        "situation": "Satisfatória" if semaphore == "green" else "Insatisfatória" if semaphore == "yellow" else "Crítica",
        "objective": "Avaliar dependências frágeis entre indicadores, responsáveis, projetos e atividades.",
        "current_value": score,
        "goal": 0,
        "responsible": None,
        "project": None,
        "activities": [],
        "status_detail": f"{len(unlinked_indicators)} indicadores com governança incompleta e {len(late_projects)} projetos com atraso.",
        "next_charge": "Reunião gerencial do período",
    }
    group["total"] += 1
    group["semaphore"][semaphore] += 1
    group["items"].append(synthetic)
    group["subgroups"]["Conexões e dependências"].append(synthetic)
    if semaphore in {"red", "yellow"}:
        group["alerts"].append(synthetic)


def _upcoming_meetings(company_id: int, today: date) -> list[dict[str, Any]]:
    meetings = (
        Meeting.query.filter(Meeting.company_id == company_id)
        .filter(Meeting.scheduled_date >= today)
        .order_by(Meeting.scheduled_date.asc(), Meeting.scheduled_time.asc())
        .limit(6)
        .all()
    )
    payload = []
    for meeting in meetings:
        data = meeting.to_dict()
        guests = data.get("guests") or {}
        internal = guests.get("internal") if isinstance(guests, dict) else []
        payload.append(
            {
                "id": meeting.id,
                "title": meeting.title,
                "date": data.get("scheduled_date"),
                "time": meeting.scheduled_time,
                "status": meeting.status,
                "project_title": data.get("project_title"),
                "guests": [guest.get("name") for guest in (internal or []) if isinstance(guest, dict)][:5],
                "agenda": data.get("agenda") or [],
            }
        )
    return payload


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_to_float(value: Any) -> float | None:
    decimal = _to_decimal(value)
    return float(decimal) if decimal is not None else None


def _date_to_iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None


def _date_only(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
