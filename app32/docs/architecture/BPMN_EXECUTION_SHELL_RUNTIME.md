# APP32 — BPMN Execution Shell & Runtime

**Data:** 2026-04-30  
**Status:** proposta arquitetural executável  
**Especialista líder:** @ARQUITETO  
**Apoios naturais:** @FRONTEND, @BACKEND_API, @BACKEND_SERVICE, @DBA, @AI_ENGINEER, @QA_AUTOMATION

---

## 1. Objetivo

Evoluir o módulo de **Gestão da Rotina > Processos > Modelagem** para suportar a jornada completa:

- identificação do processo;
- modelagem BPMN;
- operação por rotina/instância;
- automação BPMS por atividade.

No contexto deste documento, o foco principal continua sendo o **runtime visual de execução**, onde o usuário consiga:

1. iniciar uma instância de processo baseada no BPMN publicado;
2. visualizar o fluxo sendo executado em tempo real;
3. distinguir claramente:
   - atividades já cumpridas;
   - atividade em execução;
   - atividades ainda pendentes;
   - atividades pausadas ou bloqueadas;
4. parar, pausar e retomar a execução com baixa fricção;
5. registrar obrigatoriamente:
   - `started_at`;
   - `completed_at`;
6. registrar opcionalmente:
   - horas gastas por atividade e por instância;
7. executar cada atividade conforme seu modo:
   - automática;
   - interação humana em tela;
   - chamada REST externa;
   - chamada MCP.

---

## 2. Tese arquitetural

O BPMN do APP32 não deve ser apenas documento visual.

Ele deve evoluir para:

```text
BPMN publicado
→ definição oficial do fluxo
→ instância runtime por empresa
→ tracking por activity/gateway/event
→ shell visual de execução
→ delegação para executor humano, service interno, REST externo ou MCP
```

Regra central:

> O elemento BPMN não deve apontar diretamente para uma rota hardcoded.  
> Ele deve resolver um **contrato de execução** e o runtime decide como executar.

### 2.1. Esteira oficial de descoberta e execução

A evolução correta do APP32 não começa pela criação direta de tela, automação ou módulo a partir de uma activity isolada.

Ela segue a esteira abaixo:

```text
1. Modelar o processo em BPMN
2. Analisar necessidades reveladas pelo processo
3. Analisar capacidades já existentes no APP32
4. Classificar cada necessidade como:
   - núcleo novo
   - capability/complemento reutilizável
   - execução externa sem vínculo
   - execução externa com vínculo REST/MCP
   - uso de capacidade já existente
5. Projetar e implementar o que faltar
6. Configurar o BPMS para orquestrar essas capacidades
7. Vincular rotina, instância, SLA e monitoramento em shell único
```

Regra mandatória:

> O BPMN revela a demanda.  
> A arquitetura classifica a demanda.  
> O produto cria ou reaproveita capacidades.  
> O BPMS orquestra a execução final.

---

## 3. Estado atual aproveitável

O repositório já possui base útil para isso:

- `process_bpmn_diagrams` com BPMN versionado;
- `process_routines` vinculável a `bpmn_element_id`;
- `process_instances` para execução operacional;
- UI de instâncias em:
  - `C:\GestaoVersus\app32\app32\templates\modules\processes\process_instances_list.html`
  - `C:\GestaoVersus\app32\app32\templates\modules\processes\process_instance_v2.html`
- service BPMN em:
  - `C:\GestaoVersus\app32\app32\services\process_bpmn_service.py`

Conclusão:

> O passo correto não é criar outro módulo paralelo.  
> É transformar `process_instances` em runtime BPMN de verdade.

---

## 3.1. Níveis oficiais de maturidade do processo

Os processos do APP32 devem ser organizados oficialmente em 3 níveis:

## Nível A — Processo Identificado

Representa o processo apenas no nível de arquitetura/mapa.

Contém:

- cadastro do processo;
- posicionamento na arquitetura;
- vínculo com área/macroprocesso;
- visão de mapa.

