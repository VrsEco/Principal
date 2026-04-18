from datetime import datetime, timezone
from types import SimpleNamespace

from src.core import mcp_incentive_tools
from src.core.mcp_incentive_tools import register_incentive_tools


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
