# SPEC — Projetos, Necessidades Urgentes e Business Review

**Classe documental:** SPEC
**Status:** Decisão oficial v1
**Data:** 2026-06-30
**Origem:**
- `app32/docs/spec/separacao_objeto_canonico_camada_consultiva_evolutiva_v1.md`
- `app32/docs/spec/plano_aderencia_app32_objeto_canonico_camada_consultiva_fase_02_v1.md`

**Escopo:** Projetos, tarefas, urgências operacionais, Necessidades Urgentes, Business Review, APP32, Método Versus, consultores, squads, agentes e MCP.

---

## 1. Decisão central

O APP32 não deve criar um segundo sistema de projetos para atender à metodologia Versus.

A decisão oficial é:

> **Projeto, Programa de Projetos e Tarefa continuam sendo Objetos Canônicos da empresa. Necessidade Urgente é a leitura metodológica de uma dor específica que sempre deve se materializar como projeto ou programa de projetos. Business Review é o registro do valor agregado pelo trabalho da Versus.**

Assim:

- para o cliente, uma demanda urgente deve ser conduzida como **projeto** ou **programa de projetos**, ainda que sua origem apareça como atividade, processo, reunião, indicador fora da meta ou ocorrência;
- para a Versus, essa mesma demanda pode ser classificada como **Necessidade Urgente**;
- toda Necessidade Urgente deve alimentar o **Business Review** como registro simples do valor agregado pela Versus.

---

## 2. Conceitos oficiais

### 2.1. Projeto

Projeto é um Objeto Canônico da empresa.

Representa uma iniciativa com objetivo, responsável, atividades, prazo, esforço, custo, evidências e acompanhamento.

No APP32, a base atual é:

- `Project`;
- `ProjectTask`;
- colaboradores da atividade;
- dependências;
- vínculos com indicadores, processos, reuniões e evidências.

### 2.2. Urgência operacional

Urgência operacional é uma característica do trabalho dentro da empresa.

Pode aparecer como:

- prioridade `urgent` em tarefa;
- prazo crítico;
- atraso;
- risco de perda;
- bloqueio;
- incidente;
- autuação;
- demanda de cliente;
- problema financeiro;
- ruptura de processo.

Urgência operacional não é, por si só, uma entidade metodológica.

### 2.3. Necessidade Urgente

Necessidade Urgente é uma leitura da Versus sobre uma dor específica que exige resposta objetiva no curto prazo.

Toda Necessidade Urgente deve se materializar como **projeto** ou **programa de projetos**.

Ela não substitui o projeto, a tarefa ou o processo. Ela qualifica metodologicamente a frente de execução.

Ela deve funcionar como um **overlay consultivo** sobre o projeto/programa e sobre os demais Objetos Canônicos afetados.

Exemplos:

- defesa de autuação fiscal;
- risco de bloqueio de caixa;
- perda relevante de cliente;
- retrabalho recorrente em processo crítico;
- falha operacional que gera custo;
- obrigação legal com prazo curto;
- indicador crítico fora da meta;
- gargalo que impede entrega essencial.

### 2.4. Business Review

Business Review é a leitura consultiva/evolutiva dos impactos de uma demanda, urgência, decisão ou projeto.

Toda Necessidade Urgente deve alimentar o Business Review.

O Business Review deve responder, no mínimo:

- qual fato ocorreu;
- qual Objeto Canônico está envolvido;
- qual é o impacto financeiro;
- qual é o impacto operacional;
- qual é o custo de agir;
- qual é o custo de não agir;
- qual é o ganho esperado;
- qual é o risco;
- qual decisão foi tomada;
- qual aprendizado estrutural será incorporado;
- qual processo, rotina, indicador ou controle deve ser criado, ajustado ou conscientemente mantido no estado atual.

---

## 3. Regra-mãe

Antes de criar qualquer funcionalidade sobre urgências, a arquitetura deve perguntar:

> **A empresa precisa operar isso como trabalho ou a Versus precisa interpretar isso como maturação?**

Se for trabalho:

- usar `Project`;
- usar `ProjectTask`;
- usar processo;
- usar rotina;
- usar indicador;
- usar reunião;
- usar ocorrência, se aplicável.

Se for interpretação:

- usar overlay de Necessidade Urgente;
- usar Business Review;
- usar leitura de risco, custo, ganho e retorno;
- usar backlog de estruturação quando houver aprendizado estrutural.

---

## 4. Modelo conceitual recomendado

### 4.1. Objetos Canônicos

Devem permanecer como base:

- `Project`;
- `ProjectTask`;
- `Process`;
- `ProcessInstance`;
- `Routine`;
- `Indicator`;
- `IndicatorData`;
- `Meeting`;
- `Employee`;
- evidências e anexos;
- registros financeiros quando aplicável.

### 4.2. Overlays consultivos

Devem ser criados como camada adicional:

1. **UrgentNeedOverlay**
   - classifica um fato como Necessidade Urgente;
   - aponta para um ou mais Objetos Canônicos;
   - registra criticidade, origem, contexto, risco e decisão.

2. **BusinessReviewRecord**
   - registra análise de custo, investimento, ganho, risco e retorno;
   - recebe entradas de Necessidades Urgentes e também de projetos relevantes;
   - mantém evidência de valor agregado e aprendizado.

3. **StructuralLearningLink**
   - registra se o fato gera ajuste estrutural;
   - vincula a processo, rotina, indicador, controle, política ou projeto de melhoria;
   - permite aceitar conscientemente o risco quando a decisão for manter o status atual.

Esses nomes são conceituais. A implementação final pode ajustar nomes técnicos, desde que preserve a separação.

---

## 5. Relações obrigatórias

Uma Necessidade Urgente deve poder se vincular a:

- projeto;
- tarefa;
- processo;
- instância de processo;
- rotina;
- indicador;
- reunião;
- ocorrência;
- documento/evidência;
- colaborador responsável;
- área;
- registro financeiro, se aplicável.

Um Business Review deve poder se vincular a:

- uma ou mais Necessidades Urgentes;
- projetos e tarefas;
- indicadores impactados;
- processos afetados;
- custos;
- ganhos;
- riscos;
- decisões;
- evidências;
- aprendizados estruturais.

---

## 6. Campos mínimos recomendados

### 6.1. Necessidade Urgente

Campos mínimos:

- `company_id`;
- `title`;
- `description`;
- `source_type`;
- `source_ref_id`;
- `canonical_object_type`;
- `canonical_object_id`;
- `urgency_level`;
- `criticality_level`;
- `business_impact_summary`;
- `operational_impact_summary`;
- `risk_summary`;
- `decision_status`;
- `responsible_employee_id`;
- `sponsor_user_id` ou cliente patrocinador, quando aplicável;
- `created_by_user_id`;
- `created_at`;
- `updated_at`;
- `closed_at`.

### 6.2. Business Review

Campos mínimos obrigatórios para preenchimento operacional:

- `identified_need` / Necessidade Identificada;
- `applied_solution` / Solução Aplicada;
- `achieved_result` / Resultado Alcançado;
- `added_value` / Valor Agregado.

Campos financeiros ou analíticos adicionais podem existir tecnicamente para evolução futura, relatórios ou integrações, mas não devem ser exigidos como preenchimento básico do consultor.

### 6.3. Aprendizado estrutural

Campos mínimos:

- `company_id`;
- `business_review_id`;
- `target_type`;
- `target_id`;
- `learning_type`;
- `action_decision`;
- `accepted_risk_reason`;
- `recommended_change`;
- `created_project_id`, quando gerar projeto;
- `created_task_id`, quando gerar tarefa;
- `created_at`;
- `updated_at`.

---

## 7. Fluxo oficial

### 7.1. Entrada

Uma demanda pode entrar por:

- consultor;
- cliente;
- Squad Cliente;
- Squad Versus;
- agente;
- MCP;
- reunião;
- indicador fora da meta;
- processo com falha;
- tarefa atrasada;
- evento externo.

### 7.2. Registro canônico

Primeiro, a demanda deve estar vinculada a um Objeto Canônico.

Exemplos:

- projeto;
- tarefa;
- processo;
- indicador;
- reunião;
- ocorrência.