Não exige:

- BPMN;
- POP;
- rotina;
- indicador;
- automação.

Objetivo:

> Permitir que a empresa identifique e organize seus processos, mesmo antes de detalhar execução.

## Nível B — Processo Modelado (BPMN)

Representa o processo operacionalmente modelado.

Contém:

- fluxo BPMN;
- POP;
- rotina;
- indicadores.

Observação importante:

- a **rotina** pode disparar a instância:
  - manualmente;
  - por agendamento/cron;
- a tela de controle da execução pode ser:
  - **BPMN**, quando o foco for acompanhamento do fluxo;
  - **BPMS**, quando houver camada mais forte de execução/automação.

Objetivo:

> Tornar o processo executável e monitorável, mesmo sem automação profunda.

## Nível C — Processo Automatizado (BPMS)

Representa o processo com orchestration operacional por atividade.

Contém:

- contrato de atividade;
- páginas/telas;
- automações;
- integrações REST/MCP.

Observação:

> Todo processo BPMS parte de uma base modelada, mas nem todo processo modelado precisa virar BPMS.

Complemento:

> O BPMS é sempre a camada final de acoplamento operacional.  
> Ele não substitui o domínio funcional e não deve concentrar cadastro nuclear do negócio.

---

## 3.2. Regra de compatibilidade obrigatória

Mesmo sem BPMN ou automação, o processo deve continuar válido no APP32.

Portanto:

- Processo Identificado funciona sem fluxo.
- Processo Modelado funciona sem automação BPMS.
- Processo Automatizado é evolução, não pré-requisito.

Guardrail:

> O APP32 também deve servir para controlar processos e atividades executadas totalmente fora do sistema.

Exemplos:

- execução em sistema de terceiro;
- execução manual por telefone;
- execução em portal bancário;
- execução em documento físico;
- execução operacional sem tela interna no APP32.

---

## 4. Experiência do usuário desejada

## 4.1. Tela-shell da instância

A instância deve abrir em uma **shell única de processo** contendo:

- cabeçalho da instância;
- status global;
- timestamps obrigatórios;
- ações de pausar, retomar, cancelar e concluir;
- mapa BPMN renderizado;
- painel lateral ou inferior com detalhes da atividade atual;
- painel BPMS da activity corrente com:
  - modo de execução;
  - capability atual;
  - SLA;
  - contrato da atividade;
  - CTA para abrir tela interna, link externo ou indicar execução automática/REST/MCP;
- indicação das próximas etapas possíveis inferidas do BPMN;
- histórico de execução;
- horas opcionais;
- logs técnicos/operacionais.

Definição de produto:

> O shell não é “mais um módulo”.  
> Ele é uma camada transversal de trabalho que reúne tudo o que o usuário precisa para executar, controlar e retomar a atividade, mesmo quando os dados e capacidades vêm de módulos diferentes.

### Regra adicional de experiência

Quando a activity possuir contrato BPMS:

- o shell deve abrir a capability correta sem obrigar o usuário a navegar manualmente por outro menu;
- o contrato pode resolver:
  - URL interna parametrizada;
  - aba/capability interna;
  - URL externa;
  - integração REST;
  - integração MCP;
  - execução automática.

Quando não houver contrato:

- o shell continua operacional;
- o APP32 trata a etapa como controle manual/externo, sem bloquear a instância.

## 4.1.1. Compatibilização obrigatória com Calendário

O Calendário Operacional não substitui a shell BPMS.

Ele deve funcionar como **porta de entrada temporal**:

```text
Evento do calendário
→ abre a instância correta
→ posiciona o usuário na shell BPMS
→ destaca a activity atual e o próximo passo
```

Guardrail:

> Deep links originados do Calendário devem apontar para `/my-work/process-instance/<id>` e não para telas intermediárias de listagem.

## 4.2. Estados visuais do fluxo

Cada elemento BPMN relevante deve receber overlay visual por estado:

| Estado | Cor sugerida | Regra |
|---|---|---|
| `completed` | verde | atividade concluída com sucesso |
| `in_progress` | azul | atividade atual em execução |
| `pending` | cinza | ainda não iniciada |
| `paused` | âmbar | pausada manualmente |
| `waiting_external` | roxo | aguardando sistema/API/MCP externo |
| `failed` | vermelho | falha na execução |
| `skipped` | cinza tracejado | caminho não seguido por gateway |

Diretriz UX:

- cor sozinha não basta;
- incluir ícone, tooltip e legenda;
- activity atual deve pulsar sutilmente;
- zoom no elemento atual deve ser suportado.

## 4.3. Ações práticas

O usuário deve conseguir, da própria shell:

- **Iniciar execução**
- **Pausar**
- **Retomar**
- **Executar atividade atual**
- **Reprocessar atividade com falha**
- **Avançar para próxima atividade** quando permitido
- **Finalizar instância**

Sem navegação solta.  
O BPMN deve ser o condutor da jornada.

---

## 5. Campos obrigatórios e opcionais

## 5.1. Obrigatórios

Na instância:

- `started_at`
- `completed_at`
- `status`
- `current_bpmn_element_id`
- `company_id`
- `process_id`
- `process_bpmn_diagram_id`
- `process_version`

Na execução da atividade:

- `started_at`
- `completed_at` quando concluída
- `status`
- `bpmn_element_id`
- `execution_mode`
- `performed_by_user_id` quando humana

## 5.2. Opcionais

- `estimated_hours`
- `actual_hours`
- apontamentos detalhados por usuário
- tempo em pausa
- motivo da pausa
- payload técnico de integração

Regra:

> Horas são opcionais, timestamps não.

---

## 5. Arquitetura de camadas

Para sustentar os níveis A/B/C sem acoplamento excessivo, a organização recomendada é:

```text
Processo
├── Camada A: Identificação
│   ├── cadastro
│   ├── arquitetura
│   └── mapa
│
├── Camada B: Modelagem
│   ├── BPMN
│   ├── POP
│   ├── rotina
│   └── indicadores
│
└── Camada C: Automação BPMS
    ├── contrato de atividade
    ├── páginas/telas
    ├── automações
    ├── REST
    └── MCP
```

Regra central:

> O processo é a entidade raiz.  
> BPMN é camada de modelagem.  
> BPMS é camada de automação.

---

## 6. Modelo de domínio proposto

## 6.1. Processo como raiz e BPMN/BPMS como camadas opcionais

Relação conceitual:

```text
process
├── pode existir sozinho                         (Nível A)
├── pode ter BPMN/POP/Rotina/Indicadores         (Nível B)
└── pode ter Contrato/Tela/Automação/REST/MCP    (Nível C)
```

Logo:

- BPMN é opcional;
- BPMS é opcional;
- rotina não depende obrigatoriamente de automação;
- instância não depende obrigatoriamente de BPMN.

## 6.2. Evoluir `process_instances`

Adicionar ou consolidar em `process_instances`:

```text
process_instances
├── id
├── company_id
├── process_id
├── process_bpmn_diagram_id
├── process_version
├── instance_code
├── title
├── status
├── current_bpmn_element_id
├── current_execution_id
├── started_at
├── completed_at
├── paused_at
├── pause_reason
├── estimated_hours
├── actual_hours
├── trigger_type
├── runtime_context_json
├── created_by
├── created_at
└── updated_at
```

Status global recomendado:

- `pending`
- `in_progress`
- `paused`
- `waiting_external`
- `completed`
- `failed`
- `cancelled`

## 6.3. Nova tabela de execução por elemento BPMN

