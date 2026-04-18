# APP32 MCP remoto via HTTPS para claude.ai

## Objetivo

Expor o runtime MCP do APP32 por HTTPS, com segregação por surface:

- `https://app.gestaoversus.com.br/mcp/user`
- `https://app.gestaoversus.com.br/mcp/admin`
- `https://app.gestaoversus.com.br/mcp/analytics`

Sem quebrar o modo atual em `stdio` usado pelo Claude Code.

## Arquitetura entregue

### Runtime preservado

O servidor legado `stdio` continua intacto:

- `C:\GestaoVersus\app32\app32\src\core\mcp_server.py`

As surfaces continuam sendo construídas pelo registry canônico:

- `C:\GestaoVersus\app32\app32\src\core\mcp_surface_registry.py`

### Nova camada HTTP remota

Novo entrypoint HTTP:

- `C:\GestaoVersus\app32\app32\src\core\mcp_http_server.py`

Responsabilidades:

- monta três apps MCP remotas via **Streamable HTTP**
- reaproveita os builders existentes:
  - `build_user_mcp_server`
  - `build_admin_mcp_server`
  - `build_analytics_mcp_server`
- publica rotas separadas por surface
- adiciona `healthz`

### Autenticação e contexto por request

Novo módulo:

- `C:\GestaoVersus\app32\app32\src\core\mcp_http_auth.py`

Responsabilidades:

- valida Bearer token do MVP interno
- resolve `user_id`, `company_id`, `fallback_role` por request
- injeta contexto HTTP em `ContextVar`
- prepara a base para futura evolução OAuth

### Runtime de tool context adaptado

Arquivo ajustado:

- `C:\GestaoVersus\app32\app32\src\core\mcp_runtime.py`

Agora o runtime aceita:

- contexto `stdio` por env vars
- contexto HTTP por `ContextVar` de request

Isso preserva compatibilidade retroativa com o Claude Code local.

## Modo de autenticação

## MVP interno funcional

Autenticação por Bearer token com mapeamento server-side:

- `APP32_MCP_HTTP_TOKEN`
ou
- `APP32_MCP_HTTP_TOKENS_JSON`

### Exemplo recomendado

```bash
export APP32_MCP_HTTP_TOKENS_JSON='{
  "TOKEN_INTERNO_EXEMPLO": {
    "user_id": 3,
    "company_id": 9,
    "fallback_role": "colaborador",
    "allowed_surfaces": ["user", "admin", "analytics"],
    "scopes": ["mcp:access"],
    "client_id": "app32-9-3"
  }
}'
```

### Overrides controlados

Por segurança, headers/query params só sobrescrevem contexto quando:

- `APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE=1`

Headers suportados:

- `X-APP32-User-Id`
- `X-APP32-Company-Id`
- `X-APP32-Fallback-Role`
- `X-APP32-Thread-Id`

Query params equivalentes:

- `user_id`
- `company_id`
- `fallback_role`
- `thread_id`

## Preparação OAuth

O código já foi estruturado para futura evolução OAuth:

- `build_auth_settings(...)`
- `App32OAuthPreparation`
- `App32OAuthAuthorizationServerProvider`

Estado atual:

- **OAuth ainda não está completo**
- a classe/provider foi deixada como contrato explícito
- o MVP seguro para testes internos usa Bearer token

### Variáveis previstas para a próxima fase

- `APP32_MCP_HTTP_ENABLE_OAUTH`
- `APP32_MCP_OAUTH_ISSUER_URL`
- `APP32_MCP_OAUTH_RESOURCE_SERVER_URL`
- `APP32_MCP_OAUTH_DOCS_URL`

## Script de inicialização

- `C:\GestaoVersus\app32\app32\scripts\start_mcp_http.sh`

### Função

- carrega `.env`
- prepara `PYTHONPATH`
- publica `APP32_MCP_HTTP_HOST`, `APP32_MCP_HTTP_PORT`, `APP32_MCP_PUBLIC_BASE_URL`
- executa `src/core/mcp_http_server.py`

## Serviço operacional

Arquivo:

