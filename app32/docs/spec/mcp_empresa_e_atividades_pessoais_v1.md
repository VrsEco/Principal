# SPEC — Empresa por referência e atividades pessoais no MCP

Status: implementação parcial local, sem publicação.

## Entrega e checklist

Card preparado: [MCP — empresa por referência e atividades pessoais].
Registro operacional pendente: não há conector APP32 nem sessão SSH autenticada
disponível ao agente. Não criar identidade operacional alternativa.

- [x] Diagnóstico: sessão relatada resolve usuário 32, colaborador 73, empresa 8.
- [x] Filtros locais `mine_only` e `open_only` na consulta de atividades de projeto.
- [x] Testes isolados dos filtros, sem iniciar Flask ou acessar banco.
- [x] Resolução compartilhada de empresa por ID, código e nome implementada localmente.
- [x] Testes de contexto OAuth e schema FastMCP sem I/O externo.
- [x] Filtros do resolvedor em PostgreSQL descartável com dados sintéticos.
- [ ] Homologação ponta a ponta no conector real do cliente.
- [ ] Revisão, publicação autorizada e smoke no cliente.

## Atividades pessoais

`mine_only=true` usa exclusivamente o usuário autenticado e seu Employee da
empresa autorizada. Sem vínculo ativo ou em férias, negar sem fallback por nome.
Atividades com apenas `who` textual não contam como atribuições pessoais.
`open_only=true` exclui status/stage completed/cancelled e completion_date preenchida.
Os filtros precedem ordenação e limite. Defaults false preservam consultas antigas;
a descrição da tool exige ambos true para “minhas atividades em aberto”.
Este recorte cobre atividades de projeto, não instâncias de processos.

## Empresa por referência — implementação local pendente de integração

Aceitar ID numérico, client_code ou nome, inclusive apresentação “AW - Meu Chapa”.
Resolver somente na interseção das empresas ativas vinculadas ao usuário APP32
com os grants válidos do principal OAuth. Não usar contexto global de processo,
identidade enviada pelo cliente ou nome do responsável para determinar acesso.

A resolução precisa ocorrer ANTES do gate por company_id do mcp_runtime;
implementar apenas no corpo da tool não funciona porque o gate já rejeita a
requisição sem ID. Manter a avaliação canônica do grant depois da resolução.

Sem correspondência autorizada: resposta genérica, sem revelar empresa existente
fora do escopo. Múltiplas correspondências: devolver somente opções autorizadas
e exigir escolha. ID e referência conflitantes: rejeitar. Não escolher primeiro
resultado nem converter nome em grant. Resposta bem-sucedida identifica ID,
código e nome canônicos para o cliente apresentar o contexto.

## Evidência local

`test_mcp_personal_tasks_isolated.py`: 5 testes aprovados. Execução isolada das
funções reais via AST, sem bootstrap. Não substitui integração PostgreSQL,
registro/schema remoto e smoke no ambiente do cliente.

`test_mcp_company_reference_isolated.py`: 14 testes de correspondência,
ambiguidade, ausência e conflito com ID; total desta entrega: 19 testes isolados.
`company_ref` está exposto inicialmente em `list_project_tasks_secure`; não é
ainda uma ferramenta geral de descoberta nem foi aplicado às outras consultas.
Resolver ORM limita por empresas ativas, vínculos APP32 e grants avaliados pela
policy canônica. Nenhuma alteração de permissão ou registro financeiro foi executada.

Atualização de validação: 44 testes passaram (19 isolados, 5 de contexto/schema
e 20 de regressão do runtime HTTP). Banco e HTTP reais bloqueados nessa execução.
Outros 3 testes passaram em PostgreSQL 14 descartável com modelos mínimos e
decisões de grant simuladas, comprovando interseção SQL, ambiguidade e teto HTTP.
Eles não equivalem a integração com o Keycloak real ou com todo o schema APP32.
Cluster em backups/mcp-reference-pg-us59cvoy, loopback porta 57138, desligado após
TEST_EXIT=0. O primeiro orquestrador ficou aguardando pipes herdados do pg_ctl;
os testes foram concluídos em outro processo e a parada do cluster confirmada.
O orquestrador original terminou com erro após a parada, sem novo servidor ativo.
Regressão adicional: 13 testes aprovados de autorização de principal, surface
de atividades e task_ops. Total selecionado: 60 testes; não é a suíte completa.
