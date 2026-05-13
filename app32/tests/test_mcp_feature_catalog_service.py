from services.mcp_feature_catalog_service import (
    MCPDocumentationContext,
    MCPFeatureCatalogAccessError,
    MCPFeatureCatalogContextError,
    MCPFeatureCatalogService,
)


def test_list_features_filters_by_surface_and_domain():
    service = MCPFeatureCatalogService()

    user_features = service.list_features("user")
    user_feature_ids = {feature["id"] for feature in user_features}
    assert "rotina_tarefas" in user_feature_ids
    assert "processos_acompanhamento" in user_feature_ids
    assert "financeiro_fluxo_caixa" not in user_feature_ids

    finance_features = service.list_features("admin", domain="finance")
    assert [feature["id"] for feature in finance_features] == ["financeiro_fluxo_caixa"]


def test_bootstrap_requires_company_context():
    service = MCPFeatureCatalogService()
    context = MCPDocumentationContext(
        company_id=None,
        user_id=10,
        role="colaborador",
        surface="user",
        client="claude_code",
        transport="stdio",
    )

    try:
        service.bootstrap_context(context)
    except MCPFeatureCatalogContextError as exc:
        assert "company_id é obrigatório" in str(exc)
    else:  # pragma: no cover - proteção defensiva
        raise AssertionError("Era esperado erro por ausência de company_id.")


def test_guide_and_constraints_follow_surface_rules():
    service = MCPFeatureCatalogService()

    guide = service.get_feature_guide("rotina_tarefas", "user")
    assert guide["feature_id"] == "rotina_tarefas"
    assert "Tarefas da Rotina" in guide["guide_markdown"]

    constraints = service.get_feature_constraints("rotina_tarefas", "user")
    assert constraints["requires_company_id"] is True
    assert "user" in constraints["allowed_surfaces"]

    try:
        service.get_feature_guide("financeiro_fluxo_caixa", "user")
    except MCPFeatureCatalogAccessError as exc:
        assert "não está autorizada" in str(exc)
    else:  # pragma: no cover - proteção defensiva
        raise AssertionError("Era esperado bloqueio de surface para feature financeira.")


def test_bootstrap_context_exposes_current_context_and_required_context_summary():
    service = MCPFeatureCatalogService()
    context = MCPDocumentationContext(
        company_id=31,
        user_id=10,
        role="colaborador",
        surface="user",
        client="claude_code",
        transport="stdio",
        thread_id="thread-1",
    )

    payload = service.bootstrap_context(context)

    assert payload["current_context"]["required"] == ["company"]
    assert payload["current_context"]["resolved"]["company_id"] == 31
    assert payload["current_context"]["resolution"]["company"] == "request_context.company_id"
    assert "context_summary" in payload


def test_feature_constraints_expose_required_context_dimensions():
    service = MCPFeatureCatalogService()

    constraints = service.get_feature_constraints("rotina_tarefas", "user")

    assert constraints["requires_company_id"] is True
    assert constraints["requires_user_id"] is False
    assert constraints["required_context"] == ["company"]
