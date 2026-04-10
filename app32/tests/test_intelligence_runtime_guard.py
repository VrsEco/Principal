import warnings

import pytest

from src.intelligence.runtime_guard import (
    LEGACY_RUNTIME_ALLOWLIST,
    LegacyRuntimeBlockedError,
    evaluate_legacy_runtime_access,
    require_legacy_runtime_access,
)


def test_legacy_runtime_guard_is_warn_only_by_default():
    decision = evaluate_legacy_runtime_access(
        module="src.intelligence.graph.create_agent_workflow",
        operation="create_workflow",
        mode="warn",
    )

    assert decision.allowed is True
    assert decision.reason == "legacy_runtime_warn_only"
    assert decision.mode == "warn"


def test_legacy_runtime_guard_emits_deprecation_warning_without_breaking_compatibility():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        decision = require_legacy_runtime_access(
            module="src.intelligence.graphs.main_graph.run_agent_interaction",
            operation="run_interaction",
            mode="warn",
        )

    assert decision.allowed is True
    assert any(item.category is DeprecationWarning for item in captured)


def test_legacy_runtime_guard_can_block_by_configuration():
    with pytest.raises(LegacyRuntimeBlockedError):
        require_legacy_runtime_access(
            module="src.intelligence.graphs.main_graph.create_main_graph",
            operation="create_workflow",
            mode="block",
        )


def test_legacy_runtime_allowlist_covers_known_deprecated_entrypoints():
    assert {
        "src.intelligence.graph.create_agent_workflow",
        "src.intelligence.graphs.main_graph.create_main_graph",
        "src.intelligence.graphs.main_graph.run_agent_interaction",
        "src.intelligence.test_agent.run_integration_test",
        "src.intelligence.test_agent_mock.run_mock_test",
    } <= LEGACY_RUNTIME_ALLOWLIST
