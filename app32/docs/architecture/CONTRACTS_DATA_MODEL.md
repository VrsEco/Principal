# APP32 — Modelo de Dados do Núcleo de Contratos

**Data:** 2026-05-01  
**Status:** desenho lógico/canônico  
**Especialista líder:** @DBA  
**Apoios naturais:** @ARQUITETO, @BACKEND_SERVICE, @BACKEND_API, @FRONTEND

---

## 1. Objetivo

Definir o modelo de dados lógico do núcleo de **Gestão de Contratos** do APP32, em aderência a:

- multi-tenancy obrigatório;
- composição por abas `core`, `capability` e `extension`;
- consumo por BPMS;
- integração futura com:
  - faturamento;
  - financeiro;
  - fiscal;
  - assinatura;
  - MCP / REST.

Este documento responde:

- quais entidades devem existir;
- como elas se relacionam;
- o que é obrigatório no MVP;
- como o BPMS consome essas entidades sem virar dono do domínio.

---

## 2. Princípios do modelo

## 2.1. Multi-tenancy obrigatório

Toda entidade deve nascer com:

- `company_id`
- `created_at`
- `updated_at`
- `created_by`
- `updated_by`
- `is_active` quando fizer sentido

Regra:

> Nenhuma entidade de contrato pode ser consultada ou mutada apenas por `id`.

## 2.2. Entidade raiz

A entidade raiz do domínio é:

- `contract`

Todas as demais entidades orbitam o contrato diretamente ou indiretamente.

## 2.3. Domínio antes do workflow

O modelo de dados de contratos deve existir independentemente do BPMN.

O BPMS deve referenciar:

- `contract_id`
- `party_id`
- `document_id`
- `billing_item_id`

mas não deve substituir essas entidades.

## 2.4. Abas não são tabela, mas exigem fronteira de dados

As abas são artefatos de experiência, mas precisam ter base de domínio bem separada.

Exemplo:

- aba **Itens do Contrato** → `contract_items`
- aba **Itens de Faturamento** → `contract_billing_items`
- aba **Contrato Assinado** → `contract_documents`

---

## 3. Entidades canônicas

## 3.1. `contract_parties`

Representa favorecidos / contrapartes.

Campos sugeridos:

- `id`
- `company_id`
- `code`
- `name`
- `legal_name`
- `document_type`
- `document_number`
- `is_customer`
- `is_supplier`
- `status`
- `notes`
- `created_by`
- `updated_by`
- `created_at`
- `updated_at`

### Observação

Um mesmo favorecido pode ser:

- somente cliente;
- somente fornecedor;
- ambos.

## 3.2. `contract_party_contacts`

Contatos vinculados ao favorecido.

Campos sugeridos:

- `id`
- `company_id`
- `party_id`
- `contact_name`
- `contact_role`
- `email`
- `phone`
- `is_primary`

## 3.3. `contracts`

Entidade raiz do domínio.

Campos sugeridos:

- `id`
- `company_id`
- `code`
- `title`
- `party_id`
- `status`
- `contract_type`
- `currency_code`
- `signed_at`
- `service_start_at`
- `service_end_at`
- `billing_start_at`
- `billing_end_at`
- `periodicity`
- `competence_rule`
- `due_rule`
- `renewal_rule`
- `notes`
- `version`
- `created_by`
- `updated_by`
- `created_at`
- `updated_at`

## 3.4. `contract_items`

Itens negociados do contrato.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `item_code`
- `item_type`
- `description`
- `quantity`
- `unit_code`
- `unit_price`
- `total_price`
- `service_catalog_item_id` (opcional)
- `order_index`
- `notes`

## 3.5. `contract_billing_items`

Itens de faturamento vinculados ao contrato.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `contract_item_id` (opcional)
- `billing_code`
- `description`
- `amount`
- `billing_periodicity`
- `competence_rule`
- `due_rule`
- `trigger_type`
- `trigger_reference_date`
- `is_recurring`
- `order_index`

## 3.6. `contract_financial_terms`

Condições financeiras do contrato.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `payment_term_type`
- `payment_term_days`
- `billing_method`
- `pricing_model`
- `adjustment_rule`
- `default_bank_account_id` (futuro)
- `notes`

## 3.7. `contract_fiscal_terms`

Condições fiscais.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `fiscal_profile_code`
- `service_city`
- `tax_nature`
- `tax_observation`
- `notes`

## 3.8. `contract_retentions`

Retenções aplicáveis ao contrato.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `retention_type`
- `calculation_mode`
- `rate_percent`
- `fixed_amount`
- `notes`

## 3.9. `contract_triggers`

Datas, alertas e gatilhos.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `trigger_type`
- `reference_date_type`
- `reference_date_value`
- `offset_days`
- `periodicity`
- `alert_before_days`
- `is_active`

## 3.10. `contract_documents`

Artefatos do contrato.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `document_type`
- `file_name`
- `file_path`
- `mime_type`
- `document_version`
- `source`
- `is_signed_version`
- `uploaded_by`
- `uploaded_at`

### Tipos esperados

- minuta
- PDF gerado
- contrato assinado escaneado
- anexo
- evidência

## 3.11. `contract_notes`

Observações estruturadas.

Campos sugeridos:

- `id`
- `company_id`
- `contract_id`
- `note_type`
- `body`
- `visibility_scope`
- `created_by`
- `created_at`

---

## 4. Relacionamentos

```text
contract_parties
└──< contract_party_contacts

contract_parties
└──< contracts

contracts
├──< contract_items
├──< contract_billing_items
├──< contract_financial_terms
├──< contract_fiscal_terms
├──< contract_retentions
├──< contract_triggers
├──< contract_documents
└──< contract_notes
```

