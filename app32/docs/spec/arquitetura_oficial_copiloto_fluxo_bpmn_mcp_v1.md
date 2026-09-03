# Arquitetura Oficial — Copiloto de Fluxo BPMN MCP

Status: canônico  
Classe: SPEC
Atualizado em: 2026-08-01

## 1. Objetivo

Definir a arquitetura oficial do copiloto de Fluxo BPMN do APP32 para:

- analisar diagramas BPMN por tenant;
- apontar gaps de modelagem e operação;
- sugerir automações e conexões APP32/MCP/API;
- manter intervenção humana obrigatória antes da publicação.

## 2. Princípios

1. **BPMN é a fonte canônica do Fluxo**
2. **MCP opera sobre read model derivado**
3. **layout visual não é automatizado pelo copiloto**
4. **gateway complexo exige revisão humana**
5. **company_id é obrigatório em toda leitura**
6. **sugestão de automação não equivale a publicação**

## 3. Componentes oficiais

### 3.1 Parser de grafo BPMN
Arquivo:
- `C:\GestaoVersus\app32\app32\services\process_bpmn_graph_service.py`

Responsabilidade:
- parsear `bpmn_xml`;
- extrair nós, edges e lanes;
- identificar atividades executáveis, gateways e eventos;
- preparar metadados para análise MCP.

### 3.2 Serviço do copiloto de fluxo
Arquivo:
- `C:\GestaoVersus\app32\app32\services\process_flow_copilot_service.py`

Responsabilidade:
- cruzar BPMN com `ProcessRoutine` e `ProcessActivityExecutionContract`;
- calcular gaps de lane, POP e contrato;
- sugerir templates APP32;
- sugerir integrações externas;
- sugerir automações internas existentes.

### 3.3 Tooling MCP do copiloto
Arquivo:
- `C:\GestaoVersus\app32\app32\src\core\mcp_process_flow_tools.py`

Tools oficiais:
- `get_process_modeling_package_tool`
- `analyze_process_flow_copilot_tool`
- `suggest_process_flow_activity_automation_tool`
- `publish_approved_process_modeling_package_tool` — exclusiva da surface `admin`, após gate humano.

## 4. Read model derivado oficial

O copiloto deve operar sobre um grafo derivado com:

- `nodes`
- `edges`
- `lanes`
- `activities`
- `gateways`
- `events`

Cada atividade deve expor no mínimo:
- `element_id`
- `element_name`
- `element_type`
- `lane_name`
- `incoming_count`
- `outgoing_count`
- `has_pop`
- `current_contract`
- `automation_score`
- `automation_candidates`
- `integration_candidates`
- `warnings`

## 5. Regra oficial de automação

O copiloto pode sugerir:

- `human_task`
- `open_form`
- `open_app32_page`
- `mcp_task`
- `api_task`
- `ai_task`
- `ai_decision`

Mas **não pode**:
- publicar contrato automaticamente;
- assumir executor final apenas por texto de lane;
- reescrever layout do BPMN;
- fechar split/join ambíguo sem humano.

## 6. Regra oficial de intervenção humana

Intervenção humana é obrigatória quando houver:

- gateway com múltiplas saídas sem condição clara;
- mistura de fan-in e fan-out no mesmo gateway;
- atividade sem lane;
- atividade sem POP em fluxo crítico;
- proposta de integração externa sensível;
- impacto financeiro ou regulatório.

## 7. Decisão oficial sobre agentes

Não nasce agente novo nesta fase.

Responsabilidade oficial:
- `@ARQUITETO`: semântica BPMN, boundaries e governança;
- `@AI_ENGINEER`: copiloto MCP, heurísticas e sugestões;
- `@BACKEND_API`: surface, catálogo e contratos MCP.

## 8. Registro oficial em catálogo MCP

O catálogo MCP do projeto deve reconhecer a feature:
- `processos_copiloto_fluxo`

E as capabilities:
- `get_process_modeling_package_tool`
- `analyze_process_flow_copilot_tool`
- `suggest_process_flow_activity_automation_tool`

### 8.1 Separação por surface

