from datetime import datetime, timezone
from types import SimpleNamespace

from src.core import mcp_incentive_tools
from src.core.mcp_incentive_tools import register_incentive_tools
from src.intelligence.tooling.capabilities import ToolScope, infer_tool_capability


class _FakeMCP:
    def __init__(self):
        self.registered = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.registered[kwargs.get("name") or func.__name__] = func
            return func

        if args and callable(args[0]):
            return decorator(args[0])
        return decorator


def test_register_incentive_tools_exposes_get_incentive_indicators(monkeypatch):
    captured = {}

    def _fake_fetch_indicator_catalog(**kwargs):
        captured.update(kwargs)
        return [
            {
                "id": 7,
                "company_id": kwargs["company_id"],
                "code": "IND-001",
                "full_code": "AA.I.1",
                "name": "Conversão",
                "description": "Indicador canônico",
                "indicator_type": "result",
                "source_module": "crm",
                "source_id": 11,
                "source_scope": "company",
                "source_config": {"pipeline": "default"},
                "collection_mode": "automatic",
                "aggregation_function": "sum",
                "unit": "%",
                "polarity": "positive",
                "measurement_frequency": "monthly",
                "responsible_id": 3,
                "is_active": True,
                "created_at": "2026-04-17T00:00:00+00:00",
                "updated_at": "2026-04-17T00:00:00+00:00",
            }
        ]

    monkeypatch.setattr(mcp_incentive_tools, "_fetch_indicator_catalog", _fake_fetch_indicator_catalog)

    mcp = _FakeMCP()
    register_incentive_tools(mcp)

    result = mcp.registered["get_incentive_indicators"](
        company_id=31,
        is_active=True,
        collection_mode="automatic",
        source_module="crm",
        limit=50,
        user_id=9,
        request_id="req-1",
        trace_id="trace-1",
    )

    assert result["success"] is True
    assert result["data"]["count"] == 1
    assert result["data"]["model"] == "Indicator"
    assert result["data"]["items"][0]["code"] == "IND-001"
    assert result["meta"]["company_id"] == 31
    assert result["meta"]["user_id"] == 9
    assert captured == {
        "company_id": 31,
        "is_active": True,
        "collection_mode": "automatic",
        "source_module": "crm",
        "limit": 50,
    }


def test_get_incentive_indicators_rejects_invalid_limit():
    mcp = _FakeMCP()
    register_incentive_tools(mcp)

    result = mcp.registered["get_incentive_indicators"](company_id=31, limit=0)

    assert result["success"] is False
    assert result["error"]["code"] == "invalid_limit"


def test_strategic_connection_tools_expose_graph_metrics_and_summary(monkeypatch):
    fake_graph = {
        "nodes": [
            {"id": "colab_1", "label": "Ana", "type": "collaborator", "degree": 2, "health": "connected", "department": "Operações"},
            {"id": "proc_1", "label": "Vendas", "type": "process", "degree": 1, "health": "fragile"},
            {"id": "routine_1", "label": "Follow-up", "type": "routine", "degree": 1, "health": "fragile"},
            {"id": "capacity_1", "label": "Manhã", "type": "capacity", "degree": 0, "health": "orphan"},
            {"id": "ind_1", "label": "Conversão", "type": "indicator", "degree": 0, "health": "orphan"},
        ],
        "links": [
            {"source": "colab_1", "target": "proc_1", "label": "dono", "strength": "direct"},
            {"source": "colab_1", "target": "routine_1", "label": "atua na rotina", "strength": "direct"},
        ],
        "summary": {
            "total": 5,
            "orphans": 2,
            "fragile": 2,
            "connected": 1,
            "by_type": {"collaborator": 1, "process": 1, "routine": 1, "capacity": 1, "indicator": 1},
        },
    }

    monkeypatch.setattr(
        mcp_incentive_tools.IncentiveSpiderWebService,
        "build_graph",
        classmethod(lambda cls, company_id: fake_graph),
    )

    mcp = _FakeMCP()
    register_incentive_tools(mcp)

    graph_result = mcp.registered["get_strategic_connection_graph"](company_id=31, anonymize=True, user_id=9)
    metrics_result = mcp.registered["get_strategic_connection_metrics"](company_id=31)
    summary_result = mcp.registered["generate_strategic_connection_summary"](company_id=31, max_gaps=5)

    assert graph_result["success"] is True
    assert graph_result["meta"]["domain"] == "analytics"
    assert graph_result["meta"]["scope"] == "mcp_analytics"
    assert graph_result["data"]["graph"]["nodes"][0]["label"] == "Colaborador 1"
    assert "department" not in graph_result["data"]["graph"]["nodes"][0]

    assert metrics_result["success"] is True
    assert metrics_result["data"]["metrics"]["total_nodes"] == 5
    assert metrics_result["data"]["metrics"]["by_health"]["orphan"] == 2
    assert metrics_result["data"]["metrics"]["coverage"]["has_routines"] is True

    assert summary_result["success"] is True
    assert "Teia com 5 nós" in summary_result["data"]["executive_summary"]
    assert summary_result["data"]["findings"][0]["gap_type"] == "ORPHAN_NODES"


