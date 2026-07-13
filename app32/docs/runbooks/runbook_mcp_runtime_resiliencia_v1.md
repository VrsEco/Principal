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
