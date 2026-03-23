# Financeiro — Sprint 3 de Previsto x Realizado

## Objetivo
Iniciar a integração entre o orçamento matricial e o ledger financeiro, habilitando leitura real de **orçado x realizado** no cockpit e na matriz orçamentária.

## Entregas executadas

### Skill / governança do Squad
Atualização da skill do Squad para tornar obrigatório ao `@ARQUITETO`:
- registrar toda atividade no projeto `AA.J.31` (produção)
- usar sempre **Fabiano Ferreira** como responsável
- definir prazo para **uma semana após a criação**
- manter gestão com horas por agente/subagente, andamento, entregas, bloqueios, validações e conclusão

Arquivos atualizados:
- `C:\GestaoVersus\app32\.agent\skills\gestao-versus-subagents\SKILL.md`
- `C:\GestaoVersus\app32\.agent\skills\gestao-versus-subagents\subagents\arquiteto.md`
- `C:\GestaoVersus\app32\.agent\skills\gestao-versus-subagents\references\orchestration-playbook.md`
- `C:\GestaoVersus\app32\.agent\skills\gestao-versus-subagents\references\prompt-templates.md`

### Orçamento matricial com realizado
Arquivo:
- `C:\GestaoVersus\app32\services\financial_budget_service.py`

Entrega:
- `get_matrix()` agora retorna por célula:
  - `budget_amount`
  - `actual_amount`
  - `variance_amount`

Regras aplicadas:
- `competence` usa `FinancialEntry.competence_date`
- `due` usa `FinancialEntry.due_date`
- `cash` usa `FinancialSettlement.settlement_date`
- `transfer` fica fora
- `adjustment` entra em competência e fica fora de due/cash

### Dashboard com orçamento real
Arquivo:
- `C:\GestaoVersus\app32\services\financial_dashboard_analytics.py`

Entrega:
- coluna **Orçado** da DRE do dashboard passou a vir do orçamento matricial ativo
- agregação por conta contábil e sinal por `movement_nature`

## Limitações desta etapa
- ainda não há duplicação real de versão
- ainda não há importação da matriz por planilha
- o dashboard ainda não faz drill-down de desvio

## Próximo passo recomendado
- importação de orçamento via planilha
- duplicação de versão
- drill-down de desvio por linha/mês
- fechamento da conciliação entre orçamento e DRE executiva
