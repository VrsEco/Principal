# Playbook — Backlog Técnico do Módulo Multi-tenant de Leilões Imobiliários v1

Status: **RETIRADO em 2026-08-20 — não executar**
Classe documental: Playbook
SPEC de origem: `C:\GestaoVersus\app32\app32\docs\spec\modulo_leiloes_imobiliarios_multi_tenant_v1.md`
Escopo: implementação do módulo `Leilões Imobiliários` no APP32, com GanduInvest como primeiro tenant/piloto

> Playbook histórico. O módulo foi descontinuado antes da entrada em operação e seu código executável foi removido do APP32.

## 1. Decisão operacional

Implementar o antigo app GanduInvest como módulo genérico `real_estate_auctions`, usando o banco atual do APP32, novas tabelas com `company_id`, RBAC, services e MCP compatíveis com a governança existente.

## 2. Fora de escopo

Não incluir neste backlog:

- automações NF-e / SEFAZ;
- preenchimento de formulários Bradesco;
- rotinas bancárias/fiscais satélites;
- automações com credencial externa sensível.

## 3. Ordem técnica recomendada

1. fundação de banco e modelos;
2. services determinísticos;
3. API/UI com tenant e RBAC;
4. anexos/PDF;
5. importação assistida;
6. MCP e capabilities;
7. migração piloto GanduInvest;
8. hardening e release.

---

## Épico 1 — Fundação do domínio e banco

Objetivo: criar o domínio reutilizável, sem acoplamento a GanduInvest.

### Tarefas