### Observações

- `contract_billing_items` pode referenciar `contract_items`, mas não deve depender disso obrigatoriamente.
- `contract_financial_terms` e `contract_fiscal_terms` podem ter cardinalidade `1:N`, preservando histórico/versionamento futuro.
- `contract_documents` deve suportar múltiplas versões e múltiplos tipos por contrato.

---

## 5. Composição por abas x entidades

## 5.1. Cadastro de favorecido

| Aba | Scope | Entidades principais |
|---|---|---|
| Resumo | core | `contract_parties` |
| Classificação | core | `contract_parties` |
| Dados Cadastrais | core | `contract_parties` |
| Contatos | core | `contract_party_contacts` |
| Observações | core | `contract_parties` / `contract_notes` opcional |
| Financeiro | capability | futura integração |
| Fiscal | capability | futura integração |
| Documentos | capability | `contract_documents` opcional |
| Histórico | capability | auditoria / BPMS |

## 5.2. Cadastro de contrato

| Aba | Scope | Entidades principais |
|---|---|---|
| Resumo | core | `contracts` |
| Partes | core | `contracts`, `contract_parties` |
| Itens do Contrato | core | `contract_items` |
| Itens de Faturamento | core | `contract_billing_items` |
| Financeiro | core | `contract_financial_terms` |
| Fiscal | core | `contract_fiscal_terms`, `contract_retentions` |
| Datas e Gatilhos | core | `contract_triggers` |
| Retenções | core | `contract_retentions` |
| Observações | core | `contract_notes` |
| Validação / Edição | capability | `contracts` + regras de consistência |
| Gerar PDF | capability | `contract_documents` |
| Documentos | capability | `contract_documents` |
| Contrato Assinado | capability | `contract_documents` |
| Histórico do Processo | capability | BPMS |
| Integrações | capability | futura integração |
| Faturamento Derivado | capability | futura integração |

---

## 6. BPMS x modelo de dados

## 6.1. Contexto mínimo por instância

Uma instância BPMN que orquestra contratos deve conseguir guardar no `runtime_context_json`, no mínimo:

- `contract_id`
- `party_id`
- `current_tab_key` (quando fizer sentido)
- `document_id` (quando fizer sentido)

## 6.2. Contrato de atividade BPMS

Os contratos de atividade devem apontar para:

- `bpmn_element_id`
- `capability_key`
- `route_name`
- `interaction_mode`
- `ui_schema_json`

Exemplo:

- `AA.C.2.2.1.04`
  - capability: `contract.create_or_update`
  - tabs: `contract_items`, `contract_billing_items`, `contract_financial`, `contract_fiscal`, `contract_triggers`

## 6.3. Regras de ownership

O BPMS:

- não cria estrutura de contrato fora do domínio;
- não duplica dados do contrato;
- não substitui a verdade das abas core.

O BPMS:

- abre a aba ou capacidade correta;
- valida conclusão da activity;
- registra status, duração e evidência operacional.

---

## 7. Regras de customização por tenant

## 7.1. Pode variar por tenant

- visibilidade de abas;
- obrigatoriedade de campos;
- ordem das abas;
- abas extension;
- regras adicionais de retenção;
- campos fiscais específicos;
- complementos documentais.

## 7.2. Não pode variar de forma ad hoc no core

- estrutura base de `contracts`;
- classificação cliente/fornecedor do favorecido;
- existência das entidades core;
- vínculo multi-tenant;
- integridade entre contrato e itens.

Regra:

> Personalização por cliente deve preferir metadados de aba, capability e extension layer; não bifurcação de entidades nucleares.

---

## 8. MVP recomendado

## Fase MVP-1 — base do domínio

1. `contract_parties`
2. `contract_party_contacts`
3. `contracts`
4. `contract_items`
5. `contract_billing_items`
6. `contract_financial_terms`
7. `contract_fiscal_terms`
8. `contract_retentions`
9. `contract_triggers`
10. `contract_documents`
11. `contract_notes`

## Fase MVP-2 — experiência por abas

1. cadastro de favorecido com classificação
2. cadastro de contrato por abas core
3. capability de geração de PDF
4. capability de upload de contrato assinado

## Fase MVP-3 — acoplamento BPMS

1. contracts de activity
2. abertura contextual por aba/capability
3. shell de execução
4. instância piloto do processo de implantação de contratos

## Fase MVP-4 — integrações futuras

1. faturamento
2. financeiro
3. fiscal
4. assinatura
5. MCP / REST

---

## 9. Índices e constraints recomendados

## Constraints

- `contracts.company_id + contracts.code` único
- `contract_parties.company_id + contract_parties.code` único
- impedir `contract_items` sem `contract_id`
- impedir `contract_documents` sem `contract_id`

## Índices

- `contracts(company_id, status)`
- `contracts(company_id, party_id)`
- `contract_items(company_id, contract_id)`
- `contract_billing_items(company_id, contract_id)`
- `contract_documents(company_id, contract_id, document_type)`
- `contract_triggers(company_id, contract_id, trigger_type)`

---

## 10. Conclusão

O núcleo de contratos do APP32 deve nascer:

- com **entidades canônicas claras**;
- com **composição por abas governada por metadados**;
- com **suporte a customização por tenant sem contaminar o core**;
- com **BPMS consumindo o domínio, não substituindo-o**.

Frase-guia:

> O contrato é uma entidade de negócio.  
> As abas organizam a experiência.  
> O BPMS organiza a execução.  
> O multi-tenant organiza a governança.
