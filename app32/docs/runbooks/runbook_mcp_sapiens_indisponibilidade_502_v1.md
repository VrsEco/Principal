# Runbook — MCP Sapiens indisponível com 502

**Classe documental:** Runbook  
**Escopo:** MCP remoto APP32/Sapiens, surfaces `/mcp/user`, `/mcp/admin`, `/mcp/analytics`, `/mcp/ops`  
**Status:** v1 — mitigação operacional e diagnóstico

---

## 1. Sintoma

O endpoint MCP retorna `502 Bad Gateway`, enquanto a aplicação web principal segue saudável.

Exemplo:

```text
GET https://app.gestaoversus.com.br/mcp/healthz -> 502
GET https://app.gestaoversus.com.br/ -> 302 /login
```

Leitura:

- falha isolada do processo MCP;
- Nginx/proxy está vivo;
- app web/uWSGI pode estar saudável;
- o monitoramento apenas da página principal não detecta a falha.

---

## 2. Diagnóstico rápido

Executar:

```powershell
curl.exe -i https://app.gestaoversus.com.br/mcp/healthz
curl.exe -I https://app.gestaoversus.com.br/
```

Interpretação:

| Resultado | Interpretação |
|---|---|
| `/mcp/healthz` 200 | MCP saudável |
| `/mcp/healthz` 401/403 em surface autenticada | autenticação/token |
| `/mcp/healthz` 502 | processo MCP indisponível |
| `/` 302/login | app web principal saudável |

---

## 3. Mitigação imediata

Reiniciar apenas o serviço MCP, sem deploy completo.

Comando operacional canônico:

```powershell
ssh app@servidor
cd /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32
scripts/manage_mcp_http.sh restart
```

Atalho operacional legado, quando disponível na estação de engenharia:

```powershell
python C:\tmp\gv_restart_mcp_consultive.py
```

Após o restart, validar:

```powershell
curl.exe -i https://app.gestaoversus.com.br/mcp/healthz
```

Resposta esperada:

```json
{
  "ok": true,
  "transport": "streamable-http",
  "surfaces": {
    "user": "/mcp/user",
    "admin": "/mcp/admin",
    "analytics": "/mcp/analytics",
    "ops": "/mcp/ops"
  }
}
```

---

## 3.1 Comandos do gerenciador MCP

O script canônico é:

```text
app32/scripts/manage_mcp_http.sh
```

Comandos:

```bash
scripts/manage_mcp_http.sh status
scripts/manage_mcp_http.sh health
scripts/manage_mcp_http.sh restart
scripts/manage_mcp_http.sh stop
scripts/manage_mcp_http.sh start
```

Propriedades esperadas:

- restart idempotente;
- lock em `tmp/mcp_http.lock`;
- PID em `tmp/mcp_http.pid`;
- health local em `http://127.0.0.1:8101/healthz`;
- health público em `https://app.gestaoversus.com.br/mcp/healthz`;
- logs em `logs/mcp_http_stdout.log` e `logs/mcp_http_stderr.log`.

---

## 4. Causa provável

Quando o padrão observado for:

```text
initialize lento/time out -> 502 contínuo
```

a hipótese principal é:

- processo Uvicorn/FastMCP travado ou encerrado;
- worker MCP morto sem restart automático;
- exceção fatal em bootstrap/tool;
- OOM ou esgotamento de recurso;
- restart/deploy que não religou MCP adequadamente.

---

## 5. Correção estrutural necessária

O MCP precisa de observabilidade própria, independente do app web.

Requisitos:

1. health check público em `/mcp/healthz`;
2. alerta quando `/mcp/healthz` retornar `502`, timeout ou não-`200`;
3. restart automático do processo MCP;
4. smoke pós-deploy específico para MCP;
5. log separado do processo MCP;
6. validação mínima de `initialize` e `tools/list` após restart/deploy.

---

## 6. Diferença entre 502 e 401

| Código | Significado | Ação |
|---|---|---|
| 502 | processo MCP indisponível | reiniciar MCP e checar logs |
| 401 | token ausente/inválido/revogado | renovar ou corrigir token |
| 403 | token válido, mas sem surface/permissão | revisar profile/surface |
| 500 | erro da aplicação/tool | checar traceback |

---

## 7. Bug secundário conhecido

Tools de descoberta de contexto, como `list_my_companies` e `bootstrap_session_context`, não devem exigir `company_id` prévio.

Regra:

> Tool de descoberta pessoal deve exigir `user_id`, não `company_id`.

O `company_id` continua obrigatório para tools operacionais de empresa.
