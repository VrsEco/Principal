# SPEC — DRE Gerencial 02

Classe documental: SPEC

## Decisão
O relatório `income_statement_2` passa a suportar um modo gerencial comparativo, preservando multi-tenancy por `company_id` e mantendo regras no service.

## Premissas funcionais
- O usuário escolhe a ótica principal: `competence`, `due` ou `liquidation`.
- Os meses realizados são seleção explícita (`YYYY-MM`), não apenas últimos N meses.
- O modo rápido pode sugerir os últimos N meses, mas a execução deve respeitar a lista final escolhida.
- Orçamento é opcional; quando exibido, deve permitir selecionar a versão orçamentária.
- Previsto é opcional; o mês previsto padrão é o mês imediatamente posterior ao mês realizado mais recente selecionado, podendo ser alterado.
- Na ótica de liquidação:
  - realizados usam data de baixa/liquidação;
  - previsto usa vencimento;
  - orçamento usa competência orçamentária mensal da matriz selecionada;
  - receitas devem ser segregadas em nota explicativa por vencimento: recebido no mês, recebido de meses anteriores e recebido de meses posteriores.

## Layout gerencial aprovado
- A tabela principal deve preservar o plano de contas nas linhas.
- Para ganhar espaço horizontal, os valores monetários do modo gerencial devem ser exibidos sem o prefixo `R$` na tela, PDF e exportações.
- As colunas gerenciais seguem a ordem:
  1. `Orçado`
  2. `Previsto MM/AAAA`
  3. meses realizados em ordem decrescente, exemplo: `06/2026`, `05/2026`, `04/2026`
- A segregação de receitas liquidadas não deve poluir as linhas do plano de contas; deve aparecer após a DRE como `Notas explicativas da liquidação`.
- Após as notas, exibir o bloco `Resultado Líquido / Projeção`:
  1. `( + ) Total de contas a receber em aberto`
  2. `( - ) Total de contas a pagar em aberto`
  3. `( = ) Resultado Projetado do Período`
- No bloco de projeção, os saldos em aberto devem considerar todos os títulos vencidos até o último mês de referência selecionado, inclusive, sem limitar pelo primeiro mês realizado exibido.

## Fontes de dados
- Realizado: títulos/agendamentos/baixas financeiros já usados pelo DRE 02.
- Previsto: títulos/agendamentos abertos por vencimento no mês escolhido.
- Orçamento: `FinancialBudgetVersion`, `FinancialBudgetLine` e `FinancialBudgetAmount`, sempre escopados por `company_id`.

## Guardrails
- Toda query deve filtrar `company_id`.
- Não colocar regra de negócio na rota.
- UI apenas coleta filtros e renderiza payload do service.
- Exportações devem reutilizar o payload gerencial quando aplicável.
