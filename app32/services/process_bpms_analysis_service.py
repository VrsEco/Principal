from __future__ import annotations

import json
from typing import Any

from models import db, Company, Process, ProcessBpmsAnalysis

VALID_ANALYSIS_STATUSES = {"draft", "ready"}
VALID_SCOPES = {"pessoal", "equipe", "empresa"}
VALID_LEAD_SPECIALISTS = {"arquiteto", "backend_service", "backend_api", "ai_engineer", "dba", "qa_automation"}


def list_process_options(company_id: int) -> list[dict[str, Any]]:
    processes = (
        Process.query.filter_by(company_id=company_id)
        .order_by(Process.code.asc().nullslast(), Process.name.asc())
        .all()
    )
    return [{"id": p.id, "label": _process_label(p)} for p in processes]


def get_bpms_analysis(company_id: int, analysis_id: int) -> ProcessBpmsAnalysis | None:
    return ProcessBpmsAnalysis.query.filter_by(company_id=company_id, id=analysis_id).first()


def list_bpms_analyses(company_id: int, process_id: int | None = None) -> list[dict[str, Any]]:
    query = ProcessBpmsAnalysis.query.filter_by(company_id=company_id)
    if process_id:
        query = query.filter_by(process_id=process_id)
    analyses = query.order_by(ProcessBpmsAnalysis.updated_at.desc(), ProcessBpmsAnalysis.id.desc()).all()
    return [
        {
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "scope": item.scope,
            "process_id": item.process_id,
            "process_label": _process_label(item.process) if item.process else "Sem processo vinculado",
            "updated_at": item.updated_at.isoformat() if hasattr(item.updated_at, "isoformat") else item.updated_at,
        }
        for item in analyses
    ]


def build_bpms_analysis_page_context(*, company_id: int, selected_analysis_id: int | None = None, selected_process_id: int | None = None) -> dict[str, Any]:
    company = Company.query.get_or_404(company_id)
    selected_analysis = get_bpms_analysis(company_id, selected_analysis_id) if selected_analysis_id else None
    if selected_analysis and selected_analysis.process_id:
        selected_process_id = selected_analysis.process_id
    selected_process = Process.query.filter_by(company_id=company_id, id=selected_process_id).first() if selected_process_id else None
    return {
        "company": company,
        "process_options": list_process_options(company_id),
        "selected_process": {"id": selected_process.id, "label": _process_label(selected_process)} if selected_process else None,
        "selected_process_id": selected_process_id,
        "selected_analysis": selected_analysis.to_dict() if selected_analysis else _empty_analysis_payload(selected_process_id),
        "selected_analysis_id": selected_analysis.id if selected_analysis else None,
        "analyses": list_bpms_analyses(company_id, selected_process_id),
        "lead_specialist_options": [
            {"value": "arquiteto", "label": "@ARQUITETO"},
            {"value": "backend_service", "label": "@BACKEND_SERVICE"},
            {"value": "backend_api", "label": "@BACKEND_API"},
            {"value": "ai_engineer", "label": "@AI_ENGINEER"},
            {"value": "dba", "label": "@DBA"},
            {"value": "qa_automation", "label": "@QA_AUTOMATION"},
        ],
    }


