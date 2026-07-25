#!/usr/bin/env python3
"""Runtime dedicado do scheduler corporativo do APP32.

O processo web mantém APP_BOOTSTRAP_RUNTIME_SERVICES=0 para evitar que cada
worker uWSGI crie sua própria cópia dos jobs. Este launcher sobe exatamente
uma instância do APScheduler e publica um heartbeat operacional.
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Event


APP_DIR = Path(__file__).resolve().parents[1]
TMP_DIR = APP_DIR / "tmp"
LOCK_PATH = TMP_DIR / "scheduler_runtime.lock"
HEARTBEAT_PATH = TMP_DIR / "scheduler_heartbeat.json"
STOP_EVENT = Event()


def _write_heartbeat(scheduler_service) -> None:
    jobs = []
    for job in scheduler_service.scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        )
    payload = {
        "pid": os.getpid(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "running": bool(scheduler_service.is_running),
        "jobs": jobs,
    }
    temporary = HEARTBEAT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(HEARTBEAT_PATH)


def _request_stop(_signum, _frame) -> None:
    STOP_EVENT.set()


def main() -> int:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    lock_handle = LOCK_PATH.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Scheduler dedicado já está ativo; lock ocupado.", flush=True)
        return 2

    os.environ["APP_BOOTSTRAP_DB_SCHEMA"] = "0"
    os.environ["APP_BOOTSTRAP_RUNTIME_SERVICES"] = "0"
    os.environ.setdefault("FLASK_CONFIG", "production")
    sys.path.insert(0, str(APP_DIR))

    from app import create_app
    from services.scheduler_service import initialize_scheduler, scheduler_service, shutdown_scheduler

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    app = create_app("production")
    initialize_scheduler(app)
    _write_heartbeat(scheduler_service)
    print(
        f"Scheduler dedicado ativo com {len(scheduler_service.scheduler.get_jobs())} jobs.",
        flush=True,
    )

    try:
        while not STOP_EVENT.wait(30):
            _write_heartbeat(scheduler_service)
    finally:
        shutdown_scheduler()
        HEARTBEAT_PATH.unlink(missing_ok=True)
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
