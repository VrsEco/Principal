import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import portfolios as portfolios_route


class _FakeColumn:
    def asc(self):
        return self


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter_by(self, **kwargs):
        filtered = self._rows
        for key, value in kwargs.items():
            filtered = [row for row in filtered if getattr(row, key) == value]
        return _FakeQuery(filtered)

    def order_by(self, _column):
        return _FakeQuery(sorted(self._rows, key=lambda row: getattr(row, "id", 0)))

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def test_resolve_portfolio_for_summary_returns_exact_match(monkeypatch):
    exact = SimpleNamespace(id=30, company_id=9, name="Geral")
    monkeypatch.setattr(
        portfolios_route,
        "Portfolio",
        SimpleNamespace(query=_FakeQuery([exact]), id=_FakeColumn()),
    )

    result = portfolios_route._resolve_portfolio_for_summary(9, 30)

    assert result.id == 30


def test_resolve_portfolio_for_summary_falls_back_when_company_has_single_portfolio(monkeypatch):
    unique = SimpleNamespace(id=30, company_id=9, name="Geral")
    monkeypatch.setattr(
        portfolios_route,
        "Portfolio",
        SimpleNamespace(query=_FakeQuery([unique]), id=_FakeColumn()),
    )

    result = portfolios_route._resolve_portfolio_for_summary(9, 5)

    assert result.id == 30


def test_resolve_portfolio_for_summary_keeps_404_when_company_has_multiple_portfolios(monkeypatch):
    rows = [
        SimpleNamespace(id=30, company_id=9, name="Geral"),
        SimpleNamespace(id=31, company_id=9, name="Expansão"),
    ]
    monkeypatch.setattr(
        portfolios_route,
        "Portfolio",
        SimpleNamespace(query=_FakeQuery(rows), id=_FakeColumn()),
    )
    monkeypatch.setattr(
        portfolios_route,
        "abort",
        lambda code, description=None: (_ for _ in ()).throw(RuntimeError(f"{code}:{description}")),
    )

    with pytest.raises(RuntimeError, match="404:Portfólio não encontrado"):
        portfolios_route._resolve_portfolio_for_summary(9, 5)
