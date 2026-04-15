import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.operational_audit_service as audit_module
from services.operational_audit_service import OperationalAuditService
from schemas.operational_audit import OperationalAuditPanelQuery


class _FakeColumn:
    def __eq__(self, other):
        return None

    def is_(self, other):
        return None

    def desc(self):
        return None


class _FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.items = self.items[: int(value)]
        return self

    def all(self):
        return list(self.items)


def _model_stub(items, **columns):
    payload = {"query": _FakeQuery(items)}
    for column in columns:
        payload[column] = _FakeColumn()
    return SimpleNamespace(**payload)


def test_build_panel_aggregates_operational_sources_with_company_scope(monkeypatch):
    record = SimpleNamespace(
        id=31,
        company_id=9,
        origin_reference="Prestação AA.J.31",
        source_file_name="aa-j-31.pdf",
        source_channel="upload",
        updated_at=datetime(2026, 4, 9, 12, 0, 0),
        metadata_json={
            "guided_audit_trail": [
                {
                    "event_type": "guided_review_update",
                    "timestamp": "2026-04-09T12:00:00",
                    "description": "Revisão humana da prestação",
                    "actor": {"user_name": "QA"},
                    "changes": {"review_notes": {"after": "ok"}},
                }
            ]
        },
    )
    user_log = SimpleNamespace(
        id=101,
        entity_name="Prestação AA.J.31",
        action="UPDATE",
        entity_type="financial_ingestion_record",
        entity_id="31",
        description="Log da revisão humana",
        user_name="Gestor",
        user_email="gestor@teste.local",
        endpoint="/api/financial/ingestions/31",
        created_at=datetime(2026, 4, 9, 12, 1, 0),
        to_dict=lambda: {"id": 101, "action": "UPDATE"},
    )
    workflow = SimpleNamespace(
        id=201,
        workflow_code="financial_accountability",
        request_text="Importar documento financeiro",
        response_text=None,
        user_id=7,
        status="completed",
        channel="sapiens",
        created_at=datetime(2026, 4, 9, 12, 2, 0),
        to_dict=lambda: {"id": 201, "workflow_code": "financial_accountability"},
    )
    action = SimpleNamespace(
        id=301,
        title="Criar lançamento sugerido",
        description="Ação proposta por agente",
        requesting_agent="sapiens",
        handling_agent=None,
        status="pending",
        type="business_decision",
        created_at=datetime(2026, 4, 9, 12, 3, 0),
        to_dict=lambda: {"id": 301, "status": "pending"},
    )

    monkeypatch.setattr(audit_module.FinancialService, "_ensure_company_scope", lambda company_id, allowed_company_ids=None: None)
    monkeypatch.setattr(
        OperationalAuditService,
        "_collect_ai_mcp_runtime_events",
        classmethod(lambda cls, **kwargs: [
            {
                "source": "ai_mcp_runtime",
                "title": "register_system_user · human_gate_requested",
                "description": "mutação de alto risco exige confirmação explícita",
                "actor": "user:7",
                "entity_type": "ai_mcp_audit_event",
                "entity_id": 401,
                "status": "human_gate_requested",
                "channel": "admin",
                "runtime": "sapiens",
                "tool_name": "register_system_user",
                "domain": "identity_admin",
                "created_at": "2026-04-09T12:04:00",
                "raw": {"id": 401},
            }
        ]),
    )
    monkeypatch.setattr(
        audit_module,
        "FinancialIngestionRecord",
        _model_stub(record and [record], company_id=True, deleted_at=True, updated_at=True, id=True),
    )
    monkeypatch.setattr(
        audit_module,
        "UserLog",
        _model_stub([user_log], company_id=True, entity_type=True, created_at=True, id=True),
    )
    monkeypatch.setattr(
        audit_module,
        "WorkflowExecutionLog",
        _model_stub([workflow], company_id=True, created_at=True, id=True),
    )
    monkeypatch.setattr(
        audit_module,
        "AgentAction",
        _model_stub([action], company_id=True, created_at=True, id=True),
    )
    monkeypatch.setattr(
        OperationalAuditService,
        "_collect_workflow_approvals",
        classmethod(lambda cls, **kwargs: []),
    )

    result, error = OperationalAuditService.build_panel(company_id=9, allowed_company_ids=[9], limit=10)

    assert error is None
    assert result["company_id"] == 9
    assert result["summary"]["by_source"]["ai_mcp_runtime"] == 1
    assert result["summary"]["by_source"]["human_review"] == 2
    assert result["summary"]["by_source"]["sapiens_workflow"] == 1
    assert result["summary"]["by_source"]["agent_action"] == 1
    assert result["events"][0]["source"] == "ai_mcp_runtime"
    assert result["analytics"]["top_tools"][0]["name"] == "register_system_user"
    assert all(event["source"] in {"ai_mcp_runtime", "human_review", "sapiens_workflow", "agent_action"} for event in result["events"])


def test_build_panel_rejects_cross_tenant_scope(monkeypatch):
    monkeypatch.setattr(
        audit_module.FinancialService,
        "_ensure_company_scope",
        lambda company_id, allowed_company_ids=None: "A operação financeira está fora do escopo da empresa autorizada.",
    )

    result, error = OperationalAuditService.build_panel(company_id=99, allowed_company_ids=[9])

    assert result is None
    assert "fora do escopo" in error


def test_operational_audit_query_forbids_unknown_filters():
    try:
        OperationalAuditPanelQuery(company_id=9, source="human_review", unexpected="x")
    except Exception as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("Filtro extra deveria ser rejeitado")
