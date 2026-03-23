# Financeiro — Sprint 1 do Dashboard Principal

## Objetivo
Entregar a primeira tela analítica do módulo financeiro em `C:\GestaoVersus\app32\api\routes\financial.py` com foco em leitura executiva rápida, preservando a lógica madura do módulo atual.

## Regras de negócio adotadas
- **Agendamentos / Lançamentos / Liquidações**
  - afetam DRE em: **Orçado**, **Competência**, **Vencimento** e **Liquidação**
  - quando liquidados, afetam **caixa / bancos**
- **Transferências**
  - afetam apenas **saldos das contas**
  - não entram em **DRE**, **vencimento**, **competência** ou **visão caixa do dashboard**
- **Lançamentos não financeiros**
  - afetam apenas **DRE por competência**
  - não entram em **vencimento**, **liquidação** ou **caixa / bancos**

## Entrega executada
- `/financial` agora abre o **dashboard principal**
- `/financial/entries` preserva a tela operacional existente
- dashboard renderiza:
  - **Fluxo de caixa**
    - contas a receber em atraso
    - contas a pagar em atraso
    - saldo atual
    - limites de cheque especial
    - contas a receber do período
    - contas a pagar do período
    - saldo final sem limites
    - saldo final com limites
    - repetição para o período seguinte
  - **DRE**
    - colunas: **Orçado | Competência | Vencimento | Liquidação**
  - **Atalhos operacionais**

## Arquivos principais
- `C:\GestaoVersus\app32\api\routes\financial.py`
- `C:\GestaoVersus\app32\services\financial_executive_dashboard_service.py`
- `C:\GestaoVersus\app32\templates\modules\financial\dashboard.html`
- `C:\GestaoVersus\app32\templates\modules\financial\partials\_dashboard_*.html`
- `C:\GestaoVersus\app32\templates\partials\sidebar_standard.html`

## Débitos técnicos conhecidos
- **Orçado** ainda depende de valores em `metadata_json`; sem orçamento matricial estruturado, a coluna pode retornar zero
- **Saldo atual / limites** usam o que já existe em settlements + `metadata_json` das contas bancárias
- **Transferências** ainda precisam de modelagem explícita de origem/destino para futura auditoria patrimonial detalhada

## Próximas sprints recomendadas
### Sprint 2 — Orçamento matricial
- versões
- linhas
- valores mensais
- previsto x realizado consistente

### Sprint 3 — Regras especiais
- modelagem explícita de transferências bancárias
- modelagem explícita de lançamentos não financeiros
- testes multi-tenant e regressão do dashboard
