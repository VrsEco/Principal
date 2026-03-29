from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from models import Company, FinancialBudgetVersion


class FinancialBudgetCodeService:
    """Helpers determinísticos para enquadramento e codificação orçamentária."""

    CATEGORY_ALIASES = {
        "CAPEX EXTRA": "CAPEX_EXTRA",
        "CAPEX-EXTRA": "CAPEX_EXTRA",
        "CAPEX_EXTRA": "CAPEX_EXTRA",
        "CAPEXX": "CAPEX_EXTRA",
        "CAPEX EXTRAORDINARIO": "CAPEX_EXTRA",
        "CAPEX EXTRAORDINÁRIO": "CAPEX_EXTRA",
        "OPEX": "OPEX",
        "CAPEX": "CAPEX",
    }

    VERSION_CODE_PREFIX = "O"

    @staticmethod
    def normalize_text(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def normalize_budget_category(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = FinancialBudgetCodeService.normalize_text(str(value))
        if not text:
            return None
        token = re.sub(r"[^A-Za-z0-9]+", "_", text).upper().strip("_")
        return FinancialBudgetCodeService.CATEGORY_ALIASES.get(token, token)

    @staticmethod
    def normalize_budget_cycle(value: Any, *, fallback_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        if value is None:
            if fallback_date is None:
                return None
            year = fallback_date.year
            return {
                "year": year,
                "code": str(year),
                "label": f"Ciclo Orçamentário {year}",
                "type": "annual",
            }

        if isinstance(value, dict):
            year = FinancialBudgetCodeService._coerce_year(
                value.get("year") or value.get("ano") or value.get("period_year")
            )
            label = FinancialBudgetCodeService.normalize_text(
                value.get("label") or value.get("name") or value.get("description")
            )
            code = FinancialBudgetCodeService.normalize_text(
                value.get("code") or value.get("key") or value.get("id")
            )
            cycle_type = FinancialBudgetCodeService.normalize_text(value.get("type") or value.get("cycle_type")) or "annual"
            if year is None and code and code.isdigit():
                year = int(code)
            if year is None:
                year = fallback_date.year if fallback_date else None
            if year is None:
                return None
            return {
                "year": int(year),
                "code": code or str(int(year)),
                "label": label or f"Ciclo Orçamentário {int(year)}",
                "type": cycle_type,
            }

        text = FinancialBudgetCodeService.normalize_text(str(value))
        if not text:
            return None

        year = FinancialBudgetCodeService._coerce_year(text)
        if year is None:
            year = fallback_date.year if fallback_date else None
        if year is None:
            return None
        return {
            "year": int(year),
            "code": text,
            "label": f"Ciclo Orçamentário {int(year)}",
            "type": "annual",
        }

    @staticmethod
    def _coerce_date(value: Any) -> Optional[date]:
        if value is None or value == "":
            return None
        if isinstance(value, date):
            return value
        text = FinancialBudgetCodeService.normalize_text(str(value))
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except Exception:
            return None

    @staticmethod
    def normalize_version_payload(
        payload: Dict[str, Any],
        *,
        company_id: Optional[int] = None,
        existing_metadata_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized = dict(payload or {})
        metadata = dict(existing_metadata_json or {})
        incoming_metadata = normalized.get("metadata_json")
        if isinstance(incoming_metadata, dict):
            metadata.update(incoming_metadata)

        for key in (
            "budget_cycle",
            "budget_category",
            "budget_group",
            "budget_group_code",
            "budget_group_label",
            "budget_consolidation_group",
            "budget_analysis_mode",
            "budget_scope",
            "budget_version_type",
        ):
            if key in normalized:
                metadata[key] = normalized.pop(key)

        fallback_period = FinancialBudgetCodeService._coerce_date(normalized.get("period_start"))
        budget_cycle = FinancialBudgetCodeService.normalize_budget_cycle(metadata.get("budget_cycle"), fallback_date=fallback_period)
        if budget_cycle is None and fallback_period is not None:
            budget_cycle = FinancialBudgetCodeService.normalize_budget_cycle(None, fallback_date=fallback_period)
        if budget_cycle is not None:
            metadata["budget_cycle"] = budget_cycle

        budget_category = FinancialBudgetCodeService.normalize_budget_category(
            metadata.get("budget_category") or metadata.get("budget_group")
        )
        if budget_category is not None:
            metadata["budget_category"] = budget_category

        if metadata.get("budget_group") is None and budget_category:
            metadata["budget_group"] = budget_category
        if metadata.get("budget_group_code") is None and budget_category:
            metadata["budget_group_code"] = budget_category
        if metadata.get("budget_group_label") is None and budget_category:
            metadata["budget_group_label"] = budget_category.replace("_", " ").title()

        if metadata.get("budget_analysis_mode") is None:
            metadata["budget_analysis_mode"] = "separated"

        if metadata or incoming_metadata is not None or existing_metadata_json is not None:
            normalized["metadata_json"] = metadata

        if not normalized.get("code") and company_id and normalized.get("period_start"):
            normalized["code"] = FinancialBudgetCodeService.build_version_code(
                company_id=company_id,
                period_start=normalized.get("period_start"),
                budget_category=budget_category,
                existing_code=None,
            )

        return normalized

    @staticmethod
    def build_version_code(
        *,
        company_id: int,
        period_start: date,
        budget_category: Optional[str] = None,
        existing_code: Optional[str] = None,
    ) -> str:
        if existing_code:
            return existing_code

        company_code = FinancialBudgetCodeService.get_company_code(company_id)
        prefix = f"{company_code}.{FinancialBudgetCodeService.VERSION_CODE_PREFIX}"
        sequence = FinancialBudgetCodeService._next_version_sequence(company_id=company_id, prefix=prefix)
        return f"{prefix}.{sequence}"

    @staticmethod
    def get_company_code(company_id: int) -> str:
        try:
            company = Company.query.filter(Company.id == company_id).first()
        except Exception:
            company = None
        company_code = (company.client_code if company and company.client_code else None) or (
            company.name[:2].upper() if company and company.name else "CP"
        )
        return str(company_code).strip().upper()

    @staticmethod
    def enrich_version_payload(version: FinancialBudgetVersion | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(version, dict):
            payload = dict(version)
            metadata = dict(payload.get("metadata_json") or {})
            period_start = payload.get("period_start")
            if isinstance(period_start, str):
                try:
                    period_start = date.fromisoformat(period_start)
                except Exception:
                    period_start = None
            context = FinancialBudgetCodeService.extract_budget_context(metadata, period_start=period_start)
            payload.update(context)
            return payload

        payload = version.to_dict()
        context = FinancialBudgetCodeService.extract_budget_context(version.metadata_json or {}, period_start=version.period_start)
        payload.update(context)
        return payload

    @staticmethod
    def extract_budget_context(
        metadata_json: Optional[Dict[str, Any]],
        *,
        period_start: Optional[date] = None,
    ) -> Dict[str, Any]:
        metadata = dict(metadata_json or {})
        cycle = FinancialBudgetCodeService.normalize_budget_cycle(metadata.get("budget_cycle"), fallback_date=period_start)
        category = FinancialBudgetCodeService.normalize_budget_category(metadata.get("budget_category") or metadata.get("budget_group"))
        group_code = FinancialBudgetCodeService.normalize_budget_category(
            metadata.get("budget_group_code") or metadata.get("budget_group") or category
        )
        group_label = FinancialBudgetCodeService.normalize_text(metadata.get("budget_group_label"))

        if group_label is None and group_code:
            group_label = group_code.replace("_", " ").title()

        return {
            "budget_cycle": cycle,
            "budget_cycle_year": cycle.get("year") if cycle else (period_start.year if period_start else None),
            "budget_cycle_code": cycle.get("code") if cycle else (str(period_start.year) if period_start else None),
            "budget_cycle_label": cycle.get("label") if cycle else (f"Ciclo Orçamentário {period_start.year}" if period_start else None),
            "budget_category": category,
            "budget_group": group_code,
            "budget_group_label": group_label,
            "budget_analysis_mode": metadata.get("budget_analysis_mode") or "separated",
            "budget_scope": metadata.get("budget_scope"),
            "budget_version_type": metadata.get("budget_version_type"),
        }

    @staticmethod
    def matches_filters(
        version_payload: Dict[str, Any],
        *,
        budget_cycle: Any = None,
        budget_category: Optional[str] = None,
        budget_group: Optional[str] = None,
    ) -> bool:
        context = FinancialBudgetCodeService.extract_budget_context(
            version_payload.get("metadata_json"),
            period_start=FinancialBudgetCodeService._safe_date(version_payload.get("period_start")),
        )

        if budget_cycle is not None:
            requested_cycle = FinancialBudgetCodeService.normalize_budget_cycle(
                budget_cycle,
                fallback_date=FinancialBudgetCodeService._safe_date(version_payload.get("period_start")),
            )
            requested_year = requested_cycle.get("year") if requested_cycle else FinancialBudgetCodeService._coerce_year(budget_cycle)
            if requested_year is not None and context.get("budget_cycle_year") != requested_year:
                return False
            if requested_cycle and requested_cycle.get("code") and context.get("budget_cycle_code") != requested_cycle.get("code"):
                # The year match above is the main selector; code mismatch only rejects when both sides are explicit.
                explicit_code = str(requested_cycle.get("code")).strip()
                if explicit_code and explicit_code != str(requested_year):
                    return False

        if budget_category is not None:
            requested_category = FinancialBudgetCodeService.normalize_budget_category(budget_category)
            if requested_category and context.get("budget_category") != requested_category:
                return False

        if budget_group is not None:
            requested_group = FinancialBudgetCodeService.normalize_budget_category(budget_group)
            if requested_group and context.get("budget_group") != requested_group:
                return False

        return True

    @staticmethod
    def group_version_payloads(
        version_payloads: Sequence[Dict[str, Any]],
        *,
        summaries_by_id: Optional[Dict[int, Dict[str, Any]]] = None,
        group_by_cycle: bool = True,
        group_by_category: bool = True,
    ) -> List[Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for payload in version_payloads:
            version_id = int(payload.get("id"))
            context = FinancialBudgetCodeService.extract_budget_context(
                payload.get("metadata_json"),
                period_start=FinancialBudgetCodeService._safe_date(payload.get("period_start")),
            )
            cycle_key = str(context.get("budget_cycle_year") or context.get("budget_cycle_code") or "sem-ciclo")
            category_key = str(context.get("budget_category") or "sem-categoria")
            group_key = cycle_key if group_by_cycle else "all"
            bucket = groups.setdefault(
                group_key,
                {
                    "budget_cycle": context.get("budget_cycle"),
                    "cycle_key": cycle_key,
                    "cycle_label": context.get("budget_cycle_label"),
                    "versions_count": 0,
                    "summary": FinancialBudgetCodeService._empty_summary(),
                    "items": [],
                    "categories": {},
                },
            )
            bucket["versions_count"] += 1
            bucket["items"].append({**payload, "summary": summaries_by_id.get(version_id) if summaries_by_id else payload.get("summary")})
            FinancialBudgetCodeService._accumulate_summary(
                bucket["summary"],
                summaries_by_id.get(version_id) if summaries_by_id else payload.get("summary"),
            )

            if group_by_category:
                category_bucket = bucket["categories"].setdefault(
                    category_key,
                    {
                        "budget_category": context.get("budget_category"),
                        "group_key": category_key,
                        "group_label": context.get("budget_group_label"),
                        "versions_count": 0,
                        "summary": FinancialBudgetCodeService._empty_summary(),
                        "items": [],
                    },
                )
                category_bucket["versions_count"] += 1
                category_bucket["items"].append({**payload, "summary": summaries_by_id.get(version_id) if summaries_by_id else payload.get("summary")})
                FinancialBudgetCodeService._accumulate_summary(
                    category_bucket["summary"],
                    summaries_by_id.get(version_id) if summaries_by_id else payload.get("summary"),
                )

        ordered_groups: List[Dict[str, Any]] = []
        for group_key in sorted(groups.keys()):
            bucket = groups[group_key]
            bucket["categories"] = [
                category_bucket
                for _category_key, category_bucket in sorted(bucket["categories"].items(), key=lambda item: item[0])
            ]
            ordered_groups.append(bucket)
        return ordered_groups

    @staticmethod
    def summarize_version_payloads(version_payloads: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        summary = FinancialBudgetCodeService._empty_summary()
        for payload in version_payloads:
            FinancialBudgetCodeService._accumulate_summary(summary, payload.get("summary"))
        summary["versions_count"] = len(version_payloads)
        return summary

    @staticmethod
    def _accumulate_summary(target: Dict[str, Any], source: Optional[Dict[str, Any]]) -> None:
        if not source:
            return
        for key in (
            "planned_total",
            "contracted_total",
            "executed_total",
            "scheduled_total",
            "available_to_contract",
            "lines_count",
            "contracts_count",
            "documents_count",
            "schedules_count",
        ):
            if key in source:
                target[key] = float(Decimal(str(target.get(key, 0))) + Decimal(str(source.get(key, 0))))

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        return {
            "planned_total": 0.0,
            "contracted_total": 0.0,
            "executed_total": 0.0,
            "scheduled_total": 0.0,
            "available_to_contract": 0.0,
            "lines_count": 0,
            "contracts_count": 0,
            "documents_count": 0,
            "schedules_count": 0,
        }

    @staticmethod
    def _coerce_year(value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value).strip()
        match = re.search(r"(19|20)\d{2}", text)
        if match:
            try:
                return int(match.group(0))
            except Exception:
                return None
        if text.isdigit():
            try:
                return int(text)
            except Exception:
                return None
        return None

    @staticmethod
    def _safe_date(value: Any) -> Optional[date]:
        if isinstance(value, date):
            return value
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except Exception:
            return None

    @staticmethod
    def _next_version_sequence(*, company_id: int, prefix: str) -> int:
        query = FinancialBudgetVersion.query.filter(
            FinancialBudgetVersion.company_id == company_id,
            FinancialBudgetVersion.deleted_at.is_(None),
            FinancialBudgetVersion.code.like(f"{prefix}.%"),
        )
        highest = 0
        for item in query.all():
            code = str(item.code or "")
            token = code.rsplit(".", 1)[-1]
            try:
                highest = max(highest, int(token))
            except Exception:
                continue
        return highest + 1