### 7.3. Classificação consultiva

Depois, a Versus pode classificá-la como Necessidade Urgente.

Essa classificação deve registrar:

- por que é urgente;
- qual impacto gera;
- qual decisão precisa;
- qual responsável acompanha;
- qual evidência sustenta a leitura.

### 7.4. Business Review obrigatório

Toda Necessidade Urgente deve alimentar Business Review.

Isso pode acontecer:

- criando um novo registro de Business Review;
- anexando a necessidade a um Business Review em andamento;
- atualizando um Business Review existente.

### 7.5. Decisão estrutural

Após análise, deve haver uma das decisões:

1. criar ou alterar processo;
2. criar ou alterar rotina;
3. criar ou alterar indicador;
4. criar controle;
5. criar projeto de melhoria;
6. criar tarefa corretiva;
7. aceitar o risco conscientemente;
8. encerrar sem ação estrutural, com justificativa.

---

## 8. Regras de implementação

### 8.1. Multi-tenancy

Todo registro deve possuir `company_id`.

Nenhuma leitura ou escrita pode depender apenas do `id` do objeto.

### 8.2. Rotas finas

Rotas Flask devem apenas:

- validar entrada;
- resolver contexto;
- chamar service;
- devolver resposta.

Classificação de urgência, Business Review e decisão estrutural devem ficar em services.

### 8.3. Services obrigatórias

Implementação futura deve prever services equivalentes a:

- `urgent_need_service.py`;
- `business_review_service.py`;
- `structural_learning_service.py`;
- read model para cockpit consultivo.

### 8.4. MCP First

Leituras operacionais por agentes devem preferir MCP quando houver surface/capability disponível.

Ferramentas MCP futuras devem diferenciar:

- leitura operacional de projetos/tarefas;
- classificação consultiva de Necessidade Urgente;
- leitura analítica de Business Review;
- mutações sensíveis com human gate.

### 8.5. Human gate

Devem exigir confirmação humana:

- aceitar risco relevante;
- classificar impacto financeiro alto;
- fechar Business Review;
- gerar projeto ou tarefa a partir de recomendação consultiva;
- alterar processo por recomendação de agente;
- publicar conclusão para cliente.

---

## 9. UX e linguagem

### 9.1. Para o cliente

A linguagem deve ser operacional:

- Projeto;
- Atividade;
- Responsável;
- Prazo;
- Custo;
- Risco;
- Evidência;
- Decisão;
- Próxima ação.

O cliente não deve ser obrigado a entender o termo “Necessidade Urgente” para usar o APP32.

### 9.2. Para o consultor

A linguagem pode ser metodológica:

- Necessidade Urgente;
- Business Review;
- impacto;
- risco aceito;
- aprendizado estrutural;
- ponte para estruturação;
- maturação.

### 9.3. Para squads e agentes

A linguagem deve ser técnica e rastreável:

- Objeto Canônico afetado;
- camada consultiva aplicada;
- source;
- evidência;
- confiança;
- human gate;
- decisão.

---

## 10. Anti-padrões proibidos

1. Criar um módulo de Necessidades Urgentes desconectado de projetos, tarefas, processos ou indicadores.
2. Criar um segundo projeto metodológico para representar o mesmo projeto operacional.
3. Registrar Business Review sem `company_id`.
4. Fazer análise de custo/ganho apenas em texto solto sem estrutura mínima.
5. Permitir que agente aceite risco sem human gate.
6. Usar prioridade `urgent` como substituto de Necessidade Urgente.
7. Tratar toda tarefa urgente como Necessidade Urgente automaticamente.
8. Criar backlog estrutural sem vínculo com o fato que o originou.
9. Esconder do cliente a ação operacional necessária.
10. Expor ao cliente jargão metodológico quando isso não gerar valor.

---

## 11. Critérios de aceite

Uma implementação aderente deve garantir:

1. Projeto e tarefa continuam canônicos.
2. Necessidade Urgente é overlay, não duplicidade.
3. Business Review é obrigatório para Necessidade Urgente.
4. Business Review registra custo, investimento, ganho, risco e retorno.
5. Há decisão estrutural ao final da análise.
6. O risco pode ser aceito, mas precisa de justificativa.
7. Agentes podem sugerir, mas decisões críticas têm human gate.
8. Toda leitura/escrita respeita `company_id`.
9. O cliente consegue operar sem jargão Versus.
10. O consultor consegue conduzir sem planilha paralela.

---

## 12. Backlog técnico derivado

### P0 — Design técnico

1. Desenhar modelo de dados dos overlays.
2. Definir enumerações oficiais:
   - nível de urgência;
   - criticidade;
   - status de decisão;
   - tipo de review;
   - tipo de aprendizado estrutural.
3. Definir política de human gate.
4. Definir contrato MCP.

### P1 — Implementação base

1. Criar migrations.
2. Criar models.
3. Criar services.
4. Criar schemas de validação.
5. Criar APIs internas.
6. Criar read model de cockpit.

### P2 — UX

1. Adicionar leitura consultiva no cockpit do consultor.
2. Adicionar sinalização operacional simples no projeto/tarefa.
3. Criar tela de Business Review.
4. Criar trilha de decisão e evidências.

### P3 — Agentes e MCP

1. Criar tools de leitura.
2. Criar tools de classificação com human gate.
3. Criar tools de geração de recomendação.
4. Criar harness de validação tenant-safe.

---

## 13. Próxima decisão

A decisão técnica antes de implementar é:

> **O overlay de Necessidade Urgente deve aceitar vínculo polimórfico genérico (`canonical_object_type` + `canonical_object_id`) ou vínculos explícitos por coluna (`project_id`, `task_id`, `process_id`, `indicator_id` etc.)?**

Decisão oficial:

- usar colunas explícitas para os objetos principais;
- permitir `source_type/source_ref_id` apenas como complemento;
- evitar polimorfismo puro em dados críticos;
- manter rastreabilidade forte e queries simples em PostgreSQL.

---

## 14. Modelagem técnica oficial dos overlays

### 14.1. Decisão de modelagem

A modelagem oficial deve usar **colunas explícitas para vínculos principais**.

Motivos:

1. aumenta segurança de multi-tenancy;
2. facilita constraints e índices;
3. evita ambiguidade em relatórios;
4. melhora performance em PostgreSQL;
5. simplifica MCP e agentes;
6. reduz risco de apontar um overlay para objeto inexistente ou de outro tenant.

Polimorfismo genérico fica permitido apenas como **metadado complementar**, nunca como vínculo primário crítico.

### 14.2. Tabela conceitual `urgent_need_overlays`

Finalidade:

> Registrar a leitura consultiva de que um fato operacional representa uma Necessidade Urgente para a Versus.

Campos recomendados:

```text
id
company_id
title
description
status
urgency_level
criticality_level
origin_channel
origin_summary

project_id
project_task_id
process_id
process_instance_id
routine_id
indicator_id
meeting_id
occurrence_id
financial_ref_id

source_type
source_ref_id
source_payload_json

business_impact_summary
operational_impact_summary
risk_summary
decision_status
decision_summary

responsible_employee_id
created_by_user_id
updated_by_user_id
closed_by_user_id

created_at
updated_at
closed_at
```

Regras:

- `company_id` é obrigatório.
- Ao menos um vínculo principal deve existir.
- Vínculos principais devem respeitar o mesmo `company_id`.
- `source_type/source_ref_id` não substituem vínculos explícitos.
- `status` não deve controlar o projeto; controla apenas a leitura consultiva.

### 14.3. Tabela conceitual `business_review_records`

Finalidade:

> Registrar, de forma simples, o valor agregado pelo trabalho da Versus em uma Necessidade Urgente, projeto ou programa relevante.

Campos recomendados:

```text
id
company_id
title
review_type
status

urgent_need_id
project_id
project_task_id
process_id
indicator_id
meeting_id

cost_to_act
cost_to_not_act
required_investment
expected_gain
expected_return
risk_level
risk_acceptance_decision
risk_acceptance_reason

decision_summary
structural_learning_summary
next_action

responsible_employee_id
reviewed_by_user_id
created_by_user_id
updated_by_user_id

reviewed_at
created_at
updated_at
closed_at
```

