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
            gap_type="objectives_without_process",
            reason="Objetivo estratégico sem processo contribuinte mapeado.",
        )
        pillars_without_process = StrategyAlignmentN1Service._targets_without_process(
            pillars,
            links_by_type["strategic_pillar"],
            gap_type="pillars_without_process",
            reason="Pilar estratégico sem processo contribuinte mapeado.",
        )
        value_props_without_process = StrategyAlignmentN1Service._targets_without_process(
            value_propositions,
            links_by_type["value_proposition"],
            gap_type="value_propositions_without_process",
            reason="Proposta de valor sem processo que a sustente.",
        )
        differentials_without_process = StrategyAlignmentN1Service._targets_without_process(
            differentials,
            links_by_type["differential"],
            gap_type="differentials_without_process",
            reason="Diferencial competitivo sem processo core mapeado.",
        )
        competencies_without_process = StrategyAlignmentN1Service._targets_without_process(
            competencies,
            links_by_type["essential_competence"],
            gap_type="essential_competencies_without_process",
            reason="Competência essencial sem processo sustentador mapeado.",
        )
        policies_without_process = StrategyAlignmentN1Service._targets_without_process(
            policies,
            links_by_type["policy"],
            gap_type="policies_without_process",
            reason="Política sem processo aplicável mapeado.",
        )

        processes_with_objective = {
            int(link["process_id"])
            for link in links_by_type["strategic_objective"]
            if link.get("process_id") in processes_by_id or int(link.get("process_id") or 0) in processes_by_id
        }
        processes_without_objective = [
            StrategyAlignmentN1Service._with_gap_meta(
                process,
                gap_type="processes_without_objective",
                reason="Processo sem objetivo estratégico contribuído mapeado.",
            )
            for process_id, process in processes_by_id.items()
            if process_id not in processes_with_objective
        ]
        processes_without_purpose = []
        for process_id, process in processes_by_id.items():
            profile = profiles_by_process.get(process_id) or {}
            if not _clean_text(profile.get("objective")) and process_id not in processes_with_objective:
                processes_without_purpose.append(
                    StrategyAlignmentN1Service._with_gap_meta(
                        process,
                        gap_type="processes_without_purpose",
                        reason="Processo sem objetivo do processo e sem contribuição estratégica explícita.",
                    )
                )

        line_process_indicator_ids = {
            int(item["process_indicator_id"])
            for item in indicator_line_of_sight
            if item.get("process_indicator_id") is not None
        }
        process_indicators_without_corporate = [
            StrategyAlignmentN1Service._with_gap_meta(
                indicator,
                gap_type="process_indicators_without_corporate",
                reason="Indicador de processo sem linha de visada para indicador corporativo.",
            )
            for indicator in process_indicators
            if int(indicator.get("id") or 0) not in line_process_indicator_ids
        ]

        values_without_policy = [
            StrategyAlignmentN1Service._with_gap_meta(
                value,
                gap_type="values_without_policy",
                reason="Valor organizacional sem política vinculada.",
            )
            for value in StrategyAlignmentN1Service._values_without_policy(identity)
        ]
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
        completeness = StrategyAlignmentN1Service._analysis_completeness(
            identity=identity,
            processes=processes,
            profiles=profiles,
            objectives=objectives,
            pillars=pillars,
            value_propositions=value_propositions,
            differentials=differentials,
            competencies=competencies,
            policies=policies,
            process_indicators=process_indicators,
            indicator_line_of_sight=indicator_line_of_sight,
            gaps=gaps,
        )
        risk_signals = StrategyAlignmentN1Service._analysis_risk_signals(
            gaps=gaps,
            crossings=crossings,
            profiles_by_process=profiles_by_process,
            processes_by_id=processes_by_id,
            links_by_type=links_by_type,
        )

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
                "risk_signal_count": len(risk_signals),
            },
            "completeness": completeness,
            "risk_signals": risk_signals,
            "gaps": gaps,
            "crossings": crossings,
            "recommended_actions": StrategyAlignmentN1Service._analysis_actions(
                gaps=gaps,
                risk_signals=risk_signals,
            ),
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
    def _with_gap_meta(
        item: dict[str, Any],
        *,
        gap_type: str,
        reason: str,
        status: str = "unmapped",
        severity: str = "medium",
    ) -> dict[str, Any]:
        payload = dict(item or {})
        payload["gap_type"] = gap_type
        payload["gap_status"] = StrategyAlignmentN1Service._normalize_gap_status(
            payload.get("gap_status") or payload.get("mapping_status") or payload.get("status") or status
        )
        payload["severity"] = payload.get("severity") or severity
        payload["reason"] = payload.get("reason") or reason
        return payload

    @staticmethod
    def _normalize_gap_status(value: Any) -> str:
        normalized = _slug(value).replace("-", "_")
        if normalized in {"mapped", "unmapped", "confirmed_none", "misaligned"}:
            return normalized
        return "unmapped"

    @staticmethod
    def _targets_without_process(
        targets: list[dict[str, Any]],
        links: list[dict[str, Any]],
        *,
        gap_type: str,
        reason: str,
    ) -> list[dict[str, Any]]:
        missing: list[dict[str, Any]] = []
        for target in targets:
            if not any(StrategyAlignmentN1Service._target_matches(link, target) for link in links):
                missing.append(
                    StrategyAlignmentN1Service._with_gap_meta(
                        target,
                        gap_type=gap_type,
                        reason=reason,
                    )
                )
        return missing

    @staticmethod
    def _pct(numerator: int | float, denominator: int | float) -> float | None:
        if not denominator:
            return None
        return round((float(numerator) / float(denominator)) * 100, 2)

    @staticmethod
    def _analysis_completeness(
        *,
        identity: dict[str, Any],
        processes: list[dict[str, Any]],
        profiles: list[dict[str, Any]],
        objectives: list[dict[str, Any]],
        pillars: list[dict[str, Any]],
        value_propositions: list[dict[str, Any]],
        differentials: list[dict[str, Any]],
        competencies: list[dict[str, Any]],
        policies: list[dict[str, Any]],
        process_indicators: list[dict[str, Any]],
        indicator_line_of_sight: list[dict[str, Any]],
        gaps: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        identity_fields = {
            "mission": bool(_clean_text(identity.get("mission"))),
            "vision": bool(_clean_text(identity.get("vision"))),
            "values": bool(identity.get("values")),
            "purpose": bool(_clean_text(identity.get("purpose"))),
            "value_propositions": bool(identity.get("value_propositions")),
            "differentials": bool(identity.get("differentials")),
            "pillars": bool(identity.get("pillars")),
            "strategic_objectives": bool(identity.get("strategic_objectives") or objectives),
            "essential_competencies": bool(identity.get("essential_competencies")),
            "segments_icp": bool(identity.get("segments_icp")),
            "policies": bool(identity.get("policies")),
            "stakeholders": bool(identity.get("stakeholders")),
            "swot": bool(identity.get("swot")),
            "corporate_indicators": bool(identity.get("corporate_indicators")),
        }
        identity_present = sum(1 for present in identity_fields.values() if present)
        identity_total = len(identity_fields)

        target_totals = {
            "objectives": len(objectives),
            "pillars": len(pillars),
            "value_propositions": len(value_propositions),
            "differentials": len(differentials),
            "essential_competencies": len(competencies),
            "policies": len(policies),
        }
        target_missing = {
            "objectives": len(gaps.get("objectives_without_process", [])),
            "pillars": len(gaps.get("pillars_without_process", [])),
            "value_propositions": len(gaps.get("value_propositions_without_process", [])),
            "differentials": len(gaps.get("differentials_without_process", [])),
            "essential_competencies": len(gaps.get("essential_competencies_without_process", [])),
            "policies": len(gaps.get("policies_without_process", [])),
        }
        traceability_total = sum(target_totals.values()) + len(processes)
        traceability_mapped = (
            sum(max(target_totals[key] - target_missing[key], 0) for key in target_totals)
            + max(len(processes) - len(gaps.get("processes_without_objective", [])), 0)
        )
        line_process_indicator_ids = {
            int(item["process_indicator_id"])
            for item in indicator_line_of_sight
            if item.get("process_indicator_id") is not None
        }
        indicator_total = len(process_indicators)
        indicator_mapped = len(
            {
                int(indicator.get("id") or 0)
                for indicator in process_indicators
                if int(indicator.get("id") or 0) in line_process_indicator_ids
            }
        )
        block_scores = {
            "identity": StrategyAlignmentN1Service._pct(identity_present, identity_total),
            "process_profiles": StrategyAlignmentN1Service._pct(len(profiles), len(processes)),
            "traceability": StrategyAlignmentN1Service._pct(traceability_mapped, traceability_total),
            "indicators": StrategyAlignmentN1Service._pct(indicator_mapped, indicator_total),
        }
        applicable_scores = [score for score in block_scores.values() if score is not None]
        gap_status_counts: dict[str, dict[str, int]] = {}
        for gap_type, items in gaps.items():
            counts = Counter(item.get("gap_status", "unmapped") for item in items)
            gap_status_counts[gap_type] = {
                "unmapped": int(counts.get("unmapped", 0)),
                "confirmed_none": int(counts.get("confirmed_none", 0)),
                "misaligned": int(counts.get("misaligned", 0)),
            }

        return {
            "overall_pct": round(sum(applicable_scores) / len(applicable_scores), 2) if applicable_scores else 100.0,
            "by_block": {
                "identity": {
                    "pct": block_scores["identity"],
                    "present": identity_present,
                    "total": identity_total,
                    "missing_fields": [field for field, present in identity_fields.items() if not present],
                },
                "process_profiles": {
                    "pct": block_scores["process_profiles"],
                    "mapped": len(profiles),
                    "total": len(processes),
                },
                "traceability": {
                    "pct": block_scores["traceability"],
                    "mapped": traceability_mapped,
                    "total": traceability_total,
                    "target_totals": target_totals,
                    "target_missing": target_missing,
                },
                "indicators": {
                    "pct": block_scores["indicators"],
                    "mapped": indicator_mapped,
                    "total": indicator_total,
                },
            },
            "gap_status_counts": gap_status_counts,
        }

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
    def _maturity_risk_weight(maturity_level: Any) -> float | None:
        normalized = _slug(maturity_level).replace("-", "_")
        if normalized in {"", "nao_definido", "na", "none"}:
            return 0.9
        if normalized == "inicial":
            return 0.9
        if normalized == "gerenciado":
            return 0.7
        return None

    @staticmethod
    def _severity_from_weight(weight: float) -> str:
        if weight >= 0.85:
            return "high"
        if weight >= 0.6:
            return "medium"
        return "low"

    @staticmethod
    def _risk_signal(
        *,
        signal_type: str,
        weight: float,
        reason: str,
        process: dict[str, Any] | None = None,
        target: dict[str, Any] | None = None,
        gap_type: str | None = None,
    ) -> dict[str, Any]:
        return {
            "signal_type": signal_type,
            "severity": StrategyAlignmentN1Service._severity_from_weight(weight),
            "weight": round(weight, 2),
            "gap_status": "misaligned",
            "gap_type": gap_type,
            "process": process,
            "target": target,
            "reason": reason,
        }

    @staticmethod
    def _analysis_risk_signals(
        *,
        gaps: dict[str, list[dict[str, Any]]],
        crossings: dict[str, list[dict[str, Any]]],
        profiles_by_process: dict[int, dict[str, Any]],
        processes_by_id: dict[int, dict[str, Any]],
        links_by_type: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        for crossing in crossings.get("process_to_differentials", []):
            process = crossing.get("process") or {}
            process_id = int(process.get("id") or 0)
            profile = profiles_by_process.get(process_id) or {}
            weight = StrategyAlignmentN1Service._maturity_risk_weight(
                profile.get("maturity_level") or process.get("structuring_level")
            )
            if weight is not None:
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="differential_low_maturity_process",
                        weight=weight,
                        process=process,
                        target=crossing.get("target"),
                        gap_type="process_to_differentials",
                        reason="Diferencial competitivo sustentado por processo de baixa maturidade.",
                    )
                )

        for process in gaps.get("processes_without_objective", []):
            profile = profiles_by_process.get(int(process.get("id") or 0)) or {}
            criticality = _slug(profile.get("strategic_criticality")).replace("-", "_")
            if criticality == "alta":
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="high_criticality_process_without_objective",
                        weight=0.85,
                        process=processes_by_id.get(int(process.get("id") or 0), process),
                        gap_type="processes_without_objective",
                        reason="Processo de criticidade alta sem contribuição estratégica explícita.",
                    )
                )

        policy_process_ids = {
            int(link.get("process_id") or 0)
            for link in links_by_type.get("policy", [])
            if link.get("process_id") is not None
        }
        for process_id, profile in profiles_by_process.items():
            if _clean_text(profile.get("regulatory_exposure")) and process_id not in policy_process_ids:
                signals.append(
                    StrategyAlignmentN1Service._risk_signal(
                        signal_type="regulatory_exposure_without_policy_link",
                        weight=0.9,
                        process=processes_by_id.get(process_id),
                        target={"regulatory_exposure": profile.get("regulatory_exposure")},
                        gap_type="policies_without_process",
                        reason="Processo com exposição regulatória sem política/requisito regulatório vinculado.",
                    )
                )

        for indicator in gaps.get("process_indicators_without_corporate", []):
            signals.append(
                StrategyAlignmentN1Service._risk_signal(
                    signal_type="process_indicator_without_corporate_line_of_sight",
                    weight=0.65,
                    process=processes_by_id.get(int(indicator.get("process_id") or 0)),
                    target=indicator,
                    gap_type="process_indicators_without_corporate",
                    reason="Indicador operacional sem linha de visada corporativa.",
                )
            )

        signals.sort(key=lambda item: (-float(item.get("weight") or 0), item.get("signal_type") or ""))
        return signals

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
    def _target_label(item: dict[str, Any] | None) -> str:
        if not item:
            return "alvo não informado"
        return (
            _clean_text(item.get("name"))
            or _clean_text(item.get("objective"))
            or _clean_text(item.get("title"))
            or _clean_text(item.get("code"))
            or _clean_text(item.get("key"))
            or _clean_text(item.get("id"))
            or "alvo não informado"
        )

    @staticmethod
    def _action(
        *,
        priority: str,
        gap_type: str,
        action: str,
        target: dict[str, Any] | None = None,
        status: str = "unmapped",
        severity: str = "medium",
        weight: float | None = None,
    ) -> dict[str, Any]:
        return {
            "priority": priority,
            "gap_type": gap_type,
            "gap_status": status,
            "severity": severity,
            "weight": round(weight, 2) if weight is not None else None,
            "action": action,
            "target_label": StrategyAlignmentN1Service._target_label(target),
            "target": target,
        }

    @staticmethod
    def _analysis_actions(
        *,
        gaps: dict[str, list[dict[str, Any]]],
        risk_signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for signal in risk_signals:
            actions.append(
                StrategyAlignmentN1Service._action(
                    priority="P0" if signal.get("severity") == "high" else "P1",
                    gap_type=str(signal.get("gap_type") or signal.get("signal_type") or "risk_signal"),
                    status="misaligned",
                    severity=str(signal.get("severity") or "medium"),
                    weight=float(signal.get("weight") or 0),
                    target=signal.get("target") or signal.get("process"),
                    action=f"Mitigar risco: {signal.get('reason')}",
                )
            )

        action_specs = {
            "objectives_without_process": ("P1", "Vincular objetivo estratégico a processo contribuinte ou registrar confirmed_none."),
            "processes_without_objective": ("P1", "Definir objetivo estratégico contribuído pelo processo ou registrar confirmed_none."),
            "processes_without_purpose": ("P1", "Preencher objetivo do processo e propósito operacional."),
            "pillars_without_process": ("P2", "Vincular pilar estratégico a processos contribuintes."),
            "value_propositions_without_process": ("P1", "Mapear processo que entrega a proposta de valor."),
            "differentials_without_process": ("P1", "Conectar diferencial competitivo ao processo core sustentador."),
            "essential_competencies_without_process": ("P2", "Mapear competência essencial aos processos que a materializam."),
            "policies_without_process": ("P1", "Vincular política ou requisito regulatório aos processos aplicáveis."),
            "values_without_policy": ("P1", "Formalizar ou vincular política que materializa o valor organizacional."),
            "process_indicators_without_corporate": ("P1", "Criar linha de visada entre indicador de processo e indicador corporativo."),
        }
        for gap_type, items in gaps.items():
            priority, action_text = action_specs.get(gap_type, ("P2", "Revisar gap de alinhamento estratégico."))
            for item in items:
                actions.append(
                    StrategyAlignmentN1Service._action(
                        priority=priority,
                        gap_type=gap_type,
                        status=StrategyAlignmentN1Service._normalize_gap_status(item.get("gap_status")),
                        severity=str(item.get("severity") or "medium"),
                        target=item,
                        action=action_text,
                    )
                )

        if not actions:
            actions.append(
                StrategyAlignmentN1Service._action(
                    priority="P3",
                    gap_type="none",
                    status="mapped",
                    severity="low",
                    action="Sem gaps críticos detectados no read model N1 atual; validar mapa com consultor/cliente.",
                )
            )

        priority_rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        actions.sort(
            key=lambda item: (
                priority_rank.get(str(item.get("priority")), 9),
                -float(item.get("weight") or 0),
                str(item.get("gap_type") or ""),
                str(item.get("target_label") or ""),
            )
        )
        return actions


__all__ = ["StrategyAlignmentN1Error", "StrategyAlignmentN1Service"]
