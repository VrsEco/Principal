# Guia da Feature: Gestão Estratégica — Gestão de Reuniões

## Metadados
- `feature_id`: `gestao_reunioes`
- `dominio`: `meetings`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Gestão de Reuniões`
- `rotas_app`: `/meetings`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Gerenciar o ciclo de vida completo de uma reunião — agendar, iniciar, registrar discussão, encerrar e enviar ata — com pautas, decisões e ações que podem virar tarefas de projeto.

## Quando usar
- explicar como agendar uma reunião, vinculada ou não a um projeto
- orientar o ciclo de vida: agendada → iniciada → em discussão → encerrada → ata enviada
- explicar como registrar pautas (tópicos) discutidos numa reunião
- explicar como registrar decisões tomadas, com responsável e justificativa
- explicar como criar ações (atividades) a partir da reunião, e como sincronizá-las para virarem tarefas de projeto
- explicar como enviar a ata da reunião (por e-mail ou outro canal)

## Quando não usar
- para gerenciar projetos ou tarefas em si (fora do contexto de uma reunião) — feature própria: `gestao_projetos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `title`: título da reunião (para criação)

### Opcionais
- `project_id`: projeto ao qual a reunião se vincula
- `participants`, `actual_date`, `actual_time`, `actual_duration_minutes`, `meeting_notes`
- para pautas/decisões/ações: `topic_id`, `text`/`title`, `rationale`, `owner`, `responsible`, `deadline`, `priority`

## Saídas esperadas
- `lista_de_reunioes`: reuniões da empresa
- `detalhe_da_reuniao`: pautas, decisões e ações vinculadas
- `resultado_da_sincronizacao`: ações da reunião convertidas em tarefas de projeto

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Gestão de Reuniões** no menu.
2. Agendar uma nova reunião — pode ser vinculada a um projeto existente.
3. Ao iniciar a reunião, registrar a discussão de cada pauta (tópico) conforme ela acontece.
4. Para cada decisão tomada, registrar o texto da decisão, a justificativa (rationale) e o responsável.
5. Criar ações (atividades) que precisem de acompanhamento — elas podem ser sincronizadas para virar tarefas reais dentro de um projeto, evitando que combinados da reunião se percam.
6. Ao encerrar a reunião, é possível enviar a ata automaticamente para os participantes.

## Uso por IA / MCP
Hoje a IA só pode **listar** reuniões via MCP (`list_meetings`) — é a única tool deste domínio exposta no `mcp-versus`.

**Achado importante:** o domínio `meetings` já tem no código um ciclo de vida completo implementado — `schedule_meeting`, `start_meeting`, `log_meeting_discussion`, `finish_meeting`, `send_meeting_minutes`, além de CRUD completo de reunião, pautas, decisões e ações (`create_meeting`, `create_meeting_topic`, `create_meeting_decision`, `create_meeting_activity`, `sync_meeting_activities_to_project`, entre outras) — nenhuma dessas ~19 tools está no allowlist do `mcp-versus` hoje. É o mesmo padrão de gap já identificado e corrigido para o domínio `processes` nesta mesma frente de trabalho: a capacidade técnica existe, só falta decisão de expor.

Se e quando essa expansão for aprovada, o padrão recomendado é o mesmo já usado para `processes`: cohort de leitura (`list_meetings`, `get_meeting`) sempre exposto, e cohort de mutação (`create_meeting`, `finish_meeting`, `create_meeting_activity`, etc.) com `human_gate` nas ações que geram compromisso formal (decisão registrada, ação sincronizada para projeto).

## Validações e restrições
- `company_id` obrigatório; reunião de outra empresa nunca é retornada
- ação sincronizada para projeto deve respeitar o mesmo isolamento tenant-safe já usado em `gestao_projetos`
- decisão e ação registradas ficam associadas à reunião de origem, preservando rastreabilidade

## O que nunca expor
- estrutura de tabelas internas (reunião, tópicos, decisões, ações)
- nomes de services e métodos internos
- dados de reuniões de outra empresa/tenant
