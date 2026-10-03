"""Harness: real financial data, application bootstrap and outbound IO forbidden.

Run with Python from any directory. No credential or production configuration is
loaded by this runner. Windows asyncio socketpair is the only allowed connect.
"""
import inspect
import os
from pathlib import Path
import socket
import sqlite3
import sys
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

import dotenv
import dotenv.main
import psycopg2
import sqlalchemy.engine
from flask import Flask
import pytest


def forbidden(*args, **kwargs):
    raise AssertionError("Harness isolado: banco, rede externa e app real proibidos")


# Process-local isolation only: never load project .env files or instantiate RAG.
def no_dotenv(*args, **kwargs):
    return False


dotenv.load_dotenv = no_dotenv
dotenv.main.load_dotenv = no_dotenv
dotenv.dotenv_values = forbidden
dotenv.main.dotenv_values = forbidden
rag_stub = ModuleType("src.intelligence.rag")
rag_stub.knowledge_base = SimpleNamespace(query=forbidden, add_documents=forbidden)
sys.modules["src.intelligence.rag"] = rag_stub


original_connect = socket.socket.connect


def isolated_connect(self, address):
    caller = inspect.currentframe().f_back
    if (caller.f_code.co_name == "socketpair"
            and caller.f_code.co_filename == socket.__file__
            and isinstance(address, tuple)
            and address[0] in {"127.0.0.1", "::1"}):
        return original_connect(self, address)
    return forbidden()


socket.socket.connect = isolated_connect
socket.socket.connect_ex = forbidden
psycopg2.connect = forbidden
sqlite3.connect = forbidden
sqlalchemy.engine.Engine.connect = forbidden
app = Flask("isolated_reconciliation_reads")
app.config["TESTING"] = True
sys.modules["app"] = SimpleNamespace(create_app=lambda: app)

TESTS = (
    "test_financial_reconciliation_diagnostic_reads.py",
    "test_core_mcp_financial_tools.py",
    "test_core_mcp_surface_registry.py",
    "test_intelligence_security_tool_policy.py",
    "test_intelligence_security_tenant_rbac.py",
)
if __name__ == "__main__":
    raise SystemExit(pytest.main([
        "-q", "--tb=short", "-p", "no:cacheprovider", "-c", str(ROOT / "pytest.ini"),
        *[str(ROOT / "tests" / name) for name in TESTS],
    ]))
