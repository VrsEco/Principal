# Guia da Feature: Gestão Estratégica — Gestão de Projetos

## Metadados
- `feature_id`: `gestao_projetos`
- `dominio`: `projects`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Gestão de Projetos`
- `rotas_app`: `/project-portfolios`, `/projects`, `/projects/analysis`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Gerenciar projetos e portfólios da empresa, acompanhando prazos, responsáveis, orçamento e progresso, com análise consolidada da carteira.

## Quando usar
- explicar como criar e organizar um projeto (nome, responsável, prazo, orçamento, prioridade, status)
- explicar como agrupar projetos relacionados num portfólio, opcionalmente vinculado a um plano estratégico
- orientar como acompanhar o progresso e as tarefas de um projeto
- explicar a análise consolidada de projetos (carteira, atrasos, distribuição por status/prioridade)
- explicar o vínculo entre um projeto e OKRs/objetivos estratégicos

## Quando não usar
- para gerenciar processos e POPs — isso é Gestão de Processos, feature própria dentro do mesmo ramo
- para reuniões, ocorrências ou calendário/jornada — features próprias dentro de Gestão Estratégica > Execução
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `name`: nome do projeto (para criação)

### Opcionais
- `plan_id`: plano estratégico ao qual o projeto/portfólio se vincula
- `portfolio_id`: portfólio ao qual o projeto pertence
- `owner`, `status`, `priority`, `progress`, `deadline`, `budget`, `okr_links`, `notes`

## Saídas esperadas
- `lista_de_projetos`: projetos da empresa, com código, nome, responsável, status, prioridade, progresso e prazo
- `detalhe_do_projeto`: dados completos, incluindo `task_stats` (total, abertas, concluídas, atrasadas)
- `lista_de_tarefas_do_projeto`: tarefas vinculadas a um projeto
- `analise_consolidada_de_portfolio`: visão agregada da carteira de projetos

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Gestão de Projetos** no menu.
2. Em **Portfólio de Projetos**, organizar projetos relacionados sob um mesmo portfólio — pode ser vinculado a um plano estratégico já existente.
3. Em **Projetos**, criar um novo projeto informando nome (obrigatório), responsável, status, prioridade, prazo e orçamento; vincular a OKRs/objetivos estratégicos quando fizer sentido.
4. Acompanhar o progresso: cada projeto expõe um resumo de tarefas — total, abertas, concluídas e atrasadas.
5. Em **Análise de Projetos**, consultar a visão consolidada da carteira — útil para identificar projetos atrasados e a distribuição de prioridade/status entre todos os projetos da empresa.

## Uso por IA / MCP
Esta feature já é **parcialmente operacional via MCP hoje** — diferente da maioria das features financeiras:
- `list_projects` já permite à IA listar os projetos da empresa, com filtro por status;
- `list_project_tasks_secure` já permite consultar as tarefas de projeto, inclusive "minhas tarefas em aberto" (`mine_only`/`open_only`).

O que **ainda não é capability remota**: criar ou editar projeto, gerenciar portfólio, ou obter a análise consolidada formatada — essas ações continuam operacionais apenas no APP.

Qualquer evolução futura que exponha mutação de projeto/portfólio via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_process` (gate humano quando o impacto operacional justificar).

## Validações e restrições
- `company_id` obrigatório; `plan_id`/`portfolio_id` devem pertencer à mesma empresa
- nome do projeto é obrigatório na criação
- criar ou editar projeto/portfólio é mutação e deve respeitar o mesmo isolamento por tenant já usado nas tools de leitura

## O que nunca expor
- estrutura de tabelas internas (planos, portfólios, projetos, tarefas)
- nomes de services e métodos internos
- dados de projetos de outra empresa/tenant
