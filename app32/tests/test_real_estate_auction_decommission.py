from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def test_discontinued_module_has_no_runtime_surface_or_artifacts():
    removed_paths = [
        "api/routes/real_estate_auctions.py",
        "models/real_estate_auction.py",
        "services/real_estate_auction_service.py",
        "seeds/enable_real_estate_auction_module.py",
        "src/core/mcp_real_estate_auction_tools.py",
        "templates/modules/real_estate_auctions",
    ]

    assert all(not (BASE_DIR / relative_path).exists() for relative_path in removed_paths)

    runtime_files = [
        "app.py",
        "models/__init__.py",
        "services/rbac_permission_catalog_service.py",
        "services/tool_first_catalog_service.py",
        "src/intelligence/taxonomy.py",
        "src/intelligence/tool_catalog.py",
        "src/intelligence/tooling/capabilities.py",
        "src/intelligence/security/tenant_rbac.py",
        "src/intelligence/mcp_contracts/crud_domains.py",
        "src/intelligence/mcp_contracts/permission_matrix.py",
        "src/intelligence/mcp_contracts/profiles.py",
        "src/intelligence/mcp_contracts/playbooks.py",
        "templates/partials/sidebar_standard.html",
    ]

    for relative_path in runtime_files:
        content = _read(relative_path)
        assert "real_estate_auction" not in content
        assert "real-estate-auction" not in content
        assert "Leilões Imobiliários" not in content


def test_historical_migration_chain_is_preserved_without_runtime_reactivation():
    historical = BASE_DIR / "migrations/versions/20260531_0900_create_real_estate_auction_domain.py"
    successor = _read("migrations/versions/20260531_1300_create_strategy_alignment_n1.py")

    assert historical.exists()
    assert 'down_revision = "20260531_0900"' in successor


def test_historical_documents_are_explicitly_retired():
    for relative_path in [
        "docs/spec/modulo_leiloes_imobiliarios_multi_tenant_v1.md",
        "docs/playbooks/backlog_impl_modulo_leiloes_imobiliarios_multi_tenant_v1.md",
        "docs/runbooks/habilitacao_modulo_leiloes_imobiliarios_ganduinvest_v1.md",
    ]:
        assert "RETIRADO em 2026-08-20" in _read(relative_path)