- `user`/Squad Cliente: relê pacote, analisa, coleta evidências e entrega AS-IS; não publica;
- `admin`/Squad Versus: relê, revisa TO-BE e pode publicar após confirmação humana explícita;
- `resolve_app32_instruction_bundle_tool` pertence a `identity_self_service` para continuar disponível após a seleção do harness operacional;
- áudio e documentos brutos são processados pela IA/CLI local do cliente; o MCP recebe `process_modeling_intake.v1`, não o arquivo bruto.

## 9. Ordem de evolução

1. leitura e análise do fluxo;
2. sugestões de automação/conexão;
3. rascunho de contrato de execução;
4. revisão humana;
5. publicação manual controlada.

## 10. Catálogo oficial de artefatos de atividade

O APP32 passa a reconhecer seis tipos canônicos de artefato associados a elementos executáveis do BPMN:

| Código | Nome | Cor canônica no Modeler | Finalidade |
|---|---|---|---|
| `pop` | POP | azul `#2563eb` / fundo `#eff6ff` | instrução operacional, mídia e conhecimento |
| `form` | FORM | violeta `#7c3aed` / fundo `#f5f3ff` | coleta estruturada de dados |
| `check` | CHECK | verde `#059669` / fundo `#ecfdf5` | verificação, evidência e aceite item a item |
| `ai` | IA | laranja `#ea580c` / fundo `#fff7ed` | task/gateway executado ou assistido pelo Sapiens |
| `data_in` | IN | ciano `#0891b2` / fundo `#ecfeff` | conexão de dados recebidos |
| `data_out` | OUT | rosa `#e11d48` / fundo `#fff1f2` | conexão de dados enviados |

Regras oficiais:

- o artefato é externo à atividade e ligado por associação BPMN;
- sua representação visual parte da mesma base hoje usada pelo POP, alterando cor, ícone e nome;
- uma atividade aceita zero ou vários artefatos, inclusive mais de um do mesmo tipo quando houver finalidade distinta;
- o vínculo não altera a semântica nativa do elemento BPMN;
- criar o marcador não abre nem redireciona para o editor; dois cliques no artefato abrem diretamente seu editor especializado;
- POP, FORM e CHECK podem coexistir com IA, IN e OUT na mesma atividade.

### 10.1 Contrato visual para documentos e Squads

- o tipo persistido e o vínculo com `bpmn_element_id` são a verdade semântica; cor, rótulo e ícone são linguagem de leitura;
- presença de marcador colorido não comprova que o artefato esteja configurado, versionado, publicado ou adequado;
- personalização de cor do elemento BPMN não altera o tipo do artefato;
- estado de execução usa overlay, contorno ou badge e não sobrescreve a cor canônica;
- os Squads avaliam necessidade, atividade vinculada, definição, versão, obrigatoriedade, completion policy, evidência e contribuição para objetivo/risco;
- o Squad Cliente valida como o artefato é usado; o Squad Versus valida sua necessidade e coerência metodológica; Engenharia trata divergência entre XML, vínculo, editor, runtime e Book.

## 11. Modelo canônico de definição e vínculo

A implementação deve separar quatro conceitos:

1. **definição do artefato** — configuração editável e versionada;
2. **vínculo com a atividade** — associação ao `bpmn_element_id`, ordem e obrigatoriedade;
3. **snapshot publicado** — versão imutável consumida por novas instâncias;
4. **execução do artefato** — estado, dados e evidências de uma instância específica.

### 11.1. Escopo e interação multipapel

- `execution_scope=activity` mantém uma execução independente por atividade e é o padrão retrocompatível;
- `execution_scope=process_instance` materializa uma única execução por definição e instância do processo, ainda que exista vínculo com várias atividades;
- cada vínculo declara sua `phase_key`, obrigatoriedade e se pode finalizar definitivamente o artefato (`can_finalize`);
- o gate da atividade consulta o estado da interação daquela execução de atividade, não apenas o status global do documento;
- cada gravação gera trilha imutável com `company_id`, instância, atividade, artefato, fase, ator e estados anterior/posterior;
- conclusão de fase não encerra o documento compartilhado; somente vínculo autorizado pode aprová-lo definitivamente;
- FORM, CHECK, IA, IN e OUT podem usar este escopo. IA compartilha contexto e resultados acumulados, mantendo cada chamada como interação auditável;
- autorização deve validar tenant, instância, atividade corrente e vínculo ativo da definição, sem confiar na atividade âncora que criou o documento.

Entidades lógicas propostas:

