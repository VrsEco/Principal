"""create_commercial_issuer gravava o emissor mas a resposta falhava (sessão descartada por contexto aninhado)."""

import pytest
from flask import Flask
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles

from models import Company, db
from models.contracts import ContractingLegalEntity
from src.core import mcp_commercial_tools


@compiles(JSONB, "sqlite")
def _jsonb_as_json_on_sqlite(element, compiler, **kw):
    return "JSON"


class _FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn

        return register


@pytest.fixture()
def app(monkeypatch):
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[Company.__table__, ContractingLegalEntity.__table__])
        db.session.add(Company(id=1, name="Empresa Um"))
        db.session.commit()
        db.session.remove()
    monkeypatch.setattr("src.core.mcp_flask_app.get_mcp_flask_app", lambda: app)
    return app


def test_create_issuer_returns_the_item_inside_the_runtime_app_context(app):
    fake = _FakeMcp()
    mcp_commercial_tools.register_commercial_mcp_tools(fake)
    with app.app_context():  # o runtime MCP já abre este contexto
        result = fake.tools["create_commercial_issuer"](
            1, {"legal_name": "Emissora Teste Ltda", "cnpj": "29559320000168"}
        )
    assert result["success"] is True, result
    assert result["item"]["legal_name"] == "Emissora Teste Ltda"
    with app.app_context():
        assert ContractingLegalEntity.query.count() == 1
