from __future__ import annotations

import hashlib
from typing import Iterable, Optional

from models.agent_menu import AgentMenuOption

from .contracts import WorkflowDiscoveryRequest, WorkflowDiscoveryResult
from .matcher import HybridWorkflowMatcher
from .registry import WorkflowRegistry
from .reranker import CallableWorkflowReranker
from .reranker import build_default_workflow_reranker


class WorkflowRuntime:
    _registry_cache: dict[str, WorkflowRegistry] = {}
    _registry_cache_order: list[str] = []
    _registry_cache_max_size = 16

    def __init__(
        self,
        matcher: Optional[HybridWorkflowMatcher] = None,
        *,
        reranker=None,
        rerank_callable=None,
    ):
        if matcher is not None:
            self._matcher = matcher
            return

        resolved_reranker = reranker
        if resolved_reranker is None and rerank_callable is not None:
            resolved_reranker = CallableWorkflowReranker(rerank_callable)
        if resolved_reranker is None:
            resolved_reranker = build_default_workflow_reranker()

        self._matcher = HybridWorkflowMatcher(
            reranker=resolved_reranker
        )

    def discover_from_menu_options(
        self,
        text: str,
        options: Iterable[AgentMenuOption],
        preferred_company_id: Optional[int] = None,
        top_k: int = 10,
        channel: str = "web",
    ) -> WorkflowDiscoveryResult:
        registry = self.resolve_registry_from_menu_options(
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

    def resolve_registry_from_menu_options(
        self,
        options: Iterable[AgentMenuOption],
        preferred_company_id: Optional[int] = None,
    ) -> WorkflowRegistry:
        options_list = list(options)
        cache_key = self._build_registry_cache_key(
            options=options_list,
            preferred_company_id=preferred_company_id,
        )
        cached = self._registry_cache.get(cache_key)
        if cached is not None:
            return cached

        registry = WorkflowRegistry.from_menu_options(
            options=options_list,
            preferred_company_id=preferred_company_id,
        )
        self._registry_cache[cache_key] = registry
        self._registry_cache_order.append(cache_key)
        self._trim_registry_cache()
        return registry

    @classmethod
    def _trim_registry_cache(cls) -> None:
        while len(cls._registry_cache_order) > cls._registry_cache_max_size:
            stale_key = cls._registry_cache_order.pop(0)
            cls._registry_cache.pop(stale_key, None)

    @staticmethod
    def _build_registry_cache_key(
        *,
        options: list[AgentMenuOption],
        preferred_company_id: Optional[int],
    ) -> str:
        snapshot_parts = [f"preferred={preferred_company_id or 'none'}"]
        sorted_options = sorted(
            options,
            key=lambda option: (
                int(option.id or 0),
                str(option.code or ""),
            ),
        )
        for option in sorted_options:
            updated_at = getattr(option, "updated_at", None)
            updated_label = (
                updated_at.isoformat()
                if hasattr(updated_at, "isoformat")
                else str(updated_at or "")
            )
            snapshot_parts.append(
                "|".join(
                    [
                        str(getattr(option, "id", "") or ""),
                        str(getattr(option, "company_id", "") or ""),
                        str(getattr(option, "code", "") or ""),
                        str(getattr(option, "action_key", "") or ""),
                        str(int(getattr(option, "sort_order", 0) or 0)),
                        str(bool(getattr(option, "is_active", True))),
                        updated_label,
                    ]
                )
            )
        raw_key = "::".join(snapshot_parts)
        return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()
