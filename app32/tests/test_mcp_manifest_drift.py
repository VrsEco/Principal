"""Drift entre as fontes de verdade do mcp-versus (Fase 4, modo "só compara").

Catraca: divergências já existentes ficam registradas em BASELINE e só podem
diminuir. Divergência nova falha o teste; divergência corrigida exige atualizar
a linha de base. Nada aqui altera o runtime.
"""
from __future__ import annotations

import pytest

from src.core.mcp_drift import compute_drift, render_report

# Linha de base em 2026-10-08 (main abffc411f). Só pode diminuir.
BASELINE = {
    "domains_missing_in_permission_matrix": {"audit"},
    "domains_missing_in_playbooks": {"audit"},
    "domains_missing_in_tenant_rbac": set(),
    "tools_without_permissions": set(),
    "published_not_in_catalog": set(),
}
MAX_SCOPE_COMBINATIONS = 17
# Tools públicas por decisão (sem permissão) precisam ser revisadas ao entrar aqui.
EXPLICITLY_PUBLIC = {"answer_product_help"}


@pytest.fixture(scope="module")
def drift():
    return compute_drift()


@pytest.mark.parametrize("key", sorted(BASELINE))
def test_no_new_drift_between_sources(drift, key):
    current = set(drift[key])
    new = sorted(current - BASELINE[key])
    assert not new, (
        f"Drift novo em '{key}': {new}. Declare o domínio/permissão em TODAS as fontes "
        "(catálogo, matriz de permissões, playbooks e RBAC) antes de publicar a tool."
    )


@pytest.mark.parametrize("key", sorted(BASELINE))
def test_baseline_is_tight_so_it_only_shrinks(drift, key):
    fixed = sorted(BASELINE[key] - set(drift[key]))
    assert not fixed, (
        f"Drift corrigido em '{key}': {fixed}. Remova da BASELINE em "
        "tests/test_mcp_manifest_drift.py para travar o ganho."
    )


def test_scope_combinations_do_not_grow(drift):
    assert drift["scope_combinations"] <= MAX_SCOPE_COMBINATIONS, (
        f"{drift['scope_combinations']} combinações de escopos (máx. {MAX_SCOPE_COMBINATIONS}). "
        "Use um conjunto de escopos já existente para a nova tool."
    )


def test_scope_combinations_baseline_is_tight(drift):
    assert drift["scope_combinations"] >= MAX_SCOPE_COMBINATIONS, (
        f"Combinações de escopos caíram para {drift['scope_combinations']}: "
        "reduza MAX_SCOPE_COMBINATIONS em tests/test_mcp_manifest_drift.py para travar o ganho."
    )


def test_whatsapp_status_is_consistent_across_sources(drift):
    for key in ("domains_missing_in_permission_matrix", "domains_missing_in_playbooks", "domains_missing_in_tenant_rbac"):
        assert "whatsapp_status" not in drift[key]
    assert drift["per_domain"]["whatsapp_status"]["total"] == drift["per_domain"]["whatsapp_status"]["published"]


def test_report_renders_without_error(drift):
    text = render_report(drift)
    assert "Exposição por domínio" in text and "| finance |" in text


def test_explicitly_public_tools_are_reviewed(drift):
    assert set(drift["tools_explicitly_public"]) == EXPLICITLY_PUBLIC, (
        "Tool sem permissão declarada precisa de revisão: use uma permissão do catálogo ou, se for pública "
        "por decisão, registre-a em EXPLICITLY_PUBLIC e no SPEC."
    )
