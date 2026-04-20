# Auditoria Sapiens WhatsApp Empresas — Passo 1/4: entrypoints

## Objetivo
Mapear os arquivos e pontos de entrada envolvidos no recebimento de mensagens Sapiens por WhatsApp/Instagram e no encaminhamento para a camada de menu/agente com `company_id` resolvido.

## Entry points HTTP

| Canal | URL pública | Blueprint/Função | Observação |
|---|---|---|---|
| WhatsApp | `/webhook/whatsapp` | `api.webhooks.whatsapp_webhook.whatsapp_webhook_bp` / `handle_whatsapp` | Recebe JSON, form-urlencoded e multipart, valida token opcional e despacha em thread. |
| Instagram | `/webhook/instagram` | `api.webhooks.whatsapp_webhook.whatsapp_webhook_bp` / `handle_instagram` | Recebe payload simples `{sender_id, message}` e processa síncrono. |

## Registro Flask

- `app32/app.py::register_blueprints` importa `api.webhooks.whatsapp_webhook.whatsapp_webhook_bp`.
- O blueprint é registrado com `url_prefix='/webhook'`.
- O middleware CSRF/autenticação libera prefixos `/webhook/` para integrações externas.

## Arquivo central de orquestração do webhook

- `app32/api/webhooks/whatsapp_webhook.py`
  - `_load_whatsapp_request_payload`: normaliza corpo JSON/form/multipart.
  - `_extract_whatsapp_message`: extrai contato, texto e metadados do provedor.
  - `handle_whatsapp`: entrypoint HTTP de WhatsApp e disparo do processamento.
  - `process_whatsapp_message`: resolve usuário, empresa, contexto e executa menu/agente.
  - `handle_instagram`: fluxo análogo para Instagram.

## Dependências críticas mapeadas

| Responsabilidade | Módulo/Função |
|---|---|
| Identificar usuário por canal/contato | `src.intelligence.identity.resolve_user_identity(contact, channel)` |
| Resolver empresa tenant-safe | `src.intelligence.identity.get_best_company_id(user)` |
| Interceptar menu operacional | `src.intelligence.menu_engine.handle_menu_message(...)` |
| Executar agente com contexto | `src.intelligence.execution.run_agent_with_context(...)` |
| Capturar uso de workflow | `src.intelligence.execution._capture_workflow_usage_from_execution(...)` |
| Enviar resposta WhatsApp | `services.whatsapp_service.whatsapp_service.send_message(...)` |
| Enviar resposta Instagram | `services.instagram_service.instagram_service.send_message(...)` |
| Persistir mensagens | `models.agent_message.AgentMessage` |

## Ordem operacional atual

1. Requisição entra em `/webhook/whatsapp` ou `/webhook/instagram`.
2. O payload é normalizado e o contato/canal é extraído.
3. O sistema chama `resolve_user_identity(contato, canal)`.
4. Com usuário resolvido, chama `get_best_company_id(user)`.
5. Se não houver usuário ou empresa, o fluxo encerra sem fallback cross-tenant.
6. Com `company_id`, grava mensagem de entrada e tenta menu operacional.
7. Se o menu não tratar, executa o agente com `company_id`, `user_id`, `channel` e `thread_id`.
8. Grava mensagem de saída e envia resposta ao canal.

## Guardrails confirmados neste passo

- `company_id` é resolvido antes da execução do menu/agente.
- Não foi identificado fallback para `Company.query.first()` no fluxo WhatsApp/Instagram.
- O webhook externo permanece isolado em prefixo `/webhook/`, sem exigir sessão web.

## Próximos passos

- Passo 2: rastrear e formalizar o contrato de identificação de usuário por canal.
- Passo 3: rastrear e formalizar a resolução de empresas vinculadas.
- Passo 4: consolidar lacunas e proposta mínima de evolução.


## Passo 2/4 — Identificação de usuário por canal

### Contrato operacional

- A identificação deve ser iniciada sempre pelo par `(identifier, channel)` recebido do webhook.
- WhatsApp usa normalização de telefone e variantes com/sem DDI `55`, máscara e nono dígito.
- Instagram usa normalização de handle, URL de perfil e variações com/sem `@`.
- Email usa lower-case e trim.
- Telegram usa trim simples do identificador.
- Apenas usuários ativos são elegíveis.
- O rastro seguro fica em `IdentityResolutionTrace`, sem transportar objeto `User` e sem decidir `company_id`.

### Pontos de rastreabilidade implementados

- `src.intelligence.identity.build_identity_resolution_trace(identifier, channel, user)` monta o rastro sem consulta adicional.
- `src.intelligence.identity.resolve_user_identity_with_trace(identifier, channel)` resolve e retorna `(user, trace)` para novos consumidores.
- `api.webhooks.whatsapp_webhook.process_whatsapp_message` registra `WHATSAPP IDENTITY TRACE` antes de resolver empresa.
- `api.webhooks.whatsapp_webhook.handle_instagram` registra `INSTAGRAM IDENTITY TRACE` antes de resolver empresa.

### Saída segura para logs

`trace.to_safe_dict()` registra canal, identificador normalizado, estratégia, quantidade de variantes, `user_id`, status de match e motivo. O identificador bruto não é exposto no dicionário seguro.
