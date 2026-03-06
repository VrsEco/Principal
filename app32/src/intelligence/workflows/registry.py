from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from models.agent_menu import AgentMenuOption

from .contracts import WorkflowDefinition, WorkflowFieldDefinition


def _build_required_fields(raw_fields: Sequence[dict] | None) -> List[WorkflowFieldDefinition]:
    fields: List[WorkflowFieldDefinition] = []
    for raw_field in raw_fields or []:
        if not isinstance(raw_field, dict):
            continue
        key = str(raw_field.get("key") or "").strip()
        label = str(raw_field.get("label") or key).strip()
        if not key or not label:
            continue
        fields.append(
            WorkflowFieldDefinition(
                key=key,
                label=label,
                required=bool(raw_field.get("required", True)),
            )
        )
    return fields


def build_workflow_definition_from_option(option: AgentMenuOption) -> Optional[WorkflowDefinition]:
    action_key = str(option.action_key or "").strip()
    if not action_key:
        return None

    return WorkflowDefinition(
        code=str(option.code or "").strip(),
        title=str(option.title or "").strip(),
        action_key=action_key,
        description=(str(option.description).strip() if option.description else None),
        keywords=[
            str(keyword).strip()
            for keyword in (option.keywords or [])
            if str(keyword).strip()
        ],
        required_fields=_build_required_fields(option.required_fields or []),
        confirmation_template=(
            str(option.confirmation_template).strip()
            if option.confirmation_template
            else None
        ),
        execution_template=(
            str(option.execution_template).strip()
            if option.execution_template
            else None
        ),
        sort_order=int(option.sort_order or 0),
        company_id=option.company_id,
        source_option_id=option.id,
    )


class WorkflowRegistry:
    def __init__(self, workflows: Sequence[WorkflowDefinition]):
        self._workflows = list(workflows)
        self._by_code: Dict[str, WorkflowDefinition] = {
            workflow.code: workflow for workflow in self._workflows
        }

    @classmethod
    def from_menu_options(
        cls,
        options: Iterable[AgentMenuOption],
        preferred_company_id: Optional[int] = None,
    ) -> "WorkflowRegistry":
        sorted_options = sorted(
            list(options),
            key=lambda option: (
                0 if preferred_company_id is not None and option.company_id == preferred_company_id else 1,
                int(option.sort_order or 0),
                str(option.code or ""),
                int(option.id or 0),
            ),
        )

        deduped: Dict[str, WorkflowDefinition] = {}
        for option in sorted_options:
            if not bool(getattr(option, "is_active", True)):
                continue

            code = str(option.code or "").strip()
            if not code or code in deduped:
                continue

            workflow = build_workflow_definition_from_option(option)
            if workflow is None:
                continue

            deduped[code] = workflow

        workflows = sorted(
            deduped.values(),
            key=lambda workflow: (workflow.sort_order, workflow.code),
        )
        return cls(workflows)

    def list(self) -> List[WorkflowDefinition]:
        return list(self._workflows)

    def get_by_code(self, code: str) -> Optional[WorkflowDefinition]:
        return self._by_code.get(code)

    def __iter__(self):
        return iter(self._workflows)

    def __len__(self) -> int:
        return len(self._workflows)