```text
process_instance_executions
├── id
├── company_id
├── process_instance_id
├── process_id
├── process_bpmn_diagram_id
├── bpmn_element_id
├── bpmn_element_name
├── bpmn_element_type
├── execution_mode
├── handler_key
├── capability_key
├── status
├── started_at
├── completed_at
├── paused_at
├── waiting_since
├── duration_seconds
├── estimated_hours
├── actual_hours
├── performed_by_user_id
├── performer_type
├── external_ref
├── request_payload_json
├── response_payload_json
├── error_payload_json
├── metadata_json
├── created_at
└── updated_at
```

Status por atividade:

- `pending`
- `ready`
- `in_progress`
- `paused`
- `waiting_external`
- `completed`
- `failed`
- `skipped`

## 6.4. Contrato de execução da atividade

Nova tabela:

```text
process_activity_execution_contracts
├── id
├── company_id
├── process_id
├── bpmn_element_id
├── version
├── execution_mode
├── interaction_mode
├── capability_key
├── route_name
├── ui_schema_json
├── rest_config_json
├── mcp_config_json
├── auto_service_key
├── requires_human_gate
├── allows_pause
├── allows_retry
├── sla_minutes
├── completion_rules_json
├── created_at
└── updated_at
```

Observação de nível:

- Nível B pode existir sem esta tabela;
- Nível C passa a depender dela para orquestração BPMS.

## 6.5. Entidade futura recomendada: atividade operacional

Hoje parte do vínculo está em `process_routines`, o que serve para o MVP.

Para a evolução correta, recomenda-se consolidar uma entidade própria:

```text
process_activities
├── id
├── company_id
├── process_id
├── bpmn_element_id (opcional)
├── code
├── name
├── description
├── activity_kind
├── execution_profile
├── pop_routine_id (opcional)
├── indicator_binding_json
├── is_active
├── created_at
└── updated_at
```

Onde:

- `bpmn_element_id` pode ser nulo para atividade fora do fluxo;
- `activity_kind` pode diferenciar:
  - manual externa;
  - humana interna;
  - automática;
  - integração.

---

## 7. Modos de execução

## 7.1. `automatic`

Usado quando a atividade é totalmente executável no backend.

Exemplos:

- consolidar dados;
- gerar artefato;
- validar payload;
- aplicar regra interna;
- disparar job local.

Fluxo:

```text
runtime entra na activity
→ busca contract
→ chama service interno
→ grava request/response
→ marca completed ou failed
→ move token para próxima etapa
```

## 7.2. `human_task`

Usado quando a atividade exige interação humana em tela.

Fluxo:

```text
runtime entra na activity
→ shell resolve tela/componente
→ abre aba/modal/drawer/página guiada
→ usuário interage
→ validação de conclusão
→ runtime marca completed
```

## 7.3. `external_rest`

Usado quando a atividade depende de integração REST.

Campos mínimos:

- URL lógica ou integration key;
- método HTTP;
- auth strategy;
- timeout;
- política de retry;
- mapeamento request/response;
- critério de sucesso.

Fluxo:

```text
runtime entra na activity
→ monta payload
→ chama integração REST
→ status vai para waiting_external ou completed
→ callback/polling pode concluir depois
```

## 7.4. `external_mcp`

Usado quando a atividade será executada via tool MCP.

Campos mínimos:

- `surface`
- `tool_name`
- `tool_action`
- contexto necessário
- política de aprovação humana

Fluxo:

```text
runtime entra na activity
→ resolve tool MCP autorizada
→ injeta contexto tenant-safe
→ executa tool
→ registra output estruturado
→ conclui ou sinaliza falha
```

Guardrail:

> Toda chamada MCP deve ser tenant-safe e carregar `company_id`.

## 7.5. `manual_external`

Usado quando a atividade existe, é controlada pelo APP32, mas sua execução real acontece fora dele.

Exemplos:

- portal bancário;
- sistema legado de terceiro;
- ligação telefônica;
- ação presencial;
- conferência em documento externo.

Fluxo:

```text
runtime entra na activity
→ mostra instrução/POP/checklist
→ usuário registra início/execução/evidência
→ usuário conclui manualmente
→ runtime grava timestamps e histórico
```

