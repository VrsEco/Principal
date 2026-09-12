from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "deploy" / "keycloak"


def test_keycloak_templates_keep_runtime_and_secrets_outside_app32_repo() -> None:
    env_template = (DEPLOY_DIR / "keycloak-local.env.template").read_text(encoding="utf-8")
    service_template = (DEPLOY_DIR / "keycloak.service.template").read_text(encoding="utf-8")

    assert "KC_DB=postgres" in env_template
    assert "keycloak_local_hml" in env_template
    assert "KC_HTTP_ENABLED=false" in env_template
    assert "KC_HTTP_HOST=127.0.0.1" in env_template
    assert "KC_HTTPS_PORT=8443" in env_template
    assert "KC_HOSTNAME=https://localhost:8443" in env_template
    assert "KC_HTTP_MANAGEMENT_HOST=127.0.0.1" in env_template
    assert "KCRAW_DB_PASSWORD=<" in env_template
    assert "KCRAW_HTTPS_KEY_STORE_PASSWORD=<" in env_template
    assert "APP32_MCP_HTTP_ENABLE_OAUTH" not in env_template
    assert "EnvironmentFile=/etc/gestao-versus/keycloak.env" in service_template
    assert "start --optimized" in service_template


def test_realm_template_is_secretless_and_preserves_oauth_mcp_contract() -> None:
    realm_template = json.loads((DEPLOY_DIR / "realm-template.json").read_text(encoding="utf-8"))

    assert realm_template["realm"] == "app32-local"
    assert realm_template["sslRequired"] == "all"
    assert '"secret":' not in json.dumps(realm_template, separators=(",", ":")).lower()
    client = next(client for client in realm_template["clients"] if client["clientId"] == "app32-mcp-local")
    assert client["publicClient"] is True
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert {"mcp:access", "mcp:user", "mcp-resource"}.issubset(client["defaultClientScopes"])
    scopes = {scope["name"]: scope for scope in realm_template["clientScopes"]}
    assert {"mcp:access", "mcp:user", "mcp:admin", "mcp:analytics", "mcp:ops", "mcp-resource"}.issubset(scopes)
    mapper = scopes["mcp-resource"]["protocolMappers"][0]
    assert mapper["config"]["included.custom.audience"] == "app32-mcp-resource"
    subject_mapper = next(mapper for mapper in scopes["mcp-resource"]["protocolMappers"] if mapper["protocolMapper"] == "oidc-sub-mapper")
    assert subject_mapper["config"]["access.token.claim"] == "true"
    assert subject_mapper["config"]["lightweight.claim"] == "true"
    service_client = next(client for client in realm_template["clients"] if client["clientId"] == "app32-mcp-service-smoke")
    assert service_client["publicClient"] is False
    assert service_client["serviceAccountsEnabled"] is True
    assert "secret" not in service_client


def test_configr_compose_keeps_keycloak_isolated_and_loopback_only() -> None:
    configr_dir = DEPLOY_DIR / "configr"
    compose = (configr_dir / "compose.yml").read_text(encoding="utf-8")
    dockerfile = (configr_dir / "Dockerfile").read_text(encoding="utf-8")
    env_template = (configr_dir / "keycloak.env.template").read_text(encoding="utf-8")

    assert "quay.io/keycloak/keycloak:26.7.3" in dockerfile
    assert "postgres:16.10-alpine" in compose
    assert '"127.0.0.1:8080:8080"' in compose
    assert "--optimized" in compose
    assert "../secure/keycloak.env" in compose
    assert "keycloak_postgres_data" in compose
    assert "REPLACE_WITH_RANDOM_DATABASE_PASSWORD" in env_template
    assert "REPLACE_WITH_RANDOM_BOOTSTRAP_PASSWORD" in env_template
    assert "APP32_MCP_HTTP_ENABLE_OAUTH" not in compose
    assert "APP32_MCP_HTTP_ENABLE_OAUTH" not in env_template


def test_configr_image_contains_the_versioned_versus_login_theme() -> None:
    configr_dir = DEPLOY_DIR / "configr"
    dockerfile = (configr_dir / "Dockerfile").read_text(encoding="utf-8")
    theme_dir = configr_dir / "themes" / "versus" / "login"

    assert "COPY themes/versus /opt/keycloak/themes/versus" in dockerfile
    properties = (theme_dir / "theme.properties").read_text(encoding="utf-8")
    stylesheet = (theme_dir / "resources" / "css" / "versus.css").read_text(encoding="utf-8")
    assert "parent=keycloak.v2" in properties
    assert "styles=css/versus-v3.css" in properties
    assert "#kc-header-wrapper" in stylesheet
    assert ".pf-v5-c-login__container" in stylesheet
    assert "@media (max-width:900px)" in stylesheet
    assert (theme_dir / "resources" / "img" / "versus-logo-light.png").is_file()
    messages = (theme_dir / "messages" / "messages_pt_BR.properties").read_text(encoding="utf-8")
    assert "loginTitle=Entrar na sua conta" in messages