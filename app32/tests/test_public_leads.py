import os
import sys
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.routes import public_leads
from services import site_lead_service as leads

SOURCES = (
    '{"site-performance-hub": {"company_id": 9, "project_code": "AA.J.187", "task_user_id": 1},'
    ' "site-outra-empresa": {"company_id": 33}}'
)
ORIGIN = "https://site.example.com"


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SECRET_KEY="test",
        LEADS_ALLOWED_ORIGINS=[ORIGIN],
        LEADS_PRIVACY_POLICY_VERSION="2026-10",
        LEADS_SOURCES_JSON=SOURCES,
        LEADS_RATE_LIMIT_IP=5,
        LEADS_RATE_LIMIT_SOURCE=100,
    )
    app.register_blueprint(public_leads.public_leads_bp)
    created = []

    def fake_create(*, source, source_cfg, data, ip):
        created.append({"source": source, "company_id": source_cfg["company_id"], "data": data, "ip": ip})
        return f"lead{len(created)}", False

    monkeypatch.setattr(leads.SiteLeadService, "create_lead", staticmethod(fake_create))
    monkeypatch.setattr(public_leads, "db", SimpleNamespace(session=SimpleNamespace(rollback=lambda: None)))
    leads._COUNTERS.clear()
    test_client = app.test_client()
    test_client.created = created
    return test_client


def _payload(**overrides):
    body = {
        "source": "site-performance-hub",
        "nome": "Ana",
        "assunto": "orcamento",
        "relato": "Quero conversar",
        "consent": True,
        "origin": {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "out", "referrer": "https://g.co/x"},
        "page": "/servicos",
        "ts": "2026-10-15T12:00:00Z",
    }
    body.update(overrides)
    return body


def _post(client, body, origin=ORIGIN):
    return client.post("/public/leads", json=body, headers={"Origin": origin} if origin else {})


def test_valid_lead_records_utm_and_company_from_source(client):
    response = _post(client, _payload())
    assert response.status_code == 202
    assert response.get_json() == {"lead_id": "lead1"}
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    saved = client.created[0]
    assert saved["company_id"] == 9
    assert saved["data"]["origin"]["utm_source"] == "google"
    assert saved["data"]["referrer_host"] == "g.co"


def test_source_decides_company_never_the_payload(client):
    _post(client, _payload(source="site-outra-empresa"))
    assert client.created[0]["company_id"] == 33
    assert _post(client, _payload(company_id=9)).status_code == 400
    assert len(client.created) == 1


def test_unknown_source_rejected(client):
    assert _post(client, _payload(source="desconhecido")).status_code == 400
    assert _post(client, {"assunto": "orcamento", "consent": True}).status_code == 400
    assert client.created == []


@pytest.mark.parametrize("consent", [None, False, "true", 1])
def test_consent_missing_or_not_true_does_not_store(client, consent):
    body = _payload()
    body.pop("consent")
    if consent is not None:
        body["consent"] = consent
    assert _post(client, body).status_code == 400
    assert client.created == []


def test_subject_must_be_in_fixed_list(client):
    assert _post(client, _payload(assunto="qualquer")).status_code == 400


def test_cors_blocks_origin_outside_list(client):
    response = _post(client, _payload(), origin="https://evil.example.org")
    assert response.status_code == 403
    assert "Access-Control-Allow-Origin" not in response.headers
    assert client.created == []


def test_preflight_allowed_and_blocked(client):
    ok = client.options("/public/leads", headers={"Origin": ORIGIN})
    assert ok.status_code == 204 and ok.headers["Access-Control-Allow-Origin"] == ORIGIN
    bad = client.options("/public/leads", headers={"Origin": "https://evil.example.org"})
    assert bad.status_code == 403


def test_rate_limit_returns_429_and_service_keeps_working(client):
    codes = [_post(client, _payload(relato=f"msg {i}")).status_code for i in range(7)]
    assert codes[:5] == [202] * 5
    assert codes[5:] == [429, 429]
    assert leads.counters()["rejected_rate_ip"] == 2


def test_body_size_limit_and_content_type(client):
    assert _post(client, _payload(relato="x" * 5000)).status_code == 413
    response = client.post("/public/leads", data="x", headers={"Origin": ORIGIN, "Content-Type": "text/plain"})
    assert response.status_code == 400


def test_length_limits_and_strict_schema(client):
    assert _post(client, _payload(nome="n" * 81)).status_code == 400
    assert _post(client, _payload(relato="r" * 601)).status_code == 400
    assert _post(client, _payload(extra="x")).status_code == 400
    assert _post(client, _payload(origin={"utm_source": "a", "x": 1})).status_code == 400
    assert _post(client, _payload(page="http://x")).status_code == 400


def test_sensitive_patterns_are_redacted_not_blocking(client):
    body = _payload(relato="meu cpf 123.456.789-09, cnpj 12.345.678/0001-95, senha: abc123 ok")
    assert _post(client, body).status_code == 202
    relato = client.created[0]["data"]["relato"]
    assert "123.456.789" not in relato and "0001-95" not in relato and "abc123" not in relato
    assert "ok" in relato
    assert leads.counters()["redacted"] == 1


def test_unconfigured_returns_503(client):
    client.application.config["LEADS_ALLOWED_ORIGINS"] = []
    assert _post(client, _payload()).status_code == 503


def test_persist_failure_returns_503_without_crash(client, monkeypatch):
    def boom(**_):
        raise RuntimeError("db down")

    monkeypatch.setattr(leads.SiteLeadService, "create_lead", staticmethod(boom))
    assert _post(client, _payload()).status_code == 503
    assert leads.counters()["failed_persist"] == 1


def test_dedupe_hash_is_stable_and_ignores_case_and_ip():
    cfg = {"company_id": 9}
    one = leads.validate_payload(_payload(nome="Ana", relato="Oi"), cfg)
    two = leads.validate_payload(_payload(nome="ANA ", relato="oi"), cfg)
    other = leads.validate_payload(_payload(nome="Ana", relato="Outro"), cfg)
    assert leads.dedupe_hash("s", one) == leads.dedupe_hash("s", two)
    assert leads.dedupe_hash("s", one) != leads.dedupe_hash("s", other)
    assert leads.dedupe_hash("s", one) != leads.dedupe_hash("t", one)


def test_ip_is_stored_only_as_hash():
    app = Flask(__name__)
    app.config.update(SECRET_KEY="k")
    with app.app_context():
        digest = leads.hash_ip("203.0.113.9")
    assert len(digest) == 64 and "203" not in digest