Esse modo é obrigatório para preservar aderência aos processos não digitalizados no APP32.

---

## 8. Interaction modes para UI

Além do modo de execução, cada atividade humana deve declarar um `interaction_mode`:

- `inline_form`
- `tab_shell`
- `modal`
- `drawer`
- `review_screen`
- `readonly_panel`

Regra:

> `execution_mode` responde **quem executa**.  
> `interaction_mode` responde **como o usuário interage**.

---

## 9. Comportamento de pausa e retomada

## 9.1. Pausar instância

Ao pausar:

- `process_instances.status = paused`
- `paused_at` obrigatório
- `pause_reason` opcional, mas recomendado
- activity atual também vira `paused` se estiver humana

## 9.2. Retomar instância

Ao retomar:

- volta para `in_progress` ou `waiting_external`, conforme contexto;
- a shell reabre a activity atual;
- o BPMN destaca novamente o ponto de retomada.

## 9.3. Regras

- atividade automática curta não deve pausar no meio;
- atividade externa pode virar `waiting_external`, não necessariamente `paused`;
- pause/resume deve existir tanto no nível da instância quanto da activity.

---

## 10. Shell visual recomendada

## 10.1. Cabeçalho

Mostrar:

- código da instância;
- nome do processo;
- versão BPMN;
- status;
- `started_at`;
- `completed_at`;
- tempo corrido;
- horas registradas, se houver.

## 10.2. Canvas BPMN

Mostrar:

- diagrama publicado;
- overlays por estado;
- foco automático na etapa atual;
- clique no elemento para abrir:
  - detalhes;
  - contrato;
  - histórico da execução;
  - POP vinculado.

## 10.3. Painel da atividade atual

Mostrar:

- nome da atividade;
- descrição operacional;
- executor;
- modo de execução;
- tempo iniciado;
- SLA;
- ação principal:
  - executar automaticamente;
  - abrir tela;
  - chamar integração;
  - reprocessar.

## 10.4. Timeline/histórico

Listar:

- atividade iniciada;
- atividade concluída;
- pausa;
- retomada;
- falha;
- chamada externa;
- aprovação humana.

---

## 11. Regras de conclusão

Uma activity só pode ser concluída quando o contrato disser que está válida.

Exemplos:

- tela humana preenchida e salva;
- API externa retornou sucesso;
- tool MCP devolveu resultado esperado;
- checklist/aceite foi confirmado.

Logo:

> Não concluir atividade por clique cego.  
> Concluir por regra validada em service.

---

## 12. Backend e boundaries

## 12.1. Rotas finas

As rotas devem apenas:

- autenticar;
- autorizar;
- validar payload;
- delegar para service.

## 12.2. Services propostos

Criar núcleo dedicado:

```text
app32/services/process_execution_runtime_service.py
app32/services/process_execution_contract_service.py
app32/services/process_execution_dispatch_service.py
app32/services/process_execution_tracking_service.py
app32/services/process_execution_view_service.py
```

## 12.3. Responsabilidades

### `process_execution_runtime_service`
- iniciar instância pelo BPMN publicado;
- resolver próximo elemento;
- aplicar transições;
- finalizar instância.

### `process_execution_contract_service`
- ler contrato por `bpmn_element_id`;
- validar completude de configuração;
- resolver modo de execução/interação.

### `process_execution_dispatch_service`
- chamar:
  - service interno;
  - tela humana;
  - REST externo;
  - MCP.

### `process_execution_tracking_service`
- registrar timestamps;
- logs;
- retries;
- falhas;
- pausa/retomada;
- horas opcionais.

### `process_execution_view_service`
- montar payload da shell;
- gerar mapa de cores/estados para o BPMN viewer.

---

## 13. APIs sugeridas

