import os
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.incentive_service import IncentiveService


class _FakeQuery:
    def __init__(self, count_value=0, first_value=None):
        self._count_value = count_value
        self._first_value = first_value

    def filter_by(self, **kwargs):
        return self

    def count(self):
        return self._count_value

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_value


class _FakeSession:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_soft_delete_rule_set_blocks_when_has_active_rules(monkeypatch):
    monkeypatch.setattr(
        IncentiveService,
        "get_active_rules_query",
        lambda company_id, rule_set_id=None: _FakeQuery(count_value=1),
    )
    monkeypatch.setattr(
        IncentiveService,
        "get_active_participants_query",
        lambda company_id, rule_set_id=None: _FakeQuery(count_value=0),
    )
    monkeypatch.setattr(
        IncentiveService,
        "_rule_set_has_calculations",
        lambda company_id, rule_set_id: False,
    )

    ok, reason = IncentiveService.validate_rule_set_soft_delete(9, 101)

    assert ok is False
    assert "vetores vinculados" in reason


def test_soft_delete_rule_set_marks_deleted(monkeypatch):
    fake_rule_set = SimpleNamespace(
        id=101,
        company_id=9,
        is_active=True,
        deleted_at=None,
    )
    fake_session = _FakeSession()

    monkeypatch.setattr(IncentiveService, "get_rule_set", lambda company_id, rule_set_id: fake_rule_set)
    monkeypatch.setattr(
        IncentiveService,
        "validate_rule_set_soft_delete",
        lambda company_id, rule_set_id: (True, ""),
    )
    monkeypatch.setattr("services.incentive_service.db", SimpleNamespace(session=fake_session))

    ok, reason = IncentiveService.soft_delete_rule_set(9, 101)

    assert ok is True
    assert reason == ""
    assert fake_rule_set.is_active is False
    assert isinstance(fake_rule_set.deleted_at, datetime)
    assert fake_session.commits == 1


def test_soft_delete_participant_blocks_when_rule_set_has_calculation(monkeypatch):
    participant = SimpleNamespace(
        id=55,
        company_id=9,
        rule_set_id=101,
        deleted_at=None,
        elegivel=True,
    )

    monkeypatch.setattr(
        IncentiveService,
        "_rule_set_has_calculations",
        lambda company_id, rule_set_id: True,
    )

    ok, reason = IncentiveService.soft_delete_participant(9, participant)

    assert ok is False
    assert "apurações vinculadas" in reason
    assert participant.deleted_at is None


def test_soft_delete_rule_marks_deleted_even_when_company_id_is_none(monkeypatch):
    rule = SimpleNamespace(
        id=77,
        company_id=None,
        rule_set_id=101,
        deleted_at=None,
    )
    fake_session = _FakeSession()

    monkeypatch.setattr(
        IncentiveService,
        "get_rule_set",
        lambda company_id, rule_set_id: SimpleNamespace(id=101, company_id=company_id, deleted_at=None),
    )
    monkeypatch.setattr(
        IncentiveService,
        "_rule_set_has_calculations",
        lambda company_id, rule_set_id: False,
    )
    monkeypatch.setattr("services.incentive_service.db", SimpleNamespace(session=fake_session))

    ok, reason = IncentiveService.soft_delete_rule(9, rule)

    assert ok is True
    assert reason == ""
    assert rule.company_id == 9
    assert isinstance(rule.deleted_at, datetime)
    assert fake_session.commits == 1


def test_soft_delete_calculation_marks_deleted_even_when_paid(monkeypatch):
    calc = SimpleNamespace(id=9, company_id=9, status="approved", deleted_at=None)
    fake_session = _FakeSession()
    monkeypatch.setattr(IncentiveService, "get_calculation", lambda company_id, calc_id: calc)
    monkeypatch.setattr("services.incentive_service.db", SimpleNamespace(session=fake_session))

    ok, reason = IncentiveService.soft_delete_calculation(9, 9, allow_protected=False)

    assert ok is True
    assert reason == ""
    assert isinstance(calc.deleted_at, datetime)
    assert fake_session.commits == 1


def test_update_calculation_allows_paid_status(monkeypatch):
    calc = SimpleNamespace(
        id=9,
        company_id=9,
        status="paid",
        period_start=None,
        period_end=None,
    )
    fake_session = _FakeSession()
    monkeypatch.setattr(IncentiveService, "get_calculation", lambda company_id, calc_id: calc)
    monkeypatch.setattr("services.incentive_service.db", SimpleNamespace(session=fake_session))

    ok, reason, updated = IncentiveService.update_calculation(
        9,
        9,
        status="approved",
    )

    assert ok is True
    assert reason == ""
    assert updated is calc
    assert calc.status == "approved"
    assert fake_session.commits == 1


def test_soft_delete_rule_set_with_closings_soft_deletes_calculations(monkeypatch):
    fake_rule_set = SimpleNamespace(id=101, company_id=9, is_active=True, deleted_at=None)
    calculations = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    fake_session = _FakeSession()
    deleted_ids = []

    monkeypatch.setattr(IncentiveService, "get_rule_set", lambda company_id, rule_set_id: fake_rule_set)
    monkeypatch.setattr(
        IncentiveService,
        "get_active_calculations_query",
        lambda company_id: SimpleNamespace(filter_by=lambda **kwargs: SimpleNamespace(all=lambda: calculations)),
    )
    monkeypatch.setattr(
        IncentiveService,
        "get_active_participants_query",
        lambda company_id, rule_set_id=None: SimpleNamespace(all=lambda: []),
    )
    monkeypatch.setattr(
        IncentiveService,
        "get_active_rules_query",
        lambda company_id, rule_set_id=None: SimpleNamespace(all=lambda: []),
    )
    monkeypatch.setattr(
        IncentiveService,
        "soft_delete_calculation",
        lambda company_id, calc_id, allow_protected=False: (deleted_ids.append(calc_id) or True, "") if allow_protected else (False, "x"),
    )
    monkeypatch.setattr(
        IncentiveService,
        "validate_rule_set_soft_delete",
        lambda company_id, rule_set_id: (True, ""),
    )
    monkeypatch.setattr("services.incentive_service.db", SimpleNamespace(session=fake_session))

    ok, reason = IncentiveService.soft_delete_rule_set_with_closings(9, 101, allow_protected=True)

    assert ok is True
    assert reason == ""
    assert deleted_ids == [1, 2]
    assert isinstance(fake_rule_set.deleted_at, datetime)
    assert fake_rule_set.is_active is False
    assert fake_session.commits == 1
