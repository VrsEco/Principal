from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import desc

from models import (
    Indicator,
    IndicatorData,
    IndicatorEntityLink,
    IndicatorGoal,
    OKRArea,
    OKRGlobal,
    OrganizationalIdentity,
    Process,
    Project,
    db,
)


TARGET_TYPE_LABELS = {
    "process": "Processo",
    "project": "Projeto",
    "okr_global": "OKR Global",
    "okr_area": "OKR de Área",
    "strategic_objective": "Objetivo Estratégico",
}


class IndicatorLinkMapService:
    """Service de mapa N:N Indicador × Entidades monitoradas."""

    @staticmethod
    def normalize_target_ref(target_id: int | None = None, target_ref: str | None = None) -> str:
        ref = str(target_ref or "").strip()
        if ref:
            return ref
        if target_id is None:
            raise ValueError("target_id ou target_ref é obrigatório.")
        return str(int(target_id))

    @staticmethod
    def resolve_target(company_id: int, target_type: str, target_ref: str) -> dict[str, Any] | None:
        if target_type == "process":
            row = Process.query.filter_by(company_id=company_id, id=int(target_ref)).first()
            return _entity_payload(row, target_type, getattr(row, "code", None), getattr(row, "name", None)) if row else None
        if target_type == "project":
            row = Project.query.filter_by(company_id=company_id, id=int(target_ref)).first()
            return _entity_payload(row, target_type, getattr(row, "code", None), getattr(row, "name", None)) if row else None
        if target_type == "okr_global":
            row = OKRGlobal.query.filter_by(company_id=company_id, id=int(target_ref)).first()
            return _entity_payload(row, target_type, f"OKRG-{row.id}", row.objective) if row else None
        if target_type == "okr_area":
            row = OKRArea.query.filter_by(company_id=company_id, id=int(target_ref)).first()
            return _entity_payload(row, target_type, f"OKRA-{row.id}", row.objective) if row else None
        if target_type == "strategic_objective":
            identity = OrganizationalIdentity.query.filter_by(company_id=company_id).first()
            for item in (identity.strategic_objectives_json or []) if identity else []:
                key, label = _strategic_item_key_label(item)
                if key == target_ref:
                    return {
                        "type": target_type,
                        "type_label": TARGET_TYPE_LABELS[target_type],
                        "id": None,
                        "ref": key,
                        "code": key,
                        "name": label,
                    }
        return None

    @staticmethod
    def upsert_link(company_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        indicator_id = int(payload.get("indicator_id") or 0)
        target_type = str(payload.get("target_type") or "").strip()
        target_id = payload.get("target_id")
        target_id = int(target_id) if target_id not in (None, "", "null") else None
        target_ref = IndicatorLinkMapService.normalize_target_ref(target_id, payload.get("target_ref"))

        indicator = Indicator.query.filter_by(company_id=company_id, id=indicator_id).first()
        if not indicator:
            raise ValueError("Indicador inválido para a empresa ativa.")

        target = IndicatorLinkMapService.resolve_target(company_id, target_type, target_ref)
        if not target:
            raise ValueError("Destino inválido para a empresa ativa.")

        link = IndicatorEntityLink.query.filter_by(
            company_id=company_id,
            indicator_id=indicator_id,
            target_type=target_type,
            target_ref=target_ref,
        ).first()
        if not link:
            link = IndicatorEntityLink(
                company_id=company_id,
                indicator_id=indicator_id,
                target_type=target_type,
                target_ref=target_ref,
            )
            db.session.add(link)

        link.target_id = target_id or target.get("id")
        link.target_label = target.get("name")
        link.role = payload.get("role") or "primary"
        link.health_dimension = payload.get("health_dimension") or None
        link.weight = _decimal_or_none(payload.get("weight"))
        link.relationship_type = payload.get("relationship_type") or None
        link.notes = payload.get("notes") or None
        link.is_active = bool(payload.get("is_active", True))
        db.session.flush()
        return link.to_dict()

    @staticmethod
    def build_map(company_id: int, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        filters = filters or {}
        target_types = _normalize_list(filters.get("target_types")) or [
            "process",
            "project",
            "okr_global",
            "okr_area",
            "strategic_objective",
        ]

        indicators = {
            int(row.id): row
            for row in Indicator.query.filter_by(company_id=company_id, is_active=True).order_by(Indicator.name).all()
        }

        links = (
            IndicatorEntityLink.query.filter(
                IndicatorEntityLink.company_id == company_id,
                IndicatorEntityLink.is_active.is_(True),
                IndicatorEntityLink.target_type.in_(target_types),
            )
            .order_by(IndicatorEntityLink.target_type, IndicatorEntityLink.target_ref, IndicatorEntityLink.indicator_id)
            .all()
        )

        # Compatibilidade: se ainda não houve migration/backfill, inclui vínculos legados em memória.
        links_payload = [_link_payload(link, indicators.get(int(link.indicator_id))) for link in links if int(link.indicator_id) in indicators]
        links_payload.extend(_legacy_links(company_id, indicators, links_payload, target_types))

        targets = _build_targets(company_id, links_payload)
        indicator_payload = [_indicator_payload(ind) for ind in indicators.values()]
        perf = _indicator_performance(company_id, list(indicators.keys()))
        for item in indicator_payload:
            item["performance"] = perf.get(int(item["id"]))

        matrix = _build_matrix(targets, indicator_payload, links_payload, perf)
        network = _build_network(targets, indicator_payload, links_payload, perf)
        summaries = _build_summaries(company_id, targets, indicator_payload, links_payload)
        recommendations = _build_recommendations(summaries, targets, indicator_payload, links_payload)

        return {
            "company_id": company_id,
            "target_types": target_types,
            "summary": summaries,
            "matrix": matrix,
            "network": network,
            "recommendations": recommendations,
            "links": links_payload,
            "indicators": indicator_payload,
            "targets": list(targets.values()),
        }


def _entity_payload(row: Any, target_type: str, code: str | None, name: str | None) -> dict[str, Any]:
    return {
        "type": target_type,
        "type_label": TARGET_TYPE_LABELS.get(target_type, target_type),
        "id": int(row.id),
        "ref": str(row.id),
        "code": code,
        "name": name or f"{TARGET_TYPE_LABELS.get(target_type, target_type)} {row.id}",
    }


def _strategic_item_key_label(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        key = str(item.get("id") or item.get("key") or item.get("code") or item.get("name") or item.get("title") or "").strip()
        label = str(item.get("name") or item.get("title") or item.get("label") or key).strip()
        return key, label or key
    label = str(item or "").strip()
    return label, label


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = str(value).split(",")
    return [str(item).strip() for item in raw if str(item).strip()]


def _decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, "", "null"):
        return None
    return Decimal(str(value))


def _indicator_payload(ind: Indicator) -> dict[str, Any]:
    return {
        "id": int(ind.id),
        "code": ind.code,
        "name": ind.name,
        "type": ind.indicator_type,
        "unit": ind.unit,
        "polarity": ind.polarity,
        "frequency": ind.measurement_frequency,
    }


def _link_payload(link: IndicatorEntityLink, indicator: Indicator | None) -> dict[str, Any]:
    return {
        **link.to_dict(),
        "indicator_code": indicator.code if indicator else None,
        "indicator_name": indicator.name if indicator else None,
        "target_key": f"{link.target_type}:{link.target_ref}",
    }


def _legacy_links(company_id: int, indicators: dict[int, Indicator], existing: list[dict[str, Any]], target_types: list[str]) -> list[dict[str, Any]]:
    seen = {(item["indicator_id"], item["target_type"], item["target_ref"]) for item in existing}
    payload = []
    for ind in indicators.values():
        for target_type, target_id in (("process", ind.process_id), ("project", ind.project_id)):
            if target_type not in target_types or not target_id:
                continue
            key = (int(ind.id), target_type, str(target_id))
            if key in seen:
                continue
            target = IndicatorLinkMapService.resolve_target(company_id, target_type, str(target_id))
            if not target:
                continue
            payload.append({
                "id": None,
                "company_id": company_id,
                "indicator_id": int(ind.id),
                "target_type": target_type,
                "target_id": int(target_id),
                "target_ref": str(target_id),
                "target_label": target["name"],
                "role": "primary",
                "health_dimension": None,
                "weight": None,
                "relationship_type": "legacy_direct_fk",
                "notes": "Vínculo legado ainda não materializado em indicator_entity_links.",
                "is_active": True,
                "indicator_code": ind.code,
                "indicator_name": ind.name,
                "target_key": f"{target_type}:{target_id}",
            })
    return payload


def _build_targets(company_id: int, links: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    for link in links:
        target = IndicatorLinkMapService.resolve_target(company_id, link["target_type"], link["target_ref"])
        if not target:
            target = {
                "type": link["target_type"],
                "type_label": TARGET_TYPE_LABELS.get(link["target_type"], link["target_type"]),
                "id": link.get("target_id"),
                "ref": link["target_ref"],
                "code": link["target_ref"],
                "name": link.get("target_label") or link["target_ref"],
            }
        target["key"] = f'{target["type"]}:{target["ref"]}'
        targets[target["key"]] = target
    return targets


def _indicator_performance(company_id: int, indicator_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not indicator_ids:
        return {}
    goals = (
        IndicatorGoal.query.filter(
            IndicatorGoal.company_id == company_id,
            IndicatorGoal.indicator_id.in_(indicator_ids),
            IndicatorGoal.status == "active",
        )
        .order_by(IndicatorGoal.indicator_id.asc(), desc(IndicatorGoal.goal_date).nullslast(), IndicatorGoal.id.desc())
        .all()
    )
    latest_goal = {}
    for goal in goals:
        latest_goal.setdefault(int(goal.indicator_id), goal)

    records = (
        IndicatorData.query.filter(
            IndicatorData.company_id == company_id,
            IndicatorData.indicator_id.in_(indicator_ids),
        )
        .order_by(IndicatorData.indicator_id.asc(), IndicatorData.measured_date.desc(), IndicatorData.id.desc())
        .all()
    )
    latest_record = {}
    for record in records:
        latest_record.setdefault(int(record.indicator_id), record)

    indicators = {
        int(ind.id): ind
        for ind in Indicator.query.filter(
            Indicator.company_id == company_id,
            Indicator.id.in_(indicator_ids),
        ).all()
    }
    payload = {}
    for indicator_id in indicator_ids:
        goal = latest_goal.get(indicator_id)
        record = latest_record.get(indicator_id)
        score = None
        status = "sem_dados"
        if goal and record and float(goal.goal_value or 0) != 0:
            measured = float(record.measured_value or 0)
            target = float(goal.goal_value or 0)
            if indicators.get(indicator_id) and indicators[indicator_id].polarity == "negative":
                score = 100.0 if measured == 0 else round((target / measured) * 100, 1)
            else:
                score = round((measured / target) * 100, 1)
            status = "verde" if score >= 95 else "amarelo" if score >= 80 else "vermelho"
        payload[indicator_id] = {
            "score": score,
            "status": status,
            "measured_value": float(record.measured_value) if record else None,
            "measured_date": record.measured_date.isoformat() if record and record.measured_date else None,
            "goal_value": float(goal.goal_value) if goal else None,
        }
    return payload


def _build_matrix(targets: dict[str, dict[str, Any]], indicators: list[dict[str, Any]], links: list[dict[str, Any]], perf: dict[int, dict[str, Any]]) -> dict[str, Any]:
    linked_indicator_ids = sorted({int(link["indicator_id"]) for link in links})
    columns = [item for item in indicators if int(item["id"]) in linked_indicator_ids]
    links_by_cell = defaultdict(list)
    for link in links:
        links_by_cell[(link["target_key"], int(link["indicator_id"]))].append(link)
    rows = []
    for target_key, target in sorted(targets.items(), key=lambda kv: (kv[1]["type"], kv[1]["name"])):
        cells = []
        for indicator in columns:
            cell_links = links_by_cell.get((target_key, int(indicator["id"])), [])
            cells.append({
                "linked": bool(cell_links),
                "role": cell_links[0]["role"] if cell_links else None,
                "dimension": cell_links[0].get("health_dimension") if cell_links else None,
                "weight": cell_links[0].get("weight") if cell_links else None,
                "status": perf.get(int(indicator["id"]), {}).get("status") if cell_links else None,
            })
        rows.append({"target": target, "cells": cells, "link_count": sum(1 for c in cells if c["linked"])})
    return {"columns": columns, "rows": rows}


def _build_network(targets: dict[str, dict[str, Any]], indicators: list[dict[str, Any]], links: list[dict[str, Any]], perf: dict[int, dict[str, Any]]) -> dict[str, Any]:
    nodes = []
    for target in targets.values():
        nodes.append({"id": target["key"], "label": target["name"], "type": target["type"], "group": "target"})
    linked_ids = {int(link["indicator_id"]) for link in links}
    for ind in indicators:
        if int(ind["id"]) in linked_ids:
            status = perf.get(int(ind["id"]), {}).get("status")
            nodes.append({"id": f'indicator:{ind["id"]}', "label": ind["name"], "type": "indicator", "group": "indicator", "status": status})
    edges = [
        {
            "from": link["target_key"],
            "to": f'indicator:{link["indicator_id"]}',
            "role": link["role"],
            "dimension": link.get("health_dimension"),
            "weight": link.get("weight"),
        }
        for link in links
    ]
    return {"nodes": nodes, "edges": edges}


def _build_summaries(company_id: int, targets: dict[str, dict[str, Any]], indicators: list[dict[str, Any]], links: list[dict[str, Any]]) -> dict[str, Any]:
    links_by_target = Counter(link["target_key"] for link in links)
    links_by_indicator = Counter(int(link["indicator_id"]) for link in links)
    role_counts = Counter(link["role"] for link in links)
    dimension_counts = Counter(link.get("health_dimension") or "sem_dimensao" for link in links)
    target_type_counts = Counter(target["type"] for target in targets.values())

    process_total = Process.query.filter_by(company_id=company_id, is_active=True).count()
    project_total = Project.query.filter_by(company_id=company_id, is_deleted=False).count()
    okr_global_total = OKRGlobal.query.filter_by(company_id=company_id).count()
    okr_area_total = OKRArea.query.filter_by(company_id=company_id).count()

    return {
        "active_indicators": len(indicators),
        "linked_indicators": len(links_by_indicator),
        "unlinked_indicators": len(indicators) - len(links_by_indicator),
        "linked_targets": len(targets),
        "total_links": len(links),
        "target_type_counts": dict(target_type_counts),
        "role_counts": dict(role_counts),
        "dimension_counts": dict(dimension_counts),
        "targets_without_primary": sum(1 for key in targets if not any(link["target_key"] == key and link["role"] == "primary" for link in links)),
        "targets_with_many_indicators": sum(1 for count in links_by_target.values() if count >= 6),
        "indicators_monitoring_many_targets": sum(1 for count in links_by_indicator.values() if count >= 6),
        "catalog_totals": {
            "process": process_total,
            "project": project_total,
            "okr_global": okr_global_total,
            "okr_area": okr_area_total,
        },
    }


def _build_recommendations(summary: dict[str, Any], targets: dict[str, dict[str, Any]], indicators: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[dict[str, str]]:
    recommendations = []
    if summary["unlinked_indicators"]:
        recommendations.append({
            "severity": "medium",
            "title": "Indicadores sem vínculo operacional",
            "detail": f"{summary['unlinked_indicators']} indicador(es) ativo(s) não aparecem no mapa. Vincule ou inative para reduzir ruído de gestão.",
        })
    if summary["targets_without_primary"]:
        recommendations.append({
            "severity": "high",
            "title": "Entidades sem indicador primário",
            "detail": f"{summary['targets_without_primary']} processo/projeto/objetivo não possui KPI principal. Defina pelo menos um indicador primário.",
        })
    if summary["targets_with_many_indicators"]:
        recommendations.append({
            "severity": "medium",
            "title": "Possível excesso de medição",
            "detail": f"{summary['targets_with_many_indicators']} entidade(s) têm 6+ indicadores. Revise foco, peso e dimensões para evitar painel poluído.",
        })
    if summary["indicators_monitoring_many_targets"]:
        recommendations.append({
            "severity": "low",
            "title": "Indicadores muito reutilizados",
            "detail": f"{summary['indicators_monitoring_many_targets']} indicador(es) monitoram 6+ entidades. Confirme se são KPIs corporativos ou se precisam de segmentação.",
        })
    if not recommendations:
        recommendations.append({
            "severity": "success",
            "title": "Mapa consistente",
            "detail": "Não foram encontrados alertas relevantes na cobertura atual dos vínculos.",
        })
    return recommendations
