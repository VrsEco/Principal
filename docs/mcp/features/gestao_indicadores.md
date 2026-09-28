# Guia da Feature: Gestão Estratégica — Gestão de Indicadores

## Metadados
- `feature_id`: `gestao_indicadores`
- `dominio`: `strategy`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Desempenho > Gestão de Indicadores`
- `rotas_app`: `/indicators/tree`, `/indicators`, `/indicators/goals`, `/indicators/data`, `/indicators/dashboard`, `/indicators/analysis`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Estruturar a árvore hierárquica de indicadores, definir metas (de base ou de campanha, por equipe ou individuais), registrar dados de medição — inclusive em lote a partir de uma rotina de processo — e analisar desempenho via dashboard e análises comparativas históricas.

## Quando usar
- explicar como criar ou organizar a árvore de indicadores (códigos gerados automaticamente, ex.: `AA.I.1`, `AA.I.1.1`)
- explicar como definir uma meta (base ou campanha) para um indicador, por equipe ou individual
- explicar como registrar um dado de medição, inclusive em lote quando vinculado a uma rotina de processo
- explicar o dashboard de desempenho (classificação: acima da meta, na meta, abaixo, sem dado)
- explicar a análise comparativa histórica entre indicadores, metas e dados

## Quando não usar
- para gerenciar incentivos/premiação com base em indicadores — feature própria: `gestao_incentivos`
- para visualizar conexões entre indicadores e outras entidades (processos, projetos, OKRs) — feature própria: `teia_de_conexoes`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `indicator_id` / `tree_node_id`: indicador ou nó da árvore de referência
- `goal_kind`: `base` ou `campaign`
- `goal_scope`: `team` ou `individual`
- `period_start` / `period_end`: período da meta ou da medição
- `measurement_value`: valor do dado de medição

## Saídas esperadas
- `arvore_de_indicadores`: estrutura hierárquica com códigos automáticos
- `lista_de_indicadores`: indicadores com contagem de metas e registros
- `metas`: metas ativas por indicador
- `dados_de_medicao`: registros de medição, com exclusão de campanhas aditivas para evitar duplicidade
- `dashboard_de_desempenho`: classificação de desempenho por indicador
- `analise_comparativa`: histórico comparativo indicador × meta × dado

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Desempenho > Gestão de Indicadores** no menu.
2. Em **Árvore**, organizar a hierarquia de indicadores — não é possível criar subnível ou reparentar um nó que já tem indicador associado, nem excluir um nó com indicadores ou subníveis.
3. Em **Indicadores**, criar o indicador propriamente dito.
4. Em **Metas**, definir a meta: uma meta de campanha exige data de término; meta de equipe não pode ter responsável individual e vice-versa.
5. Em **Registro de Dados**, lançar os valores medidos — quando o indicador está vinculado a uma rotina de processo, é possível abrir a tela de lançamento em lote a partir da instância da rotina (isso também marca a instância como "em andamento" automaticamente).
6. Em **Análise (Dashboard)**, acompanhar a classificação de desempenho de cada indicador.
7. Em **Análises Comparativas**, consultar o histórico comparativo.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP** para o domínio de indicadores no `mcp-versus` — toda a operação é feita exclusivamente pela interface web.

**Achado importante:** o motor de cálculo (`IndicatorService.calculate_formula`) suporta indicadores compostos/por fórmula, com recálculo em cascata de indicadores dependentes quando um componente muda (`trigger_dependent_calculations`) — é uma capacidade de negócio real e não trivial, relevante para dimensionar corretamente uma futura tool de leitura de indicador calculado.

## Validações e restrições
- `company_id` obrigatório em toda consulta/gravação; não há vazamento entre empresas
- árvore: não criar subnível nem reparentar nó com indicador associado; não excluir nó com indicadores ou subníveis
- meta: `period_start` e valor numérico finito obrigatórios; `goal_kind` ∈ {base, campaign}; `goal_scope` ∈ {team, individual}; campanha exige `period_end` ≥ `period_start`; meta de equipe não pode ter responsável individual (e vice-versa)
- indicador com metas ou dados vinculados não pode ser excluído de verdade — só inativado (soft-delete, bloqueado com erro se houver vínculos)
- registro de dados exclui metas de campanha aditiva da tela de lançamento simples, para evitar duplicidade de lançamento

## O que nunca expor
- estrutura de tabelas internas ou nomes de classes/serviços (`IndicatorService`, `IndicatorGoalService`)
- indicadores, metas ou dados de outra empresa/tenant
- fórmulas de cálculo de indicadores compostos como se fossem garantia de precisão absoluta — são cálculos definidos pela própria empresa
