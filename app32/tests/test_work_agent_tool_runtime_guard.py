from __future__ import annotations

from langchain_core.messages import AIMessage

from src.intelligence.tool_context import reset_sapiens_context, set_sapiens_context
from src.intelligence.work_agents.tool_runtime_guard import build_denied_tool_messages, resolve_state_tool_context


def test_runtime_guard_blocks_admin_tool_for_collaborator() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=31,
        channel="web",
        thread_id="thread-1",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "colaborador",
                "permissions": [],
                "accessible_company_ids": [31],
            }
        },
    )
    try:
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_system_users",
                            "id": "call_admin",
                            "args": {"company_id": 31},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert len(denied) == 1
        assert denied[0].status == "error"
        assert "governança" in denied[0].content.lower()
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_allows_admin_read_for_administrator() -> None:
    token = set_sapiens_context(
        user_id=1,
        company_id=31,
        channel="web",
        thread_id="thread-2",
        metadata={
            "security": {
                "employee_id": 11,
                "role": "administrador",
                "permissions": [],
                "accessible_company_ids": [31, 32],
            }
        },
    )
    try:
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_system_users",
                            "id": "call_ok",
                            "args": {"company_id": 31},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert denied == []
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_requests_human_gate_for_high_risk_mutation(monkeypatch) -> None:
    token = set_sapiens_context(
        user_id=1,
        company_id=31,
        channel="web",
        thread_id="thread-3",
        metadata={
            "security": {
                "employee_id": 11,
                "role": "administrador",
                "permissions": [],
                "accessible_company_ids": [31],
            }
        },
    )
    try:
        monkeypatch.setattr(
            "src.intelligence.work_agents.tool_runtime_guard._ensure_tool_human_gate_request",
            lambda **kwargs: {
                "approval_request_id": 501,
                "reused_existing": False,
                "approval_key": "tool_human_gate|register_system_user",
                "action_key": "tool.register_system_user",
            },
        )
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "register_system_user",
                            "id": "call_gate",
                            "args": {"company_id": 31, "email": "novo@cliente.com"},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert len(denied) == 1
        assert denied[0].status == "error"
        assert "aprovação #501" in denied[0].content.lower()
        workflow_approval = denied[0].additional_kwargs["workflow_approval"]
        assert workflow_approval["required"] is True
        assert workflow_approval["status"] == "pending"
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_allows_resumption_after_tool_human_gate(monkeypatch) -> None:
    token = set_sapiens_context(
        user_id=1,
        company_id=31,
        channel="web",
        thread_id="thread-4",
        metadata={
            "security": {
                "employee_id": 11,
                "role": "administrador",
                "permissions": [],
                "accessible_company_ids": [31],
            }
        },
    )
    try:
        monkeypatch.setattr(
            "src.intelligence.work_agents.tool_runtime_guard._find_approved_tool_human_gate",
            lambda **kwargs: {
                "approval_request_id": 777,
                "approval_key": "tool_human_gate|register_system_user",
                "status": "approved",
            },
        )
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "register_system_user",
                            "id": "call_resume",
                            "args": {"company_id": 31, "email": "novo@cliente.com"},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert denied == []
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_allows_user_only_tool_without_company_context() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=None,
        channel="web",
        thread_id="thread-5",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "colaborador",
                "permissions": [],
                "accessible_company_ids": [],
            }
        },
    )
    try:
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "get_my_work",
                            "id": "call_user_only",
                            "args": {},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert denied == []
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_blocks_company_required_tool_without_company_context() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=None,
        channel="web",
        thread_id="thread-6",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "administrador",
                "permissions": [],
                "accessible_company_ids": [],
            }
        },
    )
    try:
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_process_hierarchy",
                            "id": "call_company_required",
                            "args": {},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert len(denied) == 1
        assert "feature exige company_id" in denied[0].content.lower()
        assert denied[0].additional_kwargs["policy_decision"]["required_context"] == ["company"]
    finally:
        reset_sapiens_context(token)


def test_resolve_state_tool_context_pins_single_accessible_company() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=None,
        channel="web",
        thread_id="thread-7",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "colaborador",
                "permissions": [],
                "accessible_company_ids": [12],
            }
        },
    )
    try:
        state = {
            "user_id": 9,
            "company_id": None,
            "context_data": {},
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "create_process_area",
                            "id": "call_pin_single_company",
                            "args": {"name": "Gestão"},
                        }
                    ],
                )
            ],
        }

        resolved = resolve_state_tool_context(state)

        assert resolved["company_id"] == 12
        assert resolved["messages"][-1].tool_calls[0]["args"]["company_id"] == 12
        assert resolved["context_data"]["tool_context_resolution"]["company_id_source"] == "security.single_accessible_company_id"
    finally:
        reset_sapiens_context(token)


def test_resolve_state_tool_context_uses_pinned_company_from_metadata() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=None,
        channel="web",
        thread_id="thread-8",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "colaborador",
                "permissions": [],
                "accessible_company_ids": [12, 15],
            },
            "workflow": {
                "payload": {
                    "_selected_company_id": 15,
                }
            },
        },
    )
    try:
        state = {
            "user_id": 9,
            "company_id": None,
            "context_data": {},
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_process_hierarchy",
                            "id": "call_pin_metadata_company",
                            "args": {},
                        }
                    ],
                )
            ],
        }

        resolved = resolve_state_tool_context(state)

        assert resolved["company_id"] == 15
        assert resolved["messages"][-1].tool_calls[0]["args"]["company_id"] == 15
        assert resolved["context_data"]["tool_context_resolution"]["company_id_source"] == "metadata.company_id"
    finally:
        reset_sapiens_context(token)


def test_runtime_guard_blocks_company_required_tool_when_multiple_companies_and_no_pin() -> None:
    token = set_sapiens_context(
        user_id=9,
        company_id=None,
        channel="web",
        thread_id="thread-9",
        metadata={
            "security": {
                "employee_id": 91,
                "role": "administrador",
                "permissions": [],
                "accessible_company_ids": [12, 15],
            }
        },
    )
    try:
        state = {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "list_process_hierarchy",
                            "id": "call_company_required_multi",
                            "args": {},
                        }
                    ],
                )
            ]
        }

        denied = build_denied_tool_messages(state)

        assert len(denied) == 1
        assert "feature exige company_id" in denied[0].content.lower()
    finally:
        reset_sapiens_context(token)
