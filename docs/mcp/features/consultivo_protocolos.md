# Guia da Feature: Consultivo — Protocolos Consultivos

## Metadados
- `feature_id`: `consultivo_protocolos`
- `dominio`: `consultive`
- `ramo_menu`: `Consultivo`
- `caminho_menu`: `Consultivo > Protocolos Consultivos`
- `rotas_app`: `/consultive/protocols`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Manter a biblioteca de protocolos — roteiros de instrução (prompt) versionados, um por frente estrutural e subfase, usados para orientar a condução metodológica de uma análise consultiva por IA, squad ou consultor.

## Quando usar
- explicar o que é um "protocolo" aqui: um roteiro de prompt/instrução versionado, não um SOP operacional nem um registro de atendimento
- explicar como consultar o protocolo ativo de uma frente/subfase/audiência
- explicar como criar uma versão própria da empresa (override) de um protocolo, preservando o modelo global padrão

## Quando não usar
- para registrar a análise em si feita num cliente — isso fica na feature `consultivo_cockpit` (análise assistida, decisão do consultor)
- para a visão de maturidade por bloco/etapa — feature própria: `consultivo_jornada_cliente`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `front_key`, `subphase_key`: frente e subfase do protocolo
- `audience`: `ai_cli`, `client_squad`, `versus_squad` ou `consultant`
- `depth_level`: `basic`, `internal_diagnosis`, `deep_research` ou `simulation`

## Saídas esperadas
- `catalogo_de_protocolos`: grade com o protocolo ativo por frente × subfase (18 combinações fixas)
- `protocolo_resolvido`: o protocolo efetivo para uma frente/subfase/audiência específica

## Como orientar o usuário
1. Acessar **Consultivo > Protocolos Consultivos** no menu.
2. Filtrar por audiência (IA/CLI, Squad Cliente, Squad Versus, Consultor) ou buscar por texto.
3. Cada linha da grade mostra o protocolo ativo daquela combinação de frente e subfase — não é uma lista de execuções, é a biblioteca de roteiros.
4. Para customizar, criar um novo protocolo: isso grava uma versão própria da empresa (override); o modelo global padrão continua preservado e serve de base para quem não tem override.
5. Editar campos como título, objetivo e o próprio texto do roteiro (prompt), além de status (rascunho/ativo/arquivado) e versão.

## Uso por IA / MCP
Existem tools MCP reais para este domínio: `consultive_resolve_protocol` (leitura, resolve o protocolo efetivo de uma frente/subfase/audiência) e `consultive_upsert_protocol` (escrita, cria/atualiza um protocolo). Nenhuma está no allowlist do `mcp-versus` hoje — assim como as demais tools de domínio `consultive`, elas são controladas por um mecanismo próprio de perfil de agente (harness/squad overlay), pensado para squads internos, não para o conector OAuth de usuário final (ver detalhamento no guia `consultivo_cockpit`).

**Achado importante:** a resolução de um protocolo segue uma cadeia de prioridade clara — (1) versão específica da empresa, se existir; (2) versão global cadastrada; (3) um catálogo padrão embutido no próprio código (20 protocolos pré-escritos, um por combinação de frente+subfase); (4) um fallback genérico final. Isso significa que mesmo uma empresa que nunca customizou nada sempre tem um protocolo padrão disponível — nunca "nenhum protocolo".

## Validações e restrições
- `company_id` obrigatório; protocolo de outra empresa nunca é retornado como override (mas o catálogo global é compartilhado entre empresas por design)
- leitura liberada a qualquer usuário autenticado com empresa ativa
- escrita (criar/editar protocolo) exige acesso total à empresa (`has_company_full_access`)
- marcar um protocolo como "ativo" sem data de aprovação registra automaticamente quem aprovou e quando

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`ConsultiveProtocolService`)
- o conteúdo de um protocolo como se fosse um registro de atendimento real a um cliente — é um roteiro/instrução, não um histórico
- dados de outra empresa/tenant
