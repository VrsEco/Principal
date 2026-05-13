# APP32 — Contrato MCP para Runtime BPMN/BPMS

**Data:** 2026-05-07  
**Status:** contrato técnico alvo  
**Especialista líder:** @ARQUITETO  
**Apoios naturais:** @AI_ENGINEER, @BACKEND_API, @BACKEND_SERVICE, @QA_AUTOMATION

---

## 1. Objetivo

Definir o contrato técnico entre:

- **runtime BPMS**;
- **MCP Sapiens**;
- **IA operadora da etapa**.

Este documento formaliza:

1. a tool MCP canônica para execução de activities;
2. o payload oficial entregue pelo runtime;
3. o envelope de contexto que a IA recebe;
4. as regras de conclusão, escalonamento e evidência.

---

## 2. Regra central

> A IA nunca executa “pela descrição solta”.  
> Ela executa sempre a partir de um **runtime packet** canônico do BPMS.

Ordem obrigatória de consumo:

1. BPMN publicado;
2. instância BPMS;
3. contrato da activity;
4. POP oficial;
5. POP para IA;
6. evidências e outputs já registrados;
7. policy de escalonamento.

---

## 3. Tool MCP canônica

Nome sugerido:

- `processes.bpms.execute_activity`

Surface recomendada:

- `user`, quando a activity for operacional tenant-safe;
- `admin`, apenas para replay, suporte ou override governado.

### 3.1. Input da tool

```json
{
  "company_id": 12,
  "process_instance_id": 845,
  "activity_execution_id": 1942,
  "expected_activity_id": "Activity_ApproveTechnicalScope",
  "mode": "execute",
  "human_gate_acknowledged": false,
  "dry_run": false
}
```

### 3.2. Regras do input

- `company_id` é obrigatório;
- `process_instance_id` é obrigatório;
- `activity_execution_id` é obrigatório;
- `expected_activity_id` protege contra drift de estado;
- `mode` inicial permitido:
  - `inspect`
  - `execute`
  - `retry`
  - `complete_manual_gate`
- `human_gate_acknowledged=true` só pode existir quando a etapa exigir confirmação explícita;
- `dry_run=true` deve devolver decisão e ações previstas sem mutação.

---

## 4. Runtime packet canônico do BPMS

O runtime nunca deve entregar contexto parcial.

Ele deve montar um pacote único, por exemplo:

```json
{
  "instance": {
    "process_instance_id": 845,
    "company_id": 12,
    "process_id": 41,
    "process_code": "PRC-ELETROPOSTO-001",
    "process_name": "Implantar operação de recarga rápida",
    "bpmn_diagram_id": 55,
    "bpmn_version": 7,
    "status": "in_progress",
    "started_at": "2026-05-07T10:00:00Z"
  },
  "phase": {
    "phase_id": "implantacao",
    "phase_name": "Implantação",
    "sequence": 3
  },
  "activity": {
    "activity_execution_id": 1942,
    "bpmn_activity_id": "Activity_ApproveTechnicalScope",
    "activity_name": "Validar escopo técnico",
    "execution_mode": "manual_ai_assisted",
    "interaction_mode": "review_screen",
    "status": "ready",
    "started_at": null,
    "due_at": "2026-05-08T18:00:00Z",
    "sla_minutes": 480
  },
  "contract": {
    "contract_id": "bpms-contract-validate-technical-scope-v1",
    "objective": "Confirmar aderência técnica antes da proposta final",
    "preconditions": [
      "viabilidade concluída",
      "dados elétricos disponíveis"
    ],
    "inputs": [
      {"name": "dados_unidade", "required": true},
      {"name": "estimativa_demanda_kw", "required": true}
    ],
    "tools": [
      {"kind": "internal_screen", "target": "/plans/12/implantation/model"},
      {"kind": "mcp_tool", "target": "plans.implantation.model.get"}
    ],
    "validations": [
      "demanda elétrica preenchida",
      "premissas críticas registradas"
    ],
    "expected_outputs": [
      "parecer_tecnico",
      "status_validacao"
    ],
    "completion_rule": "all_required_outputs_present",
    "human_gate_rule": "approval_required_if_risk_high"
  },
  "pop": {
    "official_pop_version": 3,
    "ai_pop_version": 2,
    "instructions": [
      "ler premissas da unidade",
      "conferir compatibilidade da infraestrutura",
      "registrar parecer técnico objetivo"
    ],
    "exceptions": [
      "carga insuficiente",
      "dado elétrico ausente"
    ]
  },
  "evidence": {
    "required": [
      "parecer_tecnico",
      "premissas_registradas"
    ],
    "existing": [
      {"name": "viabilidade_pdf", "status": "present"}
    ]
  },
  "escalation": {
    "must_escalate_if": [
      "missing_required_input",
      "approval_required",
      "exception_not_mapped",
      "confidence_below_threshold"
    ],
    "may_auto_complete_if": [
      "all_validations_pass",
      "all_required_outputs_present",
      "no_human_gate_active"
    ]
  }
}
```

