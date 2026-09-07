from datetime import datetime

import pytest

from services.usage_telemetry_dashboard_service import UsageTelemetryDashboardService


def test_default_period_is_seven_days(monkeypatch):
    monkeypatch.setattr('services.usage_telemetry_dashboard_service.date', type('Date', (), {'today': staticmethod(lambda: __import__('datetime').date(2026, 9, 7)), 'fromisoformat': staticmethod(__import__('datetime').date.fromisoformat)}))
    start, end = UsageTelemetryDashboardService.period()
    assert start == datetime(2026, 9, 1)
    assert end == datetime(2026, 9, 8)


@pytest.mark.parametrize('start,end', [('2026-09-07', '2026-09-06'), ('2026-01-01', '2026-05-01')])
def test_period_rejects_invalid_or_expensive_ranges(start, end):
    with pytest.raises(ValueError):
        UsageTelemetryDashboardService.period(start, end)
