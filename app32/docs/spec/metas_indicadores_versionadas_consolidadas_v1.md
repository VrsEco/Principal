# SPEC — Metas versionadas e indicadores consolidados v1

## Status
Decisão oficial do APP32 para metas recorrentes, campanhas e consolidação por colaborador.

## Modelo canônico
- `Indicator` representa a métrica única; não deve ser duplicado por consultor.
- `IndicatorGoal` representa uma versão de meta com `period_start`, `period_end`, `goal_type`, `goal_kind` e `goal_scope`.
- `goal_scope=team` exige `responsible_id IS NULL`.
- `goal_scope=individual` exige `responsible_id` pertencente à mesma `company_id`.
- `IndicatorData.employee_id` identifica o colaborador que produziu o fato medido.

## Vigência
- Meta recorrente sem `period_end` permanece válida até receber nova versão ou ser inativada.
- Nova meta-base encerra a versão anterior no dia imediatamente anterior ao novo início.
- Histórico não é sobrescrito.
- A competência é derivada de `goal_type`; não é necessário materializar uma meta a cada mês.

## Campanhas
- `goal_kind=campaign` exige período inicial e final.
- `composition_mode=additive` soma seu alvo à meta-base do mesmo escopo.
- `composition_mode=independent` mantém acompanhamento separado.
- Campanha aditiva reutiliza as medições do indicador e não gera lançamento duplicado.

## Consolidação
- O realizado da equipe é derivado das medições individuais da competência.
- Sem meta explícita de equipe, o alvo consolidado é a soma das metas individuais.
- Com meta explícita de equipe, ela prevalece e o sistema apresenta a diferença entre o alvo da equipe e o total distribuído.
- Metas e medições individuais são sempre segregadas por `company_id` e `employee_id`.

## Interface
- Cadastro de meta exige escopo explícito: equipe ou consultor.
- Medição vinculada a meta individual herda obrigatoriamente o consultor da meta.
- Dashboard apresenta linha consolidada, detalhamento por consultor e filtro de equipe/consultor.