Regras:

- `company_id` é obrigatório.
- Se houver `urgent_need_id`, o Business Review deve herdar ou validar o mesmo tenant.
- Business Review pode existir sem Necessidade Urgente quando a análise nascer de projeto estratégico ou decisão relevante.
- Toda Necessidade Urgente deve possuir ao menos um Business Review associado antes do encerramento.

### 14.4. Tabela conceitual `structural_learning_links`

Finalidade:

> Registrar o aprendizado estrutural derivado de uma urgência ou Business Review.

Campos recomendados:

```text
id
company_id
business_review_id
urgent_need_id

target_project_id
target_project_task_id
target_process_id
target_routine_id
target_indicator_id
target_meeting_id

learning_type
action_decision
accepted_risk_reason
recommended_change

created_project_id
created_task_id

created_by_user_id
updated_by_user_id
created_at
updated_at
```

Regras:

- `company_id` é obrigatório.
- Deve apontar para o Business Review que originou o aprendizado.
- Pode gerar projeto/tarefa, mas não deve criar automaticamente sem human gate.
- Pode registrar decisão consciente de aceitar risco.

---

## 15. Enumerações oficiais iniciais

### 15.1. `urgent_need.status`

```text
inbox
triage
in_review
decided
in_execution
closed
cancelled
```

### 15.2. `urgent_need.urgency_level`

```text
low
medium
high
critical
```

### 15.3. `urgent_need.criticality_level`

```text
operational
managerial
strategic
legal_regulatory
financial
reputational
```

### 15.4. `business_review.review_type`

```text
urgent_need
project_investment
process_correction
risk_acceptance
strategic_decision
financial_impact
```

### 15.5. `business_review.status`

```text
draft
in_analysis
pending_decision
approved
risk_accepted
rejected
closed
```

### 15.6. `structural_learning.learning_type`

```text
process_change
routine_change
indicator_change
control_change
policy_change
project_creation
task_creation
risk_acceptance
no_structural_action
```

---

## 16. Índices e constraints recomendados

### 16.1. Índices mínimos

```text
urgent_need_overlays(company_id, status)
urgent_need_overlays(company_id, urgency_level)
urgent_need_overlays(company_id, project_id)
urgent_need_overlays(company_id, project_task_id)
urgent_need_overlays(company_id, process_id)
urgent_need_overlays(company_id, indicator_id)

business_review_records(company_id, status)
business_review_records(company_id, review_type)
business_review_records(company_id, urgent_need_id)
business_review_records(company_id, project_id)
business_review_records(company_id, process_id)

structural_learning_links(company_id, business_review_id)
structural_learning_links(company_id, urgent_need_id)
structural_learning_links(company_id, target_process_id)
```

### 16.2. Constraints conceituais

Devem ser protegidos por validação de service e, quando viável, constraints:

- Necessidade Urgente precisa ter ao menos um vínculo canônico.
- Business Review de Necessidade Urgente precisa apontar para `urgent_need_id`.
- Encerramento de Necessidade Urgente exige Business Review.
- Aceite de risco exige justificativa.
- Geração de ação estrutural exige human gate.

---

## 17. Services oficiais a implementar

### 17.1. `urgent_need_service.py`

Responsabilidades:

- criar overlay;
- classificar urgência;
- validar vínculos canônicos;
- consultar por empresa;
- encerrar somente com Business Review;
- expor payload para cockpit consultivo.

### 17.2. `business_review_service.py`

Responsabilidades:

- criar review;
- calcular/registrar impacto;
- associar Necessidade Urgente;
- registrar decisão;
- validar aceite de risco;
- preparar decisão para human gate.

### 17.3. `structural_learning_service.py`

Responsabilidades:

- registrar aprendizado;
- vincular a processo, rotina, indicador ou projeto;
- gerar recomendação de melhoria;
- solicitar human gate para criação de projeto/tarefa;
- registrar decisão de manter risco.

### 17.4. `business_review_read_model_service.py`

Responsabilidades:

- montar cockpit consultivo;
- consolidar urgências abertas;
- consolidar impactos financeiros/operacionais;
- listar decisões pendentes;
- mostrar aprendizados estruturais.

---

## 18. Contrato de implementação incremental

### Etapa 1 — Dados

- criar models;
- criar migrations;
- criar enums/checks básicos;
- criar índices por `company_id`.

### Etapa 2 — Services

- implementar services sem UI;
- validar tenant;
- validar vínculos;
- criar testes unitários.

### Etapa 3 — Cockpit consultivo

- criar read model;
- criar tela para consultor;
- expor sinalização discreta em projeto/tarefa.

### Etapa 4 — MCP e agentes

- criar tools de leitura;
- criar tool de sugestão consultiva;
- exigir human gate para mutações críticas;
- criar harness tenant-safe.

---

## 19. Decisão final desta SPEC

A implementação deve seguir o modelo:

```text
Objeto Canônico:
Project / ProjectTask / Process / Routine / Indicator / Meeting / outros

Camada Consultiva:
UrgentNeedOverlay
BusinessReviewRecord
StructuralLearningLink

Regra:
colunas explícitas primeiro; polimorfismo apenas complementar.
```

Essa decisão é vinculante para a Fase 02.

---

## 20. Implementação inicial — Etapa 1 Dados

Status em 2026-06-30:

- models criados em `app32/models/urgent_business_review.py`;
- registry atualizado em `app32/models/__init__.py`;
- migration criada em `app32/migrations/versions/20260630_1845_create_urgent_business_review_overlays.py`;
- entidades implementadas:
  - `UrgentNeedOverlay`;
  - `BusinessReviewRecord`;
  - `StructuralLearningLink`;
- validação local realizada:
  - sintaxe dos novos arquivos;
  - import dos novos models pelo pacote `models`.

Esta etapa não inclui UI, services, APIs, MCP tools ou deploy.

---

## 21. Implementação inicial — Etapa 2 Services

Status em 2026-06-30:

- helper comum criado em `app32/services/urgent_business_review_common.py`;
- service criada em `app32/services/urgent_need_service.py`;
- service criada em `app32/services/business_review_service.py`;
- service criada em `app32/services/structural_learning_service.py`;
- validação local realizada:
  - sintaxe dos novos services;
  - import das classes de service.

Regras implementadas nesta etapa:

- `company_id` obrigatório em todas as leituras e escritas;
- validação de existência da empresa;
- validação de vínculos canônicos no mesmo tenant;
- `ProjectTask` validada via `Project.company_id`, pois a tarefa não carrega `company_id` diretamente;
- encerramento de Necessidade Urgente exige Business Review associado;
- aceite de risco exige justificativa;
- Business Review criado a partir de Necessidade Urgente herda vínculos canônicos principais quando não informados explicitamente;
- aprendizado estrutural exige Business Review válido no tenant.

Esta etapa não inclui UI, rotas Flask, MCP tools, harnesses ou deploy.

---

## 22. Implementação inicial — Etapa 3 APIs internas

Status em 2026-06-30:

- blueprint criado em `app32/api/routes/urgent_business_review.py`;
- blueprint registrado em `app32/app.py`;
- endpoints internos JSON criados sob `/api/consultive/*`;
- validação local realizada:
  - sintaxe do blueprint;
  - sintaxe do `app.py`;
  - import do blueprint.

Endpoints criados:

- `GET /api/consultive/urgent-needs`;
- `POST /api/consultive/urgent-needs`;
- `POST /api/consultive/urgent-needs/<urgent_need_id>/decision`;
- `POST /api/consultive/urgent-needs/<urgent_need_id>/status`;
- `GET /api/consultive/business-reviews`;
- `POST /api/consultive/business-reviews`;
- `POST /api/consultive/business-reviews/<review_id>/decision`;
- `GET /api/consultive/structural-learning-links`;
- `POST /api/consultive/structural-learning-links`;
- `POST /api/consultive/structural-learning-links/<learning_link_id>/decision`.

Regras mantidas:

- rotas finas;
- `login_required`;
- empresa ativa via contexto atual;
- escrita exige `has_company_full_access`;
- regra de negócio permanece nas services;
- respostas de erro de domínio em JSON;
- sem UI, MCP tools, harnesses ou deploy nesta etapa.

