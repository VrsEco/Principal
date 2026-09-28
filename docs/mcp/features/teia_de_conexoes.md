# Guia da Feature: Gestão Estratégica — Teia de Conexões

## Metadados
- `feature_id`: `teia_de_conexoes`
- `dominio`: `governance`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Governança > Teia de Conexões`
- `rotas_app`: `/incentives/spider-web`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `baixa`
- `company_id_obrigatorio`: `sim`

## Objetivo
Visualizar um grafo de conectividade entre processos, projetos, OKRs (de área e globais) e indicadores, identificando itens órfãos (sem nenhuma conexão), frágeis ou bem conectados — apoiando a governança de metas e indicadores da empresa.

## Quando usar
- explicar como identificar indicadores, processos ou OKRs sem nenhuma conexão (órfãos)
- explicar como avaliar a saúde geral de governança de metas e indicadores de uma empresa
- explicar o que significam os estados de saúde de um nó: órfão, frágil, conectado

## Quando não usar
- para editar indicadores, processos, projetos ou OKRs em si — features próprias: `gestao_indicadores`, `gestao_processos_estrutura`/`gestao_processos_execucao`, `gestao_projetos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- nenhuma — a tela é somente leitura e sempre parte do escopo da empresa ativa

## Saídas esperadas
- `grafo_de_conexoes`: nós (processos, OKRs de área/globais, indicadores, projetos) e arestas entre eles
- `resumo_de_saude_por_tipo`: contagem de órfãos, frágeis e conectados, total e por tipo de nó

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Governança > Teia de Conexões** no menu.
2. Observar o grafo: cada nó representa um processo, OKR, indicador ou projeto; cada ligação representa um vínculo real já cadastrado no sistema (ex.: projeto como iniciativa de um OKR).
3. Usar os nós marcados como "órfãos" para localizar indicadores, processos ou OKRs que ainda não têm nenhuma conexão — geralmente um sinal de que falta vincular esse item a algo mais amplo na estratégia da empresa.
4. Usar o resumo de contagem para ter uma visão rápida da saúde geral da governança.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP** para esta feature no `mcp-versus` — a visualização é feita exclusivamente pela interface web.

**Achado importante:** é uma tela puramente analítica/somente leitura (sem nenhuma mutação), o que a torna uma boa candidata a uma futura tool de leitura de baixo risco (`risk: low`, sem `human_gate`) caso a exposição via MCP seja avaliada — não há dado sensível de negócio, apenas metadados de conectividade entre entidades já visíveis em outras features.

## Validações e restrições
- `company_id` obrigatório; o grafo é sempre tenant-safe, nunca mistura dados de empresas diferentes
- é somente leitura — não há criação, edição ou exclusão de conexões diretamente nesta tela

## O que nunca expor
- estrutura de tabelas internas ou nomes de classes/serviços (`IncentiveSpiderWebService`)
- dados de outra empresa/tenant
