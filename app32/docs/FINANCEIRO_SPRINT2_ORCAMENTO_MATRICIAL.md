# Financeiro — Sprint 2 do Orçamento Matricial

## Objetivo
Adicionar a base real de **orçamento matricial multi-tenant** ao módulo financeiro, preservando a operação madura já existente e preparando integração com dashboard, DRE e previsto x realizado.

## Entregas executadas

### Banco / Modelagem
- `C:\GestaoVersus\app32\models\financial_budget.py`
- `C:\GestaoVersus\app32\migrations\versions\20260322_0900_create_financial_budget_matrix.py`

Entidades criadas:
- `FinancialBudgetVersion`
- `FinancialBudgetLine`
- `FinancialBudgetAmount`

### Backend
- `C:\GestaoVersus\app32\schemas\financial_budget.py`
- `C:\GestaoVersus\app32\services\financial_budget_service.py`
- `C:\GestaoVersus\app32\api\resources\financial_budget.py`

Endpoints REST:
- `GET/POST /api/financial/budgets/versions`
- `PUT /api/financial/budgets/versions/<version_id>`
- `GET/PUT /api/financial/budgets/versions/<version_id>/matrix`
- `GET /api/financial/budgets/options`

### Frontend
- `C:\GestaoVersus\app32\templates\modules\financial\budget_matrix.html`
- `C:\GestaoVersus\app32\templates\modules\financial\partials\_budget_matrix_*.html`
- rota:
  - `C:\GestaoVersus\app32\api\routes\financial.py`
  - página: `/financial/budget`

### MCP
- `C:\GestaoVersus\app32\src\core\mcp_server.py`

Ferramentas adicionadas:
- `list_financial_budget_versions`
- `create_financial_budget_version`
- `get_financial_budget_matrix`
- `upsert_financial_budget_matrix`

## Regras de arquitetura mantidas
- `company_id` obrigatório em toda a modelagem
- sem lógica de negócio em rota
- service layer centralizada
- espelhamento REST + MCP
- sem SQLite

## Limitações conhecidas desta sprint
- duplicação de versão ainda não implementada
- importação de planilha ainda não implementada
- realizado e desvio ainda aparecem como `0` até integração com ledger e dashboard

## Próximo passo recomendado
### Sprint 3 — Previsto x Realizado
- cruzar orçamento com lançamentos/liquidações
- alimentar DRE: Orçado | Competência | Vencimento | Liquidação
- habilitar desvios reais na matriz
- iniciar importação de planilha do orçamento
