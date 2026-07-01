# SPEC — Plano de Aderência APP32 à Separação Objeto Canônico / Camada Consultiva

**Classe documental:** SPEC  
**Status:** Plano oficial de execução da Fase 02 v1  
**Data:** 2026-06-29  
**Origem:** `app32/docs/spec/separacao_objeto_canonico_camada_consultiva_evolutiva_v1.md`  
**Escopo:** APP32, Método Versus, projetos, processos, rotinas, indicadores, painel, squads, agentes e MCP  

---

## 1. Decisão

A Fase 02 deve começar por uma adequação arquitetural: garantir que o APP32 represente a operação da empresa como **Objeto Canônico** e aplique a metodologia Versus como **Camada Consultiva/Evolutiva**, sem duplicar a gestão do cliente.

Esta SPEC define o primeiro mapa de aderência, gaps e backlog técnico.

---

## 2. Nota de governança da execução

A execução possui mais de três etapas e, pela governança do Gestão Versus, deveria ter sido materializada em cards reais no projeto `AA.J.1`.

Tentativas realizadas:

1. criação de cards via `aa_j_31_step_wrapper.py materialize`;
2. nova tentativa com permissão elevada;
3. ambas encerraram por timeout SSH.

Decisão operacional:

- seguir em fallback controlado;
- documentar o plano localmente;
- não executar deploy;
- não alterar produção;
- materializar ou reconciliar cards reais em `AA.J.1` quando a conexão SSH/MCP estiver estável.

---

## 3. Inventário inicial por domínio

### 3.1. Identidade, arquitetura e maturação estratégica

Arquivos observados:

- `app32/models/strategy_alignment.py`
- `app32/services/strategy_alignment_n1_service.py`
- `app32/services/structuring_journey_service.py`
- `app32/services/strategic_management_panel_service.py`

Leitura:

- o APP32 já possui separação conceitual madura neste domínio;
- `OrganizationalIdentity` funciona como Objeto Canônico;
- `StrategyMaturationItem` funciona como zona de maturação/overlay antes de promoção para dado canônico;
- `StructuringJourneyService` já declara explicitamente que é read model e não cria novo estado transacional;
- `StrategicManagementPanelService` já separa audiência `client` e `consultant`.

Conclusão:

> Este domínio é a principal referência positiva para a Fase 02.

---

### 3.2. Processos, rotinas e jornadas

Arquivos observados:

- `app32/models/process.py`
- `app32/models/routine.py`
- `app32/models/work_journey.py`
- `app32/services/routine_journey_binding_service.py`
- `app32/services/structuring_journey_service.py`
- `app32/services/process_*`
- `app32/services/work_journey_*`

Leitura:

- `ProcessArea`, `MacroProcess`, `Process`, `ProcessRoutine`, `Routine`, `ProcessInstance` e `WorkJourney` são Objetos Canônicos;
- `StructuringJourneyService` é Camada Consultiva/Evolutiva;
- `RoutineJourneyBinding` é vínculo operacional entre rotina e jornada;
- há sinal de mistura no próprio `Process`, que contém `kanban_stage`, `structuring_level` e `performance_level`;
- há ambiguidade em `ProcessStep.routine_id`, pois o comentário indica que pode referenciar `routines` ou `process_routines`.

Conclusão:

> O domínio está funcional, mas precisa separar melhor campos operacionais de campos metodológicos.

---

### 3.3. Projetos, tarefas, urgências e Business Review

Arquivos observados:

- `app32/models/project.py`
- `app32/services/project_service.py`
- `app32/services/project_task_service.py`
- `app32/services/project_mcp_service.py`
- `app32/services/project_task_mcp_service.py`
- `app32/services/strategic_management_panel_service.py`

Leitura:

- `Project` e `ProjectTask` são Objetos Canônicos;
- o sistema já suporta prioridade operacional, inclusive `urgent` em tarefas;
- não foi identificado modelo ou service explícito para `Necessidade Urgente` como leitura consultiva;
- não foi identificado modelo ou service explícito para Business Review metodológico;
- há campos legados textuais como `Project.owner` e `ProjectTask.who`, convivendo com vínculos melhores por colaborador/employee;
- a conexão entre indicador e tarefa ainda aparece em alguns pontos por marcador textual em `notes`, como `APP32_INDICATOR_LINK`.

Conclusão:

> Projetos estão bons como base canônica, mas falta o overlay consultivo para Necessidade Urgente e Business Review.

---

### 3.4. Indicadores, painel e linha de visada

Arquivos observados:

- `app32/models/indicator.py`
- `app32/models/strategy_alignment.py`
- `app32/services/indicator_service.py`
- `app32/services/indicator_link_map_service.py`
- `app32/services/strategic_management_panel_service.py`

Leitura:

- `Indicator`, metas e medições são Objetos Canônicos;
- `IndicatorLineOfSight` é boa estrutura de vínculo/rastreabilidade;
- o painel estratégico atua como cockpit consultivo/evolutivo;
- há uso residual de link por texto em notas em parte do painel, que deve ser substituído por vínculo estruturado.

Conclusão:

> A direção está correta, mas vínculos textuais precisam ser eliminados gradualmente.

---

### 3.5. Squads, agentes, orquestrador e MCP

Arquivos observados:

- `app32/models/ai_agent.py`
- `app32/models/ai_capability.py`
- `app32/models/agent_action.py`
- `app32/models/agent_action_backlog_link.py`
- `app32/services/squad_runtime_bootstrap_service.py`
- `app32/services/ai_mcp_console_service.py`
- `app32/services/tool_first_catalog_service.py`
- `app32/services/mcp_feature_catalog_service.py`

Leitura:

- há estrutura relevante para agentes, capabilities, backlog e MCP;
- a governança de surfaces, human gate e readiness já existe;
- ainda falta uma regra explícita de que pesquisa externa/benchmark alimenta a Camada Consultiva/Evolutiva e não substitui o Objeto Canônico;
- também falta um contrato explícito que classifique cada capability por camada de atuação: canônica, consultiva ou ambas.

Conclusão:

> A base de IA/MCP está avançada, mas precisa herdar formalmente a separação das duas camadas.

---

## 4. Congruências encontradas

1. **Multi-tenancy já é predominante**  
   A maior parte dos modelos críticos usa `company_id`.

2. **Read model consultivo já existe**  
   `StructuringJourneyService` é exemplo claro de camada evolutiva sem criar estado transacional paralelo.

3. **Maturação antes de promoção já existe**  
   `StrategyMaturationItem` é congruente com a metodologia: algo pode estar em amadurecimento antes de virar dado canônico.

4. **Painel já reconhece duas audiências**  
   `StrategicManagementPanelService` aceita `audience=client|consultant`.

5. **Processos e rotinas já têm base canônica forte**  
   Há objetos reais para áreas, macroprocessos, processos, POPs, rotinas, instâncias, jornadas e vínculos.

6. **MCP e agents já possuem noção de gate e readiness**  
   Isso conversa com a governança evolutiva.

---

## 5. Incongruências e gaps

### G1 — Falta overlay formal para Necessidade Urgente

Hoje a urgência aparece como prioridade operacional em tarefas ou instâncias, mas não há leitura consultiva explícita.

Decisão:

- não criar um projeto paralelo de Necessidade Urgente;
- criar overlay/vínculo consultivo sobre `Project`, `ProjectTask` ou outro Objeto Canônico afetado.

---

### G2 — Falta Business Review metodológico estruturado

Não foi identificado modelo/service dedicado ao Business Review da metodologia Versus.

Decisão:

- Business Review deve ser camada consultiva;
- deve se vincular a projetos, tarefas, indicadores, processos, riscos, custos e ganhos;
- toda Necessidade Urgente deve poder gerar ou alimentar Business Review.

---

### G3 — Campos metodológicos misturados no modelo `Process`

Campos como `kanban_stage`, `structuring_level` e `performance_level` estão no Objeto Canônico `Process`.

Decisão:

- avaliar se devem migrar para overlay consultivo ou perfil estruturado;
- não remover sem migração;
- manter compatibilidade até haver plano de dados.

---

### G4 — Responsáveis ainda misturam texto livre e vínculo estruturado

Exemplos:

- `Project.owner`;
- `ProjectTask.who`;
- `Process.responsible`;
- campos novos com `employee_id` convivem com legados.

Decisão:

- preservar campos legados por compatibilidade;
- priorizar vínculos estruturados por `employee_id`;
- tratar texto livre como fallback ou campo histórico.

---

### G5 — Vínculos por texto em `notes`

O painel ainda identifica links entre indicador e tarefa por marcador textual.

Decisão:

- usar vínculos estruturados como `IndicatorEntityLink` ou tabela equivalente;
- não criar novos links sem estrutura;
- migrar marcadores textuais em etapa controlada.

---

### G6 — Ambiguidade em `ProcessStep.routine_id`

O comentário indica que `routine_id` pode referenciar `routines` ou `process_routines`.

Decisão:

- separar semanticamente POP/atividade de processo e rotina recorrente;
- definir vínculo explícito e evitar campo polimórfico sem tipo.

---

### G7 — Alguns objetos de gap/workflow permitem `company_id` nulo

Exemplo:

- `WorkflowGapCandidate.company_id` está nullable.

Decisão:

- para uso operacional multi-tenant, `company_id` deve ser obrigatório;
- exceções só devem existir para triagem pré-tenant com contrato explícito.