---

## 23. Implementação inicial — Etapa 4 Read model / cockpit consultivo

Status em 2026-06-30:

- read model criado em `app32/services/business_review_read_model_service.py`;
- endpoint criado em `GET /api/consultive/cockpit`;
- validação local realizada:
  - sintaxe do read model;
  - import do read model;
  - import do blueprint.

O read model consolida:

- total e abertura de Necessidades Urgentes;
- Necessidades Urgentes críticas abertas;
- Business Reviews pendentes de consolidação do valor agregado;
- aprendizados estruturais pendentes de ação;
- exposição financeira consolidada:
  - custo de agir;
  - custo de não agir;
  - investimento requerido;
  - ganho esperado;
  - retorno esperado;
- contagens por status, tipo, urgência, criticidade e ação registrada;
- próximos focos do consultor.

Esta etapa permanece apenas como API/read model. Não inclui UI, MCP tools, harnesses ou deploy.

---

## 24. Implementação inicial — Etapa 5 Harness/testes tenant-safe

Status em 2026-06-30:

- testes criados em `app32/tests/test_urgent_business_review_tenant_contracts.py`;
- validação executada com `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- resultado: `4 passed`.

Contratos protegidos:

- cockpit consultivo usa a empresa ativa e ignora `company_id` enviado na query string;
- criação de Necessidade Urgente usa a empresa ativa e passa pelo gate de escrita;
- `ProjectTask` é validada via `Project.company_id`;
- rota não manipula `db.session` diretamente;
- rota delega regras de negócio às services.

Observação:

- o pytest padrão do ambiente carrega `pytest_flask` incompatível com a versão atual do Flask;
- por isso, a validação alvo deve usar `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` enquanto o plugin externo não for ajustado/removido do ambiente.

Esta etapa não inclui UI, MCP tools ou deploy.

---

## 25. Revisão de risco pré-UI/deploy

Status em 2026-06-30:

- migration auditada;
- models auditados;
- services auditadas;
- cadeia Alembic verificada: `20260630_1845` é head único e aponta para `20260614_1200`;
- ajustes preventivos aplicados.

Decisões de risco:

1. `financial_ref_id` permanece como campo auxiliar, mas não satisfaz sozinho o vínculo canônico obrigatório.
   - Motivo: ainda não há FK canônica definida para o alvo financeiro.
   - Consequência: Necessidade Urgente precisa apontar também para projeto, tarefa, processo, rotina, indicador, reunião ou ocorrência.

2. Aceite de risco agora exige texto não vazio também em constraint.
   - Business Review: `btrim(risk_acceptance_reason) <> ''`.
   - Aprendizado estrutural: `btrim(accepted_risk_reason) <> ''`.

3. Tenant crossing continua protegido em service/API.
   - Observação: a migration usa FKs simples por `id`, pois nem todos os objetos canônicos possuem constraint composta `(company_id, id)`.
   - Regra operacional: toda criação/alteração deve passar pelas services tenant-safe.
   - Evolução futura: avaliar constraints compostas por domínio quando a base estiver normalizada.

Risco residual aceito para esta etapa:

- inserção manual direta no banco poderia burlar a validação tenant-safe de service.
- mitigação atual: não expor mutação fora das services/APIs, manter rotas finas e incluir harness tenant-safe.
- mitigação futura: reforçar constraints compostas ou triggers tenant-safe se o domínio virar superfície crítica de escrita por integrações externas.

---

## 26. Implementação inicial — Etapa 6 UI mínima do cockpit consultivo

Status em 2026-06-30:

- página criada em `GET /consultive/cockpit`;
- template criado em `app32/templates/modules/consultive/business_review_cockpit.html`;
- usa `GET /api/consultive/cockpit?limit=12`;
- validação local realizada:
  - sintaxe da rota;
  - renderização do shell;
  - contrato responsivo do template;
  - testes alvo.

Decisões de UX:

- cabeçalho mínimo e compacto;
- página orientada à operação do consultor;
- foco inicial em prioridades, não em explicação metodológica;
- cards com densidade moderada;
- layout responsivo:
  - desktop: urgências como coluna principal e painéis laterais de valor agregado/estruturação;
  - telas médias: grid em uma coluna;
  - telas pequenas: header empilhado, cards fluidos e finanças em uma coluna.

Esta etapa ainda não inclui mutações pela UI, MCP tools, harness de navegador ou deploy.

---

## 27. Ajuste de alinhamento visual — preview estático e UI operacional

Status em 2026-06-30:

- UI real do cockpit consultivo refinada em `app32/templates/modules/consultive/business_review_cockpit.html`;
- preview estático criado em `app32/docs/previews/consultive_cockpit_preview.html` para validação visual direta no navegador;
- mensagem de falha da UI real passou a explicar que o template Jinja deve ser aberto pela aplicação, não via `file://`;
- testes alvo atualizados para proteger o contrato visual mínimo e a existência do preview.

Decisão:

- a página oficial continua sendo `GET /consultive/cockpit` dentro do APP32;
- o arquivo em `docs/previews` é apenas artefato de alinhamento visual, sem regra de negócio, sem API e sem dependência de sessão;
- o preview existe para evitar desalinhamento quando a validação visual for feita abrindo arquivo local.

Contratos de UX mantidos:

- cabeçalho mínimo;
- responsividade para telas menores;
- organização orientada à operação do consultor;
- priorização de urgências, reviews, aprendizados e exposição financeira.

Esta etapa ainda não inclui mutações pela UI, MCP tools, harness de navegador ou deploy.

## 28. Ajuste conceitual oficial — Necessidade Urgente, Projeto e Business Review

Status em 2026-06-30:

- conceito oficial ajustado após revisão metodológica;
- Necessidade Urgente passa a exigir materialização como projeto ou programa de projetos;
- Business Review passa a ser tratado como registro simples do valor agregado pelo trabalho da Versus, e não como mecanismo primário de decisão.

Decisões oficiais:

1. **Necessidade Urgente**
   - sempre vira projeto ou programa de projetos;
   - pode nascer de uma dor fiscal, financeira, operacional, estratégica, jurídica ou de gestão;
   - sua execução deve morar no objeto canônico de projeto/programa;
   - a classificação como Necessidade Urgente permanece na Camada Consultiva/Evolutiva.

2. **Estruturação Empresarial**
   - continua sendo a parte da Metodologia Versus que estrutura ou reestrutura a empresa de maneira duradoura;
   - atua sobre processos, rotinas, indicadores, controles, papéis, governança e arquitetura organizacional;
   - pode receber aprendizados vindos das Necessidades Urgentes, sem depender de um controle artificial de backlog.

3. **Business Review**
   - é o registro do valor agregado na empresa pelo trabalho da Versus;
   - solicita apenas Necessidade Identificada, Solução Aplicada, Resultado Alcançado e Valor Agregado;
   - não deve ser apresentado como etapa de decisão, pois a decisão pertence ao projeto, programa ou frente de estruturação.

Implicação para o APP32:

- a UI deve evitar tratar Business Review como “decisão pendente”;
- a UI deve apresentar Business Review como registro simples de valor agregado;
- regras técnicas atuais que ainda usam nomes como `pending_decision` devem ser tratadas como legado semântico temporário até refatoração segura.

## 29. Simplificação oficial do Business Review

Status em 2026-06-30:

O Business Review deve ser operacionalmente simples. Para registrar o valor agregado pela Versus, o consultor deve preencher apenas:

1. **Necessidade Identificada** — qual dor, risco, oportunidade ou necessidade foi percebida.
2. **Solução Aplicada** — o que a Versus fez ou conduziu.
3. **Resultado Alcançado** — o que mudou, melhorou, foi resolvido ou ficou controlado.
4. **Valor Agregado** — qual valor foi gerado para a empresa, em texto e/ou valor monetário quando aplicável.

Decisão:

- esses quatro campos formam o contrato operacional mínimo do Business Review;
- relatórios futuros poderão filtrar por data de início, data de finalização e descrição;
- campos financeiros detalhados, risco, retorno e indicadores podem existir como evolução ou derivação, mas não devem ser obrigatórios para o consultor registrar o Business Review.

---