1. Criar modelos em `C:\GestaoVersus\app32\app32\models\real_estate_auction.py`.
2. Registrar modelos em `C:\GestaoVersus\app32\app32\models\__init__.py`.
3. Criar migration Alembic em `C:\GestaoVersus\app32\app32\migrations\versions\`.
4. Criar tabelas:
   - `real_estate_auction_properties`
   - `real_estate_auction_events`
   - `real_estate_auction_financial_sheets`
   - `real_estate_auction_due_diligence`
   - `real_estate_auction_attachments`
   - `real_estate_auction_sources`
   - `real_estate_auction_import_jobs`
   - `real_estate_auction_import_job_items`
   - `real_estate_auction_tenant_settings`
5. Garantir `company_id` em todas as tabelas operacionais.
6. Criar índices mínimos:
   - `company_id, status`
   - `company_id, triage_status`
   - `company_id, auction_datetime`
   - `company_id, property_id`
7. Criar constraint `UNIQUE(company_id, code)`.

### Critérios de aceite

- migration executa em banco vazio;
- migration é idempotente onde aplicável;
- não existe tabela operacional sem `company_id`;
- models usam `models.db`, não `declarative_base()` próprio.

---

## Épico 2 — Services determinísticos

Objetivo: portar regra de negócio do GanduInvest para services testáveis no APP32.

### Tarefas

1. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_service.py`.
2. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_triage_service.py`.
3. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_finance_service.py`.
4. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_settings_service.py`.
5. Portar regras úteis de:
   - `C:\GanduInvest\src\core\services\finance_service.py`
   - `C:\GanduInvest\src\core\services\triagem_service.py`
6. Remover qualquer dependência de `company_id = 1`.
7. Exigir `company_id` explícito ou resolvido pelo contexto APP32.
8. Padronizar status canônicos:
   - `draft`
   - `in_analysis`
   - `awaiting_auction`
   - `won`
   - `lost`
   - `discarded`
   - `available_for_sale`
   - `sold`
9. Criar adaptador de compatibilidade para labels legados do GanduInvest.

### Critérios de aceite

- cálculo financeiro roda sem Flask/request/session;
- triagem roda sem Flask/request/session;
- testes cobrem dois `company_id` diferentes;
- service não retorna dado de outro tenant.

---

## Épico 3 — API e UI tenant-safe

Objetivo: expor o módulo no APP32 sem criar app paralelo.

### Tarefas

1. Criar blueprint `real_estate_auctions_bp`.
2. Arquivo sugerido: `C:\GestaoVersus\app32\app32\api\routes\real_estate_auctions.py`.
3. Registrar blueprint em `C:\GestaoVersus\app32\app32\app.py`.
4. Criar prefixos:
   - UI: `/real-estate-auctions`
   - API: `/api/real-estate-auctions`
5. Criar resolver de empresa ativa baseado em:
   - `session["active_company_id"]`;
   - `company_id` explícito validado;
   - fallback seguro já existente no APP32.
6. Criar templates em:
   - `C:\GestaoVersus\app32\app32\templates\real_estate_auctions\dashboard.html`
   - `C:\GestaoVersus\app32\app32\templates\real_estate_auctions\triage.html`
   - `C:\GestaoVersus\app32\app32\templates\real_estate_auctions\detail.html`
   - `C:\GestaoVersus\app32\app32\templates\real_estate_auctions\calendar.html`
7. Portar apenas a UX útil dos templates do GanduInvest.
8. Trocar fetches para endpoints APP32.

### Critérios de aceite

- nenhuma rota usa `.get(id)` sem `company_id`;
- rotas chamam services;
- usuário sem permissão não acessa o módulo;
- UI muda de empresa sem cruzar dados.

### Status APP32

Implementação inicial criada:

- `C:\GestaoVersus\app32\app32\api\routes\real_estate_auctions.py`;
- `C:\GestaoVersus\app32\app32\templates\modules\real_estate_auctions\workspace.html`;
- `C:\GestaoVersus\app32\app32\templates\modules\real_estate_auctions\property_form.html`;
- `C:\GestaoVersus\app32\app32\templates\modules\real_estate_auctions\property_detail.html`;
- registro do blueprint em `C:\GestaoVersus\app32\app32\app.py`.

---

## Épico 4 — RBAC, menu e habilitação por empresa

Objetivo: módulo habilitável por tenant e por perfil.

### Tarefas

1. Registrar recurso canônico `real_estate_auctions`.
2. Adicionar ações:
   - `view`
   - `create`
   - `edit`
   - `triage`
   - `manage_financial_sheet`
   - `generate_pdf`
   - `manage_sources`
   - `delete`
3. Criar seed/registro de capability se o catálogo exigir.
4. Criar `real_estate_auction_tenant_settings` para GanduInvest.
5. Adicionar item de menu condicionado a:
   - módulo habilitado;
   - permissão `view`;
   - empresa ativa.

### Critérios de aceite

- cliente sem módulo habilitado não vê menu;
- permissão controla acesso direto por URL;
- GanduInvest pode operar como piloto sem afetar demais empresas.

### Status APP32

Implementação inicial criada:

- recurso RBAC `real_estate_auctions` no catálogo sistêmico;
- menu em `C:\GestaoVersus\app32\app32\templates\partials\sidebar_standard.html`;
- helper de habilitação por tenant no context processor;
- runbook `C:\GestaoVersus\app32\app32\docs\runbooks\habilitacao_modulo_leiloes_imobiliarios_ganduinvest_v1.md`;
- seed `C:\GestaoVersus\app32\app32\seeds\enable_real_estate_auction_module.py`.

---

## Épico 5 — Storage, anexos e PDF executivo

Objetivo: portar anexos e PDF com isolamento físico e branding por tenant.

### Tarefas

1. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_storage_service.py`.
2. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_pdf_service.py`.
3. Portar regra útil de:
   - `C:\GanduInvest\src\core\services\storage_service.py`
   - `C:\GanduInvest\src\core\services\executive_pdf_service.py`
4. Armazenar arquivos em:

```text
company_<company_id>/real_estate_auctions/property_<property_id>/<category>/<file>
```

5. Suportar categorias:
   - `photo`
   - `notice`
   - `registry`
   - `report`
   - `other`
6. Parametrizar branding via `real_estate_auction_tenant_settings.settings_json`.
7. Corrigir regressão conhecida do teste de PDF mobile herdado.

### Critérios de aceite

- anexo de uma empresa não é servido para outra;
- path traversal bloqueado;
- PDF usa `company_id`;
- PDF usa branding do tenant;
- testes de storage e PDF passam.

---

## Épico 6 — Importação e fontes de leilão

Objetivo: manter importação assistida sem tornar scraping uma mutação irrestrita.

### Tarefas

1. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_import_service.py`.
2. Criar `C:\GestaoVersus\app32\app32\services\real_estate_auction_source_service.py`.
3. Portar lógica útil de:
   - `C:\GanduInvest\src\core\services\importacao_leilao_service.py`
   - `C:\GanduInvest\src\core\services\varredura_leilao_service.py`
   - `C:\GanduInvest\src\intelligence\auction_parser.py`
   - `C:\GanduInvest\src\intelligence\auction_discovery.py`
4. Configurar fontes por `company_id`.
5. Aplicar limites por execução.
6. Registrar jobs e itens processados.
7. Evitar dependência obrigatória de LLM na primeira versão.

### Critérios de aceite

- importação manual por URL funciona;
- duplicidade é controlada por `company_id + url/fingerprint`;
- varredura tem limite;
- erro por fonte não derruba o módulo inteiro.

---

## Épico 7 — MCP e Sapiens Cliente

Objetivo: expor leitura operacional e apoio de decisão via MCP governado.

### Tarefas

1. Criar tools em `C:\GestaoVersus\app32\app32\src\core\mcp_real_estate_auction_tools.py`.
2. Registrar domínio canônico `real_estate_auctions`.
3. Publicar tools iniciais na surface `user`:
   - `list_real_estate_auction_opportunities`
   - `get_real_estate_auction_property`
   - `list_real_estate_auction_calendar`
   - `summarize_real_estate_auction_pipeline`
   - `calculate_real_estate_auction_kpis`
   - `list_real_estate_auction_triage_reasons`
