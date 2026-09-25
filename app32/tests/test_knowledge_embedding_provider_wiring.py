"""Provedor de embeddings em runtime: desligado por padrão, falha fechada e piloto por empresa.

Sem rede e sem chave real: o SDK é substituído por um duplo e o ambiente é controlado por teste.
"""
from __future__ import annotations

import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.knowledge import openai_embedding_provider as provider_module
from services.knowledge import retrieval_strategy as rs
from services.knowledge.query_service import KnowledgeQueryService

ENV_ON = {
    rs.VECTOR_FLAG_ENV: "true",
    rs.EMBEDDING_MODEL_ENV: "text-embedding-3-small",
    rs.EMBEDDING_VERSION_ENV: "v1",
    rs.INDEX_GENERATION_ENV: "1",
    provider_module.API_KEY_ENV: "chave-de-teste-nao-real",
}
ALL_KEYS = (*ENV_ON, rs.VECTOR_PILOT_COMPANIES_ENV, provider_module.DEDICATED_API_KEY_ENV)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in ALL_KEYS:
        monkeypatch.delenv(key, raising=False)


def _set_env(monkeypatch, **overrides):
    values = {**ENV_ON, **overrides}
    for key, value in values.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_factory_returns_none_by_default_and_when_anything_is_missing():
    assert provider_module.build_default_embedding_provider({}) is None
    for missing in ENV_ON:
        partial = {k: v for k, v in ENV_ON.items() if k != missing}
        assert provider_module.build_default_embedding_provider(partial) is None, missing
    blank_key = {**ENV_ON, provider_module.API_KEY_ENV: "   "}
    assert provider_module.build_default_embedding_provider(blank_key) is None
    flag_off = {**ENV_ON, rs.VECTOR_FLAG_ENV: "false"}
    assert provider_module.build_default_embedding_provider(flag_off) is None


def test_dedicated_key_has_precedence_and_alone_is_enough(monkeypatch):
    only_dedicated = {k: v for k, v in ENV_ON.items() if k != provider_module.API_KEY_ENV}
    only_dedicated[provider_module.DEDICATED_API_KEY_ENV] = "chave-dedicada-nao-real"
    provider = provider_module.build_default_embedding_provider(only_dedicated)
    assert provider is not None and provider._api_key == "chave-dedicada-nao-real"

    both = {**ENV_ON, provider_module.DEDICATED_API_KEY_ENV: "chave-dedicada-nao-real"}
    assert provider_module.build_default_embedding_provider(both)._api_key == "chave-dedicada-nao-real"

    shared_only = provider_module.build_default_embedding_provider(ENV_ON)
    assert shared_only._api_key is None  # o SDK lê OPENAI_API_KEY sozinho


def test_sdk_receives_the_dedicated_key_only_when_present(monkeypatch):
    calls = []

    class FakeOpenAI:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    provider_module.OpenAIEmbeddingProvider(api_key="dedicada")._sdk()
    provider_module.OpenAIEmbeddingProvider()._sdk()
    assert calls[0]["api_key"] == "dedicada"
    assert "api_key" not in calls[1]


def test_factory_builds_provider_with_configured_model_without_calling_the_sdk():
    provider = provider_module.build_default_embedding_provider({**ENV_ON, rs.EMBEDDING_MODEL_ENV: "modelo-x"})
    assert isinstance(provider, provider_module.OpenAIEmbeddingProvider)
    assert provider.model == "modelo-x"
    assert provider._client is None  # nada é criado nem chamado até a primeira consulta


def test_sdk_client_gets_explicit_timeout_and_retries(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "openai", types.SimpleNamespace(OpenAI=FakeOpenAI))
    provider_module.OpenAIEmbeddingProvider()._sdk()
    assert captured == {
        "timeout": provider_module.DEFAULT_TIMEOUT_SECONDS,
        "max_retries": provider_module.DEFAULT_MAX_RETRIES,
    }


def test_service_has_no_provider_and_uses_full_text_by_default():
    service = KnowledgeQueryService()
    assert service._embedding_provider is None
    _, plan = service.build_plan("como cadastrar uma empresa", company_id=1)
    assert plan.strategies == rs.DEFAULT_STRATEGIES
    assert plan.fallback_reason is None
    assert plan.requested_strategy == rs.STRATEGY_FULL_TEXT


def test_service_resolves_provider_from_env_and_defaults_to_hybrid_when_ready(monkeypatch):
    _set_env(monkeypatch)
    service = KnowledgeQueryService()
    assert isinstance(service._embedding_provider, provider_module.OpenAIEmbeddingProvider)
    _, plan = service.build_plan("como cadastrar uma empresa", company_id=1)
    assert rs.STRATEGY_HYBRID in plan.strategies
    assert plan.fallback_reason is None


def test_explicit_none_provider_still_means_no_provider_even_with_env_on(monkeypatch):
    _set_env(monkeypatch)
    service = KnowledgeQueryService(embedding_provider=None)
    assert service._embedding_provider is None
    _, plan = service.build_plan("como cadastrar uma empresa", company_id=1)
    assert plan.strategies == rs.DEFAULT_STRATEGIES


def test_explicit_full_text_strategy_is_respected_even_with_env_on(monkeypatch):
    _set_env(monkeypatch)
    _, plan = KnowledgeQueryService().build_plan(
        "como cadastrar uma empresa", company_id=1, strategy=rs.STRATEGY_FULL_TEXT
    )
    assert plan.strategies == rs.DEFAULT_STRATEGIES


def test_pilot_allowlist_limits_the_default_hybrid_to_listed_companies(monkeypatch):
    _set_env(monkeypatch, **{rs.VECTOR_PILOT_COMPANIES_ENV: "7, 9"})
    service = KnowledgeQueryService()
    _, inside = service.build_plan("como cadastrar uma empresa", company_id=9)
    _, outside = service.build_plan("como cadastrar uma empresa", company_id=1)
    assert rs.STRATEGY_HYBRID in inside.strategies
    assert outside.strategies == rs.DEFAULT_STRATEGIES


@pytest.mark.parametrize(
    "raw, company_id, expected",
    [
        ("", 1, True),
        ("", None, True),
        ("1,2", 2, True),
        ("1,2", 3, False),
        ("1,2", None, False),
        ("abc", 1, False),  # lista inválida falha fechada
        (" 5 ,x, 6", 6, True),
    ],
)
def test_vector_pilot_allows_fails_closed(raw, company_id, expected):
    assert rs.vector_pilot_allows(company_id, {rs.VECTOR_PILOT_COMPANIES_ENV: raw}) is expected


def test_pilot_rejects_boolean_company_id():
    assert rs.vector_pilot_allows(True, {rs.VECTOR_PILOT_COMPANIES_ENV: "1"}) is False