## 30. Atualização da página do cockpit conforme flags metodológicas

Status em 2026-06-30:

A página do cockpit consultivo foi ajustada para refletir os conceitos operacionais atuais:

- Projeto/Programa pode ser marcado como **Necessidade Urgente**;
- Projeto/Programa pode ser marcado como **Estruturação Empresarial**;
- as duas marcações são independentes e podem coexistir;
- a seção principal do cockpit passa a tratar Necessidade Urgente como projeto/programa sinalizado, não como objeto concorrente;
- o card da Necessidade Urgente deve permitir abrir o projeto diretamente e exibir o status/progresso real do projeto;
- o Business Review passa a exibir os quatro campos simples:
  - Necessidade Identificada;
  - Solução Aplicada;
  - Resultado Alcançado;
  - Valor Agregado.



### 30.1 Contrato visual do card de Projeto de Necessidade Urgente

O card exibido na seção de Necessidades Urgentes deve mostrar apenas projetos/programas sinalizados como Necessidade Urgente.

Contrato do card:

- título: `Número do Projeto - Nome do Projeto`;
- tags obrigatórias:
  - Programa;
  - Urgência;
  - Criação;
  - Vencimento;
  - Responsável;
  - Última Movimentação;
- ação principal: abrir o projeto;
- status/progresso: usar o status/progresso real do projeto.

Não devem aparecer nesse card tags de processo, indicador, tarefa, criticidade metodológica ou outros objetos auxiliares, salvo se futuramente forem tratados em área de detalhe do projeto.

Decisão de UI:

- o cockpit do consultor é a tela de operação da camada consultiva;
- a execução permanece no Projeto/Programa;
- o Business Review registra valor agregado, sem exigir preenchimento financeiro detalhado.

---

## 31. Remoção da faixa introdutória do cockpit consultivo

Status em 2026-06-30:

A faixa explicativa com passos `Qualificar a dor`, `Registrar valor agregado`, `Converter aprendizado em estrutura` e os cards de foco P0/P1 foram removidos da página.

Decisão:

- o cockpit deve abrir direto nos painéis operacionais;
- a orientação metodológica não deve ocupar área nobre da tela;
- priorização/foco poderá voltar futuramente como recurso discreto, se houver necessidade operacional real.

---

## 32. Contrato visual e operacional do card de Business Review

Status em 2026-06-30:

O card de Business Review no cockpit consultivo deve operar com dois estados:

1. **A registrar**
   - exibido quando os quatro campos ainda não estão completos;
   - deve apresentar botão **Registrar**;
   - ao clicar, abre pop-up para preenchimento.

2. **Registrado**
   - exibido quando os quatro campos estão preenchidos;
   - deve apresentar tag com o valor capturado;
   - deve exibir os textos registrados, inteiros ou em prévia curta.

Campos do pop-up:

- Necessidade Identificada;
- Solução Aplicada;
- Resultado Alcançado;
- Valor Agregado.

Decisão técnica:

- o pop-up usa a API existente de Business Review;
- `Necessidade Identificada` atualiza o título do Business Review;
- `Solução Aplicada` usa `next_action` no modelo atual;
- `Resultado Alcançado` usa `structural_learning_summary` no modelo atual;
- `Valor Agregado` usa `decision_summary` no modelo atual;
- estes nomes técnicos são compatibilidade temporária até eventual migration de campos explícitos.

---

## 33. Formato do Valor Agregado no Business Review

Status em 2026-06-30:

O campo **Valor Agregado** deve capturar três partes:

1. valor;
2. tipo: `única` ou `recorrente`;
3. periodicidade: mensal, anual ou outra aplicável.

Formato visual oficial:

- `48.000,00 - única - anual`;
- `15.000,00 - recorrente - mensal`.

Decisão:

- no pop-up, esses dados devem ser preenchidos em campos separados para reduzir erro;
- no card e relatórios, o valor deve aparecer concatenado no formato oficial;
- por enquanto, o formato pode ser armazenado no campo técnico de valor agregado atual, até criação futura de campos estruturados próprios.

---

## 34. Estruturação Empresarial no Cockpit do Consultor

Status em 2026-07-01:

A seção de **Estruturação Empresarial** do cockpit consultivo deve representar as quatro frentes oficiais da Metodologia Versus para maturação duradoura da empresa.

### 34.1. Frentes oficiais

A Estruturação Empresarial no cockpit deve conter quatro cards principais:

1. **Identidade Organizacional**
   - Missão;
   - Visão;
   - Valores;
   - Posicionamento;
   - Organograma.

2. **Processos**
   - Arquitetura: áreas, macroprocessos, processos, responsáveis de processo e indicadores quando aplicável;
   - Modelagem: estrutura/recursos, fluxo, POP, recursos, rotina, SPEC para IA e indicadores;
   - Implantação: projeto ou programa associado, treinamento, comunicação e entrada em operação;
   - Estabilização: 3 ciclos dentro das faixas de controle dos indicadores, acompanhados/auditados pela Versus;
   - Auditoria: inclusão do processo no rol de auditoria interna, com periodicidade e critérios.

3. **Planejamento Estratégico**
   - Estruturado;
   - Conectado;
   - Desdobrado;
   - Vinculado ao Gerenciamento Estratégico.

4. **Gerenciamento Estratégico**
   - Indicadores Estratégicos;
   - Ciclos de Gestão;
   - Gestão de Incentivos;
   - Teia de Conexões;
   - Decisão, Ação e Aprendizado.

### 34.2. Contrato visual inicial

Enquanto não houver read model específico de Estruturação Empresarial, a UI deve exibir os quatro cards como contrato metodológico-operacional, com:

- título da frente;
- microstatus sequenciais dos componentes da frente;
- leitura de maturidade consolidada;
- status inicial conservador: **A estruturar**;
- ação principal: **Abrir frente** ou equivalente futuro.

Os microstatus devem seguir linguagem simples e operacional, por exemplo:

```text
1 - Arquitetura · OK · 100%
2 - Modelagem · Parcial · 55%
3 - Implantação · Em projeto · 30%
4 - Estabilização · 1/3 ciclos
5 - Auditoria · Pendente · 0%
```

### 34.3. Regras de integração futura

- Necessidades Urgentes podem gerar aprendizados que alimentam uma ou mais frentes de Estruturação Empresarial.
- Projetos/Programas podem ser sinalizados como Estruturação Empresarial sem deixar de ser Objetos Canônicos.
- Processos em implantação devem ter projeto ou programa associado.
- Processos só entram como estabilizados após 3 ciclos dentro das faixas de controle dos indicadores, acompanhados/auditados pela Versus.
- A passagem para Auditoria significa inclusão do processo no rol de auditoria interna.
- Gerenciamento Estratégico deve manter relação explícita com Planejamento Estratégico, indicadores, ciclos de gestão, incentivos e teia de conexões.

Decisão:

- a seção antiga **Aprendizados a converter** deixa de ser o painel principal da estruturação;
- aprendizados estruturais continuam existindo como origem/insumo, mas a tela principal deve organizar a estruturação pelas quatro frentes oficiais.

---

## 35. Realinhamento oficial — Cockpit, Jornada de Estruturação e Maturação N1

Status em 2026-07-01:

Após revisão do APP32 e do Paper canônico da Metodologia Versus, fica definido que o **Cockpit do Consultor** é a superfície oficial de condução da Camada Consultiva/Evolutiva.

### 35.1 Decisão de navegação

No sidebar, a entrada principal deve ser:

```text
Módulos → Consultivo → Cockpit do Consultor
```

As telas **Jornada de Estruturação** e **Maturação N1** não devem permanecer como entradas equivalentes no menu principal, pois geram duplicidade conceitual e operacional.

### 35.2 Papel oficial do Cockpit do Consultor

O Cockpit do Consultor deve consolidar:

1. Estruturação Empresarial;
2. Necessidades Urgentes;
3. Business Reviews.

A Estruturação Empresarial deve ser organizada por dois eixos complementares:

1. **Trilha de Maturidade da Estruturação** — estágio macro da empresa nas Fases 00, 01, 02 e 03;
2. **Frentes estruturais** — dimensões concretas trabalhadas no cockpit.

