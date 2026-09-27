# Guia da Feature: Gestão Financeira — Orçamento Matricial

## Metadados
- `feature_id`: `financeiro_orcamento_matricial`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Orçamento Matricial`
- `rota_app`: `/financial/budget`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Planejar e acompanhar o orçamento da empresa numa matriz por conta contábil e centro de resultado, mês a mês, comparando valor planejado com valor realizado.

## Quando usar
- explicar como criar ou clonar uma versão de orçamento
- orientar como preencher a matriz orçamentária (linhas por conta/centro de resultado x meses)
- explicar a diferença entre o workspace de **planejamento** e o de **execução** (acompanhamento)
- explicar como o sistema compara orçado x realizado
- orientar sobre versões de orçamento — só uma fica ativa por vez

## Quando não usar
- para lançamentos financeiros avulsos (isso é a feature de lançamentos/agendamentos, não orçamento)
- para relatórios financeiros fora do contexto orçamentário
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `version_id`: versão de orçamento (ou dados para criar uma nova)

### Opcionais
- `chart_account_id`, `cost_center_id`: filtros de conta contábil e centro de resultado
- período (`start_date`/`end_date`)
- valores mensais planejados por linha

## Saídas esperadas
- `lista_de_versoes`: versões de orçamento da empresa, com indicação da versão ativa
- `matriz_orcamentaria`: linhas (conta x centro de resultado) com valores planejados por mês
- `comparativo_orcado_realizado`: valor planejado x valor real por linha e mês

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Orçamento Matricial** no menu.
2. Criar uma nova versão de orçamento, ou clonar uma versão existente como ponto de partida — **só uma versão fica ativa por vez**; ativar uma nova desativa automaticamente a anterior.
3. No **workspace de planejamento**, preencher a matriz: cada linha combina uma conta contábil e um centro de resultado, com um valor planejado por mês.
4. No **workspace de execução**, acompanhar o realizado: o sistema calcula automaticamente o valor real de cada linha e mês, comparando com o planejado — o cálculo pode considerar lançamentos contábeis ou movimentação de caixa, conforme a configuração da linha.
5. Linhas de orçamento também podem nascer de contratos ou documentos recorrentes, que geram valores automaticamente ao longo do tempo — fluxo mais avançado, útil para despesas fixas e compromissos programados.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada à matriz orçamentária. Via MCP, a IA pode:
- consultar catálogos financeiros já existentes (`list_financial_catalog_items`, com `catalog_type` de conta contábil ou centro de resultado) para dar contexto sobre a estrutura usada no orçamento;
- explicar o fluxo de planejamento e execução orçamentária usando este guia;
- **não pode** criar versões, preencher a matriz ou lançar valores por MCP — essas ações ainda não são capability canônica remota.

Qualquer evolução futura que exponha orçamento via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; conta contábil e centro de resultado devem pertencer à mesma empresa
- apenas uma versão de orçamento fica ativa por vez por empresa
- excluir uma versão remove as linhas e valores vinculados a ela
- criar, editar ou excluir versão/linha de orçamento é mutação financeira sensível e precisa de confirmação humana

## O que nunca expor
- lógica interna de cálculo do realizado (por lançamento ou por caixa)
- estrutura de tabelas internas (versões, linhas, contratos, documentos recorrentes)
- nomes de services e métodos internos
- dados financeiros de outra empresa/tenant
