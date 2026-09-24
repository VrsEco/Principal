"""SQL real em cluster descartável; modelos mínimos e grants sintéticos."""
import os
import sys
from types import SimpleNamespace

import pytest
from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session

from services.mcp_company_reference_service import resolve_company_reference


@pytest.fixture
def postgres_scope(monkeypatch):
    url = os.getenv("APP32_REFERENCE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("Requer PostgreSQL descartável explicitamente configurado")
    from sqlalchemy.engine import make_url
    parsed = make_url(url)
    assert parsed.host == "127.0.0.1" and parsed.port != 5432
    assert parsed.database == "mcp_reference_test" and parsed.drivername.startswith("postgresql")
    engine = create_engine(url)
    base = declarative_base()

    class Company(base):
        __tablename__ = "reference_test_companies"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        client_code = Column(String)
        is_active = Column(Boolean)

    class User(base):
        __tablename__ = "reference_test_users"
        id = Column(Integer, primary_key=True)
        is_active = Column(Boolean)

    class Principal(base):
        __tablename__ = "reference_test_principals"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer)
        is_active = Column(Boolean)

    class Grant(base):
        __tablename__ = "reference_test_grants"
        id = Column(Integer, primary_key=True)
        principal_id = Column(Integer)
        company_id = Column(Integer)
        allowed = Column(Boolean)

    base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            for cls in (Company, User, Principal, Grant):
                cls.query = session.query(cls)
            session.add_all([
                Company(id=8, name="Meu Chapa", client_code="AW", is_active=True),
                Company(id=9, name="SEGREDO", client_code="ZZ", is_active=True),
                Company(id=10, name="Meu Chapa", client_code="AX", is_active=True),
                Company(id=11, name="Inativa", client_code="AI", is_active=False),
                User(id=32, is_active=True), Principal(id=71, user_id=32, is_active=True),
                Grant(id=1, principal_id=71, company_id=8, allowed=True),
                Grant(id=2, principal_id=71, company_id=9, allowed=False),
                Grant(id=3, principal_id=71, company_id=10, allowed=True),
                Grant(id=4, principal_id=71, company_id=11, allowed=True),
            ])
            session.flush()
            monkeypatch.setitem(sys.modules, "models.company", SimpleNamespace(Company=Company))
            monkeypatch.setitem(sys.modules, "models.user", SimpleNamespace(User=User))
            monkeypatch.setitem(sys.modules, "models.identity_principal", SimpleNamespace(
                IdentityPrincipal=Principal, PrincipalCompanyGrant=Grant))
            monkeypatch.setitem(sys.modules, "services.principal_authorization_service", SimpleNamespace(
                principal_authorization_service=SimpleNamespace(evaluate_grant=lambda **kw:
                    SimpleNamespace(allowed=kw["grant"].allowed))))
            access = {"ids": [8, 9, 11]}
            monkeypatch.setitem(sys.modules, "utils.company_access", SimpleNamespace(
                get_accessible_company_ids=lambda **kw: access["ids"]))
            monkeypatch.setitem(sys.modules, "utils.permissions", SimpleNamespace(is_platform_admin=lambda **kw: False))
            yield access
            session.rollback()
    finally:
        base.metadata.drop_all(engine)
        engine.dispose()


def test_sql_intersection_excludes_revoked_unlinked_and_inactive(postgres_scope):
    assert resolve_company_reference("Meu Chapa", principal_id=71, user_id=999) == 8
    for reference in ("ZZ", "AX", "AI"):
        with pytest.raises(PermissionError, match="entre as autorizadas"):
            resolve_company_reference(reference, principal_id=71)


def test_sql_ambiguity_contains_only_authorized_companies(postgres_scope):
    postgres_scope["ids"] = [8, 9, 10]
    with pytest.raises(ValueError, match="ambígua") as error:
        resolve_company_reference("Meu Chapa", principal_id=71)
    assert "AW" in str(error.value) and "AX" in str(error.value)
    assert "SEGREDO" not in str(error.value)


def test_sql_http_ceiling_cannot_be_expanded(postgres_scope):
    with pytest.raises(PermissionError):
        resolve_company_reference("AW", user_id=32, accessible_company_ids=[])