```text
POST   /api/processes/<process_id>/instances/start
GET    /api/process-instances/<instance_id>/runtime
POST   /api/process-instances/<instance_id>/pause
POST   /api/process-instances/<instance_id>/resume
POST   /api/process-instances/<instance_id>/activities/<execution_id>/execute
POST   /api/process-instances/<instance_id>/activities/<execution_id>/complete
POST   /api/process-instances/<instance_id>/activities/<execution_id>/retry
GET    /api/process-instances/<instance_id>/timeline
GET    /api/process-instances/<instance_id>/bpmn-overlay
```

Todos com escopo obrigatório por `company_id`.

---

## 14. Payload de overlay para o viewer

Exemplo:

```json
{
  "instance_id": 981,
  "current_bpmn_element_id": "Activity_ReviewContract",
  "elements": [
    {
      "bpmn_element_id": "Activity_CreateDraft",
      "status": "completed",
      "started_at": "2026-04-30T14:02:11Z",
      "completed_at": "2026-04-30T14:03:04Z",
      "duration_seconds": 53
    },
    {
      "bpmn_element_id": "Activity_ReviewContract",
      "status": "in_progress",
      "started_at": "2026-04-30T14:03:08Z"
    },
    {
      "bpmn_element_id": "Activity_SendExternalApi",
      "status": "pending"
    }
  ]
}
```

---

## 15. Estratégia de implantação

## Fase 1 — Nível B forte (Modelagem operacional)

- reaproveitar `process_instances`;
- criar viewer BPMN com overlays;
- obrigar `started_at` e `completed_at`;
- adicionar pause/resume;
- destacar current activity.

## Fase 2 — Runtime por atividade

- criar `process_instance_executions`;
- gerar tracking por `bpmn_element_id`;
- suportar transição real de atividade.

## Fase 3 — Nível C forte (Automação BPMS)

- configurar `execution_mode`;
- configurar `interaction_mode`;
- suportar:
  - automática;
  - manual externa;
  - humana;
  - REST;
  - MCP.

## Fase 4 — Runtime inteligente

- retries;
- SLA;
- filas externas;
- callbacks;
- approval gates;
- manifesto AI-readable da execução.

---

## 16. Decisões arquiteturais

1. O runtime BPMN deve nascer sobre o que já existe, não como módulo paralelo.
2. `process_instances` continua sendo a raiz operacional.
3. A trilha por atividade deve usar `bpmn_element_id`.
4. `started_at` e `completed_at` passam a ser obrigatórios no ciclo de execução.
5. Horas continuam opcionais.
6. O viewer BPMN precisa receber overlay por estado.
7. Pause/resume deve ser recurso nativo da shell.
8. Execução deve ser orientada por contrato, não por tela hardcoded.
9. REST externo e MCP são modos de execução de primeira classe.
10. Toda operação deve ser tenant-safe com `company_id`.
11. Nível A, B e C devem coexistir sem obrigar maturidade artificial.
12. BPMN e BPMS não são sinônimos:
    - BPMN = modelagem;
    - BPMS = execução/automação.
13. Processos executados fora do APP continuam sendo casos válidos de primeira classe.

---

## 17. Próximo recorte recomendado

Sequência mais segura para implementação:

1. criar payload de overlay BPMN para instância;
2. evoluir a tela `process_instance_v2.html` para shell de execução;
3. introduzir status `paused` e `waiting_external`;
4. adicionar `current_bpmn_element_id` em `process_instances`;
5. criar `process_instance_executions`;
6. só depois plugar `automatic | manual_external | human_task | external_rest | external_mcp`.

---

## 18. Síntese final

O que você pediu se traduz assim no APP32:

- **BPMN deixa de ser só desenho**
- **vira mapa vivo da execução**
- **mostra o passado, o presente e o próximo passo**
- **permite pausar/retomar**
- **registra início e fim obrigatoriamente**
- **permite horas como camada opcional**
- **executa atividades por contrato**
- **suporta humano, automático, REST e MCP**

Esse é o caminho correto para transformar o BPMN do APP32 em **runtime operacional real**.