4. Segurar com gate/perfil restrito:
   - `apply_real_estate_auction_triage_decision`
   - `update_real_estate_auction_financial_sheet`
   - `run_real_estate_auction_import_job`
   - `delete_real_estate_auction_property`
5. Atualizar catálogo/capabilities sem criar surface paralela.

### Critérios de aceite

- MCP respeita `company_id`;
- MCP respeita RBAC;
- leitura operacional funciona na surface `user`;
- mutações sensíveis exigem permissão/gate.

---

## Épico 8 — Migração piloto GanduInvest

Objetivo: migrar dados e comportamento útil do app piloto sem carregar dívida estrutural.

### Tarefas

1. Identificar `company_id` oficial da GanduInvest no APP32.
2. Criar script idempotente em `C:\GestaoVersus\app32\app32\scripts\migrate_gandu_invest_auctions.py`.
3. Migrar:
   - imóveis;
   - leilões;
   - fichas financeiras;
   - diligências;
   - anexos;
   - fontes de scraping.
4. Mapear status legados para status canônicos.
5. Gerar relatório de divergências.
6. Validar contagens origem/destino.

### Critérios de aceite

- migração pode ser reexecutada sem duplicar dados;
- cada registro migrado recebe `company_id`;
- relatório aponta perdas ou campos não mapeados;
- GanduInvest visualiza apenas seus próprios dados.

---

## Épico 9 — QA, regressão e release

Objetivo: liberar o módulo com segurança mínima de produção.

### Tarefas

1. Testes unitários:
   - finance;
   - triage;
   - settings;
   - storage;
   - importação.
2. Testes API:
   - autorização;
   - tenant crossing;
   - CRUD mínimo;
   - triagem.
3. Testes UI:
   - dashboard;
   - detalhe;
   - calendário;
   - ficha financeira.
4. Testes MCP:
   - listagem;
   - detalhe;
   - KPIs;
   - isolamento por empresa.
5. Smoke pós-deploy em empresa GanduInvest.

### Critérios de aceite

- suite local passa;
- smoke remoto passa;
- não há endpoint sem `company_id`;
- não há fallback `company_id = 1`;
- não há lógica de negócio nova em rota.

---

## 4. Sequência sugerida de PRs

### PR 1 — Domínio e migrations

Entrega:

- models;
- migrations;
- tenant settings;
- testes básicos de isolamento.

### PR 2 — Services

Entrega:

- finance;
- triage;
- settings;
- property service;
- testes unitários.

### PR 3 — API/UI

Entrega:

- blueprint;
- templates principais;
- RBAC;
- menu.

### PR 4 — Anexos/PDF

Entrega:

- storage;
- PDF executivo;
- branding por tenant;
- testes de arquivo.

### PR 5 — Importação

Entrega:

- importação URL;
- fontes;
- jobs;
- parser/descoberta.

### PR 6 — MCP

Entrega:

- tools;
- catálogo;
- testes MCP.

### PR 7 — Migração GanduInvest

Entrega:

- script de migração;
- validação;
- smoke piloto.

---

## 5. Riscos principais

| Risco | Severidade | Mitigação |
|---|---:|---|
| Tenant crossing por `.get(id)` | Crítica | Sempre filtrar `id + company_id`; testes negativos |
| Financeiro sensível exposto via MCP | Alta | Surface `user` só leitura/cálculo; mutações com gate |
| Portar app inteiro e criar fork | Alta | Usar módulo genérico e settings por tenant |
| Schema sync em startup | Alta | Usar Alembic, nunca auto-migração em runtime |
| Storage cruzando empresa | Alta | Path particionado e validação de root |
| Scraping sem limite | Média | Jobs com limite e permissões específicas |
| Drift entre SPEC, código e MCP | Média | Atualizar catálogo/RBAC junto com cada PR |

---

## 6. Definition of Done global

O módulo só estará pronto para piloto quando:

- o banco for o atual do APP32;
- todas as tabelas tiverem `company_id`;
- GanduInvest estiver configurada como tenant;
- outro tenant puder ser ativado apenas por settings/RBAC;
- testes comprovarem isolamento entre empresas;
- MCP não tiver catálogo paralelo;
- satélites NF-e/Bradesco permanecerem fora do módulo;
- documentação estiver atualizada em SPEC + Playbook.

---

## 7. Próxima ação recomendada

Começar pelo **PR 1 — Domínio e migrations**, criando modelos e migration sem UI, sem MCP e sem migração de dados real.

Frase-guia:

> Primeiro estabilizar o domínio.
> Depois portar experiência.
> Por fim ativar GanduInvest como piloto.
