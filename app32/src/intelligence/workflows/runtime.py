from __future__ import annotations

from typing import Iterable, Optional

from models.agent_menu import AgentMenuOption

from .contracts import WorkflowDiscoveryRequest, WorkflowDiscoveryResult
from .matcher import LexicalWorkflowMatcher
from .registry import WorkflowRegistry


class WorkflowRuntime:
    def __init__(self, matcher: Optional[LexicalWorkflowMatcher] = None):
        self._matcher = matcher or LexicalWorkflowMatcher()

    def discover_from_menu_options(
        self,
        text: str,
        options: Iterable[AgentMenuOption],
        preferred_company_id: Optional[int] = None,
        top_k: int = 10,
        channel: str = "web",
    ) -> WorkflowDiscoveryResult:
        registry = WorkflowRegistry.from_menu_options(
            options=options,
            preferred_company_id=preferred_company_id,
        )
        request = WorkflowDiscoveryRequest(
            text=text,
            company_id=preferred_company_id,
            channel=channel,
            top_k=top_k,
        )
        return self._matcher.discover(request=request, registry=registry)