- `C:\GestaoVersus\app32\app32\deploy\systemd\app32-mcp-http.service`

### Instalação sugerida no servidor

```bash
sudo cp /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/deploy/systemd/app32-mcp-http.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable app32-mcp-http
sudo systemctl restart app32-mcp-http
sudo systemctl status app32-mcp-http
```

### Logs

```bash
tail -f /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/logs/mcp_http_stdout.log
tail -f /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/logs/mcp_http_stderr.log
```

## Reverse proxy HTTPS

Snippet sugerido:

- `C:\GestaoVersus\app32\app32\deploy\nginx\app32-mcp-http.conf`

Fluxo esperado:

- Nginx público recebe HTTPS em `app.gestaoversus.com.br`
- proxy reverso encaminha para `127.0.0.1:8101`
- MCP HTTP fica acessível para a nuvem da Anthropic

## URL final esperada

- `https://app.gestaoversus.com.br/mcp/user`
- `https://app.gestaoversus.com.br/mcp/admin`
- `https://app.gestaoversus.com.br/mcp/analytics`
- `https://app.gestaoversus.com.br/healthz` **não** é deste serviço
- `https://app.gestaoversus.com.br/mcp/healthz` via proxy do snippet sugerido

## Comandos de execução no servidor

### Execução manual

```bash
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32
chmod +x scripts/start_mcp_http.sh
APP32_MCP_PUBLIC_BASE_URL="https://app.gestaoversus.com.br" \
APP32_MCP_HTTP_PORT="8101" \
scripts/start_mcp_http.sh
```

### Smoke de health

```bash
curl -s http://127.0.0.1:8101/healthz
```

## Curl de validação

### Sem autenticação deve negar

```bash
curl -i https://app.gestaoversus.com.br/mcp/user
```

Resposta esperada:

- `401 unauthorized`

### Com autenticação MVP

```bash
curl -i https://app.gestaoversus.com.br/mcp/user \
  -H "Authorization: Bearer TOKEN_INTERNO_EXEMPLO"
```

### Com override controlado

```bash
curl -i "https://app.gestaoversus.com.br/mcp/user?thread_id=teste-claude" \
  -H "Authorization: Bearer TOKEN_INTERNO_EXEMPLO" \
  -H "X-APP32-User-Id: 3" \
  -H "X-APP32-Company-Id: 9"
```

## Como cadastrar no claude.ai

### Situação atual

O **MVP técnico entregue** já coloca o APP32 em HTTP/HTTPS remoto e protegido.

Porém, para **custom connector do claude.ai**, o desenho alvo correto é **OAuth**.

### O que já é possível agora

- homologar reachability pública
- validar segregação de surfaces
- validar proteção por autenticação
- validar tool listing e runtime HTTP

### O que ainda falta para o claude.ai final

Concluir a camada OAuth:

1. endpoint de autorização
2. endpoint de token
3. associação do usuário Claude ao usuário APP32 autenticado
4. persistência/revogação de tokens
5. consentimento e escopos por surface/tenant

## Riscos e recomendações

- não publicar token em query string em produção real
- preferir token por header somente
- manter `APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE=0` em produção
- habilitar override apenas em smoke controlado
- para claude.ai, concluir OAuth antes de uso amplo
- restringir firewall para IPs da Anthropic se aplicável

## Plano exato para fechar OAuth corretamente

1. criar storage persistente de clientes OAuth do MCP
2. criar storage persistente de authorization codes
3. criar storage persistente de access/refresh tokens
4. criar vínculo entre usuário APP32 autenticado e integração MCP remota
5. implementar `App32OAuthAuthorizationServerProvider`
6. expor endpoints de auth no mesmo domínio MCP
7. validar callback da Anthropic no fluxo de connector web
8. testar consentimento e revogação

## Smoke já executado nesta entrega

- parser/import do novo servidor HTTP
- criação das mounts:
  - `/mcp/user`
  - `/mcp/admin`
  - `/mcp/analytics`
- testes unitários focados em:
  - auth MVP
  - resolução de contexto HTTP
  - montagem da app HTTP
  - compatibilidade do runtime com contexto remoto
