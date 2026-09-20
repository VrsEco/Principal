# Runbook v1 — Resiliência do Runtime MCP HTTP

**Classe documental:** Runbook  
**Status:** oficial  
**Escopo:** runtime MCP HTTP remoto do APP32 em produção  
**Serviço:** `https://app.gestaoversus.com.br/mcp/healthz`

---

## 1. Decisão operacional

O MCP HTTP deve ser tratado como serviço separado da aplicação web.

O site pode estar saudável em `/healthz` enquanto o runtime MCP está fora em `/mcp/healthz`.

---

## 2. Scripts canônicos

Gerenciador idempotente:

```bash
scripts/manage_mcp_http.sh status
scripts/manage_mcp_http.sh health
scripts/manage_mcp_http.sh restart
scripts/manage_mcp_http.sh stop
scripts/manage_mcp_http.sh start
```

Monitor leve:

```bash
scripts/monitor_mcp_http.sh
```

O monitor:

- valida health local e público;
- acumula falhas consecutivas;
- só reinicia após threshold;
- usa o manager idempotente;
- registra logs em `logs/mcp_http_monitor.log`.

---

## 3. Cron recomendado

Exemplo em produção:

```cron
*/3 * * * * cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32 && bash scripts/monitor_mcp_http.sh >> logs/mcp_http_monitor.log 2>&1
```

Threshold padrão:

```bash
APP32_MCP_MONITOR_FAIL_THRESHOLD=3
```

Isso evita restart por falha isolada.

---

## 4. Ação administrativa no APP32

Tela:

```text
Sistema → IA Corporativa → Configurações de Canais → CLI/IA MCP
```

Ação:

```text
Reparar runtime MCP
```

Rotas:

```text
GET  /api/integrations/mcp-runtime/status
POST /api/integrations/mcp-runtime/repair
```

Regras:

- somente usuário com permissão de administração de integrações;
- não altera token;
- não altera `company_id`;
- apenas consulta/reinicia o processo MCP HTTP.

---

## 5. Diagnóstico rápido

Se o MCP cair:

1. testar `/healthz` web;
2. testar `/mcp/healthz`;
3. se web OK e MCP 502, usar `scripts/manage_mcp_http.sh restart`;
4. validar `/mcp/healthz`;
5. verificar `logs/mcp_http_stderr.log` e `logs/mcp_http_monitor.log`.

---

## 6. Critério de sucesso

O runtime está saudável quando:

- `scripts/manage_mcp_http.sh status` mostra `local_health=ok`;
- `scripts/manage_mcp_http.sh status` mostra `public_health=ok`;
- `/mcp/healthz` retorna `200`;
- o cliente MCP conecta via `streamable-http`.

---

## 7. Recuperação no cliente MCP

Ao receber HTTP `502`, `503` ou `504`:

1. confirmar que a operação interrompida era somente leitura e idempotente;
2. aguardar 1 segundo e reabrir a sessão `streamable-http`;
3. restaurar a empresa ativa e o harness anterior;
4. repetir a leitura; se necessário, aguardar 2 e depois 4 segundos;
5. interromper após três tentativas e escalar para Engenharia.

Não renovar/revogar token por esse sintoma e não migrar para SSE. Se a operação era mutação, consultar o estado do APP32 antes de qualquer nova escrita; nunca repetir automaticamente.

O health público informa a política em `transient_recovery`. Durante restart controlado, o servidor pode responder `503` com `Retry-After: 2`; isso é recuperável e não representa perda de tenant ou autorização.

## 8. Descoberta sem tool exata

Se `resolve_app32_operation_tool` retornar `capability_not_available`, encerrar sem atualizar `tools/list`. Em `specialist_discovery`, atualizar a lista apenas uma vez e executar somente uma tool que responda diretamente ao pedido. Não usar ferramenta adjacente para produzir uma resposta aproximada.

Para consultas de conexões/métricas estratégicas no Squad Cliente, o fluxo esperado é `resolve_app32_operation_tool` -> `get_strategic_connection_metrics` no harness Coordenador. Não trocar para `analytics`. Se o preflight efetivo não confirmar catálogo, overlay, tenant e RBAC, tratar como indisponibilidade e não tentar grafo ou resumo como fallback.

## 9. Falha de trilha durável — incremento local P0

`AIExecutionAuditPersistenceError` bloqueia a mutação antes do callback quando o evento de autorização não foi persistido. Verificar conexão PostgreSQL, contexto Flask, tabela/indexes `ai_mcp_audit_events` e logs redigidos. Não desativar o requisito nem reenviar flags de confirmação.

A aprovação pode ter sido consumida antes da falha da trilha; consultar o registro e solicitar nova aprovação humana para o payload exato, sem replay automático. Leitura mantém emissão best-effort. Aplicar `20260916_1000` antes de promover o writer v2; criação de tabela em runtime foi removida no incremento local. Não habilitar DDL no usuário operacional para contornar schema ausente.

