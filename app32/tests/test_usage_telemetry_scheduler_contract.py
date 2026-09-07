from pathlib import Path


def test_scheduler_does_not_touch_telemetry_when_feature_is_disabled():
    source = (Path(__file__).resolve().parents[1] / 'services' / 'scheduler_service.py').read_text(encoding='utf-8')
    start = source.index('def aggregate_usage_telemetry(app):')
    body = source[start:source.index('\ndef check_overdue_tasks', start)]
    assert 'USAGE_TELEMETRY_ENABLED' in body
    assert 'telemetry_disabled' in body
    assert body.index('telemetry_disabled') < body.index('UsageTelemetryReadinessService')
