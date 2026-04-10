from __future__ import annotations

import logging
import os
import warnings
from dataclasses import dataclass
from typing import Literal


LegacyRuntimeGuardMode = Literal["warn", "block", "off"]

LEGACY_RUNTIME_GUARD_ENV = "APP32_LEGACY_RUNTIME_GUARD_MODE"
DEFAULT_LEGACY_RUNTIME_GUARD_MODE: LegacyRuntimeGuardMode = "warn"

LEGACY_RUNTIME_ALLOWLIST: frozenset[str] = frozenset(
    {
        "src.intelligence.graph.create_agent_workflow",
        "src.intelligence.graph.agent_workflow",
        "src.intelligence.graphs.main_graph.create_main_graph",
        "src.intelligence.graphs.main_graph.run_agent_interaction",
        "src.intelligence.test_agent.run_integration_test",
        "src.intelligence.test_agent_mock.run_mock_test",
    }
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LegacyRuntimeGuardDecision:
    """Resultado auditável para uso/depreciação de runtime legado Sapiens."""

    module: str
    operation: str
    mode: LegacyRuntimeGuardMode
    allowed: bool
    reason: str
    caller: str | None = None

    def to_dict(self) -> dict[str, str | bool | None]:
        return {
            "module": self.module,
            "operation": self.operation,
            "mode": self.mode,
            "allowed": self.allowed,
            "reason": self.reason,
            "caller": self.caller,
        }


class LegacyRuntimeBlockedError(RuntimeError):
    """Erro controlado quando um runtime legado for bloqueado por configuração."""


def _normalize_mode(mode: str | None) -> LegacyRuntimeGuardMode:
    normalized = (mode or DEFAULT_LEGACY_RUNTIME_GUARD_MODE).strip().lower()
    if normalized in {"warn", "block", "off"}:
        return normalized  # type: ignore[return-value]
    return DEFAULT_LEGACY_RUNTIME_GUARD_MODE


def get_legacy_runtime_guard_mode() -> LegacyRuntimeGuardMode:
    return _normalize_mode(os.getenv(LEGACY_RUNTIME_GUARD_ENV))


def evaluate_legacy_runtime_access(
    *,
    module: str,
    operation: str,
    caller: str | None = None,
    mode: LegacyRuntimeGuardMode | str | None = None,
) -> LegacyRuntimeGuardDecision:
    """Avalia acesso a runtime legado sem executar efeito colateral."""

    resolved_mode = _normalize_mode(mode) if mode is not None else get_legacy_runtime_guard_mode()
    allowed = resolved_mode != "block"
    reason = (
        "legacy_runtime_guard_disabled"
        if resolved_mode == "off"
        else "legacy_runtime_warn_only"
        if resolved_mode == "warn"
        else "legacy_runtime_blocked"
    )
    return LegacyRuntimeGuardDecision(
        module=module,
        operation=operation,
        mode=resolved_mode,
        allowed=allowed,
        reason=reason,
        caller=caller,
    )


def require_legacy_runtime_access(
    *,
    module: str,
    operation: str,
    caller: str | None = None,
    mode: LegacyRuntimeGuardMode | str | None = None,
) -> LegacyRuntimeGuardDecision:
    """
    Guard rail central para runtimes legados.

    A fase AA.J.31.1318 usa `warn` como padrão para preservar compatibilidade,
    deixando `block` disponível por configuração operacional controlada.
    """

    decision = evaluate_legacy_runtime_access(
        module=module,
        operation=operation,
        caller=caller,
        mode=mode,
    )
    payload = decision.to_dict()

    if decision.mode == "off":
        logger.debug("legacy_runtime_guard_off", extra={"legacy_runtime_guard": payload})
        return decision

    if not decision.allowed:
        logger.error("legacy_runtime_blocked", extra={"legacy_runtime_guard": payload})
        raise LegacyRuntimeBlockedError(
            f"Runtime legado bloqueado: {decision.module} ({decision.operation}). "
            "Use o runtime oficial src.intelligence.execution.run_agent_with_context."
        )

    logger.warning("legacy_runtime_deprecated", extra={"legacy_runtime_guard": payload})
    warnings.warn(
        (
            f"{decision.module} está depreciado para novos usos; "
            "use src.intelligence.execution.run_agent_with_context / "
            "src.intelligence.work_agents.graph."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    return decision


__all__ = [
    "DEFAULT_LEGACY_RUNTIME_GUARD_MODE",
    "LEGACY_RUNTIME_ALLOWLIST",
    "LEGACY_RUNTIME_GUARD_ENV",
    "LegacyRuntimeBlockedError",
    "LegacyRuntimeGuardDecision",
    "LegacyRuntimeGuardMode",
    "evaluate_legacy_runtime_access",
    "get_legacy_runtime_guard_mode",
    "require_legacy_runtime_access",
]
