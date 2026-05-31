# SPEC — Módulo Multi-tenant de Leilões Imobiliários v1

Status: especificação inicial para implementação
Escopo: APP32, módulo de Leilões Imobiliários, GanduInvest como primeiro tenant/piloto, reutilização futura por outros clientes

## 1. Decisão oficial

O antigo app `C:\GanduInvest` deve ser absorvido pelo APP32 como um **módulo genérico de Leilões Imobiliários**, e não como aplicação paralela nem como fork específico de cliente.

### Decisão de banco

O módulo deve usar o **banco PostgreSQL atual do APP32**, com novas tabelas integradas e obrigatoriamente escopadas por `company_id`.

### Regra

Banco separado por cliente não é o padrão.
Banco separado só pode ser aprovado por exceção arquitetural quando houver exigência legal, contratual, volumetria extrema ou isolamento físico obrigatório.

---

## 2. Nome canônico do módulo

### Nome funcional

- `Leilões Imobiliários`

### Chave técnica sugerida

- `real_estate_auctions`

### Primeiro tenant/piloto

- `GanduInvest`

### Regra de produto

`GanduInvest` é configuração de cliente.
O produto reutilizável é o módulo `Leilões Imobiliários`.

---

## 3. Fora de escopo nesta SPEC

Devem ser desconsiderados para o MVP deste módulo:

- automações de NF-e / SEFAZ;
- preenchimento de formulários Bradesco;
- rotinas fiscais/bancárias satélites;
- automações que dependam de portal externo com credencial sensível.

Esses componentes podem virar capabilities separadas no futuro, mas não pertencem ao núcleo de Leilões Imobiliários.

---

## 4. Princípios obrigatórios

1. Toda tabela operacional deve conter `company_id`.
2. Toda leitura e escrita deve filtrar por `company_id`.
3. Nenhuma rota pode consultar registro apenas por `id`.
4. Lógica de negócio deve ficar em `services/`, nunca em rota.
5. Regras financeiras devem ser determinísticas e testáveis.
6. Customização por cliente deve ser metadado/configuração, não fork de código.
7. MCP deve consumir o mesmo domínio, permissões e isolamento do APP32.

---

## 5. Modelo de dados recomendado

## 5.1 `real_estate_auction_properties`

Tabela central de oportunidades/imóveis.

Campos mínimos:

- `id`
- `company_id`
- `code`
- `nickname`
- `address`
- `district`
- `city`
- `state`
- `zip_code`
- `property_type`
- `auxiliary_filter`
- `sale_modality`
- `land_area`
- `private_area`
- `built_area`
- `registry_number`
- `registry_office`
- `court_district`
- `bank`
- `occupied`
- `status`
- `triage_status`
- `triage_reason_code`
- `triage_reason_label`
- `triage_notes`
- `appraisal_value`
- `estimated_quick_sale_value`
- `estimated_normal_sale_value`
- `recommended_max_bid`
- `auctioneer`
- `auction_url`
- `notice_url`
- `buyer_name`
- `broker_name`
- `closed_sale_value`
- `auction_won_at`
- `available_for_sale_at`
- `sold_at`
- `created_at`
- `updated_at`

Constraints e índices:

- `UNIQUE(company_id, code)`
- `INDEX(company_id, status)`
- `INDEX(company_id, triage_status)`
- `INDEX(company_id, city, state)`

---

## 5.2 `real_estate_auction_events`

Histórico de praças/leilões de um imóvel.

Campos mínimos:

- `id`
- `company_id`
- `property_id`
- `auction_type`
- `auction_datetime`
- `minimum_bid`
- `modality`
- `auctioneer`
- `winning_bid`
- `result`
- `notes`
- `created_at`
- `updated_at`

Constraints e índices:

- `property_id` referencia `real_estate_auction_properties(id)`
- `INDEX(company_id, auction_datetime)`
- `INDEX(company_id, property_id)`

---

## 5.3 `real_estate_auction_financial_sheets`

Ficha financeira determinística da oportunidade.

Campos mínimos:

- `id`
- `company_id`
- `property_id`
- `winning_bid`
- `auctioneer_commission_percent`
- `other_acquisition_costs`
- `transfer_tax_percent`
- `transfer_tax_value`
- `registry_cost_percent`
- `registry_cost_value`
- `eviction_cost`
- `renovation_budget`
- `cleaning_cost`
- `overdue_property_tax`
- `future_property_tax`
- `overdue_condo_fee`
- `future_condo_fee`
- `legal_fees`
- `contingency_value`
- `capital_cost_months`
- `capital_cost_percent`
- `minimum_profit_percent`
- `minimum_profit_value`
- `projected_sale_value`
- `broker_commission_percent`
- `sale_tax_percent`
- `operational_expenses`
- `last_calculation_snapshot_json`
- `created_at`
- `updated_at`

