"""Run the fixed engineering unit baseline with fail-closed external I/O guards.

Not an integration runner or an OS sandbox. Never use it for PostgreSQL/E2E tests.
Guards are installed before pytest imports/collects application modules.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
import socket
import sqlite3
import _sqlite3
import subprocess
import sys
import traceback
from unittest.mock import patch
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace


TEST_FILES = (
    "test_engineering_token_economy.py",
    "test_engineering_measurement.py",
    "test_engineering_runtime_catalog.py",
    "test_engineering_model_broker.py",
    "test_engineering_quality_gate.py",
    "test_engineering_sessions.py",
    "test_engineering_context_governor.py",
    "test_engineering_task_router.py",
    "test_sapiens_engineering_guidance.py",
    "test_mcp_squad_runtime.py",
    "test_mcp_sapiens_activation.py",
    "test_mcp_instruction_registry.py",
    "test_instruction_registry_service.py",
    "test_mcp_permission_matrix.py",
    "test_mcp_connection_snippet_service.py",
    "test_mcp_connection_experience_spec.py",
    "test_core_mcp_session_harness_tools.py",
    "test_core_mcp_runtime_http_context.py",
    "test_core_mcp_surface_registry.py",
    "test_mcp_profile_contracts.py",
    "test_mcp_profile_scope_matrix.py",
)


def main() -> int:
    # Windows platform detection may run `ver`; finish stdlib discovery before
    # applying guards, still before importing any application/test module.
    platform.uname()
    platform.platform()
    platform.processor()
    app_root = Path(__file__).resolve().parents[1]
    repo_root = app_root.parent
    attempts: list[str] = []
    traces: set[str] = set()

    def deny(operation):
        def blocked(*args, **kwargs):
            # Do not log connection strings, tokens or payloads.
            attempts.append(operation)
            frames = traceback.extract_stack(limit=24)[:-1]
            traces.add(operation + ": " + " -> ".join(
                f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}" for frame in frames
            ))
            raise RuntimeError(f"Engineering baseline forbids {operation}")
        return blocked

    with ExitStack() as stack:
        # asyncio on Windows needs private wakeup sockets. Preallocate only
        # those pairs; do not permit arbitrary localhost/network connections.
        pairs = [socket.socketpair() for _ in range(4)]
        for pair in pairs:
            for sock in pair:
                stack.callback(sock.close)

        def private_socketpair(*args, **kwargs):
            if not pairs:
                return deny("socketpair pool exhausted")()
            return pairs.pop()

        stack.enter_context(patch.object(socket, "socketpair", private_socketpair))
        stack.enter_context(patch.dict(os.environ, {
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "APP_BOOTSTRAP_RUNTIME_SERVICES": "0",
            "APP_BOOTSTRAP_DB_SCHEMA": "0",
        }))
        stack.enter_context(patch.object(socket.socket, "connect", deny("socket.connect")))
        stack.enter_context(patch.object(socket.socket, "connect_ex", deny("socket.connect_ex")))
        stack.enter_context(patch.object(socket.socket, "sendto", deny("socket.sendto")))
        stack.enter_context(patch.object(socket, "getaddrinfo", deny("DNS lookup")))
        stack.enter_context(patch.object(subprocess, "Popen", deny("subprocess")))
        stack.enter_context(patch.object(os, "system", deny("os.system")))
        stack.enter_context(patch.object(sqlite3, "connect", deny("SQLite connect")))
        stack.enter_context(patch.object(_sqlite3, "connect", deny("SQLite native connect")))
        # libpq does not use Python sockets: block the driver separately.
        import psycopg2
        from apscheduler.schedulers.base import BaseScheduler
        stack.enter_context(patch.object(psycopg2, "connect", deny("PostgreSQL connect")))
        stack.enter_context(patch.object(BaseScheduler, "start", deny("scheduler.start")))

        sys.path.insert(0, str(app_root))
        # Catalog imports instantiate legacy RAG/email/WhatsApp singletons.
        # They are not the subject of these contract tests: replace their
        # external configuration/storage seams before collecting the catalog.
        rag = ModuleType("src.intelligence.rag")
        rag.knowledge_base = SimpleNamespace(
            search=deny("RAG search"), add_documents=deny("RAG write"),
        )
        stack.enter_context(patch.dict(sys.modules, {"src.intelligence.rag": rag}))
        import utils.integration_settings as integration_settings
        stack.enter_context(patch.object(
            integration_settings, "resolve_service_config", lambda *args, **kwargs: {},
        ))
        stack.enter_context(patch.object(
            integration_settings, "resolve_openai_api_key", lambda *args, **kwargs: None,
        ))
        import pytest
        code = pytest.main([
            "-c", str(repo_root / "pytest.ini"), "-q",
            *[str(app_root / "tests" / name) for name in TEST_FILES],
        ])
        # A caught exception in app code must not hide a forbidden I/O attempt.
        if attempts:
            print("Blocked external operations: " + ", ".join(sorted(set(attempts))))
            for trace in sorted(traces):
                print(trace)
            return 1
        print("Engineering baseline: zero blocked external I/O attempts.")
        return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
