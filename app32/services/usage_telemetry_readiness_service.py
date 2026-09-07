from time import monotonic


class UsageTelemetryReadinessService:
    """Gate explícito antes de habilitar coleta assíncrona."""

    @staticmethod
    def check(config, *, redis_factory=None):
        if not config.get('USAGE_TELEMETRY_ENABLED', False):
            return {'ready': False, 'reason': 'telemetry_disabled'}
        try:
            if redis_factory is None:
                import redis
                redis_factory = redis.Redis.from_url
            started = monotonic()
            client = redis_factory(config['REDIS_URL'], socket_connect_timeout=1, socket_timeout=1)
            if not client.ping():
                return {'ready': False, 'reason': 'redis_unavailable'}
            return {'ready': True, 'redis_latency_ms': round((monotonic() - started) * 1000, 1)}
        except Exception:
            return {'ready': False, 'reason': 'redis_unavailable'}
