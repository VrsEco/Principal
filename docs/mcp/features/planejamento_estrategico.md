# Guia da Feature: Planejamento Estratégico — Identidade Organizacional e Planos

## Metadados
- `feature_id`: `planejamento_estrategico`
- `dominio`: `strategy`
- `ramo_menu`: `Planejamento Estratégico`
- `caminho_menu`: `Planejamento Estratégico`
- `rotas_app`: `/companies/{company_id}/identity`, `/plans`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Definir a identidade organizacional (missão, visão e valores) e conduzir planos estratégicos — de crescimento ou de implantação — com participantes, OKRs globais e de área, diagnóstico de progresso por seção e relatório final.

## Quando usar
- explicar como consultar ou editar missão, visão e valores da empresa
- explicar como criar ou acompanhar um plano estratégico (modo crescimento ou modo implantação)
- explicar como definir OKRs e resultados-chave, globais ou de uma área específica
- explicar o diagnóstico de progresso de um plano (status de cada seção, resumo financeiro quando aplicável)

## Quando não usar
- para gerenciar indicadores ou incentivos em si — features próprias: `gestao_indicadores`, `gestao_incentivos`
- para o Cockpit do Consultor ou a Jornada do Cliente (menu **Consultivo**, separado deste) — não são a mesma feature, mesmo lendo dados relacionados
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `plan_id`: plano de referência
- `section_key`: seção do plano (varia por modo — ver "Validações")
- `okr_title` / `key_result_title`: para criação de OKR/resultado-chave
- `deadline`: prazo do OKR/resultado-chave (aceita `YYYY-MM-DD` ou `DD/MM/YYYY`)

## Saídas esperadas
- `identidade_organizacional`: missão, visão e valores da empresa
- `lista_de_planos`: planos estratégicos da empresa
- `diagnostico_do_plano`: progresso, status por seção e (em planos de implantação) resumo financeiro
- `okrs_e_resultados_chave`: OKRs e KRs globais ou de área

## Como orientar o usuário
1. Acessar **Planejamento Estratégico > Identidade Organizacional** para consultar ou editar missão, visão e valores — a edição de fato acontece na tela de dados da empresa (aba "Editar identidade"); a página de Identidade é majoritariamente uma visão consolidada (inclui Organograma).
2. Acessar **Planejamento Estratégico > Planos Estratégicos** para criar ou abrir um plano.
3. Um plano é sempre de um modo: **crescimento** (participantes, direcionadores, OKRs globais, OKRs de área, projetos, relatório final) ou **implantação** (participantes, alinhamento societário, modelo, execução, financeiro, projetos, relatório final) — as seções disponíveis mudam conforme o modo.
4. Dentro do modo crescimento, as seções de OKRs globais e de área permitem criar objetivos e resultados-chave vinculados ao plano.
5. Consultar o diagnóstico do plano para ver o progresso por seção; planos de implantação também mostram investimento total e payback estimado.
6. Apenas usuários com acesso total à empresa entram em Planos Estratégicos — colaboradores comuns não têm acesso a essa área.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP exposta no `mcp-versus`** para este domínio — as 23 tools do domínio `strategy` existem no código (`src/intelligence/tools_domains/strategy_ops.py`, `src/core/mcp_strategy_alignment_tools.py`) e já rodam nas surfaces internas (`sapiens`, `admin`, `analytics`), mas nenhuma está no allowlist do piloto OAuth.

Tools relevantes a esta feature especificamente:
- **Identidade**: `get_strategy_identity_tool` / `upsert_strategy_identity_tool` — leem/escrevem os mesmos campos `mission`/`vision`/`values` que aparecem na tela; o upsert também sincroniza de volta para o registro da empresa. `upsert_strategy_identity_tool` tem `human_gate=True`.
- **Planos e diagnóstico**: `list_plans`, `get_plan_diagnostics` (texto formatado), `get_plan_diagnostics_read_model` (JSON, surface analytics), `update_plan_section` (valida a seção contra o modo do plano antes de aceitar).
- **OKRs**: `create_global_okr`, `create_area_okr`, `create_global_key_result`, `create_area_key_result` — escrevem nos mesmos modelos usados pelo wizard visual, com validação cross-tenant explícita (rejeita `plan_id` ou OKR de outra empresa) e limite de taxa de mutação por tenant/usuário. Diferente da identidade, essas 4 tools **não têm `human_gate`** hoje — só exigem permissão.

**Achado importante:** a tabela de identidade organizacional tem, no banco, um conjunto bem mais rico de campos (propósito, pilares, objetivos estratégicos, SWOT, stakeholders, políticas, ICP, diferenciais) do que a tela de Identidade Organizacional mostra — hoje só missão/visão/valores aparecem na interface. Isso é decisão de produto documentada (o SPEC interno de "Alinhamento Estratégico N1" define que esses campos técnicos alimentam uma camada consultiva mais profunda, acessível hoje apenas via MCP/API e indiretamente pelo Cockpit do Consultor no menu Consultivo — não pela tela de Identidade). Não oriente o usuário a procurar esses campos na tela; se ele precisar deles, é uma conversa sobre a camada consultiva, fora do escopo desta feature.

Também existe um blueprint de OKRs (`/okrs`) com dashboard próprio, mas ele **não está linkado em nenhum menu hoje** — só é alcançado por um card dentro do Cockpit do Consultor. Não oriente o usuário a acessar `/okrs` diretamente como parte do fluxo normal de Planejamento Estratégico; o fluxo real de OKR é dentro do wizard do plano.

## Validações e restrições
- `company_id` obrigatório; dados de outra empresa nunca são retornados
- **Planos Estratégicos exige acesso total à empresa** — colaborador sem esse acesso recebe 403 ao tentar entrar em `/plans`
- `section_key` é validado contra a lista de seções válidas do modo do plano (`growth` ou `implantation`); seção de um modo não é aceita no outro
- criação de OKR/KR valida que o plano, o OKR pai (para KR) ou a área pertencem à mesma empresa antes de gravar
- edição de identidade pode, dependendo do `status` informado, não gravar direto no dado oficial e entrar numa fila de maturação interna para confirmação posterior — isso é um detalhe de mecanismo interno da camada consultiva, não da tela de Identidade em si

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`StrategyAlignmentN1Service`, `PlanService`)
- campos técnicos da identidade estruturada (pilares, SWOT, ICP, políticas) como se fizessem parte da tela de Identidade Organizacional — eles não aparecem lá
- planos, OKRs ou identidade de outra empresa/tenant
