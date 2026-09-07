from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock


def test_aggregation_is_hour_bucketed_and_idempotent(monkeypatch):
    from services import usage_telemetry_aggregation_service as service
    session = SimpleNamespace(company_id=7, user_id=11,
        login_at=datetime(2026, 9, 7, 10, 15), last_seen_at=datetime(2026, 9, 7, 10, 45))
    presence_query = Mock()
    presence_query.filter.return_value.all.return_value = [session]
    telemetry_query = Mock()
    telemetry_query.filter_by.return_value.first.return_value = None
    telemetry = Mock(query=telemetry_query)
    created = []
    telemetry.side_effect = lambda **kwargs: created.append(SimpleNamespace(**kwargs)) or created[-1]
    database = Mock()
    class Column:
        def __ge__(self, value): return ('>=', value)
        def __lt__(self, value): return ('<', value)
    monkeypatch.setattr(service, 'UserPresenceSession', SimpleNamespace(query=presence_query, last_seen_at=Column()))
    monkeypatch.setattr(service, 'UsageTelemetryHourly', telemetry)
    monkeypatch.setattr(service, 'db', database)

    result = service.UsageTelemetryAggregationService.aggregate_hour(datetime(2026, 9, 7, 10, 59))

    assert result == {'bucket_started_at': '2026-09-07T10:00:00', 'users': 1}
    assert created[0].company_id == 7
    assert created[0].active_seconds == 1800
    assert created[0].sessions_started == 1
    database.session.commit.assert_called_once()


def test_aggregation_never_reads_user_logs_or_mcp_tokens():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / 'services' / 'usage_telemetry_aggregation_service.py').read_text(encoding='utf-8').lower()
    assert 'userlog' not in source
    assert 'token' not in source
