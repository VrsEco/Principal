# Plano MCP First — Módulo de Orçamento

## Objetivo
Garantir que o novo módulo de Orçamento, com Ciclo Orçamentário, CAPEX/OPEX/Extra e execução financeira vinculada, nasça **espelhado em REST e MCP** desde a primeira versão.

## Princípio de arquitetura
- Toda operação de negócio do módulo deve existir em:
  1. **API REST** para UI/integrações humanas
  2. **MCP Tool** para agentes IA / automação
- Toda operação MCP deve respeitar **multi-tenancy por `company_id`**.
- MCP não deve conter regra de negócio própria: deve delegar para a mesma camada de serviço usada pela API.

## Escopo funcional do módulo
Hierarquia alvo:

- **Ciclo Orçamentário**
- **Orçamento** (CAPEX, OPEX, CAPEX Extra, etc.)
- **Verba**
- **Contrato**
- **NF / Assemelhado**
- **Agendamento**
- **Lançamento**

## Operações que devem ser espelhadas em MCP

### 1) Listar ciclos orçamentários
**Uso:** descobrir anos, status e agrupamentos disponíveis.

**REST esperado**
- listar ciclos do contexto da empresa

**MCP sugerido**
- `list_budget_cycles(company_id, filters...)`

**Retorno mínimo**
- `id`
- `code`
- `name`
- `year`
- `status`
- indicadores consolidados

---

### 2) Listar orçamentos de um ciclo
**Uso:** visualizar CAPEX/OPEX/Extra e consolidar por grupo.

**REST esperado**
- listar orçamentos por `cycle_id`
- suportar visão individual e consolidada

**MCP sugerido**
- `list_budget_versions(company_id, cycle_id, budget_type=None, consolidated=False)`

**Retorno mínimo**
- `id`
- `full_code`
- `name`
- `budget_category`
- `scenario_type`
- `status`
- totais previstos/executados

---

### 3) Criar verba
**Uso:** criar a unidade de alocação dentro de um orçamento.

**REST esperado**
- criar verba vinculada ao orçamento selecionado

**MCP sugerido**
- `create_budget_line(company_id, budget_version_id, payload)`

**Regras**
- validar orçamento pai no escopo da empresa
- gerar/validar código hierárquico
- persistir `metadata_json` e vínculos estruturais

---

### 4) Criar contrato
**Uso:** registrar o compromisso orçamentário derivado da verba.

**MCP sugerido**
- `create_budget_contract(company_id, budget_line_id, payload)`

**Regras**
- herdar contexto da verba
- validar contraparte, status e valor
- preservar trilha `company_id -> version -> line`

---

### 5) Criar NF / Assemelhado
**Uso:** registrar lastro documental do contrato.

**MCP sugerido**
- `create_budget_document(company_id, budget_contract_id, payload)`

**Regras**
- herdar contexto do contrato
- permitir `document_type`, `document_number`, `document_amount`
- atualizar status documental conforme vínculo com agendamentos

---

### 6) Gerar agendamento
**Uso:** criar previsão operacional do financeiro do dia a dia.

**MCP sugerido**
- `create_schedule_from_budget_document(company_id, budget_document_id, payload)`

**Regras**
- herdar automaticamente:
  - `budget_cycle_id`
  - `budget_version_id`
  - `budget_line_id`
  - `budget_contract_id`
  - `budget_document_id`
- permitir criação manual com enquadramento orçamentário assistido
- suportar criação sem orçamento, marcada como `fora_do_orcamento` ou `nao_planejado`

---

### 7) Consultar execução orçamentária
**Uso:** consolidar previsto x realizado em todos os níveis.

**MCP sugerido**
- `get_budget_execution(company_id, cycle_id, budget_version_ids=None, line_id=None, contract_id=None, document_id=None)`

**Retorno mínimo**
- previsto
- contratado
- documentado
- agendado
- realizado
- saldo
- desvio

## Padrão de consolidação
O módulo deve permitir:

- visão **individual**
  - um orçamento específico
- visão **por grupo**
  - CAPEX + CAPEX Extra
- visão **total**
  - todos os orçamentos do ciclo

## Impacto técnico esperado

### Backend
- criação de tools MCP espelhando serviços existentes
- unificação da camada de negócio para REST e MCP
- cuidado com filtros por `company_id` em todas as consultas

### Dados
- necessidade de ciclo orçamentário como entidade de topo
- suporte a classificação CAPEX/OPEX/Extra
- suporte a código hierárquico estruturado

### Financeiro do dia a dia
- o agendamento operacional não pode depender exclusivamente do fluxo de orçamento
- deve existir enquadramento orçamentário opcional/assistido
- lançamento deve herdar vínculo quando originado de agendamento

## Plano acionável

### Fase 1 — Contrato MCP
- definir nomes das tools
- padronizar payloads e retornos
- garantir `company_id` em todas as assinaturas

### Fase 2 — Espelhamento de leitura
- listar ciclos
- listar orçamentos
- consultar execução consolidada

### Fase 3 — Espelhamento de escrita
- criar verba
- criar contrato
- criar documento
- gerar agendamento

### Fase 4 — Hardening
- validar multi-tenancy
- validar unicidade de códigos
- validar consistência hierárquica
- testar cenários CAPEX/OPEX/Extra e consolidado

## Critério de aceite
O módulo só está pronto para produção quando:
- cada operação de negócio tiver endpoint REST e tool MCP equivalente
- o agente conseguir planejar, criar e consultar o orçamento sem depender de tela
- a execução financeira diária continuar operando mesmo quando o usuário não navegar pela árvore orçamentária

## Referências locais
- `C:\GestaoVersus\app32\services\financial_budget_workspace_service.py`
- `C:\GestaoVersus\app32\api\resources\financial_budget.py`
- `C:\GestaoVersus\app32\services\financial_service.py`
- `C:\GestaoVersus\app32\services\financial_schedule_service.py`
- `C:\GestaoVersus\app32\services\financial_direct_entry_service.py`