- `ProcessActivityArtifactDefinition`
  - `id`, `company_id`, `process_id`, `artifact_type`, `name`, `status`, `version`, `execution_scope`, `configuration_json`, timestamps;
- `ProcessActivityArtifactLink`
  - `id`, `company_id`, `process_id`, `bpmn_element_id`, `artifact_definition_id`, `display_order`, `is_required`, `completion_policy_json`;
- `ProcessActivityArtifactExecution`
  - `id`, `company_id`, `process_instance_id`, `activity_execution_id`, `artifact_definition_id`, `artifact_version`, `scope_key`, `status`, `input_json`, `output_json`, `evidence_json`, `started_at`, `completed_at`;
- `ProcessActivityArtifactInteraction`
  - `id`, `company_id`, `process_instance_id`, `activity_execution_id`, `artifact_execution_id`, `phase_key`, `action`, `actor_user_id`, `before_json`, `after_json`, `created_at`.

`ProcessRoutine` continua sendo a base legada do POP durante a migração. A camada canônica deve oferecer adaptador para que POPs existentes sejam expostos como artefatos sem duplicação nem quebra de URLs.

Toda consulta e mutação deve validar `company_id` em definição, vínculo, processo, instância e execução. Não é permitido confiar apenas em ids recebidos.

## 12. Contratos específicos por tipo

### 12.1. POP

- conteúdo rico, passos, imagens, vídeos e anexos;
- versão oficial e conteúdo adicional para IA;
- evidência configurável de leitura, ciência ou aceite.

### 12.2. FORM

- schema de seções e campos;
- tipos, validações e regras condicionais;
- resposta persistida por execução;
- mapeamento opcional de respostas para variáveis da instância;
- controle de edição após envio e trilha de auditoria.

### 12.3. CHECK

- itens ordenados e versionados;
- opções de resposta, comentário e evidência;
- política para item obrigatório, não aplicável e reprovação;
- cálculo de progresso e regra explícita de aceite.

### 12.4. IA

- tipo `task` ou `gateway`;
- objetivo, contrato de entrada/saída e instruções;
- surface e tools MCP autorizadas;
- autonomia, threshold de confiança e human gate;
- fallback humano, retry e evidência estruturada.

### 12.5. IN

- origem lógica, trigger e estratégia de autenticação;
- schema e mapeamento de entrada;
- idempotency key, timeout e política de erro;
- persistência do evento recebido e correlação com a instância.

### 12.6. OUT

- destino lógico, trigger e estratégia de autenticação;
- schema, template e mapeamento do payload;
- retry, idempotência e critério de entrega;
- persistência de request, response e confirmação.

Segredos nunca devem ser persistidos em `configuration_json`; o artefato referencia credenciais governadas por integration key ou secret store.

## 13. Editores e publicação

Cada tipo possui tela própria, visualmente coerente com sua cor semântica e baseada no shell já validado para POP.

Fluxo oficial:

```text
clicar no artefato no BPMN
→ abrir editor correto
→ editar rascunho
→ validar contrato específico
→ publicar versão
→ disponibilizar a versão somente para novas instâncias
```

O editor deve mostrar o processo e o `bpmn_element_id` de origem, permitir voltar ao fluxo e impedir publicação quando a configuração mínima do tipo estiver incompleta.

## 14. Runtime e regra de conclusão

Ao ativar uma atividade, o runtime deve materializar as execuções dos artefatos vinculados usando o snapshot publicado.

Estados mínimos:

- `pending`
- `in_progress`
- `waiting_external`
- `waiting_human`
- `completed`
- `failed`
- `skipped`, somente quando a política permitir.

Uma atividade só pode ser concluída quando:

- todos os artefatos obrigatórios satisfizerem sua `completion_policy`;
- FORM obrigatório possuir resposta válida e salva;
- CHECK obrigatório atender à regra de aceite;
- POP obrigatório possuir a evidência configurada;
- IA/IN/OUT obrigatório estiver concluído ou em fallback humano formalmente resolvido;
- a validação ocorrer em service, nunca apenas no frontend.

Finalização direta da instância não pode contornar esses gates. Override, quando permitido por RBAC, exige justificativa e auditoria.

## 15. Endereço eletrônico e acesso

A identidade do artefato e de suas respostas é interna e persistida no banco. A navegação autenticada recomendada é:

```text
/my-work/process-instance/{instance_id}?execution_id={activity_execution_id}&artifact_execution_id={artifact_execution_id}
```

Regras:

- a rota sempre resolve o tenant e a autorização no backend;
- URL pública permanente não é requisito nem fonte da verdade;
- acesso externo, quando necessário, usa token assinado, escopo mínimo, expiração e revogação;
- o link externo nunca expõe ids suficientes para acesso sem validação.

## 16. Assignment por atividade e Portal de Processos

O trabalho deve ser atribuído no nível da execução da atividade, não apenas no nível da instância.

Entidade lógica proposta:

- `ProcessExecutionAssignment`
  - `id`, `company_id`, `activity_execution_id`, `assignee_type`, `employee_id`, `team_id`, `role_key`, `status`, `assigned_at`, `claimed_at`, `completed_at`.

Resolução oficial:

1. atribuição explícita ao colaborador;
2. claim válido de uma fila de equipe;
3. regra de papel/equipe do contrato;
4. fallback governado para responsável da instância.

O Portal de Processos deve expor:

- resumo pessoal no mapa geral;
- badge `N atividades para você` nos processos pertinentes;
- seção `Minhas execuções neste processo` no detalhe;
- cards por atividade acionável com instância, atividade, SLA, progresso de artefatos e ação `Continuar`;
- separação visual entre executar atividade existente e iniciar nova instância.

Atividades automáticas de IA/IN/OUT não entram na fila pessoal. Entram somente quando gerarem revisão, aprovação, exceção ou fallback humano.

## 17. Contrato com Sapiens

O artefato `IA` é a superfície de configuração fluida do AI Task / AI Gateway com Sapiens. Ele não cria um motor paralelo:

- o BPMS conserva o estado e decide transições válidas;
- o contrato da atividade define objetivo e completion rule;
- o artefato IA define execução, tools, autonomia, confiança e fallback;
- o runtime packet agrega POP, FORM, CHECK, dados IN, contexto da instância e outputs anteriores;
- o Sapiens executa via MCP tenant-safe e devolve resposta estruturada;
- o service valida evidência e somente então conclui ou encaminha a atividade.

## 18. Critérios de aceite arquitetural

A evolução estará aderente quando:

- os seis tipos puderem ser associados externamente ao mesmo elemento BPMN;
- cada tipo abrir seu editor correto e publicar versão validada;
- instâncias preservarem o snapshot da versão iniciada;
- respostas de FORM e CHECK ficarem auditáveis por instância/atividade;
- a conclusão respeitar todos os artefatos obrigatórios;
- IA/IN/OUT registrarem request, output, falha e correlação;
- assignment e consultas do Portal forem escopados por `company_id`;
- o usuário chegar do Portal à atividade correta sem procurar manualmente a instância;
- automações só aparecerem como trabalho humano quando houver gate ou exceção;
- POPs atuais continuarem funcionais durante a migração.

## 19. Ordem oficial de concretização

1. compatibilidade de POP e modelo genérico de definição/vínculo/versionamento;
2. editores e runtime de FORM e CHECK;
3. execução de artefatos e gates de conclusão na shell da instância;
4. assignment por atividade e projeção no Portal/Meu Trabalho;
5. artefato IA integrado ao contrato MCP/Sapiens;
6. artefatos IN/OUT e motor resiliente de integrações;
7. telemetria, analytics e hardening multi-tenant/E2E.

## 20. Estado de implementação

### Fundação concluída em 2026-08-01

- modelos `ProcessActivityArtifactDefinition`, `ProcessActivityArtifactLink` e `ProcessActivityArtifactExecution`;
- migração `20260801_1500` com constraints, índices e backfill dos POPs BPMN existentes;
- service tenant-safe de definição, vínculo, listagem, snapshot, materialização e gate;
- adaptador de `ProcessRoutine` integrado à criação/abertura atual do POP;
- cobertura unitária dos seis tipos, snapshot legado, gate e constraints multi-tenant.

### FORM/CHECK e shell concluídos em 2026-08-01

- APIs de criação, edição, publicação, arquivamento e consulta de artefatos;
- validação específica dos schemas de FORM e CHECK;
- telas próprias FORM/violeta e CHECK/verde;
- materialização automática dos artefatos ao iniciar a execução da atividade;
- preenchimento e persistência de FORM/CHECK dentro da shell da instância;
- gate de conclusão da atividade para artefatos obrigatórios;
- bloqueio de conclusão automática por IA quando houver artefato obrigatório pendente.