As quatro frentes oficiais são:

1. Identidade Organizacional;
2. Processos;
3. Planejamento Estratégico;
4. Gerenciamento Estratégico.

### 35.3 Papel oficial da Trilha de Maturidade da Estruturação

A Trilha de Maturidade da Estruturação é o eixo macro de leitura da evolução metodológica da empresa.

Ela deve indicar, no Cockpit do Consultor:

- fase atual da empresa;
- aderência da Identidade Organizacional ao gate da Fase 00;
- gate em andamento;
- evidências exigidas para avanço;
- pendências críticas;
- riscos de avanço prematuro;
- próximo avanço recomendado.

Contrato conceitual mínimo:

| Fase | Leitura canônica | Gate dominante |
|---|---|---|
| 00 | Base Organizacional / empresa na mão | identidade mínima, organograma, responsabilidades, controle mínimo e visão inicial confiável |
| 01 | Processos finalísticos | cadeia de valor principal estabilizada |
| 02 | Todos os processos | operação inteira sob lógica de processo, indicador e rotina |
| 03 | Planejamento e gestão estratégicos | estratégia em ciclo vivo de decisão, ação e aprendizado |

A trilha não substitui as quatro frentes. Ela organiza o estágio macro; as frentes organizam a análise e a ação concreta.

### 35.4 Papel oficial da Jornada de Estruturação

A Jornada de Estruturação deve deixar de ser uma segunda superfície principal.

Ela deve ser reaproveitada como:

- read model interno de maturidade;
- fonte de cálculo de gates;
- fonte de pendências por bloco/sub-bloco;
- tela de detalhe quando aberta a partir de uma frente do cockpit;
- possível experiência guiada do cliente, se validada posteriormente.

O serviço `StructuringJourneyService` continua útil, mas deve ser subordinado ao read model do Cockpit do Consultor.

### 35.5 Papel oficial da Maturação N1

A Maturação N1 deve ser tratada como **fila de revisão e human gate** da camada consultiva/evolutiva.

Ela deve ser reaproveitada como:

- backlog de hipóteses e sugestões;
- mecanismo de confirmação, manutenção ou rejeição;
- motor de promoção para dado canônico;
- detalhe operacional acessado dentro da frente correspondente do cockpit.

A tela `alignment_n1_maturation.html` pode permanecer temporariamente para uso técnico/administrativo, mas não deve ser apresentada como módulo principal ao usuário comum.

### 35.6 Duplicidades resolvidas

- Trilha de Maturidade passa a ser eixo macro do Cockpit; a Jornada fornece detalhe, cálculo e evidências quando necessário.
- Identidade Organizacional passa a ser frente do Cockpit; a Jornada pode fornecer maturidade e pendências.
- Processos passa a ser frente do Cockpit; a Jornada pode fornecer arquitetura/modelagem/gates.
- Planejamento Estratégico e Gerenciamento Estratégico passam a ser frentes do Cockpit; o N1 fornece análise de alinhamento, rastreabilidade e backlog de maturação.
- Business Review permanece registro simples de valor agregado e não deve ser confundido com Maturação N1.

### 35.7 Backlog técnico derivado

1. Remover ou ocultar do sidebar as entradas independentes de Jornada de Estruturação e Maturação N1.
2. Criar no Cockpit uma leitura da Trilha de Maturidade da Estruturação acima das quatro frentes, com fase atual, gate, evidências faltantes e próximo avanço.
3. Criar read model de Estruturação Empresarial para o Cockpit consumindo, quando aplicável:
   - `StructuringJourneyService`;
   - `StrategyAlignmentN1Service`;
   - objetos canônicos de identidade, processos, indicadores, projetos e auditoria.
4. Fazer o botão **Abrir frente** abrir detalhe contextual da frente, e não uma tela genérica concorrente.
5. Fazer o botão **Ver detalhe da trilha** abrir a Jornada de Estruturação como detalhe subordinado ao Cockpit.
6. Atualizar linguagem visual para esconder termos técnicos como S1/S2/payload do usuário comum.
7. Preservar rotas antigas temporariamente com redirecionamento ou acesso administrativo, até estabilização do novo fluxo.

---

## 36. Maturação Assistida por Squads, MCP e Agentes

Status em 2026-07-01:

Fica definido que o Cockpit do Consultor deve evoluir para ser a superfície oficial de **maturação assistida** da Estruturação Empresarial.

### 36.1 Decisão de produto

A assistência por IA, Squads e MCP deve acontecer **dentro das frentes do cockpit**, e não como módulo paralelo.

As quatro frentes oficiais são:

1. Identidade Organizacional;
2. Processos;
3. Planejamento Estratégico;
4. Gerenciamento Estratégico.

Cada frente poderá acionar agentes, MCP tools, análises do Squad Versus e validações do Squad de Engenharia conforme o tipo de maturação necessária.

### 36.2 Contrato operacional da maturação assistida

O fluxo padrão deve seguir esta lógica:

```text
Consultor abre uma frente
→ MCP coleta dados reais do APP32
→ Agente especializado analisa maturidade, lacunas e evidências
→ Squad Versus qualifica a leitura metodológica
→ Squad de Engenharia aponta gaps técnicos/sistêmicos quando existirem
→ Pesquisa externa/benchmark é acionada quando necessário
→ Recomendação é consolidada
→ Consultor valida
→ APP32 registra decisão, ação, projeto, revisão ou maturação
```

### 36.3 Responsabilidades por ator

#### MCP

- Fonte primária da verdade operacional.
- Deve consultar objetos canônicos por `company_id`.
- Deve preservar tenant, permissões, surface e rastreabilidade.
- Deve ser preferido para leituras internas antes de qualquer análise agentic.

#### Squad Versus

- Responsável pela interpretação metodológica.
- Avalia aderência à Metodologia Versus.
- Sugere próximos passos de maturação.
- Ajuda a transformar evidências em decisão consultiva.

#### Squad de Engenharia

- Responsável pela avaliação técnica e sistêmica.
- Identifica ausência de modelo, campo, API, read model, MCP tool, índice, validação, permissão ou UX.
- Recomenda correções sistêmicas quando a limitação for do APP32, não da empresa.

#### Agentes de IA

- Apoiam análise, síntese, recomendação e geração de artefatos.
- Podem pesquisar boas práticas, benchmarks e referências externas quando solicitado ou metodologicamente necessário.
- Devem diferenciar claramente dado interno, inferência e referência externa.
- Não podem confirmar maturidade, fechar gate ou alterar objeto crítico sem human gate.

#### Consultor Versus

- Continua sendo o responsável pela condução metodológica.
- Valida recomendações.
- Decide o encaminhamento junto ao cliente/patrocinador quando necessário.
- Registra a decisão no APP32.

### 36.4 Ações esperadas no Cockpit

Cada card de frente estrutural deve poder evoluir para suportar ações como:

- **Analisar frente**;
- **Gerar diagnóstico assistido**;
- **Pesquisar boas práticas**;
- **Sugerir plano de maturação**;
- **Revisar evidências**;
- **Preparar reunião com o cliente**;
- **Apontar gaps técnicos**;
- **Abrir pendências de maturação**.

Essas ações devem ser contextuais. Por exemplo:

- em **Identidade Organizacional**, agentes analisam missão, visão, valores, posicionamento e organograma;
- em **Processos**, agentes analisam arquitetura, modelagem, implantação, estabilização e auditoria;
- em **Planejamento Estratégico**, agentes analisam estruturação, conexão, desdobramento e vínculo com o gerenciamento;
- em **Gerenciamento Estratégico**, agentes analisam indicadores, ciclos, incentivos, teia de conexões, decisão, ação e aprendizado.

### 36.5 Regras de segurança e governança

1. Toda leitura interna deve respeitar `company_id`.
2. MCP é a fonte preferencial para dados operacionais da empresa.
3. Pesquisa externa não substitui dado interno.
4. Agentes devem separar:
   - fato interno;
   - inferência;
   - recomendação;
   - benchmark externo.
5. Decisões críticas exigem human gate.
6. Recomendações aceitas devem gerar registro rastreável: decisão, projeto, atividade, revisão, Business Review ou item de maturação.
7. O usuário comum não deve ser obrigado a operar jargões técnicos como S1/S2, payload, block_type ou surface.

