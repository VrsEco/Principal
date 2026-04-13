from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence

from models.agent_menu import AgentMenuOption
from models.workflow_gap import WorkflowGapCandidate
from models.workflow_usage import WorkflowExecutionLog
from src.intelligence.workflows.registry import WorkflowRegistry


def _normalize_text(value: Any) -> str:
    return str(value or '').strip()


def _sorted_counts(label: str, values: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        {label: key, 'count': count}
        for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]


def _option_parent_code(option: AgentMenuOption) -> Optional[str]:
    parent = getattr(option, 'parent', None)
    if parent is None:
        return None
    return _normalize_text(getattr(parent, 'code', None)) or None


def _option_parent_title(option: AgentMenuOption) -> Optional[str]:
    parent = getattr(option, 'parent', None)
    if parent is None:
        return None
    return _normalize_text(getattr(parent, 'title', None)) or None


def build_workflow_catalog(
    *,
    options: Sequence[AgentMenuOption],
    usage_logs: Sequence[WorkflowExecutionLog],
    gap_candidates: Sequence[WorkflowGapCandidate],
    preferred_company_id: Optional[int],
) -> Dict[str, Any]:
    registry = WorkflowRegistry.from_menu_options(options, preferred_company_id=preferred_company_id)
    workflows = registry.list()

    options_by_id = {int(option.id): option for option in options if getattr(option, 'id', None) is not None}
    usage_by_code: Dict[str, List[WorkflowExecutionLog]] = defaultdict(list)
    for item in usage_logs or []:
        code = _normalize_text(getattr(item, 'workflow_code', None))
        if code:
            usage_by_code[code].append(item)

    gaps_by_code: Dict[str, List[WorkflowGapCandidate]] = defaultdict(list)
    for gap in gap_candidates or []:
        for raw_code in getattr(gap, 'matched_workflow_codes', None) or []:
            code = _normalize_text(raw_code)
            if code:
                gaps_by_code[code].append(gap)

    catalog_items: List[Dict[str, Any]] = []
    summary_channels: Dict[str, int] = defaultdict(int)
    summary_sources: Dict[str, int] = defaultdict(int)
    used_workflows = 0
    workflows_with_gaps = 0

    for workflow in workflows:
        option = options_by_id.get(int(workflow.source_option_id or 0))
        logs = usage_by_code.get(workflow.code, [])
        gaps = gaps_by_code.get(workflow.code, [])
        if logs:
            used_workflows += 1
        if gaps:
            workflows_with_gaps += 1

        channel_counts: Dict[str, int] = defaultdict(int)
        status_counts: Dict[str, int] = defaultdict(int)
        route_counts: Dict[str, int] = defaultdict(int)
        for log in logs:
            channel = _normalize_text(getattr(log, 'channel', None)) or '(sem_canal)'
            status = _normalize_text(getattr(log, 'status', None)) or '(sem_status)'
            route_source = _normalize_text(getattr(log, 'route_source', None)) or '(sem_origem)'
            channel_counts[channel] += 1
            status_counts[status] += 1
            route_counts[route_source] += 1
            summary_channels[channel] += 1
            summary_sources[route_source] += 1

        last_gap_at = None
        if gaps:
            ordered = sorted(gaps, key=lambda item: getattr(item, 'created_at', None) or 0, reverse=True)
            last_gap_at = getattr(ordered[0], 'created_at', None)

        required_fields = [field.model_dump() for field in workflow.required_fields]
        item = {
            'code': workflow.code,
            'title': workflow.title,
            'action_key': workflow.action_key,
            'description': workflow.description,
            'sort_order': workflow.sort_order,
            'company_id': workflow.company_id,
            'scope': 'company' if workflow.company_id is not None else 'global',
            'source_option_id': workflow.source_option_id,
            'parent_code': _option_parent_code(option) if option is not None else None,
            'parent_title': _option_parent_title(option) if option is not None else None,
            'required_fields': required_fields,
            'keywords': list(workflow.keywords or []),
            'intent_examples': list(workflow.intent_examples or []),
            'usage': {
                'count': int(getattr(option, 'usage_count', 0) or 0),
                'last_used_at': getattr(option, 'last_used_at', None).isoformat() if getattr(option, 'last_used_at', None) else None,
                'log_count': len(logs),
                'by_channel': _sorted_counts('channel', channel_counts),
                'by_status': _sorted_counts('status', status_counts),
                'by_route_source': _sorted_counts('route_source', route_counts),
            },
            'gaps': {
                'count': len(gaps),
                'last_gap_at': last_gap_at.isoformat() if last_gap_at else None,
            },
            'is_active': bool(getattr(option, 'is_active', True)) if option is not None else True,
        }
        catalog_items.append(item)

    catalog_items.sort(key=lambda entry: (entry['sort_order'], entry['code']))

    return {
        'summary': {
            'workflow_count': len(catalog_items),
            'used_workflow_count': used_workflows,
            'unused_workflow_count': max(len(catalog_items) - used_workflows, 0),
            'workflow_with_gap_count': workflows_with_gaps,
            'global_workflow_count': sum(1 for item in catalog_items if item['scope'] == 'global'),
            'company_workflow_count': sum(1 for item in catalog_items if item['scope'] == 'company'),
            'channels': _sorted_counts('channel', summary_channels),
            'route_sources': _sorted_counts('route_source', summary_sources),
        },
        'workflows': catalog_items,
    }
