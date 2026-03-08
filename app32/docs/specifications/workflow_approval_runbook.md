# Workflow Approval Runbook

## Objetivo
Padronizar a operação do fluxo de aprovação humana (**HITL**) do `Workflow Engine V3`.

## Escopo atual
A política de aprovação cobre inicialmente ações sensíveis executadas por canais conversacionais:

- `project_task.complete`
- `process_instance.complete`
- `meeting.start`

Canais protegidos:
- `telegram`
- `whatsapp`
- `email`

No canal `web`, a execução continua direta por padrão.

## Fluxo operacional
1. usuário solicita a ação sensível;
2. `WorkflowApprovalPolicyGuard` intercepta a execução;
3. o sistema cria uma `AgentAction` do tipo `workflow_approval_request`;
4. a conversa recebe metadata estruturada em `menu_metadata.workflow_approval`;
5. um aprovador autorizado executa a aprovação ou rejeição;
6. quando aprovada, a retomada segura usa `resume_payload`;
7. a trilha final fica registrada em `AgentAction.payload` e `AgentMessage.metadata_json`.

## Metadados esperados
### Durante a interceptação
```json
{
  "workflow_approval": {
    "required": true,
    "status": "pending",
    "approval_request_id": 123,
    "approval_key": "meeting.start|3|9|R-55",
    "action_key": "meeting.start",
    "object_code": "R-55",
    "channel": "whatsapp",
    "resume_payload": {
      "action_key": "meeting.start",
      "payload": {"codigo_reuniao": "R-55"},
      "active_company_id": 9,
      "user_id": 3,
      "channel": "whatsapp"
    }
  }
}
```

### Após aprovação
Campos mínimos esperados em `AgentAction.payload`:
- `approval_status = approved`
- `approved_by_user_id`
- `approved_at`
- `resume_payload`
- `resume_result`

### Após rejeição
Campos mínimos esperados em `AgentAction.payload`:
- `approval_status = rejected`
- `rejected_by_user_id`
- `rejected_at`
- `rejection_feedback` (quando informado)

## Endpoints operacionais
### Listagem operacional
`GET /api/agents/actions/workflow-approvals`

Filtros suportados:
- `status` (`pending`, `approved`, `executed`, `rejected`, `expired`, `all`)
- `action_key`
- `channel`
- `user_id`
- `limit` (1 a 100)

Retorno esperado:
- `filters`
- `count`
- `workflow_approvals[]` com bloco `approval` estruturado

### Métricas operacionais
`GET /api/agents/actions/workflow-approvals/metrics`

Objetivo:
- acompanhar volume por status, ação, canal e aprovador;
- apoiar fila operacional e revisão de gargalos;
- medir approvals expirados pendentes.

Retorno esperado:
- `limit`
- `metrics.total`
- `metrics.by_status`
- `metrics.by_action_key`
- `metrics.by_channel`
- `metrics.by_requester_user_id`
- `metrics.by_approver_user_id`
- `metrics.expired_pending`

### Revalidar
`POST /api/agents/actions/revalidate/<action_id>`

Uso recomendado:
- quando a solicitação estiver com `approval_status = expired`;
- quando o aprovador decidir renovar o prazo sem executar imediatamente.

Retorno esperado:
- `message`
- `action`
- `resume_payload`
- `approval_metadata`

### Aprovar
`POST /api/agents/actions/approve/<action_id>`

Retorno esperado:
- `message`
- `action`
- `resume_payload`
- `resume_result`
- `approval_metadata`

### Rejeitar
`POST /api/agents/actions/reject/<action_id>`

Body opcional:
```json
{
  "feedback": "Segurar até validarmos com o cliente."
}
```

Retorno esperado:
- `message`
- `action`
- `resume_payload`
- `approval_metadata`

## Checklist de validação
### Aprovação
- o `AgentAction` saiu de `pending` para `approved` ou `executed`;
- `approval_metadata.workflow_approval.event` foi preenchido;
- `resume_result` existe quando houve retomada;
- um `AgentMessage` outbound foi criado com `agent_name = workflow_approval`.

### Rejeição
- o `AgentAction` saiu de `pending` para `rejected`;
- `rejection_feedback` foi persistido quando informado;
- um `AgentMessage` outbound foi criado com o evento `rejected`.

## Observabilidade
A trilha mínima deve existir nestes pontos:
- `AgentAction.payload`
- `AgentMessage.metadata_json.workflow_approval`
- `menu_metadata.workflow_approval`

## Próximos endurecimentos recomendados
- regra de expiração de approval pendente;
- retry/retomada idempotente com chave única por execução;
- painel operacional com filtros por status/evento;
- métricas por ação sensível, canal e aprovador.

## Expiração
Por padrão, approvals pendentes expiram em **24 horas** após a criação ou última revalidação.

Quando expira:
- a aprovação continua como `status = pending` no registro base;
- o payload operacional passa a refletir `approval_status = expired`;
- tentativas de aprovar/rejeitar retornam conflito (`409`) até revalidação.
