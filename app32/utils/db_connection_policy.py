"""PostgreSQL transport limits and process-local pools for the web runtime."""
import os
import threading


def production_connection_options(environ):
    def positive(name, default):
        value = int(environ.get(name) or default)
        if value < 1:
            raise ValueError(f"{name} must be positive")
        return value

    return {
        "pool_recycle": positive("SQLALCHEMY_POOL_RECYCLE", 120),
        "pool_timeout": positive("SQLALCHEMY_POOL_TIMEOUT", 5),
        "connect_args": {
            "connect_timeout": positive("DB_CONNECT_TIMEOUT_SECONDS", 5),
            "keepalives": 1,
            "keepalives_idle": positive("DB_KEEPALIVES_IDLE_SECONDS", 15),
            "keepalives_interval": positive("DB_KEEPALIVES_INTERVAL_SECONDS", 5),
            "keepalives_count": positive("DB_KEEPALIVES_COUNT", 3),
            "tcp_user_timeout": positive("DB_TCP_USER_TIMEOUT_MS", 15000),
        },
    }


class ProcessLocalDatabasePools:
    """Reset inherited pools before Flask loads a session or does a pre-ping.

    Intended for prefork WSGI servers: master must not handle live requests.
    Never closes parent connections or retries an application transaction.
    Background jobs must manage their own process/session lifecycle.
    """

    def __init__(self, app, engines, logger):
        self.app = app
        self.engines = tuple(engines)
        self.logger = logger
        self.pid = os.getpid()
        self.lock = threading.Lock()

    def __call__(self, environ, start_response):
        pid = os.getpid()
        if self.pid != pid:
            with self.lock:
                if self.pid != pid:
                    for engine in self.engines:
                        engine.dispose(close=False)
                    self.pid = pid
                    self.logger.warning("db_pool_reset_after_fork")
        return self.app(environ, start_response)


def install_process_local_pools(app, db):
    with app.app_context():
        engines = tuple(db.engines.values())
    app.wsgi_app = ProcessLocalDatabasePools(app.wsgi_app, engines, app.logger)
    options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
    transport = options.get("connect_args", {})
    app.logger.warning(
        "db_connection_policy_enabled recycle_seconds=%s pool_wait_seconds=%s "
        "connect_seconds=%s tcp_unacked_ms=%s",
        options.get("pool_recycle"), options.get("pool_timeout"),
        transport.get("connect_timeout"), transport.get("tcp_user_timeout"),
    )