### 36.6 Backlog técnico derivado

1. Criar contrato de read model para maturação assistida por frente do Cockpit.
2. Mapear MCP tools existentes que alimentam cada frente.
3. Identificar lacunas de tools para identidade, processos, planejamento e gerenciamento estratégico.
4. Definir contrato de resposta agentic com campos mínimos:
   - resumo;
   - evidências internas;
   - lacunas;
   - recomendações;
   - riscos;
   - benchmarks externos, quando houver;
   - decisão sugerida;
   - necessidade de human gate.
5. Criar UX contextual para ações assistidas, sem criar módulo paralelo de agentes.
6. Registrar logs/auditoria das recomendações aceitas ou rejeitadas.

---

## 37. Desenho funcional do Cockpit Assistido

Status em 2026-07-01:

Esta seção transforma a decisão de maturação assistida em desenho funcional para evolução do Cockpit do Consultor.

O Cockpit deve oferecer ações contextuais por frente estrutural, usando o que já existe no APP32 sempre que possível e criando novas capacidades apenas onde houver lacuna real.

### 37.1 Princípio de UX

O consultor não deve precisar escolher manualmente qual agente, tool ou serviço usar.

A experiência deve ser orientada por intenção:

```text
Consultor escolhe a frente → escolhe uma ação → Cockpit orquestra MCP, serviços, agentes e squads → consultor valida o resultado.
```

A UI deve expor ações simples, como:

- **Analisar frente**;
- **Gerar diagnóstico**;
- **Pesquisar boas práticas**;
- **Sugerir plano de maturação**;
- **Revisar evidências**;
- **Preparar reunião**;
- **Apontar gaps técnicos**.

A complexidade de MCP, N1, read model, S1/S2, block_type, services e agents deve permanecer encapsulada.

A Estruturação Empresarial deve iniciar com a leitura da **Trilha de Maturidade da Estruturação**. Essa leitura deve ser exibida como bloco macro antes das quatro frentes, com linguagem operacional para o consultor:

- fase atual;
- gate atual;
- próximo avanço;
- evidências faltantes;
- botão **Ver detalhe da trilha**.

Depois da trilha, o cockpit apresenta as quatro frentes estruturais, que concentram as ações assistidas por Squads, MCP e agentes.

### 37.2 Ações funcionais por frente

| Frente | Ações principais | Resultado esperado para o consultor |
|---|---|---|
| Identidade Organizacional | Analisar identidade; revisar coerência; pesquisar posicionamento; sugerir ajustes; preparar conversa com cliente | Diagnóstico de missão, visão, valores, posicionamento e organograma, com lacunas e próximos passos |
| Processos | Analisar arquitetura; avaliar modelagem; revisar implantação; checar estabilização; preparar plano de auditoria | Leitura de maturidade por processo, gaps de modelagem/implantação/estabilização e ações recomendadas |
| Planejamento Estratégico | Avaliar estruturação; checar conexão com processos/projetos; revisar desdobramento; sugerir prioridades | Diagnóstico do planejamento, lacunas de conexão e plano de alinhamento com execução |
| Gerenciamento Estratégico | Avaliar indicadores; ciclos; incentivos; teia de conexões; decisão/ação/aprendizado | Leitura de gestão viva, riscos, desalinhamentos, incentivos e conexões críticas |

### 37.3 Fontes e capacidades existentes por frente

#### Identidade Organizacional

Capacidades já existentes ou reaproveitáveis:

- `CompanyIdentityService`;
- `StrategyAlignmentN1Service.get_identity`;
- `StructuringJourneyService`;
- MCP tools:
  - `get_strategy_identity_tool`;
  - `get_organizational_identity_tool`;
  - `upsert_organizational_identity_tool`, apenas com human gate;
  - `list_strategy_maturation_backlog_tool`.

Uso no Cockpit:

- ler missão, visão, valores, posicionamento e organograma;
- identificar campos ausentes, parciais ou contraditórios;
- comparar identidade declarada com projetos, processos e indicadores;
- sugerir perguntas para o consultor levar ao cliente;
- gerar hipóteses de maturação sem promover automaticamente para canônico.

Lacunas prováveis:

- contrato específico para coerência entre identidade, organograma, processos e estratégia;
- histórico de versões/decisões da identidade;
- vínculo explícito entre posicionamento e planejamento estratégico.

#### Processos

Capacidades já existentes ou reaproveitáveis:

- `StructuringJourneyService`;
- `StrategyAlignmentN1Service.get_process_profile`;
- `ProcessBpmnService`, `ProcessFlowCopilotService`, `ProcessPopCopilotService` e serviços correlatos de processo;
- MCP tools:
  - `get_structuring_journey_tool`;
  - `get_process_strategy_profile_tool`;
  - `get_process_strategic_profile_tool`;
  - `analyze_process_flow_copilot_tool`;
  - `suggest_process_flow_activity_automation_tool`;
  - `draft_process_pop_step_description_tool`;
  - `get_process_pop_step_media_context_tool`;
  - `list_strategy_maturation_backlog_tool`.

Uso no Cockpit:

- avaliar arquitetura: áreas, macroprocessos, processos, donos e indicadores;
- avaliar modelagem: fluxo, POP, recursos, rotina, SPEC para IA e indicadores;
- apontar processos com implantação sem projeto associado;
- acompanhar estabilização por ciclos dentro das faixas de controle;
- sugerir inclusão em auditoria quando houver estabilidade suficiente;
- converter aprendizado de Necessidade Urgente em melhoria de processo quando aplicável.

Lacunas prováveis:

- read model único de maturidade de processo nas cinco etapas: Arquitetura, Modelagem, Implantação, Estabilização e Auditoria;
- vínculo formal entre processo implantado e projeto/programa de implantação;
- contrato de estabilidade auditada por 3 ciclos;
- integração mais explícita com auditoria interna.

#### Planejamento Estratégico

Capacidades já existentes ou reaproveitáveis:

- `StrategyAlignmentN1Service.run_alignment_analysis`;
- `StrategicManagementPanelService`;
- `IndicatorLinkMapService`;
- MCP tools:
  - `analyze_strategic_alignment_n1_tool`;
  - `run_strategy_alignment_n1_analysis_tool`;
  - `get_strategy_alignment_n1_readiness_tool`;
  - `list_process_strategy_alignment_links_tool`;
  - `list_indicator_line_of_sight_tool`;
  - `list_strategy_maturation_backlog_tool`.

Uso no Cockpit:

- avaliar se o planejamento existe e está estruturado;
- verificar conexão entre objetivos, processos, projetos e indicadores;
- identificar objetivos sem processo, indicador ou projeto correspondente;
- sugerir prioridades de desdobramento;
- preparar discussão estratégica com o cliente.

Lacunas prováveis:

- contrato canônico do planejamento estratégico como objeto vivo, quando ainda estiver disperso em OKRs/projetos/indicadores;
- leitura simples para o consultor sem jargão N1;
- vínculo explícito entre planejamento estratégico e Business Review quando houver valor agregado estratégico.

#### Gerenciamento Estratégico

Capacidades já existentes ou reaproveitáveis:

- `StrategicManagementPanelService`;
- `IndicatorLinkMapService`;
- `IncentiveSpiderWebService`;
- `IncentiveService`;
- MCP tools:
  - `get_incentive_indicators`;
  - `get_strategic_connection_graph`;
  - `get_strategic_connection_metrics`;
  - `generate_strategic_connection_summary`;
  - `list_indicator_line_of_sight_tool`.

Uso no Cockpit:

- avaliar cobertura e saúde dos indicadores;
- identificar indicadores sem ciclo de gestão;
- avaliar coerência de incentivos;
- visualizar a teia de conexões entre estratégia, processos, projetos, pessoas e indicadores;
- apontar decisões pendentes, ações não desdobradas e aprendizados não convertidos.

Lacunas prováveis:

- leitura integrada entre ciclos de gestão, reuniões e decisões;
- contrato de aprendizado estratégico recorrente;
- UX executiva para teia de conexões dentro do Cockpit;
- critério de maturidade do gerenciamento estratégico por evidência, não apenas por existência de indicadores.