Regra:

Os KPIs devem ser recalculáveis pelo service. O snapshot é apenas evidência/auditoria, não fonte primária da regra.

Constraints e índices:

- `UNIQUE(company_id, property_id)`
- `INDEX(company_id, property_id)`

---

## 5.4 `real_estate_auction_due_diligence`

Dados de avaliação, posse e diligência.

Campos mínimos:

- `id`
- `company_id`
- `property_id`
- `condo_fee_value`
- `building_age`
- `building_description`
- `property_description`
- `region_square_meter_value`
- `resident_contacted`
- `resident_report`
- `manager_contacted`
- `manager_report`
- `other_debts`
- `internal_notes`
- `created_at`
- `updated_at`

Constraints e índices:

- `UNIQUE(company_id, property_id)`
- `INDEX(company_id, property_id)`

---

## 5.5 `real_estate_auction_attachments`

Anexos por imóvel e tenant.

Campos mínimos:

- `id`
- `company_id`
- `property_id`
- `category`
- `original_filename`
- `stored_filename`
- `storage_path`
- `mime_type`
- `size_bytes`
- `created_at`
- `updated_at`

Categorias iniciais:

- `photo`
- `notice`
- `registry`
- `report`
- `other`

Regra:

O storage físico deve ficar particionado por empresa e imóvel:

```text
company_<company_id>/real_estate_auctions/property_<property_id>/<category>/<file>
```

---

## 5.6 `real_estate_auction_sources`

Fontes de importação/varredura de oportunidades.

Campos mínimos:

- `id`
- `company_id`
- `name`
- `domain`
- `base_url`
- `link_pattern`
- `listing_selector`
- `active`
- `created_at`
- `updated_at`

Regra:

Fonte é configuração por empresa. Um cliente pode usar fontes diferentes de outro sem alteração no core.

---

## 5.7 `real_estate_auction_import_jobs`

Execuções de importação/varredura.

Campos mínimos:

- `id`
- `company_id`
- `source_id`
- `status`
- `started_at`
- `finished_at`
- `total_found`
- `total_imported`
- `total_duplicated`
- `total_error`
- `notes`

---

## 5.8 `real_estate_auction_import_job_items`

Itens processados por job.

Campos mínimos:

- `id`
- `company_id`
- `job_id`
- `url`
- `status`
- `error_message`
- `fingerprint`
- `created_at`
- `updated_at`

---

## 5.9 `real_estate_auction_tenant_settings`

Configurações específicas por empresa.

Campos mínimos:

- `id`
- `company_id`
- `module_enabled`
- `display_name`
- `code_prefix`
- `settings_json`
- `created_at`
- `updated_at`

Exemplos de `settings_json`:

```json
{
  "triage": {
    "min_roi_percent": 18,
    "default_reasons": ["baixa_margem", "risco_juridico", "fora_do_radar"]
  },
  "pdf": {
    "brand_label": "GanduInvest",
    "primary_color": "#0F172A"
  },
  "auction": {
    "default_commission_percent": 5,
    "default_broker_commission_percent": 5
  }
}
```

Regra:

`settings_json` pode ajustar comportamento do tenant, mas não pode remover `company_id`, burlar RBAC, ampliar surface MCP ou quebrar constraints globais.

---

## 6. Serviços obrigatórios

O módulo deve nascer com services próprios:

- `RealEstateAuctionService`
- `RealEstateAuctionTriageService`
- `RealEstateAuctionFinanceService`
- `RealEstateAuctionPdfService`
- `RealEstateAuctionStorageService`
- `RealEstateAuctionImportService`
- `RealEstateAuctionSourceService`

### Regra

Rotas devem orquestrar request/response.
Cálculo, transição de status, triagem, storage e importação pertencem aos services.

---

## 7. API e UI

## 7.1 Blueprint/API

Blueprint sugerido:

- `real_estate_auctions_bp`

Prefixos sugeridos:

- UI: `/real-estate-auctions`
- API: `/api/real-estate-auctions`

## 7.2 Telas iniciais

- dashboard de oportunidades;
- triagem;
- calendário de leilões;
- detalhe do imóvel;
- ficha financeira;
- anexos/documentos;
- geração de PDF executivo.

## 7.3 Resolução de empresa

A empresa ativa deve ser resolvida por:

1. `session["active_company_id"]`, quando existir;
2. `company_id` explícito, somente se o usuário tiver permissão;
3. fallback seguro do APP32.

É proibido usar `company_id = 1` como fallback operacional.

---

## 8. RBAC e permissões

Recurso canônico sugerido:

- `real_estate_auctions`

Ações mínimas:

