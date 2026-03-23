from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from models.workflow_gap import WorkflowGapCandidate
from tests.conversation_regression.operational_report import build_operational_report
from tests.conversation_regression.real_case_catalog import (
    build_real_case_backlog_sync_payload,
    build_real_case_export,
)
from tests.conversation_regression.runner import FIXTURES_PATH, load_catalog


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _dedupe_cases_by_id(cases: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id or case_id in seen:
            continue
        seen.add(case_id)
        deduped.append(case)
    return deduped


class ConversationRegressionService:
    """Pipeline operacional da suíte conversacional V5."""

    @staticmethod
    def load_base_catalog() -> Dict[str, List[Dict[str, Any]]]:
        return load_catalog()

    @staticmethod
    def collect_workflow_gap_candidates(
        *,
        status: str = "inbox",
        limit: int = 100,
        company_id: Optional[int] = None,
        resolution_types: Optional[List[str]] = None,
    ) -> List[WorkflowGapCandidate]:
        query = WorkflowGapCandidate.query
        if status:
            query = query.filter(WorkflowGapCandidate.status == status)
        if company_id is not None:
            query = query.filter(WorkflowGapCandidate.company_id == company_id)
        if resolution_types:
            query = query.filter(WorkflowGapCandidate.resolution_type.in_(list(resolution_types)))
        query = query.order_by(WorkflowGapCandidate.created_at.desc())
        if limit:
            query = query.limit(int(limit))
        return list(query.all())

    @staticmethod
    def build_augmented_catalog(
        *,
        base_catalog: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        workflow_gap_candidates: Optional[Iterable[Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        catalog = {
            chapter: list(cases)
            for chapter, cases in dict(base_catalog or ConversationRegressionService.load_base_catalog()).items()
        }
        exported = build_real_case_export(list(workflow_gap_candidates or []))
        all_chapters = set(catalog.keys()) | set(exported.keys())
        merged: Dict[str, List[Dict[str, Any]]] = {}
        for chapter in sorted(all_chapters):
            merged[chapter] = _dedupe_cases_by_id(
                list(catalog.get(chapter, [])) + list(exported.get(chapter, []))
            )
        return merged

    @staticmethod
    def _normalize_case_input(value: Any) -> str:
        return " ".join(str(value or "").strip().lower().split())

    @staticmethod
    def annotate_export_with_catalog_coverage(
        *,
        exported_cases: Dict[str, List[Dict[str, Any]]],
        base_catalog: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        covered_inputs: Dict[str, set[str]] = {}
        for chapter, cases in (base_catalog or {}).items():
            covered_inputs[chapter] = {
                ConversationRegressionService._normalize_case_input(case.get("input"))
                for case in (cases or [])
                if ConversationRegressionService._normalize_case_input(case.get("input"))
            }

        annotated: Dict[str, List[Dict[str, Any]]] = {}
        for chapter, cases in (exported_cases or {}).items():
            known_inputs = covered_inputs.get(chapter, set())
            annotated[chapter] = []
            for case in cases or []:
                item = dict(case)
                normalized_input = ConversationRegressionService._normalize_case_input(item.get("input"))
                item["resolved_in_catalog"] = bool(normalized_input and normalized_input in known_inputs)
                annotated[chapter].append(item)
        return annotated

    @staticmethod
    def build_snapshot(
        *,
        workflow_gap_candidates: Optional[Iterable[Any]] = None,
        base_catalog: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        base_catalog = dict(base_catalog or ConversationRegressionService.load_base_catalog())
        catalog = ConversationRegressionService.build_augmented_catalog(
            base_catalog=base_catalog,
            workflow_gap_candidates=workflow_gap_candidates,
        )
        exported_cases = build_real_case_export(list(workflow_gap_candidates or []))
        annotated_export = ConversationRegressionService.annotate_export_with_catalog_coverage(
            exported_cases=exported_cases,
            base_catalog=base_catalog,
        )
        report = build_operational_report(catalog)
        backlog_sync = build_real_case_backlog_sync_payload(annotated_export)
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "catalog": catalog,
            "real_cases": annotated_export,
            "report": report,
            "backlog_sync": backlog_sync,
        }

    @staticmethod
    def persist_snapshot(
        snapshot: Dict[str, Any],
        *,
        output_dir: str,
        stem: str = "conversation_regression_snapshot",
    ) -> Dict[str, str]:
        from tests.conversation_regression.operational_report import (
            render_operational_report_html,
            render_operational_report_json,
        )

        root = _ensure_dir(Path(output_dir))
        catalog_path = root / f"{stem}.catalog.json"
        report_json_path = root / f"{stem}.report.json"
        report_html_path = root / f"{stem}.report.html"
        backlog_sync_path = root / f"{stem}.backlog_sync.json"
        metadata_path = root / f"{stem}.meta.json"

        catalog_path.write_text(
            json.dumps(snapshot.get("catalog") or {}, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        report_json_path.write_text(
            render_operational_report_json(snapshot.get("report") or {}),
            encoding="utf-8",
        )
        report_html_path.write_text(
            render_operational_report_html(snapshot.get("report") or {}),
            encoding="utf-8",
        )
        backlog_sync_path.write_text(
            json.dumps(snapshot.get("backlog_sync") or {}, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        metadata_path.write_text(
            json.dumps(
                {
                    "generated_at": snapshot.get("generated_at"),
                    "fixtures_path": str(FIXTURES_PATH),
                    "version": "v7",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        return {
            "catalog_json": str(catalog_path),
            "report_json": str(report_json_path),
            "report_html": str(report_html_path),
            "backlog_sync_json": str(backlog_sync_path),
            "metadata_json": str(metadata_path),
        }
