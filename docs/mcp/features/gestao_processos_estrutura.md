# Guia da Feature: Gestão Estratégica — Gestão de Processos (Estrutura)

## Metadados
- `feature_id`: `gestao_processos_estrutura`
- `dominio`: `processes`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Gestão de Processos`
- `rotas_app`: `/process-map`, `/processes`, `/process-portal`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Estruturar e visualizar a hierarquia de processos da empresa — Áreas, Macroprocessos e Processos — em três formas de acesso: mapa visual (Big Picture), lista para modelagem, e portal compacto para consulta.

## Quando usar
- explicar como consultar a hierarquia completa de processos (Áreas → Macroprocessos → Processos)
- orientar como criar uma nova Área de Processo, um Macroprocesso ou um Processo
- explicar a diferença entre o **mapa visual** (Arquitetura de Processos), a **lista de modelagem** (Processos) e o **portal compacto** (Portal de Processos, versão enxuta e compartilhável do mapa)
- explicar como atualizar responsável, descrição ou ordem de um macroprocesso

## Quando não usar
- para acompanhar instâncias em execução (abertas/atrasadas/encerradas) — feature própria: `gestao_processos_execucao`
- para análise de gaps de fluxo BPMN — feature própria: `processos_copiloto_fluxo`
- para documentar um passo de POP com vídeo — feature própria: `processos_pop_copilot`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant (opcional em leitura — usa a empresa ativa da sessão quando ausente)

### Opcionais (conforme a operação)
- `area_id` / `macro_process_id` / dados do processo, para criação e atualização
- `responsible`, `description`, `order_index` (para macroprocesso)

## Saídas esperadas
- `hierarquia_de_processos`: Áreas → Macroprocessos → Processos, completa
- `area_criada` / `macroprocesso_criado_ou_atualizado` / `processo_criado`
- `mapa_visual` / `portal_compacto`: representações do mesmo dado para consumo humano

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Gestão de Processos** no menu.
2. Em **Arquitetura de Processos**, visualizar o mapa completo (Big Picture) — útil para enxergar a empresa inteira de uma vez.
3. Em **Modelagem de Processos**, trabalhar a lista de processos para criar ou ajustar Áreas, Macroprocessos e Processos — este é o nível onde as rotinas (POPs) depois se penduram.
4. Em **Portal de Processos**, usar a versão compacta do mapa quando o objetivo for compartilhar ou imprimir, sem a interatividade completa.
5. Antes de criar um novo item, consultar a hierarquia existente para evitar duplicidade — Área é o nível mais alto, seguido de Macroprocesso, seguido de Processo.

## Uso por IA / MCP
Esta feature já tem **forte cobertura MCP** hoje:
- `list_process_hierarchy` já lista toda a estrutura Área → Macro → Processo da empresa;
- `create_process_area`, `create_macro_process` e `create_process` já permitem à IA criar itens da hierarquia (mutações de risco médio/alto, `create_process` com `human_gate=True` por impactar execução operacional e rastreabilidade);
- `update_macro_process` já permite atualizar responsável, descrição e ordem de um macroprocesso.

Isso torna esta uma das features mais maduras do catálogo — a IA pode consultar e até estruturar a hierarquia diretamente, sempre respeitando o gate humano nas mutações mais sensíveis.

## Validações e restrições
- `company_id` obrigatório em mutações; leitura usa a empresa ativa quando não informado
- hierarquia é estritamente Área → Macroprocesso → Processo; um item só pode existir vinculado ao nível superior correto
- criar um Processo é mutação de alto risco (`human_gate=True`) por ser o nível onde rotinas/POPs se penduram, com impacto direto na execução operacional

## O que nunca expor
- estrutura de tabelas internas
- nomes de services e métodos internos
- dados de processos de outra empresa/tenant