---

## 5. Envelope de contexto entregue à IA

A IA não deve receber apenas `prompt`.

Ela deve receber:

1. **contexto de identidade**;
2. **runtime packet**;
3. **política de autonomia**;
4. **formato de resposta exigido**.

### 5.1. Identity context

```json
{
  "user_id": 123,
  "company_id": 12,
  "employee_id": 778,
  "surface": "user",
  "channel": "mcp",
  "fallback_role": "colaborador"
}
```

### 5.2. Autonomy policy

```json
{
  "execution_policy": {
    "may_write": true,
    "may_call_tools": true,
    "may_complete_activity": true,
    "may_override_flow": false,
    "may_skip_required_evidence": false,
    "must_request_human_when": [
      "approval_required",
      "exception_not_mapped",
      "high_financial_risk",
      "high_legal_risk"
    ]
  }
}
```

### 5.3. Response contract da IA

```json
{
  "decision": "complete",
  "summary": "Escopo validado sem pendências críticas.",
  "actions_taken": [
    "premissas conferidas",
    "parecer técnico registrado"
  ],
  "outputs": {
    "parecer_tecnico": "aprovado",
    "status_validacao": "ok"
  },
  "evidence_generated": [
    "parecer_tecnico",
    "premissas_registradas"
  ],
  "escalation": null,
  "confidence": 0.93
}
```

Decisões iniciais permitidas:

- `complete`
- `wait_human`
- `retry_later`
- `fail_business`

---

## 6. Regra de evidência

Toda execução por IA precisa deixar evidência estruturada.

Campos mínimos:

- `activity_execution_id`
- `company_id`
- `executed_by_mode = ai_mcp`
- `decision`
- `outputs`
- `validations_passed`
- `evidence_generated`
- `confidence`
- `escalation_reason`
- `occurred_at`

Regra:

> Sem evidência estruturada, a activity não pode ser considerada concluída pela IA.

---

## 7. Regras de escalonamento

Escalonar obrigatoriamente quando houver:

- aprovação formal;
- exceção não mapeada no POP para IA;
- input obrigatório ausente;
- divergência entre BPMN, contrato e estado da instância;
- risco alto financeiro, fiscal, jurídico ou reputacional;
- confidence abaixo do threshold da activity.

Threshold inicial sugerido:

- `0.85` para auto-complete;
- abaixo disso, `wait_human`.

---

## 8. Guardrails arquiteturais

- `company_id` obrigatório em toda mutation;
- a tool não pode recalcular livremente a próxima etapa;
- a transição válida vem do motor BPMS;
- a IA não pode concluir activity sem `completion_rule` satisfeita;
- override humano deve ficar auditado;
- a tool MCP deve delegar mutação real para `services/`, nunca para rota com regra embutida.

---

## 9. Sequência recomendada de implementação

1. criar schema Pydantic do runtime packet;
2. criar schema Pydantic do response contract da IA;
3. criar service `build_bpms_runtime_packet(...)`;
4. criar tool `processes.bpms.execute_activity`;
5. criar policy engine de escalonamento;
6. criar storage de evidências de execução IA;
7. plugar no shell BPMS e no MCP remoto.

---

## 10. Resultado esperado

Com esse contrato:

- o BPMS continua sendo a verdade da orquestração;
- o MCP continua sendo a camada de execução tool-first;
- a IA passa a operar com contexto suficiente e governado;
- a conclusão da etapa deixa de depender de inferência solta e passa a depender de contrato, evidência e policy.