### Assignment e Portal concluídos em 2026-08-01

- modelo `ProcessExecutionAssignment` por execução de atividade, escopado por `company_id`;
- alvos canônicos por colaborador, equipe ou função, com fallback governado da instância;
- ciclo `assigned/claimed/completed/cancelled` sincronizado com a execução;
- `Meu Trabalho` passa a respeitar primeiro o assignment da atividade e abre a shell com `execution_id`;
- Portal mostra `N para você` no mapa e `Minhas execuções` no detalhe do processo;
- somente atividades humanas acionáveis, gates, exceções ou fallbacks humanos entram na projeção pessoal.

### Linguagem visual do modelador concluída em 2026-08-01

- seletor de cor contextual para tarefas, subprocessos, gateways, eventos, pools/lanes, dados, anotações e conexões;
- paleta curta com preenchimentos claros e contornos contrastantes;
- padrão semântico por tipo, opção de personalização e restauração sem cor;
- persistência via `modeling.setColor` no XML BPMN/DI, mantendo exportação e reabertura;
- artefatos POP/FORM/CHECK/IA/IN/OUT preservam suas cores canônicas;
- estado de execução permanece uma camada separada, por overlay/contorno/badge, sem sobrescrever a cor autoral.
- o Book reaplica as cores canônicas de POP, FORM, CHECK, IA, IN e OUT ao snapshot SVG com base nos IDs e nomes do XML BPMN, inclusive para snapshots anteriores;
- novos salvamentos persistem as cores dos artefatos no BPMN DI por `modeling.setColor`, reduzindo divergência entre Modeler, exportação e Book.

### 12.7 Visão integrada no detalhe do processo

O detalhe do processo deve disponibilizar uma navegação plana, em uma única linha, com as visões `SIPOC`, `Recursos`, `Fluxo`, `POP`, `Formulários`, `Checklists`, `IA`, `Rotinas` e `Indicadores`. Em larguras reduzidas, a linha é preservada com rolagem horizontal, sem transformar os artefatos em um segundo nível de menu.

- `Formulários` e `Checklists` listam definições versionadas do processo e suas atividades BPMN vinculadas;
- a edição abre o editor especializado do tipo de artefato;
- a criação continua no Modeler, pois o vínculo com uma atividade ou gateway é obrigatório e contextual;
- `IA` apresenta os contratos ativos de AI Task e AI Gateway e direciona sua configuração ao elemento correspondente no Modeler;
- todas as consultas permanecem delimitadas por `company_id` e `process_id`.

### Shell UI dos editores concluída em 2026-08-01

- FORM, CHECK, IN e OUT usam uma shell responsiva comum;
- cabeçalho reúne tipo, processo, elemento BPMN, status, retorno ao Modeler, salvar e publicar;
- painel principal concentra conteúdo/contrato e a lateral concentra identificação, vínculo e governança;
- cores canônicas permanecem por tipo: FORM violeta, CHECK verde, IN ciano e OUT rosa;
- folha de estilo é carregada pelo bloco `head` do layout com versionamento de asset.
- o POP aberto pelo marcador BPMN entra em modo focado, ocultando resumo e abas do processo, mas preservando o editor legado e o retorno direto ao Modeler;
- o Modeler usa cabeçalho e ribbon compactos, mantendo arquivo, visualização, modelagem e orientação contextual sem reduzir desnecessariamente o canvas.

Ainda não fazem parte das ondas concluídas:

- dispatchers operacionais dos artefatos IA/IN/OUT;
- enforcement do gate na finalização administrativa direta da instância.

Esses itens devem avançar em ondas posteriores, sem reabrir o modelo canônico desta fundação.

### Publicação MCP do pacote aprovado

- capability canônica: `publish_approved_process_modeling_package_tool`;
- entrada: `company_id`, `process_id`, pacote estruturado e `human_gate_confirmed=true`;
- escopo: perfil, BPMN publicado, POP legado adaptado e artefatos versionados com vínculos BPMN;
- garantias: escopo por tenant, validação do hash BPMN, idempotência e arquivamento da versão anterior do mesmo artefato;
- permissão: `processes.ai_assistant.execute`, risco alto e gate humano obrigatório.
