# Financeiro — Sprint 4 de Importação do Orçamento Matricial

## Objetivo
Habilitar a importação da matriz orçamentária via planilha XLSX, preservando multi-tenancy, service layer e espelhamento REST + MCP.

## Entregas executadas

### Serviço de importação
- `C:\GestaoVersus\app32\services\financial_budget_import_service.py`

Capacidades:
- gerar modelo XLSX da versão orçamentária
- ler planilha XLSX
- mapear colunas fixas + meses da versão
- resolver conta contábil e centro de custo por código
- converter planilha em payload da matriz
- reaproveitar `FinancialBudgetService.upsert_matrix`

### REST
- `C:\GestaoVersus\app32\api\resources\financial_budget.py`
- `C:\GestaoVersus\app32\app.py`
- `C:\GestaoVersus\app32\api\routes\financial.py`

Novos contratos:
- `POST /api/financial/budget/versions/<version_id>/import`
- `GET /financial/budget-template?company_id=<id>&version_id=<id>`

### MCP
- `C:\GestaoVersus\app32\src\core\mcp_server.py`

Nova tool:
- `import_financial_budget_matrix`

### Frontend
- `C:\GestaoVersus\app32\templates\modules\financial\budget_matrix.html`
- `C:\GestaoVersus\app32\templates\modules\financial\partials\_budget_matrix_side.html`

Fluxo entregue:
- selecionar versão
- baixar modelo
- anexar XLSX
- importar planilha
- recarregar a matriz

## Regras aplicadas
- importação aceita apenas `XLSX`
- linhas exigem:
  - código da linha
  - nome da linha
  - visão orçamentária
  - natureza
- meses são derivados da própria versão orçamentária
- códigos de conta contábil e centro de custo são validados no tenant

## Próximo passo recomendado
- duplicação de versão
- importação com staging/preview
- download de erros de importação
- drill-down de desvio no dashboard e na matriz
