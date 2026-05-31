from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter, defaultdict
from typing import Any, Iterable

from models import (
    Company,
    Indicator,
    IndicatorLineOfSight,
    OKRArea,
    OKRGlobal,
    OrganizationalIdentity,
    Process,
    ProcessStrategicAlignmentLink,
    ProcessStrategyProfile,
    db,
)
from models.strategy_alignment import (
    INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES,
    PROCESS_MATURITY_LEVEL_VALUES,
    PROCESS_STRATEGIC_CRITICALITY_VALUES,
    STRATEGY_ALIGNMENT_LINK_TYPES,
    STRATEGY_ALIGNMENT_TARGET_REF_TYPES,
)


class StrategyAlignmentN1Error(ValueError):
    """Erro de domínio para readiness/análise N1 de alinhamento estratégico."""


def _slug(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_list(value: Any, *, field: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    raise StrategyAlignmentN1Error(f"Campo '{field}' deve ser uma lista estruturada.")


def _safe_dict(value: Any, *, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise StrategyAlignmentN1Error(f"Campo '{field}' deve ser um objeto estruturado.")


def _json_text(value: Any) -> str | None:
    if value in (None, "", [], {}):
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _item_label(item: dict[str, Any]) -> str | None:
    for key in ("name", "nome", "title", "titulo", "objective", "objetivo", "label", "code", "codigo", "key"):
        if _clean_text(item.get(key)):
            return _clean_text(item.get(key))
    return None


def _normalize_identity_items(items: Any, *, kind: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(_safe_list(items, field=kind)):
        if isinstance(raw, str):
            item: dict[str, Any] = {"name": raw}
        elif isinstance(raw, dict):
            item = dict(raw)
        else:
            item = {"value": raw}
        label = _item_label(item) or f"{kind}-{index + 1}"
        key = _clean_text(item.get("key")) or _clean_text(item.get("id")) or _clean_text(item.get("code")) or _slug(label)
        item.setdefault("name", label)
        item["key"] = str(key)
        item["target_key"] = str(key)
        item["kind"] = kind
        normalized.append(item)
    return normalized


def _model_dict(row: Any) -> dict[str, Any]:
    if hasattr(row, "to_dict"):
        return row.to_dict()
    return dict(row or {})


class StrategyAlignmentN1Service:
    """Service tenant-safe para leitura/escrita e análise N1 de alinhamento estratégico."""

    ANALYSIS_ID = "strategic_alignment_n1"
    READ_MODEL = "strategic.alignment_n1"

    _IDENTITY_FIELD_MAP = {
        "mission": "mission",
        "vision": "vision",
        "vision_horizon_year": "vision_horizon_year",
        "purpose": "purpose",
        "values": "values_json",
        "values_json": "values_json",
        "value_propositions": "value_propositions_json",
        "value_propositions_json": "value_propositions_json",
        "differentials": "differentials_json",
        "differentials_json": "differentials_json",
        "pillars": "pillars_json",
        "pillars_json": "pillars_json",
        "strategic_objectives": "strategic_objectives_json",
        "strategic_objectives_json": "strategic_objectives_json",
        "essential_competencies": "essential_competencies_json",
        "essential_competencies_json": "essential_competencies_json",
        "segments_icp": "segments_icp_json",
        "segments_icp_json": "segments_icp_json",
        "policies": "policies_json",
        "policies_json": "policies_json",
        "stakeholders": "stakeholders_json",
        "stakeholders_json": "stakeholders_json",
        "swot": "swot_json",
        "swot_json": "swot_json",
        "corporate_indicators": "corporate_indicators_json",
        "corporate_indicators_json": "corporate_indicators_json",
    }
    _IDENTITY_LIST_ATTRS = {
        "values_json",
        "value_propositions_json",
        "differentials_json",
        "pillars_json",
        "strategic_objectives_json",
        "essential_competencies_json",
        "segments_icp_json",
        "policies_json",
        "stakeholders_json",
        "corporate_indicators_json",
    }
    _PROFILE_FIELD_MAP = {
        "objective": "objective",
        "owner": "owner",
        "owner_employee_id": "owner_employee_id",
        "customer_type": "customer_type",
        "customer_description": "customer_description",
        "customer": "customer_description",
        "strategic_criticality": "strategic_criticality",
        "criticidade_estrategica": "strategic_criticality",
        "maturity_level": "maturity_level",
        "nivel_maturidade": "maturity_level",
        "regulatory_exposure": "regulatory_exposure",
        "risco_exposicao_regulatoria": "regulatory_exposure",
        "indicators": "indicators_json",
        "indicators_json": "indicators_json",
        "sipoc": "sipoc_json",
        "sipoc_json": "sipoc_json",
        "cost_resources_volume": "cost_resources_volume_json",
        "cost_resources_volume_json": "cost_resources_volume_json",
        "applicable_policies": "applicable_policies_json",
        "applicable_policies_json": "applicable_policies_json",
        "risks": "risks_json",
        "risks_json": "risks_json",
    }
    _PROFILE_LIST_ATTRS = {"indicators_json", "applicable_policies_json", "risks_json"}
    _PROFILE_DICT_ATTRS = {"sipoc_json", "cost_resources_volume_json"}

    @staticmethod
    def _ensure_access(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> None:
        if accessible_company_ids is None:
            return
        if int(company_id) not in {int(item) for item in accessible_company_ids}:
            raise PermissionError("Empresa fora do escopo analítico autorizado para alinhamento estratégico N1.")

    @staticmethod
    def _require_company(company_id: int) -> Company:
        company = Company.query.filter_by(id=company_id).first()
        if company is None:
            raise StrategyAlignmentN1Error(f"Empresa não encontrada: company_id={company_id}.")
        return company

    @staticmethod
    def _require_process(company_id: int, process_id: int) -> Process:
        process = Process.query.filter_by(company_id=company_id, id=process_id).first()
        if process is None:
            raise StrategyAlignmentN1Error(
                f"Processo não encontrado no tenant informado: company_id={company_id}, process_id={process_id}."
            )
        return process

    @staticmethod
    def _require_indicator(company_id: int, indicator_id: int, *, label: str = "indicador") -> Indicator:
        indicator = Indicator.query.filter_by(company_id=company_id, id=indicator_id).first()
        if indicator is None:
            raise StrategyAlignmentN1Error(
                f"{label.capitalize()} não encontrado no tenant informado: company_id={company_id}, indicator_id={indicator_id}."
            )
        return indicator

    @staticmethod
    def get_identity(company_id: int) -> dict[str, Any]:
        company = StrategyAlignmentN1Service._require_company(company_id)
        identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()
        if identity is not None:
            return identity.to_dict()

        return {
            "id": None,
            "company_id": company_id,
            "mission": company.mission,
            "vision": company.vision,
            "vision_horizon_year": None,
            "purpose": None,
            "values": [],
            "value_propositions": [],
            "differentials": [],
            "pillars": [],
            "strategic_objectives": [],
            "essential_competencies": [],
            "segments_icp": [],
            "policies": [],
            "stakeholders": [],
            "swot": {},
            "corporate_indicators": [],
            "legacy": {
                "mvv_mission": company.mission,
                "mvv_vision": company.vision,
                "mvv_values": company.values,
                "structured": False,
            },
            "structured": False,
        }

    @staticmethod
    def upsert_identity(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload de identidade deve ser um objeto.")

        company = StrategyAlignmentN1Service._require_company(company_id)
        identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()
        if identity is None:
            identity = OrganizationalIdentity(company_id=company_id, created_by_user_id=user_id)
            db.session.add(identity)
        identity.updated_by_user_id = user_id

        for key, value in payload.items():
            attr = StrategyAlignmentN1Service._IDENTITY_FIELD_MAP.get(key)
            if not attr:
                continue
            if attr in StrategyAlignmentN1Service._IDENTITY_LIST_ATTRS:
                value = _safe_list(value, field=key)
            elif attr == "swot_json":
                value = _safe_dict(value, field=key)
            elif attr == "vision_horizon_year" and value not in (None, ""):
                value = int(value)
            elif attr in {"mission", "vision", "purpose"}:
                value = _clean_text(value)
            setattr(identity, attr, value)

        if "mission" in payload:
            company.mission = identity.mission
        if "vision" in payload:
            company.vision = identity.vision
        if "values" in payload or "values_json" in payload:
            company.values = _json_text(identity.values_json)

        if commit:
            db.session.commit()
        return identity.to_dict()

    @staticmethod
    def get_process_profile(company_id: int, process_id: int) -> dict[str, Any]:
        process = StrategyAlignmentN1Service._require_process(company_id, process_id)
        profile = ProcessStrategyProfile.query.filter_by(company_id=company_id, process_id=process_id).first()
        if profile is not None:
            payload = profile.to_dict()
            payload["process"] = StrategyAlignmentN1Service._process_payload(process)
            payload["profile_exists"] = True
            return payload
        return {
            "id": None,
            "company_id": company_id,
            "process_id": process_id,
            "process": StrategyAlignmentN1Service._process_payload(process),
            "objective": None,
            "owner": process.responsible,
            "owner_employee_id": process.owner_employee_id,
            "customer_type": None,
            "customer_description": None,
            "strategic_criticality": None,
            "maturity_level": process.structuring_level,
            "regulatory_exposure": None,
            "indicators": [],
            "sipoc": {},
            "cost_resources_volume": {},
            "applicable_policies": [],
            "risks": [],
            "profile_exists": False,
        }

    @staticmethod
    def upsert_process_profile(
        company_id: int,
        process_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload do perfil estratégico do processo deve ser um objeto.")
        process = StrategyAlignmentN1Service._require_process(company_id, process_id)
        profile = ProcessStrategyProfile.query.filter_by(company_id=company_id, process_id=process_id).first()
        if profile is None:
            profile = ProcessStrategyProfile(
                company_id=company_id,
                process_id=process_id,
                owner=process.responsible,
                owner_employee_id=process.owner_employee_id,
                created_by_user_id=user_id,
            )
            db.session.add(profile)
        profile.updated_by_user_id = user_id

        for key, value in payload.items():
            attr = StrategyAlignmentN1Service._PROFILE_FIELD_MAP.get(key)
            if not attr:
                continue
            if attr in StrategyAlignmentN1Service._PROFILE_LIST_ATTRS:
                value = _safe_list(value, field=key)
            elif attr in StrategyAlignmentN1Service._PROFILE_DICT_ATTRS:
                value = _safe_dict(value, field=key)
            elif attr == "strategic_criticality" and value not in (None, ""):
                value = _slug(value).replace("-", "_")
                value = {"média": "media", "medio": "media", "médio": "media"}.get(value, value)
                if value not in PROCESS_STRATEGIC_CRITICALITY_VALUES:
                    raise StrategyAlignmentN1Error("Criticidade estratégica inválida. Use alta, media ou baixa.")
            elif attr == "maturity_level" and value not in (None, ""):
                value = _slug(value).replace("-", "_")
                if value not in PROCESS_MATURITY_LEVEL_VALUES:
                    raise StrategyAlignmentN1Error(
                        "Nível de maturidade inválido. Use nao_definido, inicial, gerenciado, padronizado, mensurado ou otimizado."
                    )
            elif attr == "owner_employee_id" and value not in (None, ""):
                value = int(value)
            else:
                value = _clean_text(value)
            setattr(profile, attr, value)

        if commit:
            db.session.commit()
        response = profile.to_dict()
        response["process"] = StrategyAlignmentN1Service._process_payload(process)
        response["profile_exists"] = True
        return response

    @staticmethod
    def list_alignment_links(company_id: int, process_id: int | None = None) -> list[dict[str, Any]]:
        StrategyAlignmentN1Service._require_company(company_id)
        query = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id)
        if process_id is not None:
            StrategyAlignmentN1Service._require_process(company_id, process_id)
            query = query.filter_by(process_id=process_id)
        links = query.order_by(
            ProcessStrategicAlignmentLink.process_id.asc(),
            ProcessStrategicAlignmentLink.link_type.asc(),
            ProcessStrategicAlignmentLink.id.asc(),
        ).all()
        return [link.to_dict() for link in links]

    @staticmethod
    def upsert_alignment_link(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload do vínculo estratégico deve ser um objeto.")
        process_id = int(payload.get("process_id") or 0)
        if process_id <= 0:
            raise StrategyAlignmentN1Error("process_id é obrigatório para vínculo estratégico.")
        StrategyAlignmentN1Service._require_process(company_id, process_id)

        link_id = payload.get("id")
        link = None
        if link_id:
            link = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id, id=int(link_id)).first()
            if link is None:
                raise StrategyAlignmentN1Error(f"Vínculo estratégico não encontrado: id={link_id}.")
        if link is None:
            link = ProcessStrategicAlignmentLink(company_id=company_id, process_id=process_id, created_by_user_id=user_id)
            db.session.add(link)

        link.link_type = _clean_text(payload.get("link_type")) or link.link_type
        if link.link_type not in STRATEGY_ALIGNMENT_LINK_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de vínculo estratégico inválido: {link.link_type}.")
        link.process_id = process_id
        link.target_ref_type = _clean_text(payload.get("target_ref_type"))
        if link.target_ref_type and link.target_ref_type not in STRATEGY_ALIGNMENT_TARGET_REF_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de alvo estratégico inválido: {link.target_ref_type}.")
        link.target_ref_id = int(payload["target_ref_id"]) if payload.get("target_ref_id") not in (None, "") else None
        link.target_key = _clean_text(payload.get("target_key"))
        link.target_payload_json = _safe_dict(payload.get("target_payload") or payload.get("target_payload_json"), field="target_payload") if (payload.get("target_payload") or payload.get("target_payload_json")) is not None else {}
        link.contribution_type = _clean_text(payload.get("contribution_type"))
        link.contribution_weight = payload.get("contribution_weight")
        link.notes = _clean_text(payload.get("notes"))
        link.updated_by_user_id = user_id

        StrategyAlignmentN1Service._validate_alignment_target(company_id, link)

        if commit:
            db.session.commit()
        return link.to_dict()

    @staticmethod
    def delete_alignment_link(company_id: int, link_id: int, *, commit: bool = True) -> dict[str, Any]:
        link = ProcessStrategicAlignmentLink.query.filter_by(company_id=company_id, id=link_id).first()
        if link is None:
            raise StrategyAlignmentN1Error(f"Vínculo estratégico não encontrado no tenant: id={link_id}.")
        payload = link.to_dict()
        db.session.delete(link)
        if commit:
            db.session.commit()
        return {"deleted": True, "link": payload}

    @staticmethod
    def list_indicator_line_of_sight(company_id: int, process_id: int | None = None) -> list[dict[str, Any]]:
        StrategyAlignmentN1Service._require_company(company_id)
        query = IndicatorLineOfSight.query.filter_by(company_id=company_id)
        if process_id is not None:
            StrategyAlignmentN1Service._require_process(company_id, process_id)
            process_indicator_ids = [
                row.id
                for row in Indicator.query.filter_by(company_id=company_id, process_id=process_id).with_entities(Indicator.id).all()
            ]
            if not process_indicator_ids:
                return []
            query = query.filter(IndicatorLineOfSight.process_indicator_id.in_(process_indicator_ids))
        links = query.order_by(IndicatorLineOfSight.id.asc()).all()
        return [item.to_dict() for item in links]

    @staticmethod
    def upsert_indicator_line_of_sight(
        company_id: int,
        payload: dict[str, Any],
        *,
        user_id: int | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise StrategyAlignmentN1Error("Payload da linha de visada de indicadores deve ser um objeto.")
        process_indicator_id = int(payload.get("process_indicator_id") or 0)
        corporate_indicator_id = int(payload.get("corporate_indicator_id") or 0)
        if process_indicator_id <= 0 or corporate_indicator_id <= 0:
            raise StrategyAlignmentN1Error("process_indicator_id e corporate_indicator_id são obrigatórios.")

        process_indicator = StrategyAlignmentN1Service._require_indicator(
            company_id,
            process_indicator_id,
            label="indicador de processo",
        )
        corporate_indicator = StrategyAlignmentN1Service._require_indicator(
            company_id,
            corporate_indicator_id,
            label="indicador corporativo",
        )
        if not process_indicator.process_id:
            raise StrategyAlignmentN1Error("Indicador de processo precisa estar vinculado a um processo do tenant.")
        StrategyAlignmentN1Service._require_process(company_id, int(process_indicator.process_id))
        if corporate_indicator.process_id:
            raise StrategyAlignmentN1Error("Indicador corporativo não deve estar vinculado a um processo específico.")

        relationship_type = _clean_text(payload.get("relationship_type")) or "contributes_to"
        if relationship_type not in INDICATOR_LINE_OF_SIGHT_RELATIONSHIP_TYPES:
            raise StrategyAlignmentN1Error(f"Tipo de linha de visada inválido: {relationship_type}.")

        link_id = payload.get("id")
        line = None
        if link_id:
            line = IndicatorLineOfSight.query.filter_by(company_id=company_id, id=int(link_id)).first()
            if line is None:
                raise StrategyAlignmentN1Error(f"Linha de visada não encontrada: id={link_id}.")
        if line is None:
            line = IndicatorLineOfSight.query.filter_by(
                company_id=company_id,
                process_indicator_id=process_indicator_id,
                corporate_indicator_id=corporate_indicator_id,
            ).first()
        if line is None:
            line = IndicatorLineOfSight(
                company_id=company_id,
                process_indicator_id=process_indicator_id,
                corporate_indicator_id=corporate_indicator_id,
                created_by_user_id=user_id,
            )
            db.session.add(line)

        line.relationship_type = relationship_type
        line.contribution_weight = payload.get("contribution_weight")
        line.notes = _clean_text(payload.get("notes"))
        line.updated_by_user_id = user_id

        if commit:
            db.session.commit()
        return line.to_dict()

    @staticmethod
    def delete_indicator_line_of_sight(company_id: int, link_id: int, *, commit: bool = True) -> dict[str, Any]:
        line = IndicatorLineOfSight.query.filter_by(company_id=company_id, id=link_id).first()
        if line is None:
            raise StrategyAlignmentN1Error(f"Linha de visada não encontrada no tenant: id={link_id}.")
        payload = line.to_dict()
        db.session.delete(line)
        if commit:
            db.session.commit()
        return {"deleted": True, "line_of_sight": payload}

    @staticmethod
    def get_readiness(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> dict[str, Any]:
        StrategyAlignmentN1Service._ensure_access(company_id, accessible_company_ids)
        identity = StrategyAlignmentN1Service.get_identity(company_id)
        process_count = Process.query.filter_by(company_id=company_id).count()
        profile_count = ProcessStrategyProfile.query.filter_by(company_id=company_id).count()
        links = StrategyAlignmentN1Service.list_alignment_links(company_id)
        line_of_sight_count = IndicatorLineOfSight.query.filter_by(company_id=company_id).count()
        process_indicator_count = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.process_id.isnot(None),
        ).count()
        corporate_indicator_count = Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.process_id.is_(None),
        ).count()

        identity_fields = {
            "mission": bool(_clean_text(identity.get("mission"))),
            "vision": bool(_clean_text(identity.get("vision"))),
            "values": bool(identity.get("values")),
            "purpose": bool(_clean_text(identity.get("purpose"))),
            "value_propositions": bool(identity.get("value_propositions")),
            "differentials": bool(identity.get("differentials")),
            "pillars": bool(identity.get("pillars")),
            "strategic_objectives": bool(
                identity.get("strategic_objectives")
                or OKRGlobal.query.filter_by(company_id=company_id).first()
                or OKRArea.query.filter_by(company_id=company_id).first()
            ),
            "essential_competencies": bool(identity.get("essential_competencies")),
            "segments_icp": bool(identity.get("segments_icp")),
            "policies": bool(identity.get("policies")),
            "stakeholders": bool(identity.get("stakeholders")),
            "swot": bool(identity.get("swot")),
            "corporate_indicators": bool(identity.get("corporate_indicators") or corporate_indicator_count),
        }
        link_counts = Counter(link["link_type"] for link in links)
        required_link_types = {
            "strategic_objective",
            "strategic_pillar",
            "value_proposition",
            "differential",
            "essential_competence",
            "policy",
        }

        missing_identity = [field for field, present in identity_fields.items() if not present]
        missing_links = sorted(link_type for link_type in required_link_types if link_counts.get(link_type, 0) == 0)
        ready = (
            bool(identity_fields["mission"] and identity_fields["vision"] and identity_fields["strategic_objectives"])
            and process_count > 0
            and link_counts.get("strategic_objective", 0) > 0
        )

        return {
            "company_id": company_id,
            "analysis_id": StrategyAlignmentN1Service.ANALYSIS_ID,
            "read_model": StrategyAlignmentN1Service.READ_MODEL,
            "ready_for_analysis": ready,
            "identity": {
                "structured": bool(identity.get("structured")),
                "field_coverage": identity_fields,
                "missing_fields": missing_identity,
            },
            "process_architecture": {
                "processes": process_count,
                "process_strategy_profiles": profile_count,
                "coverage_pct": round((profile_count / process_count) * 100, 2) if process_count else 0,
            },
            "traceability": {
                "alignment_links": len(links),
                "alignment_links_by_type": dict(link_counts),
                "missing_link_types": missing_links,
                "indicator_line_of_sight_links": line_of_sight_count,
                "process_indicators": process_indicator_count,
                "corporate_indicators": corporate_indicator_count,
            },
            "recommended_next_actions": StrategyAlignmentN1Service._readiness_actions(
                missing_identity=missing_identity,
                missing_links=missing_links,
                process_count=process_count,
                profile_count=profile_count,
                process_indicator_count=process_indicator_count,
                line_of_sight_count=line_of_sight_count,
            ),
        }

    @staticmethod
    def run_alignment_analysis(company_id: int, accessible_company_ids: Iterable[int] | None = None) -> dict[str, Any]:
        StrategyAlignmentN1Service._ensure_access(company_id, accessible_company_ids)
        StrategyAlignmentN1Service._require_company(company_id)
        identity = StrategyAlignmentN1Service.get_identity(company_id)
        processes = [StrategyAlignmentN1Service._process_payload(row) for row in Process.query.filter_by(company_id=company_id).all()]
        profiles = [row.to_dict() for row in ProcessStrategyProfile.query.filter_by(company_id=company_id).all()]
        links = StrategyAlignmentN1Service.list_alignment_links(company_id)
        process_indicators = [
            StrategyAlignmentN1Service._indicator_payload(row)
            for row in Indicator.query.filter(Indicator.company_id == company_id, Indicator.process_id.isnot(None)).all()
        ]
        corporate_indicators = [
            StrategyAlignmentN1Service._indicator_payload(row)
            for row in Indicator.query.filter(Indicator.company_id == company_id, Indicator.process_id.is_(None)).all()
        ]
        indicator_line_of_sight = StrategyAlignmentN1Service.list_indicator_line_of_sight(company_id)
        okr_objectives = StrategyAlignmentN1Service._load_okr_objectives(company_id)
        return StrategyAlignmentN1Service.build_alignment_analysis_from_records(
            company_id=company_id,
            identity=identity,
            processes=processes,
            profiles=profiles,
            links=links,
            process_indicators=process_indicators,
            corporate_indicators=corporate_indicators,
            indicator_line_of_sight=indicator_line_of_sight,
            okr_objectives=okr_objectives,
        )

    @staticmethod
    def build_alignment_analysis_from_records(
        *,
        company_id: int,
        identity: dict[str, Any],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        links: list[dict[str, Any]],
        process_indicators: list[dict[str, Any]],
        corporate_indicators: list[dict[str, Any]],
        indicator_line_of_sight: list[dict[str, Any]],
        okr_objectives: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        processes_by_id = {int(item["id"]): item for item in processes if item.get("id") is not None}
        profiles_by_process = {
            int(item["process_id"]): item
            for item in profiles
            if item.get("process_id") is not None
        }
        links_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for link in links:
            links_by_type[str(link.get("link_type"))].append(link)

        objectives = _normalize_identity_items(identity.get("strategic_objectives", []), kind="strategic_objective")
        objectives.extend(okr_objectives or [])
        pillars = _normalize_identity_items(identity.get("pillars", []), kind="strategic_pillar")
        value_propositions = _normalize_identity_items(identity.get("value_propositions", []), kind="value_proposition")
        differentials = _normalize_identity_items(identity.get("differentials", []), kind="differential")
        competencies = _normalize_identity_items(identity.get("essential_competencies", []), kind="essential_competence")
        policies = _normalize_identity_items(identity.get("policies", []), kind="policy")

        objectives_without_process = StrategyAlignmentN1Service._targets_without_process(
            objectives,
            links_by_type["strategic_objective"],
        )
        pillars_without_process = StrategyAlignmentN1Service._targets_without_process(
            pillars,
            links_by_type["strategic_pillar"],
        )
        value_props_without_process = StrategyAlignmentN1Service._targets_without_process(
            value_propositions,
            links_by_type["value_proposition"],
        )
        differentials_without_process = StrategyAlignmentN1Service._targets_without_process(
            differentials,
            links_by_type["differential"],
        )
        competencies_without_process = StrategyAlignmentN1Service._targets_without_process(
            competencies,
            links_by_type["essential_competence"],
        )
        policies_without_process = StrategyAlignmentN1Service._targets_without_process(
            policies,
            links_by_type["policy"],
        )

        processes_with_objective = {
            int(link["process_id"])
            for link in links_by_type["strategic_objective"]
            if link.get("process_id") in processes_by_id or int(link.get("process_id") or 0) in processes_by_id
        }
        processes_without_objective = [
            process for process_id, process in processes_by_id.items() if process_id not in processes_with_objective
        ]
        processes_without_purpose = []
        for process_id, process in processes_by_id.items():
            profile = profiles_by_process.get(process_id) or {}
            if not _clean_text(profile.get("objective")) and process_id not in processes_with_objective:
                processes_without_purpose.append(process)

        line_process_indicator_ids = {
            int(item["process_indicator_id"])
            for item in indicator_line_of_sight
            if item.get("process_indicator_id") is not None
        }
        process_indicators_without_corporate = [
            indicator
            for indicator in process_indicators
            if int(indicator.get("id") or 0) not in line_process_indicator_ids
        ]

        values_without_policy = StrategyAlignmentN1Service._values_without_policy(identity)
        crossings = {
            "process_to_objectives": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["strategic_objective"],
                processes_by_id,
                objectives,
            ),
            "process_to_pillars": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["strategic_pillar"],
                processes_by_id,
                pillars,
            ),
            "process_to_value_propositions": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["value_proposition"],
                processes_by_id,
                value_propositions,
            ),
            "process_to_differentials": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["differential"],
                processes_by_id,
                differentials,
            ),
            "process_to_policies": StrategyAlignmentN1Service._crossings_for_links(
                links_by_type["policy"],
                processes_by_id,
                policies,
            ),
            "indicator_line_of_sight": indicator_line_of_sight,
        }
        gaps = {
            "objectives_without_process": objectives_without_process,
            "processes_without_objective": processes_without_objective,
            "processes_without_purpose": processes_without_purpose,
            "pillars_without_process": pillars_without_process,
            "value_propositions_without_process": value_props_without_process,
            "differentials_without_process": differentials_without_process,
            "essential_competencies_without_process": competencies_without_process,
            "policies_without_process": policies_without_process,
            "values_without_policy": values_without_policy,
            "process_indicators_without_corporate": process_indicators_without_corporate,
        }
        gap_counts = {name: len(items) for name, items in gaps.items()}

        return {
            "company_id": company_id,
            "analysis_id": StrategyAlignmentN1Service.ANALYSIS_ID,
            "read_model": StrategyAlignmentN1Service.READ_MODEL,
            "summary": {
                "processes": len(processes),
                "process_profiles": len(profiles),
                "strategic_objectives": len(objectives),
                "pillars": len(pillars),
                "value_propositions": len(value_propositions),
                "differentials": len(differentials),
                "essential_competencies": len(competencies),
                "policies": len(policies),
                "alignment_links": len(links),
                "process_indicators": len(process_indicators),
                "corporate_indicators": len(corporate_indicators),
                "indicator_line_of_sight_links": len(indicator_line_of_sight),
                "gap_counts": gap_counts,
            },
            "gaps": gaps,
            "crossings": crossings,
            "recommended_actions": StrategyAlignmentN1Service._analysis_actions(gap_counts),
        }

    @staticmethod
    def _validate_alignment_target(company_id: int, link: ProcessStrategicAlignmentLink) -> None:
        if link.target_ref_type in {"identity_json", "policy", "custom", None}:
            if not link.target_ref_id and not link.target_key:
                raise StrategyAlignmentN1Error("Informe target_key ou target_ref_id para o vínculo estratégico.")
            return
        if not link.target_ref_id:
            raise StrategyAlignmentN1Error(f"target_ref_id é obrigatório para target_ref_type={link.target_ref_type}.")
        if link.target_ref_type == "okr_global":
            exists = OKRGlobal.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        elif link.target_ref_type == "okr_area":
            exists = OKRArea.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        elif link.target_ref_type == "indicator":
            exists = Indicator.query.filter_by(company_id=company_id, id=link.target_ref_id).first()
        else:
            exists = True
        if not exists:
            raise StrategyAlignmentN1Error(
                f"Alvo estratégico não encontrado no tenant: {link.target_ref_type}:{link.target_ref_id}."
            )

    @staticmethod
    def _process_payload(process: Process) -> dict[str, Any]:
        return {
            "id": process.id,
            "company_id": process.company_id,
            "macro_id": process.macro_id,
            "code": process.code,
            "name": process.name,
            "description": process.description,
            "responsible": process.responsible,
            "responsible_id": process.responsible_id,
            "owner_employee_id": process.owner_employee_id,
            "structuring_level": process.structuring_level,
            "performance_level": process.performance_level,
            "is_active": bool(process.is_active),
        }

    @staticmethod
    def _indicator_payload(indicator: Indicator) -> dict[str, Any]:
        payload = indicator.to_dict()
        payload.update(
            {
                "process_id": indicator.process_id,
                "source_scope": indicator.source_scope,
                "source_module": indicator.source_module,
                "indicator_type": indicator.indicator_type,
            }
        )
        return payload

    @staticmethod
    def _load_okr_objectives(company_id: int) -> list[dict[str, Any]]:
        objectives: list[dict[str, Any]] = []
        for okr in OKRGlobal.query.filter_by(company_id=company_id).all():
            objectives.append(
                {
                    "kind": "strategic_objective",
                    "key": f"okr_global:{okr.id}",
                    "target_key": f"okr_global:{okr.id}",
                    "target_ref_type": "okr_global",
                    "target_ref_id": okr.id,
                    "objective": okr.objective,
                    "owner": okr.owner,
                    "deadline": okr.deadline.isoformat() if okr.deadline else None,
                    "key_results": [kr.to_dict() for kr in okr.key_results],
                }
            )
        for okr in OKRArea.query.filter_by(company_id=company_id).all():
            objectives.append(
                {
                    "kind": "strategic_objective",
                    "key": f"okr_area:{okr.id}",
                    "target_key": f"okr_area:{okr.id}",
                    "target_ref_type": "okr_area",
                    "target_ref_id": okr.id,
                    "objective": okr.objective,
                    "owner": okr.owner,
                    "department": okr.department,
                    "deadline": okr.deadline.isoformat() if okr.deadline else None,
                    "key_results": [kr.to_dict() for kr in okr.key_results],
                }
            )
        return objectives

    @staticmethod
    def _target_matches(link: dict[str, Any], target: dict[str, Any]) -> bool:
        target_ref_type = target.get("target_ref_type")
        target_ref_id = target.get("target_ref_id")
        if target_ref_type and target_ref_id and link.get("target_ref_type") == target_ref_type:
            try:
                if int(link.get("target_ref_id") or 0) == int(target_ref_id):
                    return True
            except (TypeError, ValueError):
                pass
        link_key = _clean_text(link.get("target_key"))
        if link_key:
            candidates = {
                _slug(target.get("key")),
                _slug(target.get("target_key")),
                _slug(target.get("name")),
                _slug(target.get("objective")),
                _slug(target.get("title")),
                _slug(target.get("code")),
            }
            return _slug(link_key) in candidates
        return False

    @staticmethod
    def _targets_without_process(targets: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        for target in targets:
            if not any(StrategyAlignmentN1Service._target_matches(link, target) for link in links):
                missing.append(target)
        return missing

    @staticmethod
    def _crossings_for_links(
        links: list[dict[str, Any]],
        processes_by_id: dict[int, dict[str, Any]],
        targets: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        crossings: list[dict[str, Any]] = []
        for link in links:
            process = processes_by_id.get(int(link.get("process_id") or 0))
            target = next((item for item in targets if StrategyAlignmentN1Service._target_matches(link, item)), None)
            crossings.append(
                {
                    "link_id": link.get("id"),
                    "process": process,
                    "target": target or {
                        "target_ref_type": link.get("target_ref_type"),
                        "target_ref_id": link.get("target_ref_id"),
                        "target_key": link.get("target_key"),
                        "target_payload": link.get("target_payload") or link.get("target_payload_json") or {},
                    },
                    "contribution_type": link.get("contribution_type"),
                    "contribution_weight": link.get("contribution_weight"),
                    "notes": link.get("notes"),
                }
            )
        return crossings

    @staticmethod
    def _values_without_policy(identity: dict[str, Any]) -> list[dict[str, Any]]:
        values = _normalize_identity_items(identity.get("values", []), kind="value")
        policies = _normalize_identity_items(identity.get("policies", []), kind="policy")
        if not values:
            return []
        if not policies:
            return values

        missing: list[dict[str, Any]] = []
        policy_keys = {_slug(item.get("key")) for item in policies} | {_slug(item.get("name")) for item in policies}
        for value in values:
            linked_keys = value.get("policy_keys") or value.get("policies") or []
            if isinstance(linked_keys, str):
                linked_keys = [linked_keys]
            if not linked_keys or not any(_slug(item) in policy_keys for item in linked_keys):
                missing.append(value)
        return missing

    @staticmethod
    def _readiness_actions(
        *,
        missing_identity: list[str],
        missing_links: list[str],
        process_count: int,
        profile_count: int,
        process_indicator_count: int,
        line_of_sight_count: int,
    ) -> list[str]:
        actions: list[str] = []
        if missing_identity:
            actions.append("Completar identidade organizacional estruturada: " + ", ".join(missing_identity[:6]))
        if process_count == 0:
            actions.append("Cadastrar arquitetura de processos antes da análise N1.")
        elif profile_count < process_count:
            actions.append("Preencher perfil estratégico dos processos sem objetivo/dono/criticidade/SIPOC.")
        if missing_links:
            actions.append("Criar vínculos de rastreabilidade pendentes: " + ", ".join(missing_links))
        if process_indicator_count and line_of_sight_count == 0:
            actions.append("Vincular indicadores de processo aos indicadores corporativos.")
        if not actions:
            actions.append("Executar analyze_strategic_alignment_n1_tool e revisar gaps.")
        return actions

    @staticmethod
    def _analysis_actions(gap_counts: dict[str, int]) -> list[str]:
        actions: list[str] = []
        if gap_counts.get("objectives_without_process"):
            actions.append("Priorizar vínculo Processo → Objetivo estratégico para objetivos sem processo.")
        if gap_counts.get("processes_without_objective"):
            actions.append("Revisar processos sem contribuição estratégica explícita.")
        if gap_counts.get("differentials_without_process"):
            actions.append("Conectar diferenciais competitivos aos processos core que os sustentam.")
        if gap_counts.get("values_without_policy"):
            actions.append("Formalizar políticas que materializam valores organizacionais.")
        if gap_counts.get("process_indicators_without_corporate"):
            actions.append("Criar linha de visada entre indicadores de processo e indicadores corporativos.")
        if not actions:
            actions.append("Sem desalinhamentos críticos detectados no read model N1 atual.")
        return actions


__all__ = ["StrategyAlignmentN1Error", "StrategyAlignmentN1Service"]
