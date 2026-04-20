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


## Passo 3/4 — Resolução de empresas vinculadas

### Contrato operacional

- A empresa efetiva deve nascer exclusivamente dos vínculos do usuário em `Employee`.
- Vínculos `active` têm prioridade sobre vínculos inativos/legados.
- Quando houver múltiplos vínculos ativos, a seleção atual é determinística por `company_id ASC, employee_id ASC`.
- Admin sem vínculo explícito não recebe fallback para a primeira empresa ativa do banco, pois isso cria risco de tenant crossing.
- A ausência de vínculo encerra o fluxo antes de menu/agente, mantendo `company_id` obrigatório.

### Pontos de rastreabilidade implementados

- `src.intelligence.identity.CompanyResolutionTrace` registra origem da seleção, candidato escolhido e motivo.
- `src.intelligence.identity.get_company_resolution_with_trace(user)` retorna `(company_id, trace)`.
- `src.intelligence.identity.get_best_company_id(user)` passa a reutilizar o contrato rastreável e emitir `SAPIENS COMPANY RESOLUTION TRACE`.
- A resolução não importa nem consulta `Company` diretamente; a fronteira tenant-safe é a vinculação do usuário em `Employee`.

### Lacuna remanescente para evolução posterior

Quando o usuário possuir múltiplas empresas ativas e a intenção não deixar claro o contexto, o canal deve pedir seleção explícita antes da confirmação final. O passo 4 consolida essa proposta mínima.


## Passo 4/4 — Lacunas consolidadas e proposta mínima

### Diagnóstico final

O fluxo Sapiens WhatsApp/Instagram está funcionalmente mapeado e passou a ter rastreabilidade explícita em dois pontos críticos: identificação do usuário por canal e resolução tenant-safe de empresa vinculada. O webhook não deve executar menu, agente ou ação operacional sem `user_id` e `company_id` resolvidos.

### Lacunas consolidadas

| Lacuna | Risco | Proposta mínima |
|---|---|---|
| Usuário com múltiplas empresas ativas | Executar consulta/ação no tenant errado quando a mensagem não explicita a empresa. | Introduzir estado de seleção de empresa por `thread_id` antes da confirmação final. |
| Persistência de contexto de empresa por conversa | Usuário precisa repetir seleção ou o sistema pode depender apenas da seleção determinística. | Persistir contexto curto por canal/thread com expiração e invalidar ao usuário trocar explicitamente de empresa. |
| Observabilidade operacional | Logs existem, mas ainda não há métrica/consulta central para falhas de identidade/empresa. | Criar painel/sinalização para `identity_trace.reason` e `company_trace.reason`. |
| Ambiguidade entre leitura simples e mutação | Canal pode encaminhar ação sensível sem etapa clara de confirmação. | Exigir confirmação explícita quando houver mutação ou impacto financeiro/governança. |

### Proposta mínima de evolução

1. **Resolver usuário** por `(identifier, channel)` e gerar `IdentityResolutionTrace`.
2. **Resolver empresas vinculadas** via `Employee`, gerando `CompanyResolutionTrace`.
3. **Se nenhuma empresa for resolvida**, encerrar com mensagem orientativa e não chamar menu/agente.
4. **Se houver uma única empresa ativa**, seguir automaticamente com `company_id` resolvido.
5. **Se houver múltiplas empresas ativas**, perguntar a empresa antes de executar comandos que dependam de tenant.
6. **Persistir seleção temporária** por `thread_id` + `user_id` + `channel` para reduzir fricção.
7. **Confirmar mutações sensíveis** antes de executar ferramentas administrativas, financeiras ou de governança.
8. **Medir falhas** de identidade/empresa em observabilidade própria para suporte e evolução.

### Critério de aceite para próxima implementação

- Nenhuma resposta operacional sem `company_id` resolvido.
- Nenhum fallback global para empresa ativa do banco.
- Toda seleção automática deve ser explicável via trace.
- Todo usuário multiempresa deve ter caminho claro para escolher/trocar empresa no canal.
- Fluxos de leitura podem ser fluidos; fluxos de mutação sensível exigem confirmação.

### Estado após esta auditoria

- Entry points mapeados e protegidos por testes contratuais.
- Identificação por canal rastreável.
- Resolução de empresa vinculada rastreável e sem fallback cross-tenant.
- Próxima frente recomendada: implementar seleção explícita de empresa por thread para usuários multiempresa.
