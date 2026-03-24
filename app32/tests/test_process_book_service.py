import os
import sys
from datetime import date
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services import process_book_service


class _FakeColumn:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return ("eq", self.name, other)

    def in_(self, values):
        return ("in", self.name, tuple(values))

    def asc(self):
        return ("asc", self.name)

    def desc(self):
        return ("desc", self.name)


class _FakeListQuery:
    def __init__(self, rows):
        self.rows = rows
        self.options_args = ()
        self.filter_calls = []
        self.order_by_args = ()

    def options(self, *args):
        self.options_args = args
        return self

    def filter(self, *args):
        self.filter_calls.append(args)
        return self

    def order_by(self, *args):
        self.order_by_args = args
        return self

    def all(self):
        return list(self.rows)


class _FakeFirstQuery:
    def __init__(self, row):
        self.row = row
        self.filter_calls = []
        self.order_by_args = ()

    def filter(self, *args):
        self.filter_calls.append(args)
        return self

    def order_by(self, *args):
        self.order_by_args = args
        return self

    def first(self):
        return self.row


def test_load_indicators_supports_process_source_link_and_measured_fields(monkeypatch):
    indicator = SimpleNamespace(
        id=14,
        code="PRC.IND.14",
        name="Lead time",
        group=SimpleNamespace(name="Operação"),
        unit="dias",
        formula="fim - início",
        data_source="manual",
        polarity="negative",
    )
    latest_goal = SimpleNamespace(goal_value=12, goal_date=date(2026, 3, 31))
    latest_record = SimpleNamespace(measured_value=9, measured_date=date(2026, 3, 24))

    indicator_query = _FakeListQuery([indicator])
    goal_query = _FakeFirstQuery(latest_goal)
    record_query = _FakeFirstQuery(latest_record)

    monkeypatch.setattr(process_book_service, "joinedload", lambda value: ("joinedload", value))
    monkeypatch.setattr(process_book_service, "or_", lambda *args: ("or", args))
    monkeypatch.setattr(process_book_service, "and_", lambda *args: ("and", args))
    monkeypatch.setattr(
        process_book_service,
        "Indicator",
        SimpleNamespace(
            query=indicator_query,
            group=_FakeColumn("group"),
            company_id=_FakeColumn("company_id"),
            process_id=_FakeColumn("process_id"),
            source_module=_FakeColumn("source_module"),
            source_id=_FakeColumn("source_id"),
            code=_FakeColumn("code"),
            id=_FakeColumn("id"),
        ),
    )
    monkeypatch.setattr(
        process_book_service,
        "IndicatorGoal",
        SimpleNamespace(
            query=goal_query,
            company_id=_FakeColumn("company_id"),
            indicator_id=_FakeColumn("indicator_id"),
            goal_date=_FakeColumn("goal_date"),
            created_at=_FakeColumn("created_at"),
        ),
    )
    monkeypatch.setattr(
        process_book_service,
        "IndicatorData",
        SimpleNamespace(
            query=record_query,
            company_id=_FakeColumn("company_id"),
            indicator_id=_FakeColumn("indicator_id"),
            measured_date=_FakeColumn("measured_date"),
            created_at=_FakeColumn("created_at"),
        ),
    )

    payload = process_book_service._load_indicators(process_id=2, company_id=9)

    assert payload == [
        {
            "code": "PRC.IND.14",
            "name": "Lead time",
            "group_name": "Operação",
            "unit": "dias",
            "formula": "fim - início",
            "data_source": "manual",
            "polarity": "negative",
            "current_value": "9 dias",
            "goal_value": "12 dias",
            "goal_date": "31/03/2026",
            "last_record_date": "24/03/2026",
        }
    ]

    assert indicator_query.filter_calls[0] == (("eq", "company_id", 9),)
    assert indicator_query.filter_calls[1] == (
        (
            "or",
            (
                ("eq", "process_id", 2),
                (
                    "and",
                    (
                        ("in", "source_module", process_book_service.PROCESS_SOURCE_MODULES),
                        ("eq", "source_id", 2),
                    ),
                ),
            ),
        ),
    )
    assert record_query.order_by_args == (("desc", "measured_date"), ("desc", "created_at"))
