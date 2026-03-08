# Workflow Engine V3

## Objetivo
Transformar o runtime atual em um modelo **workflow-first**, onde:

1. a LLM descobre a intenção;
2. o catálogo de workflows ranqueia candidatos;
3. o fluxo determinístico coleta parâmetros;
4. a execução real ocorre via service/API/MCP.

## Incremento entregue na Fase 1

### Novo pacote
`src/intelligence/workflows/`

#### Módulos
- `direct_execution.py`
  - dispatcher/registry das execuções determinísticas imediatas
  - centraliza o roteamento por `action_key` para handlers síncronos do runtime conversacional
- `company_selection.py`
  - coordinator genérico da seleção de empresa operacional (`awaiting_operation_company`)
  - centraliza decisão de prompt inicial, validação da escolha e propagação do contexto de empresa selecionada
- `confirmation.py`
  - coordinator genérico da confirmação final (`awaiting_confirmation`)
  - centraliza cancelamento, execução direta, delegação para prompt de execução e reconfirmação com ajuste de payload
- `contracts.py`
  - contratos Pydantic do núcleo:
    - `WorkflowDefinition`
    - `WorkflowFieldDefinition`
    - `WorkflowMatch`
    - `WorkflowDiscoveryRequest`
    - `WorkflowDiscoveryResult`
- `normalization.py`
  - normalização, tokenização e raízes léxicas reutilizáveis
- `registry.py`
  - conversão de `AgentMenuOption` em workflows acionáveis
  - deduplicação por código, priorizando escopo da empresa
  - cache local do índice semântico por catálogo montado
- `matcher.py`
  - descoberta híbrida:
    - `LexicalWorkflowMatcher`
    - `SemanticWorkflowMatcher`
    - `HybridWorkflowMatcher`
  - suporte a rerank opcional sobre o top de candidatos
- `runtime.py`
  - fachada do runtime para descoberta sobre catálogo vindo do menu atual
  - cache de catálogos/registries por snapshot do menu
- `semantic_index.py`
  - perfis semânticos pré-computados por workflow
  - tokens, raízes e bigramas cacheados para ranking semântico
- `reranker.py`
  - reranker heurístico real sobre o top-k do matcher híbrido
  - pronto para futura troca por reranker LLM
- `evaluation.py`
  - suíte utilitária para medir assertividade do discovery
  - produz relatório de acerto por caso de teste
- `session.py`
  - contrato de estado transitório do workflow a partir de `AgentMenuSession`
- `session_runtime.py`
  - runtime unificado de navegação da sessão
  - centraliza snapshot, stack de retorno, restore e renderização do prompt atual
- `field_collection.py`
  - coordinator genérico da coleta de parâmetros (`awaiting_fields`)
  - centraliza merge de respostas numeradas, cálculo de faltantes e ajuste contextual por ação
- `summary.py`
  - coordinator do fluxo de resumo:
    - período
    - empresa
    - colaborador
    - status
    - decisão de execução/retorno
- `handlers/summary_handler.py`
  - handler dedicado da execução final do resumo
  - consolida validação, escopo da empresa e montagem do relatório
- `handlers/project_task_handler.py`
  - handlers dedicados para:
    - `project_task.create`
    - `project_task.complete`
  - consolida resolução de escopo, normalização do payload e resposta final
- `handlers/process_instance_handler.py`
  - handler dedicado da execução de `process_instance.complete`
  - consolida parsing do código, conclusão determinística e resposta final
- `handlers/my_work_handler.py`
  - handler dedicado das consultas `my_work.*`
  - consolida resolução de escopo, período e montagem do relatório final
- `handlers/onboarding_handler.py`
  - handlers dedicados para:
    - `onboarding.status`
    - `onboarding.go_live_check`
    - `onboarding.start`
    - `onboarding.diagnose`
  - consolida resolução de empresa, leitura de métricas e respostas operacionais do onboarding
- `handlers/meeting_handler.py`
  - handlers dedicados para:
    - `meeting.schedule`
    - `meeting.start`
    - `meeting.summarize`
  - consolida escopo de empresa, parsing de data/hora, persistência do draft e leitura estruturada da reunião
- `schemas/summary.py`
  - schema canônico do payload de execução de resumo
- `schemas/project_task.py`
  - schemas canônicos de:
    - criação de atividade
    - conclusão de atividade
- `schemas/process_instance.py`
  - schema canônico do payload de conclusão de instância de processo
- `schemas/my_work.py`
  - schema canônico da ação de consulta `my_work.*`
- `schemas/onboarding.py`
  - schemas canônicos de entrada para `onboarding.start` e `onboarding.diagnose`
- `schemas/meeting.py`
  - schema canônico do payload de agendamento de reunião
- `presenters/summary_presenter.py`
  - formatação dos prompts do wizard de resumo
- `presenters/confirmation_presenter.py`
  - formatação da confirmação final dos workflows
- `selection.py`
  - coordinator genérico para seleção assistida (`awaiting_item_selection`)
- `schemas/selection.py`
  - contrato do contexto oculto de seleção assistida