def test_strategic_connection_tools_reject_invalid_company_id():
    mcp = _FakeMCP()
    register_incentive_tools(mcp)

    result = mcp.registered["get_strategic_connection_graph"](company_id=0)

    assert result["success"] is False
    assert result["error"]["code"] == "invalid_company_id"
    assert result["meta"]["domain"] == "analytics"


def test_strategic_connection_capabilities_are_analytics_scoped():
    for tool_name in (
        "get_strategic_connection_graph",
        "get_strategic_connection_metrics",
        "generate_strategic_connection_summary",
    ):
        capability = infer_tool_capability(SimpleNamespace(name=tool_name, description="Teia"))

        assert capability.domain == "analytics"
        assert ToolScope.SAPIENS.value in capability.scopes
        assert ToolScope.MCP_ANALYTICS.value in capability.scopes
        assert capability.permissions == ("analytics.read",)
        assert "tenant_safe" in capability.tags


def test_fetch_indicator_catalog_filters_company_and_optional_fields(monkeypatch):
    class _FakeQuery:
        def __init__(self, rows):
            self.rows = list(rows)

        def filter_by(self, **kwargs):
            filtered = [
                row
                for row in self.rows
                if all(getattr(row, field) == value for field, value in kwargs.items())
            ]
            return _FakeQuery(filtered)

        def limit(self, value):
            return _FakeQuery(self.rows[:value])

        def all(self):
            return list(self.rows)

    rows = [
        SimpleNamespace(
            id=1,
            company_id=31,
            code="A",
            full_code="AA.I.1",
            name="Ativo",
            description=None,
            indicator_type="result",
            source_module="crm",
            source_id=None,
            source_scope="company",
            source_config={"pipeline": "default"},
            collection_mode="automatic",
            aggregation_function="sum",
            unit="%",
            polarity="positive",
            measurement_frequency="monthly",
            responsible_id=None,
            is_active=True,
            created_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            id=2,
            company_id=31,
            code="B",
            full_code="AA.I.2",
            name="Inativo",
            description=None,
            indicator_type="result",
            source_module="crm",
            source_id=None,
            source_scope="company",
            source_config={},
            collection_mode="automatic",
            aggregation_function="sum",
            unit="%",
            polarity="positive",
            measurement_frequency="monthly",
            responsible_id=None,
            is_active=False,
            created_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            id=3,
            company_id=99,
            code="C",
            full_code="AA.I.3",
            name="Outro tenant",
            description=None,
            indicator_type="result",
            source_module="erp",
            source_id=None,
            source_scope="company",
            source_config={},
            collection_mode="manual",
            aggregation_function="sum",
            unit="%",
            polarity="positive",
            measurement_frequency="monthly",
            responsible_id=None,
            is_active=True,
            created_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        ),
    ]

    fake_indicator_model = SimpleNamespace(query=_FakeQuery(rows))
    monkeypatch.setattr(mcp_incentive_tools, "Indicator", fake_indicator_model)

    items = mcp_incentive_tools._fetch_indicator_catalog(
        company_id=31,
        is_active=True,
        collection_mode="automatic",
        source_module="crm",
        limit=10,
    )

    assert [item["id"] for item in items] == [1]
    assert items[0]["created_at"] == "2026-04-17T00:00:00+00:00"
