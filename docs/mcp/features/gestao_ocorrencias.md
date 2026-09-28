# Guia da Feature: Gestão Estratégica — Gestão de Ocorrências

## Metadados
- `feature_id`: `gestao_ocorrencias`
- `dominio`: `processes`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Execução > Gestão de Ocorrências`
- `rotas_app`: `/process-occurrences`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Registrar ocorrências — positivas ou negativas — vinculadas a um colaborador, processo ou projeto, com título, descrição, tipo e pontuação, e controlar quem pode ver cada registro.

## Quando usar
- explicar como registrar uma ocorrência (positiva ou negativa) sobre um colaborador
- explicar como consultar ocorrências vinculadas a um processo, projeto ou colaborador específico
- explicar como editar ou excluir uma ocorrência já registrada
- explicar filtros disponíveis: processo, projeto, colaborador, tipo, texto livre, período

## Quando não usar
- para tratar achados de auditoria formal — feature própria: `auditoria_interna`
- para gerenciar o processo ou projeto em si — features próprias: `gestao_processos_estrutura`/`gestao_processos_execucao`, `gestao_projetos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `title`: título da ocorrência
- `type`: tipo da ocorrência

### Opcionais
- `employee_id`: colaborador responsável/alvo da ocorrência
- `process_id` / `project_id`: vínculo opcional
- `description`: descrição detalhada
- `score`: pontuação livre (não há cálculo automático a partir do tipo)
- `collaborators_ids`: lista de colaboradores adicionais vinculados

## Saídas esperadas
- `lista_de_ocorrencias`: ocorrências da empresa, com filtros e paginação opcional
- `detalhe_da_ocorrencia`: dados completos de uma ocorrência

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Execução > Gestão de Ocorrências** no menu.
2. Registrar uma nova ocorrência, informando título, tipo e, se aplicável, o colaborador, processo ou projeto relacionado.
3. Usar os filtros (processo, projeto, colaborador, tipo, texto, período) para localizar ocorrências já registradas.
4. Editar ou excluir uma ocorrência existente conforme necessário — a exclusão é definitiva (sem lixeira).

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP** para o domínio de ocorrências no `mcp-versus` — toda a operação é feita exclusivamente pela interface web.

**Achado importante:** a lógica de CRUD de ocorrências não segue o padrão de `service` usado em outras áreas do sistema — está implementada diretamente no recurso REST (`api/resources/occurrence.py`), sem uma camada de serviço dedicada. Isso não afeta o usuário final, mas é relevante para quem for construir a tool MCP futuramente.

Se e quando essa exposição for aprovada, o padrão recomendado é o mesmo já usado nas demais features: cohort de leitura (listar/consultar ocorrências) sempre exposto, e cohort de mutação (criar/editar/excluir) com atenção especial à regra de visibilidade por colaborador (usuário sem acesso total à empresa só pode registrar ocorrência em seu próprio nome, e só enxerga ocorrências onde é responsável ou colaborador vinculado).

## Validações e restrições
- `company_id` obrigatório; ocorrência de outra empresa nunca é retornada (403 se o `company_id` do registro não bater com a empresa ativa)
- usuário sem acesso total à empresa: ao criar, o sistema força `employee_id` e `collaborators_ids` para o próprio colaborador — não é possível registrar ocorrência em nome de outra pessoa
- visibilidade: colaborador só enxerga ocorrências onde é o responsável (`employee_id`) ou está na lista de colaboradores vinculados; usuário com acesso total à empresa vê todas
- a permissão usada é a do recurso `processes` (não existe recurso RBAC dedicado a `occurrences`)
- exclusão é definitiva (hard delete), sem soft-delete

## O que nunca expor
- estrutura de tabelas internas (`occurrences`)
- nomes de classes/métodos internos (`OccurrenceListResource`, `OccurrenceResource`)
- ocorrências de outra empresa/tenant, ou de colaboradores fora da visibilidade do usuário
