# SPEC — Captação pública de leads dos sites da Versus (v1)

Atividades: AA.J.26.24 (mensuração e origem dos contatos) e etapa 2 do projeto AA.J.187 (captura multicanal e funil comercial). Empresa AA - Versus (company_id 9).

## Contrato

`POST https://<host-app32>/public/leads` — `Content-Type: application/json`, corpo até 4 KB, somente HTTPS.

```json
{
  "source": "site-performance-hub",
  "nome": "opcional, até 80",
  "assunto": "obrigatório, da lista fixa",
  "relato": "opcional, até 600",
  "consent": true,
  "origin": {"utm_source":"","utm_medium":"","utm_campaign":"","utm_content":"","utm_term":"","referrer":"https://host/x","landing":"/caminho"},
  "page": "/caminho",
  "ts": "2026-10-15T12:00:00Z"
}
```

| Código | Significado |
|---|---|
| 202 `{"lead_id"}` | lead gravado |
| 200 `{"lead_id"}` | repetição na janela de dedupe (devolve o lead original) |
| 400 | validação, `source` desconhecido, `consent` ≠ `true`, campo fora do esquema, não-HTTPS |
| 403 | `Origin` fora da lista de domínios |
| 413 | corpo acima de 4 KB |
| 429 | limite de taxa (por IP ou por source) |
| 503 | endpoint não configurado ou falha temporária de gravação |

Regras:
- `source` é identificador público, não credencial. O servidor o mapeia para `company_id` (e projeto/usuário da tarefa) via `LEADS_SOURCES_JSON`; `company_id` no corpo é rejeitado.
- Esquema estrito: qualquer campo extra é 400. `assunto` precisa estar em `assuntos` do source (padrão: `orcamento, duvida, parceria, suporte, outro` — **confirmar a lista real do site**).
- CPF, CNPJ, número de cartão e trechos `senha:`/`token:` no nome ou relato são substituídos por `[removido]`; o lead é gravado mesmo assim.
- Dedupe: hash de (source, nome, assunto, relato, UTMs, host do referrer), sem diferenciar maiúsculas, na janela `LEADS_DEDUPE_WINDOW_SECONDS` (600 s). O IP não entra no hash.
- LGPD: grava só com `consent: true`; guarda `consent_at` e `privacy_policy_version`; IP somente como HMAC-SHA256 (`ip_hash`); exclusão sob solicitação com `SiteLeadService.erase(company_id, lead_id)` (anula nome, relato, IP e o texto da tarefa; mantém UTM/assunto para contagem agregada).
- Destino: tabela `site_leads` (status `novo`; índices por empresa, data e canal/campanha) e, se `project_code` + `task_user_id` estiverem no source, uma tarefa "Lead novo: <assunto>" no projeto. Falha na tarefa não impede o lead.
- Não lê nem altera chats, contatos ou webhook Z-API do WhatsApp.

## Configuração (variáveis de ambiente; nada fixo no código)

| Variável | Uso |
|---|---|
| `LEADS_ALLOWED_ORIGINS` | domínios do site, ex.: `https://site1.com.br,https://www.site1.com.br` |
| `LEADS_SOURCES_JSON` | `{"site-performance-hub":{"company_id":9,"project_code":"AA.J.187","task_user_id":<id>,"assuntos":[...]}}` |
| `LEADS_PRIVACY_POLICY_VERSION` | versão vigente da política (ex.: `2026-10`) |
| `LEADS_IP_HASH_SALT` | sal do hash de IP (padrão: `SECRET_KEY`) |
| `LEADS_RATE_LIMIT_IP` / `LEADS_RATE_LIMIT_SOURCE` | req/min (padrão 10 / 120) |
| `LEADS_REQUIRE_HTTPS` | padrão `true` |

Sem `LEADS_ALLOWED_ORIGINS`, `LEADS_SOURCES_JSON` e `LEADS_PRIVACY_POLICY_VERSION`, o endpoint responde 503.

**Domínios autorizados:** a preencher pelo dono (nenhum registrado nesta entrega).

## Conexão no site (`assets/config.js`)

```js
leadEndpoint: "https://<host-app32>/public/leads",
leadSource: "site-performance-hub",
```

O formulário deve: marcar o consentimento (enviar `consent: true` só se marcado), enviar `fetch(..., {method:"POST", keepalive:true, headers:{"Content-Type":"application/json"}, body})` sem token e sem esperar a resposta, e abrir o WhatsApp após 4 s (ou ao concluir) mesmo se falhar. Não enviar `credentials`.

## Observabilidade

Logs `site_lead event=<created|duplicate|redacted|rejected_*|failed_persist>` sem nome nem relato. Contadores em memória por processo (`services.site_lead_service.counters()`); volume por canal sai de `site_leads` (`GROUP BY utm_source, utm_medium, utm_campaign`).

## Limitações conhecidas

- O rate limit reutiliza `utils.security.consume_rate_limit`, que é em memória por processo: com vários workers o limite efetivo é por worker.
- Não há tela do dono além da tarefa no projeto; relatório por canal é consulta SQL por ora.
- Migração `20261015_1000` cria `site_leads` (revisão anterior `20260606_1600`); não aplicada em nenhum ambiente.