---

### G8 — Pesquisa externa dos agentes ainda não tem contrato metodológico

A metodologia agora exige pesquisa profunda e ampla para boas práticas, benchmarks e temas externos.

Decisão:

- criar contrato de pesquisa externa;
- classificar resultados como subsídio consultivo;
- exigir fonte, data, síntese e vínculo com objeto canônico quando virar recomendação.

---

## 6. Backlog técnico priorizado

### P0 — Base de segurança arquitetural

1. Criar matriz oficial de classificação por modelo/service:
   - Canônico;
   - Consultivo/Evolutivo;
   - Vínculo/Overlay;
   - Infra/Runtime.

2. Revisar objetos com `company_id` nulo em domínios operacionais.

3. Definir regra para campos legados textuais de responsável.

---

### P1 — Projetos, urgências e Business Review

1. Criar SPEC derivada de Projetos, Necessidades Urgentes e Business Review.

2. Definir overlay consultivo:
   - entidade mínima;
   - vínculos com `Project` e `ProjectTask`;
   - impacto financeiro/operacional;
   - risco;
   - ganho esperado;
   - decisão;
   - evidência.

3. Criar service de classificação consultiva sem lógica em rota.

4. Criar read model para cockpit consultivo.

---

### P1 — Processos, rotinas e jornadas

1. Criar SPEC derivada de Processos, Rotinas e Jornadas.

2. Decidir destino de:
   - `Process.kanban_stage`;
   - `Process.structuring_level`;
   - `Process.performance_level`.

3. Resolver ambiguidade de `ProcessStep.routine_id`.

4. Formalizar diferença entre:
   - rotina operacional;
   - POP;
   - instância de processo;
   - jornada operacional;
   - jornada de estruturação.

---

### P1 — Squads, agentes, MCP e pesquisa externa

1. Criar SPEC derivada de Squads, Agentes, Orquestrador e Pesquisa Externa.

2. Classificar capabilities por camada:
   - lê/altera Objeto Canônico;
   - gera análise consultiva;
   - atua em ambas.

3. Criar contrato para pesquisa externa:
   - pergunta;
   - fontes;
   - data;
   - síntese;
   - benchmark;
   - recomendação;
   - vínculo com objeto canônico;
   - confiança;
   - decisão humana quando aplicável.

---

### P2 — Indicadores e painel

1. Eliminar novos vínculos por marcador textual em `notes`.

2. Migrar gradualmente links existentes para vínculo estruturado.

3. Separar explicitamente superfície operacional do indicador e cockpit consultivo do painel.

---

### P2 — Onboarding e setup

1. Criar SPEC derivada de Onboarding e Setup.

2. Separar:
   - cadastro canônico da empresa;
   - readiness consultivo;
   - setup MCP/Sapiens;
   - onboarding assistido.

---

## 7. Ordem recomendada de execução

1. **SPEC Projetos, Necessidades Urgentes e Business Review**  
   Motivo: é o maior gap frente ao paper e ao uso real do consultor.

2. **SPEC Processos, Rotinas e Jornadas**  
   Motivo: há mistura conceitual relevante e risco de modelagem polimórfica.

3. **SPEC Squads, Agentes, MCP e Pesquisa Externa**  
   Motivo: precisa normatizar como agentes atuam nas duas camadas.

4. **Matriz de classificação técnica dos modelos/services atuais**  
   Motivo: vira checklist para refatoração sem quebrar produção.

5. **Implementação incremental dos overlays**  
   Motivo: evita migração grande e reduz risco operacional.

---

## 8. Critérios de aceite da Fase 02

A Fase 02 será considerada bem estruturada quando:

1. todo domínio crítico tiver classificação por camada;
2. Necessidade Urgente não duplicar Projeto;
3. Business Review existir como camada consultiva rastreável;
4. processos não misturarem operação e maturidade sem intenção explícita;
5. agentes e squads declararem quando atuam no canônico, no consultivo ou em ambos;
6. pesquisa externa tiver contrato e fonte;
7. `company_id` estiver protegido em todo fluxo operacional;
8. UI do cliente permanecer operacional e simples;
9. cockpit consultivo permitir condução metodológica sem planilha paralela;
10. não houver deploy sem janela controlada pelo patrocinador técnico.

---

## 9. Próxima decisão arquitetural

A próxima decisão deve ser:

> **Como modelar a Necessidade Urgente e o Business Review sem criar um segundo sistema de projetos?**

Recomendação inicial:

- criar um overlay consultivo vinculado a `Project`/`ProjectTask`;
- manter `Project` como Objeto Canônico;
- manter `ProjectTask.priority = urgent` como urgência operacional;
- criar leitura Versus separada para impacto, risco, ganho, custo, investimento, decisão e aprendizado estrutural.

