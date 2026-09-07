from services.usage_telemetry_readiness_service import UsageTelemetryReadinessService


def test_disabled_never_opens_redis_connection():
    assert UsageTelemetryReadinessService.check({'USAGE_TELEMETRY_ENABLED': False}, redis_factory=lambda *_a, **_k: (_ for _ in ()).throw(AssertionError())) == {'ready': False, 'reason': 'telemetry_disabled'}


def test_enabled_requires_redis_ping():
    class Healthy:
        def ping(self): return True
    result = UsageTelemetryReadinessService.check({'USAGE_TELEMETRY_ENABLED': True, 'REDIS_URL': 'redis://safe'}, redis_factory=lambda *_a, **_k: Healthy())
    assert result['ready'] is True


def test_redis_failure_does_not_enable_telemetry():
    result = UsageTelemetryReadinessService.check({'USAGE_TELEMETRY_ENABLED': True, 'REDIS_URL': 'redis://safe'}, redis_factory=lambda *_a, **_k: (_ for _ in ()).throw(OSError()))
    assert result == {'ready': False, 'reason': 'redis_unavailable'}
