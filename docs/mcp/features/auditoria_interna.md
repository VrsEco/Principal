# Guia da Feature: Gestão Estratégica — Auditoria Interna

## Metadados
- `feature_id`: `auditoria_interna`
- `dominio`: `governance`
- `ramo_menu`: `Gestão Estratégica`
- `caminho_menu`: `Gestão Estratégica > Governança > Auditoria Interna`
- `rotas_app`: `/internal-audit`, `/internal-audit/checklists`, `/internal-audit/areas`, `/internal-audit/auditors`, `/internal-audit/executions`, `/internal-audit/points`, `/internal-audit/workpapers`, `/internal-audit/findings`, `/internal-audit/reports`, `/internal-audit/follow-ups`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Conduzir o ciclo completo de auditoria interna: cadastrar áreas e auditores, montar checklists, executá-los sobre uma área, registrar pontos de auditoria, convertê-los em achados, documentar papéis de trabalho e evidências, emitir relatórios formais e acompanhar follow-ups.

## Quando usar
- explicar como cadastrar área e auditor, e montar um checklist de auditoria
- explicar como executar um checklist sobre uma área (registro de conformidade/não-conformidade item a item)
- explicar como um item de execução não conforme gera automaticamente um ponto de auditoria
- explicar como converter um ponto de auditoria em achado formal
- explicar como documentar papel de trabalho e vincular evidências (projeto, tarefa ou reunião) a um achado
- explicar como emitir um relatório formal de auditoria
- explicar como registrar e acompanhar follow-up de um achado

## Quando não usar
- para registrar ocorrências do dia a dia fora do processo formal de auditoria — feature própria: `gestao_ocorrencias`
- para gerenciar o projeto, tarefa ou reunião citados como evidência — features próprias: `gestao_projetos`, `gestao_reunioes`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `area_id`, `checklist_id`, `execution_id`, `point_id`, `finding_id`, `report_id`: identificadores para navegar o ciclo (área → checklist → execução → ponto → achado → relatório → follow-up)

## Saídas esperadas
- `dashboard_de_auditoria`: resumo geral
- `checklists`: checklists cadastrados e seus itens
- `execucoes`: execuções de checklist sobre uma área
- `pontos_de_auditoria`: pontos identificados (manualmente ou gerados a partir de item de execução não conforme)
- `papeis_de_trabalho`: documentação de trabalho da auditoria
- `achados`: achados formais, com evidências vinculadas
- `relatorios`: relatórios formais emitidos (com snapshot congelado no momento da emissão)
- `follow_ups`: acompanhamento de achados

## Como orientar o usuário
1. Acessar **Gestão Estratégica > Governança > Auditoria Interna** no menu.
2. Cadastrar áreas e auditores; montar um checklist com os itens a verificar.
3. Executar o checklist sobre uma área — cada item é marcado como conforme ou não conforme; um item não conforme gera automaticamente um ponto de auditoria.
4. A partir de um ponto de auditoria, usar a opção "Gerar achado" para formalizá-lo como achado.
5. Documentar papéis de trabalho e vincular evidências (projeto, tarefa ou reunião) ao achado — o sistema valida que a evidência pertence à mesma empresa.
6. Emitir o relatório formal de auditoria a partir dos achados — a emissão gera um snapshot congelado do relatório.
7. Registrar follow-ups para acompanhar a resolução de um achado ao longo do tempo.

## Uso por IA / MCP
**Atualização:** as 3 tools MCP de leitura deste domínio já estão publicadas no allowlist do `mcp-versus` (cohort `PILOT_AUDIT_READ_TOOL_NAMES`, `src/core/mcp_surface_registry.py`). Diferente da maioria dos cohorts de leitura já expostos (`list_open_process_instances`, `get_meeting`), estas **não são sempre visíveis** — são uma coorte condicional, no mesmo padrão das leituras financeiras (`PILOT_ANALYTICS_FINANCE_READ_TOOL_NAMES`): exigem o scope OAuth `mcp:analytics` (concedido por padrão ao client piloto) e a permissão RBAC `audit.read` por chamada, revalidada a cada execução. O motivo é que essas tools têm scope de catálogo `MCP_ANALYTICS`/`MCP_ADMIN`, não `MCP_USER`.

- `get_internal_audit_summary(company_id)`: contadores agregados da auditoria interna da empresa
- `list_internal_audit_points(company_id, status=None, limit=50)`: lista pontos de auditoria (limite máx. 100)
- `list_internal_audit_findings(company_id, status=None, limit=50)`: lista achados de auditoria (limite máx. 100)

São deliberadamente somente leitura no próprio código-fonte (`src/core/mcp_internal_audit_tools.py`) — pontos e achados continuam dependendo de triagem humana na interface oficial antes de qualquer mutação. Mutação (criar/atualizar checklist, execução, ponto, achado, relatório, follow-up) segue indisponível via MCP mesmo no código interno — ainda exigiria trabalho de implementação, não é só allowlist.

**Achado importante, contra-intuitivo em relação ao menu:** o menu exibe as tags "MVP" (Checklists) e "Onda 2/3/4" (Execuções, Pontos, Papéis de Trabalho, Achados, Relatórios, Follow-ups), sugerindo que partes da feature ainda não existiriam. Na prática, **todo o ciclo já está implementado no backend**, com service dedicado (~35 métodos cobrindo todas as etapas) e schema de banco próprio (13 tabelas: áreas, auditores, checklists e itens, execuções e itens, pontos, papéis de trabalho, achados, vínculos de evidência, relatórios, follow-ups, agenda). As tags parecem ser rótulos de um roadmap que já foi superado pelo código — vale explicar isso ao usuário sem prometer mais do que existe: a lógica de negócio está completa, mas a interface das telas mais recentes (execuções, pontos, papéis de trabalho, achados, relatórios, follow-ups) é minimalista/utilitária, sem os componentes visuais mais elaborados de áreas como Indicadores ou Incentivos.

## Validações e restrições
- `company_id` obrigatório; toda leitura e escrita é restrita à empresa ativa
- RBAC específico de papel de auditor: escrita (criar/editar) exige que o usuário tenha acesso total à empresa OU papel de `auditor_admin`/`auditor` — diferente do RBAC genérico por recurso usado nas demais features de Gestão Estratégica
- leitura (consulta) é liberada a qualquer usuário logado com empresa ativa, mesmo sem papel de auditor
- evidências vinculadas a um achado são validadas: projeto, tarefa ou reunião citados precisam pertencer à mesma empresa
- emissão de relatório gera um snapshot congelado — o relatório emitido não muda retroativamente se os achados forem depois alterados

## O que nunca expor
- estrutura de tabelas internas ou nomes de classes/serviços (`InternalAuditService`, modelos `Audit*`)
- achados, pontos ou relatórios de auditoria de outra empresa/tenant
- conteúdo de auditoria para usuário sem papel de auditor e sem acesso total à empresa, mesmo que a leitura básica seja tecnicamente permitida — oriente com cautela quando o assunto for achado/relatório sensível
