# Guia da Feature: Consultivo — Cockpit do Consultor

## Metadados
- `feature_id`: `consultivo_cockpit`
- `dominio`: `consultive`
- `ramo_menu`: `Consultivo`
- `caminho_menu`: `Consultivo > Cockpit do Consultor`
- `rotas_app`: `/consultive/cockpit`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Dar uma visão consolidada da maturidade estrutural do cliente em 4 frentes (Identidade Organizacional, Processos, Planejamento Estratégico, Gerenciamento Estratégico), com necessidades urgentes, business reviews pendentes de decisão e aprendizado estrutural — ponto de partida para o consultor priorizar onde atuar.

## Quando usar
- explicar a visão geral de maturidade das 4 frentes estruturais
- explicar como abrir a análise detalhada de uma frente específica
- explicar necessidades urgentes, business reviews e aprendizado estrutural pendentes de decisão
- orientar o registro de "valor agregado" de um business review (necessidade identificada, solução aplicada, resultado, valor)

## Quando não usar
- para a jornada de maturidade do cliente ao longo do tempo — feature própria: `consultivo_jornada_cliente`
- para consultar ou editar o roteiro/prompt de condução metodológica — feature própria: `consultivo_protocolos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `front_key`: `identity`, `processes`, `growth_plan` ou `strategic_management` (para abrir a análise detalhada de uma frente)
- `analysis_id`: análise assistida específica

## Saídas esperadas
- `resumo_das_4_frentes`: card resumo com maturidade de cada frente
- `analise_detalhada_da_frente`: evidências, gaps e recomendações reais de uma frente
- `necessidades_urgentes`: lista de necessidades abertas
- `business_reviews`: pendentes de decisão, com exposição financeira agregada
- `aprendizado_estrutural`: aprendizados pendentes de virar ação

## Como orientar o usuário
1. Acessar **Consultivo > Cockpit do Consultor** no menu.
2. Observar o resumo das 4 frentes estruturais no topo.
3. Clicar em "Abrir frente" (ou "Pré-analisar") para ver a análise real e detalhada daquela frente — evidências contadas do sistema, gaps identificados e recomendações priorizadas.
4. Acompanhar necessidades urgentes, business reviews pendentes (registrar valor agregado quando resolvidos) e aprendizados estruturais pendentes de virar ação.
5. Usar o link para a Trilha de Estruturação para navegar até a Jornada do Consultor.

## Uso por IA / MCP
**Achado crítico, essencial para nunca informar errado ao usuário:** o card-resumo das 4 frentes que aparece ao abrir o Cockpit é **hardcoded/estático** no código (percentuais fixos, não calculados por empresa) — reflete um estado ilustrativo, não a maturidade real daquele cliente específico. **Só a análise detalhada** (ao clicar "Abrir frente") roda cálculo real: conta registros de verdade no banco daquela empresa (processos modelados, OKRs, indicadores ativos, etc.) e devolve maturidade, evidências e recomendações reais. Nunca afirme que o percentual do card-resumo representa a situação real do cliente.

A análise detalhada de frente é **determinística, sem IA generativa** — o próprio código documenta isso explicitamente ("a primeira entrega não executa IA generativa; critérios metodológicos conservadores"). `external_benchmarks` sempre vem vazio (pesquisa externa de mercado não está implementada).

Existem 12 tools MCP reais para este domínio (`consultive_get_front_context`, `consultive_get_front_evidence`, `consultive_get_front_gaps`, `consultive_get_methodology_guidance`, `consultive_get_next_action`, `consultive_resolve_protocol`, `consultive_list_assisted_analyses`, `consultive_register_assisted_analysis`, `consultive_register_squad_validation`, `consultive_register_consultant_decision`, `consultive_upsert_protocol`, `consultive_create_recommended_action`), registradas em `src/core/mcp_consultive_assisted_analysis_tools.py`. **Nenhuma está no allowlist do `mcp-versus`** — mas o motivo aqui é diferente do resto do catálogo: essas tools já são controladas por um mecanismo próprio de RBAC dinâmico por perfil de agente (harness/squad overlay, `src/intelligence/mcp_contracts/`), pensado para squads internos da Versus (ex.: `harness_coordenador_cliente_v1`), não para o conector OAuth de usuário final. Registrar uma análise assistida ou uma decisão de consultor sempre exige `human_gate_confirmed=True` e resolve o usuário autenticado pelo contexto da sessão — o payload nunca pode forjar outro usuário. Validação de squad só pode validar o próprio squad (`_require_own_squad_validation`); decisão do consultor é sempre o gate humano final antes de qualquer conversão operacional.

## Validações e restrições
- `company_id` obrigatório; leitura liberada a qualquer usuário logado com empresa ativa (não exige perfil de consultor)
- escrita (decisões, registro de valor agregado, protocolos) exige acesso total à empresa (`has_company_full_access`): admin de plataforma, cliente vinculado, ou colaborador com cargo Administrador/Superuser
- análise assistida só é elegível para avançar a jornada quando tem evidência humana, evidência interna, riscos, recomendações e benchmark (ou justificativa de não aplicável) — a IA/cliente não pode forçar esse avanço
- validação de squad só pode validar o próprio squad; decisão do consultor exige que a análise já esteja elegível

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`BusinessReviewReadModelService`, `ConsultiveAssistedAnalysisService`)
- os percentuais do card-resumo como se fossem a maturidade real do cliente
- dados de outra empresa/tenant
