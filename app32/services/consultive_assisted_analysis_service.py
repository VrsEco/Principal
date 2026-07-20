from __future__ import annotations

from typing import Any

from models import (
    AssistedAnalysis,
    AssistedAnalysisDecision,
    AssistedAnalysisValidation,
    Company,
    db,
)
from models.consultive_assisted_analysis import (
    ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES,
    ASSISTED_ANALYSIS_DECISION_VALUES,
    ASSISTED_ANALYSIS_STATUS_VALUES,
    ASSISTED_ANALYSIS_TYPE_VALUES,
    ASSISTED_ANALYSIS_VALIDATION_SQUAD_VALUES,
    ASSISTED_ANALYSIS_VALIDATION_STATUS_VALUES,
    CONSULTIVE_FRONT_KEY_VALUES,
)
from services.urgent_business_review_common import UrgentBusinessReviewError
from services.consultive_protocol_service import ConsultiveProtocolService


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_text(value: Any, field: str) -> str:
    text = _clean_text(value)
    if not text:
        raise UrgentBusinessReviewError(f"Campo obrigatório não informado: {field}.")
    return text


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _has_evidence(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_has_evidence(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_evidence(item) for item in value)
    return bool(_clean_text(value))


def _analysis_eligibility(
    *,
    analysis_type: str,
    payload: dict[str, Any],
    protocol_snapshot: dict[str, Any],
) -> tuple[bool, list[str]]:
    if analysis_type == "technical_test":
        return False, ["technical_test_not_methodological"]

    reasons: list[str] = []
    subphase_key = _clean_text(
        payload.get("subphase_key")
        or payload.get("protocol_subphase_key")
        or protocol_snapshot.get("subphase_key")
    )
    if not subphase_key:
        reasons.append("subphase_key_missing")
    for field in ("human_evidence", "internal_evidence", "risks", "recommendations"):
        if not _has_evidence(payload.get(field)):
            reasons.append(f"{field}_missing")
    if not _has_evidence(payload.get("benchmarks")) and not _has_evidence(
        payload.get("benchmark_not_applicable_reason")
    ):
        reasons.append("benchmark_or_justification_missing")
    return not reasons, reasons


def _normalize_choice(value: Any, allowed: tuple[str, ...], *, default: str, field: str) -> str:
    normalized = str(value or default).strip().lower()
    if normalized not in allowed:
        raise UrgentBusinessReviewError(f"Valor inválido para {field}: {value}.")
    return normalized


class ConsultiveAssistedAnalysisService:
    """Service tenant-safe para análises assistidas recebidas via IA/CLI + MCP."""

    evaluate_eligibility = staticmethod(_analysis_eligibility)

    @staticmethod
    def _require_company(company_id: int) -> Company:
        company = Company.query.filter_by(id=company_id).first()
        if company is None:
            raise UrgentBusinessReviewError(f"Empresa não encontrada: company_id={company_id}.")
        return company

    @staticmethod
    def _normalize_front_key(front_key: Any) -> str:
        return _normalize_choice(
            front_key,
            CONSULTIVE_FRONT_KEY_VALUES,
            default="identity",
            field="front_key",
        )

    @staticmethod
    def _require_analysis(company_id: int, analysis_id: int) -> AssistedAnalysis:
        row = AssistedAnalysis.query.filter_by(company_id=company_id, id=analysis_id).first()
        if row is None:
            raise UrgentBusinessReviewError(
                f"Análise assistida não encontrada no tenant informado: company_id={company_id}, analysis_id={analysis_id}."
            )
        return row

    @staticmethod
    def _protocol_snapshot(
        *,
        company_id: int,
        front_key: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        supplied = payload.get("protocol_snapshot") or payload.get("protocol_snapshot_json")
        if isinstance(supplied, dict) and supplied:
            return dict(supplied)
        return ConsultiveProtocolService.resolve_protocol(
            company_id=company_id,
            front_key=front_key,
            subphase_key=payload.get("protocol_subphase_key") or payload.get("subphase_key"),
            audience=payload.get("protocol_audience") or "ai_cli",
            depth_level=payload.get("protocol_depth_level") or None,
        )

    @staticmethod
    def _serialize_analysis(row: AssistedAnalysis) -> dict[str, Any]:
        item = row.to_dict()
        validations = getattr(row, "validations", None)
        decisions = getattr(row, "decisions", None)
        item["validations"] = (
            [validation.to_dict() for validation in validations.order_by(AssistedAnalysisValidation.updated_at.desc()).all()]
            if validations is not None
            else []
        )
        latest_decision = (
            decisions.order_by(AssistedAnalysisDecision.created_at.desc()).first()
            if decisions is not None
            else None
        )
        item["latest_decision"] = latest_decision.to_dict() if latest_decision is not None else None
        return item

    @staticmethod
    def list_analyses(
        *,
        company_id: int,
        front_key: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        ConsultiveAssistedAnalysisService._require_company(company_id)
        query = AssistedAnalysis.query.filter_by(company_id=company_id)
        if front_key:
            query = query.filter_by(front_key=ConsultiveAssistedAnalysisService._normalize_front_key(front_key))
        if status:
            query = query.filter_by(
                status=_normalize_choice(
                    status,
                    ASSISTED_ANALYSIS_STATUS_VALUES,
                    default="received",
                    field="status",
                )
            )
        rows = query.order_by(AssistedAnalysis.created_at.desc()).limit(max(1, min(int(limit or 100), 500))).all()
        return [ConsultiveAssistedAnalysisService._serialize_analysis(row) for row in rows]

    @staticmethod
    def register_assisted_analysis(
        *,
        company_id: int,
        front_key: str,
        payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        ConsultiveAssistedAnalysisService._require_company(company_id)
        if not isinstance(payload, dict):
            raise UrgentBusinessReviewError("Payload da análise assistida deve ser um objeto.")

        normalized_front_key = ConsultiveAssistedAnalysisService._normalize_front_key(front_key)
        protocol_snapshot = ConsultiveAssistedAnalysisService._protocol_snapshot(
            company_id=company_id,
            front_key=normalized_front_key,
            payload=payload,
        )
        analysis_type = _normalize_choice(
            payload.get("analysis_type"),
            ASSISTED_ANALYSIS_TYPE_VALUES,
            default="technical_test",
            field="analysis_type",
        )
        journey_eligible, eligibility_reasons = _analysis_eligibility(
            analysis_type=analysis_type,
            payload=payload,
            protocol_snapshot=protocol_snapshot,
        )
        source_payload = payload.get("source_payload") or {}
        if not isinstance(source_payload, dict):
            raise UrgentBusinessReviewError("source_payload deve ser um objeto.")
        source_payload = dict(source_payload)
        for evidence_field in (
            "subphase_key",
            "human_evidence",
            "internal_evidence",
            "benchmark_not_applicable_reason",
        ):
            if evidence_field in payload:
                source_payload[evidence_field] = payload.get(evidence_field)

        row = AssistedAnalysis(
            company_id=company_id,
            front_key=normalized_front_key,
            analysis_type=analysis_type,
            journey_eligible=journey_eligible,
            eligibility_reasons_json=eligibility_reasons,
            status=_normalize_choice(
                payload.get("analysis_status") or payload.get("status"),
                ASSISTED_ANALYSIS_STATUS_VALUES,
                default="received",
                field="status",
            ),
            ai_origin=_clean_text(payload.get("ai_origin")),
            responsible=_clean_text(payload.get("responsible")),
            diagnosis=_required_text(payload.get("diagnosis"), "diagnosis"),
            benchmarks=_clean_text(payload.get("benchmarks")),
            risks=_clean_text(payload.get("risks")),
            recommendations=_clean_text(payload.get("recommendations")),
            source_payload_json=source_payload,
            protocol_id=_optional_int(payload.get("protocol_id") or protocol_snapshot.get("id")),
            protocol_version=_clean_text(payload.get("protocol_version")) or _clean_text(protocol_snapshot.get("protocol_version")),
            protocol_source=_clean_text(payload.get("protocol_source")) or _clean_text(protocol_snapshot.get("source")),
            protocol_title=_clean_text(payload.get("protocol_title")) or _clean_text(protocol_snapshot.get("title")),
            protocol_snapshot_json=protocol_snapshot,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        db.session.add(row)
        db.session.flush()

        validation_payloads = {
            "client": payload.get("client_squad_validation"),
            "versus": payload.get("versus_squad_validation"),
            "engineering": payload.get("engineering_squad_validation"),
        }
        if journey_eligible:
            for squad, notes in validation_payloads.items():
                if _clean_text(notes):
                    db.session.add(
                        AssistedAnalysisValidation(
                            company_id=company_id,
                            analysis_id=row.id,
                            squad=squad,
                            status="pending",
                            notes=_clean_text(notes),
                            validated_by_user_id=user_id,
                        )
                    )

        db.session.commit()
        return ConsultiveAssistedAnalysisService._serialize_analysis(row)

    @staticmethod
    def _require_journey_eligible(analysis: AssistedAnalysis) -> None:
        if analysis.analysis_type != "methodological" or not analysis.journey_eligible:
            raise UrgentBusinessReviewError(
                "Análise técnica ou metodologicamente inelegível não pode avançar para validação, decisão ou conversão."
            )

    @staticmethod
    def register_squad_validation(
        *,
        company_id: int,
        analysis_id: int,
        squad: str,
        status: str,
        notes: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, Any]:
        analysis = ConsultiveAssistedAnalysisService._require_analysis(company_id, analysis_id)
        ConsultiveAssistedAnalysisService._require_journey_eligible(analysis)
        normalized_squad = _normalize_choice(
            squad,
            ASSISTED_ANALYSIS_VALIDATION_SQUAD_VALUES,
            default="client",
            field="squad",
        )
        normalized_status = _normalize_choice(
            status,
            ASSISTED_ANALYSIS_VALIDATION_STATUS_VALUES,
            default="pending",
            field="status",
        )
        row = AssistedAnalysisValidation.query.filter_by(
            company_id=company_id,
            analysis_id=analysis_id,
            squad=normalized_squad,
        ).first()
        if row is None:
            row = AssistedAnalysisValidation(
                company_id=company_id,
                analysis_id=analysis_id,
                squad=normalized_squad,
            )
            db.session.add(row)

        row.status = normalized_status
        row.notes = _clean_text(notes)
        row.validated_by_user_id = user_id
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def register_consultant_decision(
        *,
        company_id: int,
        analysis_id: int,
        payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        analysis = ConsultiveAssistedAnalysisService._require_analysis(company_id, analysis_id)
        ConsultiveAssistedAnalysisService._require_journey_eligible(analysis)
        if not isinstance(payload, dict):
            raise UrgentBusinessReviewError("Payload da decisão deve ser um objeto.")

        row = AssistedAnalysisDecision(
            company_id=company_id,
            analysis_id=analysis.id,
            decision=_normalize_choice(
                payload.get("consultant_decision") or payload.get("decision"),
                ASSISTED_ANALYSIS_DECISION_VALUES,
                default="hold",
                field="decision",
            ),
            conversion_target=_normalize_choice(
                payload.get("conversion_target"),
                ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES,
                default="none",
                field="conversion_target",
            ),
            decision_reason=_required_text(payload.get("decision_reason"), "decision_reason"),
            next_action=_clean_text(payload.get("next_action")),
            governance_notes=_clean_text(payload.get("governance_notes")),
            decided_by_user_id=user_id,
        )
        db.session.add(row)

        if row.decision == "reject":
            analysis.status = "rejected"
        elif row.conversion_target != "none":
            analysis.status = "conversion_requested"
        else:
            analysis.status = "validated" if row.decision == "accept" else "under_review"
        analysis.updated_by_user_id = user_id
        db.session.commit()
        return row.to_dict()

    @staticmethod
    def create_recommended_action(
        *,
        company_id: int,
        analysis_id: int,
        conversion_target: str,
        payload: dict[str, Any],
        user_id: int | None = None,
    ) -> dict[str, Any]:
        """Gate reservado: registra intenção sem criar objeto operacional automaticamente."""
        analysis = ConsultiveAssistedAnalysisService._require_analysis(company_id, analysis_id)
        ConsultiveAssistedAnalysisService._require_journey_eligible(analysis)
        target = _normalize_choice(
            conversion_target,
            ASSISTED_ANALYSIS_CONVERSION_TARGET_VALUES,
            default="none",
            field="conversion_target",
        )
        if target == "none":
            raise UrgentBusinessReviewError("conversion_target deve indicar um objeto operacional para conversão.")
        analysis.status = "conversion_requested"
        analysis.updated_by_user_id = user_id
        db.session.commit()
        return {
            "company_id": company_id,
            "analysis_id": analysis_id,
            "conversion_target": target,
            "status": "pending_human_execution",
            "payload": dict(payload or {}),
            "user_id": user_id,
            "message": "Ação recomendada registrada como intenção; criação operacional deve ocorrer por tool específica com gate humano.",
        }


__all__ = ["ConsultiveAssistedAnalysisService"]