- `view`
- `create`
- `edit`
- `triage`
- `manage_financial_sheet`
- `generate_pdf`
- `manage_sources`
- `delete`

Regra:

`delete`, `manage_sources` e mutações financeiras devem exigir permissão explícita e não devem ser publicadas livremente na surface MCP `user`.

---

## 9. MCP / Sapiens Cliente

## 9.1 Domínio MCP canônico

- `real_estate_auctions`

## 9.2 Surface principal

- `user`

## 9.3 Tools iniciais permitidas na surface `user`

- `list_real_estate_auction_opportunities`
- `get_real_estate_auction_property`
- `list_real_estate_auction_calendar`
- `summarize_real_estate_auction_pipeline`
- `calculate_real_estate_auction_kpis`
- `list_real_estate_auction_triage_reasons`

## 9.4 Tools que exigem gate/perfil mais restrito

- `apply_real_estate_auction_triage_decision`
- `update_real_estate_auction_financial_sheet`
- `run_real_estate_auction_import_job`
- `delete_real_estate_auction_property`

Regra:

MCP deve reutilizar o mesmo RBAC do APP32. Não pode existir servidor, catálogo ou policy paralela só para o módulo.

---

## 10. Customização para clientes futuros

Quando outro cliente desejar usar o módulo:

1. criar ou selecionar a empresa em `companies`;
2. criar `real_estate_auction_tenant_settings` para o `company_id`;
3. conceder permissões RBAC;
4. configurar fontes, motivos de triagem e branding;
5. opcionalmente importar dados iniciais;
6. liberar UI e MCP conforme perfil.

### Regra

Novo cliente não gera nova tabela, novo banco nem novo fork.
Novo cliente gera nova configuração e novos dados com outro `company_id`.

---

## 11. Migração do GanduInvest piloto

## 11.1 Origem

Origem funcional:

- `C:\GanduInvest\src\core\models\models.py`
- `C:\GanduInvest\src\core\services\finance_service.py`
- `C:\GanduInvest\src\core\services\triagem_service.py`
- `C:\GanduInvest\src\core\services\storage_service.py`
- `C:\GanduInvest\src\core\services\executive_pdf_service.py`
- `C:\GanduInvest\src\core\services\importacao_leilao_service.py`
- `C:\GanduInvest\src\core\services\varredura_leilao_service.py`

## 11.2 Conversão necessária

- trocar `declarative_base()` por `models.db`;
- trocar `Session` próprio por `db.session`;
- substituir `schema_sync.py` por migrations Alembic;
- remover fallback `company_id = 1`;
- escopar todos os `.get(id)` por `company_id`;
- mover lógica de rota para services;
- separar templates em pasta própria do módulo;
- corrigir teste pendente do PDF executivo antes do release.

---

## 12. Critérios de aceite do MVP

O MVP só pode ser aceito quando:

- todas as tabelas operacionais tiverem `company_id`;
- todos os endpoints bloquearem tenant crossing;
- não houver lógica financeira em rota;
- migrations Alembic estiverem idempotentes;
- RBAC controlar acesso ao módulo;
- PDF executivo respeitar tenant/branding;
- storage de anexos estiver particionado por empresa;
- testes cobrirem isolamento entre duas empresas;
- MCP expuser apenas tools compatíveis com surface e permissão.

---

## 13. Fases recomendadas

## Fase 1 — Fundação

- modelos;
- migrations;
- services principais;
- tenant settings;
- testes de isolamento.

## Fase 2 — UI/API

- dashboard;
- triagem;
- detalhe;
- calendário;
- ficha financeira.

Implementação inicial APP32:

- blueprint `real_estate_auctions_bp`;
- UI em `/real-estate-auctions`;
- API em `/api/real-estate-auctions`;
- templates Jinja em `templates/modules/real_estate_auctions`;
- item de menu condicionado a permissão e habilitação do tenant;
- seed operacional em `seeds/enable_real_estate_auction_module.py`.

## Fase 3 — Documentos e anexos

- storage;
- anexos;
- PDF executivo;
- branding por tenant.

## Fase 4 — Importação assistida

- importação por URL;
- fontes por tenant;
- jobs de varredura com limites.

## Fase 5 — MCP

- tools de leitura;
- cálculo de KPIs;
- pipeline/agenda;
- mutações com gate.

---

## 14. Conclusão

O APP32 deve tratar Leilões Imobiliários como:

- domínio funcional reutilizável;
- módulo habilitável por empresa;
- tabelas integradas ao banco atual;
- customização por tenant via configuração;
- MCP governado pela mesma matriz de permissões;
- GanduInvest como piloto, não como exceção arquitetural.

Frase-guia:

> O módulo é multi-cliente.
> O banco é o do APP32.
> O isolamento é por `company_id`.
> A customização é por configuração, não por fork.