### 37.4 Agentes sugeridos por ação

Os agentes podem ser implementados como perfis/orquestrações internas, não necessariamente como usuários visíveis.

| Ação | Agente principal | Apoio | Observação |
|---|---|---|---|
| Analisar frente | Agente Analista da Frente | MCP + Squad Versus | Diagnóstico com evidências internas |
| Gerar diagnóstico | Agente Consultivo Versus | Squad Versus | Consolida maturidade, riscos e próximos passos |
| Pesquisar boas práticas | Agente Pesquisador | Internet + benchmark + Squad Versus | Deve separar benchmark externo de dado interno |
| Sugerir plano de maturação | Agente Planejador | Squad Versus + Squad Engenharia | Gera proposta, não execução automática |
| Revisar evidências | Agente Auditor Metodológico | MCP + N1 | Confere se evidências sustentam status/maturidade |
| Preparar reunião | Agente Preparador de Reunião | MCP + histórico + recomendações | Gera pauta, perguntas e decisões esperadas |
| Apontar gaps técnicos | Agente Engenharia | Squad Engenharia | Identifica lacunas de modelo, API, MCP, dados e UX |

### 37.5 Contrato de resposta agentic

Toda análise assistida do Cockpit deve retornar um envelope padronizado, mesmo que a primeira versão seja apenas interna ao service/read model.

Contrato mínimo:

```json
{
  "front": "processes",
  "action": "generate_diagnosis",
  "company_id": 1,
  "summary": "Resumo executivo para o consultor.",
  "maturity": {
    "status": "partial",
    "score": 55,
    "basis": "Evidências encontradas e critérios aplicados."
  },
  "internal_evidence": [
    {
      "type": "process",
      "id": 123,
      "label": "Processo fiscal",
      "finding": "Existe fluxo, mas POP está incompleto."
    }
  ],
  "gaps": [
    {
      "type": "methodological",
      "severity": "medium",
      "description": "Implantação não possui projeto associado."
    }
  ],
  "recommendations": [
    {
      "priority": "P1",
      "description": "Criar projeto de implantação e treinamento do processo fiscal.",
      "target_object": "project"
    }
  ],
  "external_benchmarks": [],
  "engineering_gaps": [],
  "human_gate_required": true,
  "suggested_next_action": "open_maturation_plan"
}
```

Regras do contrato:

- `internal_evidence` só pode conter dados vindos do APP32/MCP/services;
- `external_benchmarks` deve identificar origem externa e não pode ser confundido com evidência interna;
- `engineering_gaps` deve separar problema do sistema de problema da empresa;
- `human_gate_required` deve ser `true` sempre que houver sugestão de promoção canônica, alteração crítica, criação de projeto ou mudança de status de maturidade.

### 37.6 Estados da ação assistida

Cada ação assistida deve seguir estados simples:

| Estado | Significado |
|---|---|
| `draft` | análise gerada, ainda não revisada pelo consultor |
| `reviewing` | consultor está avaliando ou complementando |
| `accepted` | recomendação aceita e convertida em ação/registro |
| `rejected` | recomendação recusada com motivo |
| `converted` | recomendação virou projeto, atividade, revisão, Business Review ou item de maturação |

Esses estados não precisam aparecer com nomes técnicos para o usuário final, mas devem existir para auditoria e aprendizado dos agentes.

### 37.7 Conversão da recomendação em ação

Uma recomendação aceita deve poder gerar apenas objetos canônicos ou registros consultivos já definidos:

| Recomendação | Conversão permitida |
|---|---|
| Resolver execução | Projeto, programa ou atividade |
| Corrigir processo | Frente de processo, projeto de implantação, POP, rotina ou auditoria |
| Rever identidade | Item de maturação/human gate ou atualização canônica validada |
| Melhorar estratégia | Revisão do planejamento, vínculo de objetivo, projeto ou indicador |
| Melhorar gestão | Indicador, ciclo, incentivo, reunião, decisão ou plano de ação |
| Registrar valor | Business Review |
| Corrigir sistema | Backlog técnico do Squad Engenharia |

Regra: agentes não devem criar objetos críticos diretamente sem confirmação explícita do consultor.

### 37.8 Implementação em fases

#### Fase A — Read model funcional

- Criar read model por frente com dados internos já disponíveis.
- Não executar IA generativa ainda.
- Expor apenas diagnóstico determinístico: status, evidências, gaps e próximos passos.

#### Fase B — Assistência agentic controlada

- Adicionar ação **Gerar diagnóstico assistido**.
- Usar MCP/services como contexto obrigatório.
- Salvar resposta como draft.
- Exigir validação do consultor.

#### Fase C — Pesquisa e benchmark

- Adicionar ação **Pesquisar boas práticas**.
- Separar benchmark externo de evidência interna.
- Exigir citação/origem quando houver pesquisa externa.

#### Fase D — Conversão assistida

- Permitir converter recomendação aceita em projeto, atividade, item de maturação, Business Review ou backlog técnico.
- Registrar aceite/rejeição para aprendizado.

#### Fase E — Aprendizado contínuo

- Usar histórico de recomendações aceitas/rejeitadas para melhorar prompts, critérios e orquestração.
- Manter human gate para decisões críticas.

### 37.9 Primeira entrega recomendada

A primeira entrega deve ser conservadora e funcional:

1. Adicionar botão **Analisar frente** em cada card da Estruturação Empresarial.
2. Abrir um painel lateral ou modal com:
   - resumo;
   - evidências internas;
   - gaps;
   - recomendações;
   - gaps técnicos;
   - ação sugerida.
3. Usar apenas services/read models existentes, sem criar automação autônoma.
4. Registrar o resultado como draft local/auditável.
5. Deixar **Pesquisar boas práticas** e **Converter recomendação** para fases seguintes.

Essa sequência reduz risco, entrega valor rápido ao consultor e prepara a base para uso mais forte de agentes e IA sem comprometer segurança, multi-tenancy ou clareza metodológica.

---

## 38. Realinhamento oficial — Painel de Gestão Estratégica e Cockpit do Consultor

Status em 2026-07-01:

Após revisão do Painel de Gestão Estratégica, fica definido que ele deve permanecer como superfície operacional/executiva da empresa, e não como segunda porta da metodologia Versus.

### 38.1 Papel oficial do Painel de Gestão Estratégica

O Painel de Gestão Estratégica deve responder:

> Como está a gestão estratégica da empresa agora?

Ele deve concentrar:

- indicadores;
- metas e medições;
- semáforos;
- reuniões;
- decisões;
- ações corretivas;
- projetos vinculados a indicadores;
- incentivos;
- teia de conexões quando usada para decisão gerencial.

Esses elementos pertencem ao Objeto Canônico da empresa ou a leituras executivas diretamente ligadas à sua gestão operacional.

### 38.2 O que sai do Painel como porta principal

A Trilha de Maturidade da Estruturação, com Fases 00, 01, 02 e 03, gates e leitura de avanço metodológico, não deve permanecer como coluna principal do Painel de Gestão Estratégica.

Essa trilha pertence ao Cockpit do Consultor, como eixo macro da Estruturação Empresarial.

O Painel pode exibir apenas uma chamada discreta para o Cockpit, por exemplo:

```text
Maturidade metodológica acompanhada no Cockpit do Consultor.
```

### 38.3 Relação correta entre as telas

- **Painel de Gestão Estratégica**: gestão operacional da estratégia pela empresa.
- **Cockpit do Consultor**: condução consultiva/evolutiva da maturidade, fases, gates e frentes estruturais.

O Painel pode alimentar evidências para a frente **Gerenciamento Estratégico** do Cockpit, mas não deve tentar substituir o Cockpit.

### 38.4 Backlog técnico derivado

1. Remover a coluna de Trilha de Maturidade do template do Painel de Gestão Estratégica.
2. Manter, no máximo, um card discreto de encaminhamento para o Cockpit do Consultor.
3. Preservar temporariamente o read model `structuring_trail` na API para compatibilidade, mas tratá-lo como legado/auxiliar.
4. Consumir os dados do Painel dentro da análise assistida da frente Gerenciamento Estratégico no Cockpit.