- `schemas/field_collection.py`
  - contrato canônico dos campos obrigatórios de workflow
- `schemas/company_selection.py`
  - contratos canônicos da lista e do contexto oculto de seleção de empresa
- `presenters/selection_presenter.py`
  - formatação do prompt de seleção assistida
- `presenters/field_collection_presenter.py`
  - formatação do prompt de coleta de campos pendentes
- `presenters/company_selection_presenter.py`
  - formatação do prompt de seleção operacional de empresa

### Integração inicial
`src/intelligence/menu_engine.py`

O método `_match_options_by_keywords(...)` agora delega a descoberta ao
`WorkflowRuntime`, reduzindo acoplamento e abrindo espaço para:

- matcher híbrido;
- rerank por LLM/opcional;
- coleta de parâmetros desacoplada;
- sessão de workflow separada do menu legado.

Na evolução da Fase 4, o runtime de discovery passou a operar em camadas:

1. `LexicalWorkflowMatcher`
   - mantém match explícito por código, título, palavra-chave e `action_key`;
2. `SemanticWorkflowMatcher`
   - usa descrição, exemplos de intenção, campos obrigatórios e raízes léxicas;
   - permite recuperar intenções próximas mesmo sem phrase match exato;
3. `HybridWorkflowMatcher`
   - consolida score lexical + score semântico;
   - aceita reranker opcional para desempate/repriorização dos melhores candidatos.

Na Fase 4.2, o runtime também passou a expor telemetria do discovery em
`WorkflowDiscoveryResult.telemetry`, incluindo:

- quantidade de matches por estágio;
- top candidatos léxicos;
- top candidatos semânticos;
- top final após rerank;
- deltas aplicados pelo reranker;
- workflow final selecionado e motivos.

Na Fase 4.3, essa telemetria passou a ser propagada também para o fluxo
conversacional:

- `MenuInterceptResult` agora transporta `metadata` estruturada;
- respostas interceptadas pelo `menu_engine` passam a carregar:
  - estágio do intercept;
  - workflow selecionado;
  - trace compacto do discovery híbrido;
- `run_agent_with_context(...)` propaga `menu_metadata` para as respostas;
- logs em `AgentMessage.metadata_json` passam a registrar o contexto de
  discovery também em Web, Telegram e WhatsApp.

Na evolução seguinte, o discovery passou a aceitar também um **reranker LLM
real e plugável**:

- `LLMWorkflowReranker` opera apenas sobre o top-k já fechado pelo catálogo;
- o fallback padrão permanece seguro em `HeuristicWorkflowReranker`;
- `WorkflowRuntime` pode habilitar o reranker LLM por configuração,
  sem abrir mão do catálogo determinístico;
- a telemetria agora informa também o `reranker_kind` efetivamente usado.

Na camada seguinte de hardening, o discovery implícito passou a aplicar uma
**política de confiança** antes de auto-selecionar um workflow:

- vitória isolada segue seleção direta;
- múltiplos candidatos com margem forte podem seguir direto;
- candidatos próximos passam a cair em desambiguação;
- a decisão de confiança é adicionada à telemetria compacta do discovery.

Também foi evoluída a frente de **avaliação contínua do discovery**:

- métricas de `top_k_accuracy` e `mean_reciprocal_rank`;
- breakdown por domínio operacional;
- catálogo padrão de casos de avaliação;
- runner utilitário em `scripts/qa/run_workflow_discovery_evaluation.py`.

Na Fase 6, o runtime também passou a operar com **policy guard + HITL**:

- `WorkflowApprovalPolicyGuard` intercepta ações sensíveis em canais conversacionais;
- a execução gera `workflow_approval_request` com `resume_payload` seguro;
- aprovação e rejeição têm trilha auditável em `AgentAction.payload`;
- os endpoints operacionais retornam `approval_metadata` estruturado;
- há listagem operacional dedicada em `/api/agents/actions/workflow-approvals`;
- approvals pendentes agora possuem expiração/revalidação operacional;
- métricas agregadas por ação/canal/aprovador ficam disponíveis no backend operacional;
- payload visual de painel operacional de approvals já está disponível no backend;
- WhatsApp, Instagram e Telegram compartilham a mesma família de apresentação de chat;
- o fluxo conversacional grava `AgentMessage` outbound com o evento da aprovação.

Runbook operacional complementar:
- `docs/specifications/workflow_approval_runbook.md`

Além disso, o fluxo de `summary.*` já foi parcialmente migrado:

- o `menu_engine` atua como adapter de canal/sessão;
- o `SummaryWorkflowCoordinator` centraliza transições do wizard;
- o `SummaryWorkflowExecutionHandler` centraliza a execução final do resumo.

No domínio de projetos, a execução de `project_task.create` também já saiu do
`menu_engine` e passou a delegar para `ProjectTaskCreateExecutionHandler`.

No domínio de reuniões, a execução de `meeting.schedule` já delega para
`MeetingScheduleExecutionHandler`.

Também já foram extraídos:

- `MeetingStartExecutionHandler`
- `MeetingSummarizeExecutionHandler`

Agora os handlers extraídos também deixam de consumir diretamente o payload
legado e passam a convertê-lo para contratos Pydantic canônicos na camada
`src/intelligence/workflows/schemas/`.

Também foi iniciada a camada de `presenters/`, para tirar do `menu_engine`
texto de prompt/confirmação que pertence ao runtime conversacional.

Na evolução seguinte, os presenters também passaram a considerar o canal de
saída (`web`, `whatsapp`, `telegram`), com:

- sanitização específica por canal;
- títulos/prompts com estilo consistente;
- extração da montagem de `my_work.*` para presenter dedicado;
- `SessionPromptRenderer` repassando o canal corrente ao runtime de render.

Na Fase 8.4, os presenters passaram a usar uma camada comum de blocos conversacionais (`presenters/conversation_presenter.py`), padronizando:

- cabeçalhos e subtítulos premium;
- callouts de status (`info`, `warning`, `success`, `danger`);
- blocos de guidance/CTA reutilizáveis;
- mensagens mais consistentes entre web e família `chat` (`whatsapp`, `instagram`, `telegram`).

Na sequência, a lógica de `awaiting_item_selection` também passou a migrar para
o runtime dedicado, reduzindo ramificações específicas no `menu_engine`.

Agora a navegação genérica da sessão também começou a sair do `menu_engine`,
com `SessionNavigationRuntime` e `SessionPromptRenderer` assumindo:

- `back/restore`;
- `transition_state`;
- `snapshot` do estado atual;
- render do prompt corrente por status.

Também foi iniciada a migração da coleta genérica de parâmetros:

- `FieldCollectionCoordinator` passa a consolidar `merge_reply_payload(...)`;
- cálculo de faltantes deixa de ficar inline no `menu_engine`;
- o prompt de `awaiting_fields` passa a ser formatado por presenter dedicado.

Na sequência, a confirmação final também começou a sair do `menu_engine`:

- `ConfirmationCoordinator` centraliza as decisões de `sim` / `não` / ajuste;
- a resposta direta determinística e o fallback para prompt de execução ficam definidos por rota;
- o `menu_engine` fica responsável apenas por persistir/resetar sessão e devolver o intercept apropriado.

Também foi iniciada a extração do fluxo de empresa operacional:

- `OperationCompanySelectionCoordinator` decide quando a seleção é necessária;
- o contexto oculto `_operation_company_choices` passa a ter schema próprio;
- a escolha válida atualiza `_selected_company_id` e, quando aplicável, o contexto de `summary.*`.

Também começou a migração do bloco de execução direta:

- `DirectExecutionDispatcher` concentra o mapa `action_key -> handler`;
- `build_direct_execution_request(...)` e `build_handler_executor(...)` padronizam a montagem dos requests dos handlers V3;
- `_try_execute_direct_option(...)` passa a ser fachada sobre esse dispatcher;
- isso prepara a retirada progressiva de branches de execução do `menu_engine`.

Na sequência, as primeiras execuções diretas também começaram a sair do
`menu_engine` para handlers do V3:

- `project_task.complete`
- `process_instance.complete`
- `my_work.*`
- `onboarding.*`

## Regras desta etapa
- somente opções com `action_key` entram no catálogo de workflow;
- itens de navegação do menu continuam existindo, mas não competem como fluxo executável;
- o runtime de discovery agora é híbrido, mas ainda determinístico por padrão;
- o rerank segue opcional e desacoplado, preparando a futura entrada de LLM sem deixar a execução sair do catálogo.

## Próximos passos recomendados

### Fase 1.1 — concluída
- introduzir `WorkflowSessionState`
- separar descoberta de fluxo de navegação de menu

### Fase 1.2 — concluída
- migrar as transições do wizard de `summary.*` para coordinator dedicado
- manter compatibilidade do `menu_engine` como adapter

### Fase 1.3 — concluída
- consolidar `handlers/` por domínio
- iniciar por `summary_handler`
- extrair `project_task.create`
- extrair `meeting.schedule`

### Fase 1.4 — em andamento
- mover confirmação e prompts restantes do `menu_engine.py` para o runtime novo
- expandir schemas para fluxos com seleção assistida e confirmação explícita
- iniciar presenters por domínio para respostas por canal
- iniciar `SessionRuntime` unificado para back/restore/prompt atual
- extrair a coleta genérica de campos pendentes (`awaiting_fields`)
- extrair a confirmação final (`awaiting_confirmation`)
- extrair a seleção operacional de empresa (`awaiting_operation_company`)
- iniciar dispatcher/registry para execuções diretas

### Próxima frente sugerida
- conectar um reranker LLM real sobre o top-k do `HybridWorkflowMatcher`
- evoluir a camada semântica para embeddings/cache vetorial de workflows
- padronizar presenters por canal (`web`, `whatsapp`, `telegram`)

- `scripts/qa/run_workflow_discovery_evaluation.py`: runner utilitário com `--config` para validar discovery em development ou production.