def save_bpms_analysis(*, company_id: int, form_data: dict[str, Any], actor_user_id: int | None) -> ProcessBpmsAnalysis:
    analysis_id = _coerce_int(form_data.get("analysis_id"))
    process_id = _coerce_int(form_data.get("process_id"))
    process = Process.query.filter_by(company_id=company_id, id=process_id).first() if process_id else None
    if process_id and not process:
        raise ValueError("Processo vinculado não encontrado para a empresa ativa.")

    analysis = get_bpms_analysis(company_id, analysis_id) if analysis_id else None
    if analysis_id and not analysis:
        raise ValueError("Análise BPMS não encontrada para a empresa ativa.")
    if analysis is None:
        analysis = ProcessBpmsAnalysis(company_id=company_id, created_by_user_id=actor_user_id)
        db.session.add(analysis)

    title = str(form_data.get("title") or "").strip() or ("Análise BPMS - " + _process_label(process) if process else "Análise BPMS")
    status = str(form_data.get("status") or "draft").strip().lower()
    scope = str(form_data.get("scope") or "empresa").strip().lower()
    lead_specialist = str(form_data.get("lead_specialist") or "").strip().lower() or None
    if status not in VALID_ANALYSIS_STATUSES:
        raise ValueError("Status da análise inválido.")
    if scope not in VALID_SCOPES:
        raise ValueError("Escopo da análise inválido.")
    if lead_specialist and lead_specialist not in VALID_LEAD_SPECIALISTS:
        raise ValueError("Especialista líder inválido.")

    analysis.process_id = process_id
    analysis.title = title
    analysis.status = status
    analysis.scope = scope
    analysis.lead_specialist = lead_specialist

    text_fields = (
        "objective", "goal", "problem_statement", "expected_result",
        "current_indicators", "missing_indicators", "success_measurement",
        "as_is_summary", "as_is_steps", "as_is_exceptions", "bottlenecks", "operational_risks", "dependencies",
        "to_be_summary", "to_be_steps", "controls", "expected_automation", "desired_indicators",
        "identified_gaps", "architectural_impact", "governance_notes", "recommendation_summary",
        "implement_now", "parameterize_now", "customize_later", "develop_for_real", "not_now", "next_action",
        "dependencies_before_execution",
    )
    for field in text_fields:
        setattr(analysis, field, _clean_text(form_data.get(field)))

    analysis.app_adherence_json = _coerce_json_list(form_data.get("app_adherence_json"))
    analysis.gap_classification_json = _coerce_json_list(form_data.get("gap_classification_json"))
    analysis.prioritization_json = _coerce_json_list(form_data.get("prioritization_json"))
    analysis.requires_architect = _coerce_bool(form_data.get("requires_architect"))
    analysis.requires_backend_service = _coerce_bool(form_data.get("requires_backend_service"))
    analysis.requires_backend_api = _coerce_bool(form_data.get("requires_backend_api"))
    analysis.requires_ai_engineer = _coerce_bool(form_data.get("requires_ai_engineer"))
    analysis.requires_dba = _coerce_bool(form_data.get("requires_dba"))
    analysis.requires_qa_automation = _coerce_bool(form_data.get("requires_qa_automation"))
    analysis.updated_by_user_id = actor_user_id

    db.session.commit()
    return analysis


def _empty_analysis_payload(process_id: int | None) -> dict[str, Any]:
    return {
        "id": None,
        "process_id": process_id,
        "title": "",
        "status": "draft",
        "scope": "empresa",
        "objective": "",
        "goal": "",
        "problem_statement": "",
        "expected_result": "",
        "current_indicators": "",
        "missing_indicators": "",
        "success_measurement": "",
        "as_is_summary": "",
        "as_is_steps": "",
        "as_is_exceptions": "",
        "bottlenecks": "",
        "operational_risks": "",
        "dependencies": "",
        "to_be_summary": "",
        "to_be_steps": "",
        "controls": "",
        "expected_automation": "",
        "desired_indicators": "",
        "app_adherence_json": [{"stage": "", "exists": "", "where": "", "observation": ""}],
        "identified_gaps": "",
        "gap_classification_json": [{"gap": "", "classification": "", "justification": ""}],
        "prioritization_json": [{"item": "", "impact": "", "effort": "", "risk": "", "priority": ""}],
        "architectural_impact": "",
        "requires_architect": False,
        "requires_backend_service": False,
        "requires_backend_api": False,
        "requires_ai_engineer": False,
        "requires_dba": False,
        "requires_qa_automation": False,
        "governance_notes": "",
        "recommendation_summary": "",
        "implement_now": "",
        "parameterize_now": "",
        "customize_later": "",
        "develop_for_real": "",
        "not_now": "",
        "next_action": "",
        "lead_specialist": "",
        "dependencies_before_execution": "",
    }


def _process_label(process: Process | None) -> str:
    if not process:
        return "Sem processo"
    code = (process.code or "").strip()
    name = (process.name or "").strip()
    return f"{code} - {name}" if code else name


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: Any) -> int | None:
    try:
        if value in (None, "", "null"):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "on", "yes", "sim"}


def _coerce_json_list(raw_value: Any) -> list[dict[str, Any]]:
    if raw_value in (None, "", []):
        return []
    if isinstance(raw_value, list):
        return [item for item in raw_value if isinstance(item, dict)]
    try:
        parsed = json.loads(str(raw_value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]
