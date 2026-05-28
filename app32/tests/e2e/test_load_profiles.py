from __future__ import annotations

from app32.tests.e2e.data.builders import build_seed_batch_plan
from app32.tests.e2e.data.profiles import DATA_VOLUME_PROFILES, LARGE_DATASET
from app32.tests.e2e.load.concurrency_profiles import (
    MCP_CONCURRENCY_PROFILES,
    USER_CONCURRENCY_PROFILES,
)
from app32.tests.e2e.load.mcp_session_plan import build_mcp_session_plan


def test_data_volume_profiles_present():
    assert {"small", "large", "huge"} <= set(DATA_VOLUME_PROFILES)


def test_seed_batch_plan_uses_profile():
    plan = build_seed_batch_plan(
        run_marker="AUTOE2E::demo",
        company_id=9,
        profile=LARGE_DATASET,
    )
    assert plan.volume_profile == "large"
    assert plan.record_count == LARGE_DATASET.record_count


def test_user_concurrency_profile_present():
    assert USER_CONCURRENCY_PROFILES["high"].concurrent_users >= 30


def test_mcp_session_plan_requires_isolation():
    plan = build_mcp_session_plan(MCP_CONCURRENCY_PROFILES["high"])
    assert plan.requires_authentication is True
    assert plan.tenant_isolation_required is True
    assert "admin" in plan.surfaces