Validar colunas OAuth/policy e índices `company_id` após migration, tanto em banco novo quanto em banco com tabela legada. A trilha usa conexão/transação própria; falha nela não deve commitar nem desfazer trabalho pendente na sessão da tool. Downgrade é preservador de evidências e não remove schema aditivo.

### Laboratório PostgreSQL do P0

Executar `app32/scripts/qa/run_audit_p0_postgresql_lab.py --pg-bin <diretório-portátil>`: cria cluster novo com SCRAM, porta dinâmica e somente loopback, usa dados sintéticos e encerra o listener em `finally`. Não instala serviço e não lê `DATABASE_URL` do APP32. Binários/dados/logs ficam no diretório ignorado `app32/tmp/audit_p0_pg_lab`; não devem entrar em commits.

A suíte opt-in aceita somente `APP32_AUDIT_P0_TEST_URL` loopback e database com prefixo `app32_audit_p0_`. Schemas gerados são removidos ao término. Verificar `result.json` com `suite_exit_code=0` e `listener_stopped=true`. No Windows, o runner usa arquivos de log para evitar pipe retido pelos filhos de `pg_ctl`. Não executar contra banco real de cliente.

Para validar o caminho real de implantação, executar o runner com `--deployment-replay`: ele cria outro banco sintético, registra apenas a revisão predecessora `20260913_1500`, chama `flask db upgrade` com os bootstraps desligados e exige head `20260916_1000` mais as colunas estruturadas. `--full-chain` é diagnóstico de dívida histórica e hoje deve revelar a ausência de baseline para `companies`; não usar essa falha anterior ao P0 como motivo para editar migrations já aplicadas.

A mesma suíte valida JWT RS256 real sem rede externa. O token deve ter issuer/audience/client/scopes contratados, `issuer/sub` provisionado e grant ativo para o `company_id` pedido. Confirmar também as negativas de audience incompatível, tenant sem grant e principal revogado, além do evento estruturado em `ai_mcp_audit_events`. Esse ensaio não substitui o IdP público: para o rollout, repetir com JWKS HTTPS, redirect do cliente real e revogação no provedor.

Antes de abrir a rota piloto, executar `python scripts/qa/check_oauth_mcp_rollout_readiness.py --mode pilot` a partir de `app32/`. Saída `ready=false` ou exit code `2` bloqueia a promoção. O preflight é read-only e deliberadamente não aceita token em argumento. Para ampliar a coorte existente, usar `--mode cohort`; nunca converter o piloto em corte global apenas para fazer o gate passar.

Depois de o gate estático passar, repetir com `--live`. Exit code `3` significa falha ou drift em discovery, JWKS ou metadata do resource server. Não usar `--insecure`, não ignorar CA e não enviar access token nesse diagnóstico; a prova live é exclusivamente de metadados públicos e TLS.

Baseline público confirmado em 17/09/2026: issuer `https://id.gestaoversus.com.br/realms/app32`, JWKS no endpoint Keycloak do realm e resource piloto `https://app.gestaoversus.com.br/mcp/pilot/user`. Sem bearer, aceitar somente `401 invalid_token` com `resource_metadata` canônico. `200`, fallback legado ou metadata divergente interrompem o rollout.

### Smoke autenticado no Codex CLI

1. executar `codex mcp login --scopes mcp:access,mcp:user --oauth-client-registration auto mcp-versus` e concluir o login apenas no navegador;
2. confirmar que o CLI informa sucesso sem copiar senha, authorization code, access token ou refresh token para logs/evidências;
3. abrir sessão read-only e chamar somente `list_user_app32_capabilities`;
4. aprovar apenas a chamada corrente, nunca a opção permanente durante homologação;
5. registrar somente resumo, domínios e scopes — não o bearer nem o payload de identidade;
6. encerrar a sessão do CLI após a evidência.

Baseline autenticado: 4 capabilities em 3 domínios, com scope `mcp_user`. Divergência, pedido de mutação ou ausência de aprovação humana interrompe o smoke. Esta prova valida o endpoint publicado, não substitui deploy/migration do P0.

### Smoke OAuth analytics controlado

Para a coorte financeira, usar exclusivamente
`https://app.gestaoversus.com.br/mcp/pilot/analytics/` e um cliente OAuth com
o scope `mcp:analytics`. Antes de consultar dado de cliente, confirmar que
`tools/list` e `list_analytics_app32_capabilities` apresentam exatamente as
quatro leituras permitidas: cadastros-base, regras de automação, regras de
classificação e lançamentos financeiros. A lista não pode conter mutação.

Executar um positivo somente-leitura para a empresa concedida e um negativo
para outro `company_id`; este deve falhar por ausência de grant. Divergência
entre manifesto e tools registradas, escopo diferente de `mcp:analytics` ou
qualquer retorno de dados de outro tenant interrompe o rollout. Não registrar
token, código OAuth nem valores financeiros na evidência.
