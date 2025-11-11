# TestSprite AI Testing Report (MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** app31
- **Date:** 2025-11-10
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

### Requirement: Authentication Endpoints
- **Description:** Endpoints `/auth/login`, `/auth/logout`, `/auth/register`, `/auth/change-password` devem autenticar usuários e cumprir o padrão de resposta JSON definido em `API_STANDARDS.md`.

#### Test TC001
- **Test Name:** authentication login endpoint
- **Test Code:** [TC001_authentication_login_endpoint.py](./TC001_authentication_login_endpoint.py)
- **Test Error:** Read timeout ao chamar `POST /auth/login` via túnel Testsprite (`HTTPConnectionPool(host='tun.testsprite.com', port=8080)`)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/98e07b85-d99e-43d5-b2a8-b79d2b9cab65
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** O endpoint não respondeu dentro do tempo limite. Suspeita: servidor local não acessível pelo túnel ou handshake HTTPS/CSRF faltando; impede login automatizado e viola requisito de disponibilidade.
---

#### Test TC002
- **Test Name:** authentication logout endpoint
- **Test Code:** [TC002_authentication_logout_endpoint.py](./TC002_authentication_logout_endpoint.py)
- **Test Error:** Read timeout ao chamar `POST /auth/logout`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/be8de84e-abfb-4c22-a942-0439a1c3105b
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Mesmo comportamento do login: sem resposta via túnel. Provável dependência de sessão prévia não criada ou indisponibilidade do endpoint para acesso automatizado.
---

#### Test TC003
- **Test Name:** authentication register endpoint
- **Test Code:** [TC003_authentication_register_endpoint.py](./TC003_authentication_register_endpoint.py)
- **Test Error:** Read timeout ao chamar `POST /auth/register`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/5c6633c4-4c91-4703-aa0a-79a710d4866f
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Endpoint também inacessível no túnel. Necessário validar exposição pública/autenticação exigida para criação via API.
---

#### Test TC004
- **Test Name:** authentication change password endpoint
- **Test Code:** [TC004_authentication_change_password_endpoint.py](./TC004_authentication_change_password_endpoint.py)
- **Test Error:** Read timeout ao chamar `POST /auth/change-password`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/577eb9ef-7bb2-4987-bf44-fa0ab5029a8e
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Sem resposta no túnel. Além da indisponibilidade, endpoints protegidos deveriam retornar JSON 401 se sessão inexistente; teste não recebeu resposta para validar isso.

---

### Requirement: User Logs API
- **Description:** Endpoints `/logs/`, `/logs/stats`, `/logs/entity-activity/<type>/<id>` devem responder em JSON autenticado conforme governança de auditoria.

#### Test TC005
- **Test Name:** user logs list endpoint
- **Test Code:** [TC005_user_logs_list_endpoint.py](./TC005_user_logs_list_endpoint.py)
- **Test Error:** Read timeout em `POST /auth/login` durante preparação; chamada subsequente a `/logs/` não ocorreu
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/4ca14925-893a-4f93-bb33-88752b02b99f
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Teste depende de login que falhou (mesma causa da suíte de autenticação). Sem sessão válida não se consegue validar paginação/JSON do endpoint.
---

#### Test TC006
- **Test Name:** user logs statistics endpoint
- **Test Code:** [TC006_user_logs_statistics_endpoint.py](./TC006_user_logs_statistics_endpoint.py)
- **Test Error:** `JSONDecodeError` ao chamar `GET /logs/stats`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/0d05e7fe-7e00-4aa5-beff-837978597ae2
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Resposta não era JSON (provável HTML da página de login redirecionada). Endpoint precisa retornar `401` com JSON quando não autenticado e validar cabeçalho `Content-Type`.
---

#### Test TC007
- **Test Name:** user logs entity activity endpoint
- **Test Code:** [TC007_user_logs_entity_activity_endpoint.py](./TC007_user_logs_entity_activity_endpoint.py)
- **Test Error:** `AssertionError: Response Content-Type should include 'application/json'`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/1a45586c-2cfa-4e37-8ac2-8a4c16ffe59e
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Endpoint entregou conteúdo sem `application/json` (indicativo de HTML). Ajustar decorators para retorno de JSON mesmo em falha de permissão.

---

### Requirement: Route Audit API
- **Description:** Endpoints administrativos `/route-audit/api/*` devem fornecer relatórios JSON e aceitar habilitação de auto-logging seguindo o padrão de segurança (apenas admin).

#### Test TC008
- **Test Name:** route audit summary endpoint
- **Test Code:** [TC008_route_audit_summary_endpoint.py](./TC008_route_audit_summary_endpoint.py)
- **Test Error:** `AssertionError: 200 response should be JSON`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/3265013f-2031-4640-8e0f-5d6c8021bf4c
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Resposta provavelmente HTML. Falta header JSON ou endpoint redirecionou para login sem status 401 JSON.
---

#### Test TC009
- **Test Name:** route audit routes list endpoint
- **Test Code:** [TC009_route_audit_routes_list_endpoint.py](./TC009_route_audit_routes_list_endpoint.py)
- **Test Error:** `JSONDecodeError` ao processar resposta de `GET /route-audit/api/routes?filter=all`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/aa0920f2-b61d-41c4-a61d-13f4a73988c5
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Conteúdo não JSON (HTML ou mensagem de erro). Necessário garantir resposta JSON, mesmo para erros de autenticação/filtro.
---

#### Test TC010
- **Test Name:** route audit enable auto logging endpoint
- **Test Code:** [TC010_route_audit_enable_auto_logging_endpoint.py](./TC010_route_audit_enable_auto_logging_endpoint.py)
- **Test Error:** Read timeout ao chamar `POST /route-audit/api/entity/project/enable`
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/185162a1-85ba-45d8-ad06-c37037a415b6/cb5d18d3-bbd8-4922-9d1f-c5c9b45dd4e2
- **Status:** ❌ Failed
- **Severity:** HIGH
- **Analysis / Findings:** Sem resposta no túnel. Pode indicar bloqueio CSRF, verificação de referer ou indisponibilidade do serviço.

---

## 3️⃣ Coverage & Matching Metrics

- **0.00%** dos testes passaram

| Requirement              | Total Tests | ✅ Passed | ❌ Failed |
|--------------------------|-------------|-----------|-----------|
| Authentication Endpoints | 4           | 0         | 4         |
| User Logs API            | 3           | 0         | 3         |
| Route Audit API          | 3           | 0         | 3         |

---

## 4️⃣ Key Gaps / Risks
- Todos os endpoints exercitados ficaram inacessíveis via túnel Testsprite (timeouts ou HTML de login). É crítico validar configuração de exposição/rede.
- Respostas de APIs protegidas não seguem o padrão `401 JSON` quando a sessão é inválida, o que quebra governança (`API_STANDARDS.md`).
- Sem testes concluídos: não há evidência automatizada do comportamento das rotas. Priorizar: revisar autenticação via API, adicionar suporte a tokens ou fixture de sessão para testes externos e reexecutar a suíte.
