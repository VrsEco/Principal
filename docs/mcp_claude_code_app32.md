# APP32 MCP seguro no Claude Code

## Objetivo do MVP

Este MVP operacionaliza a MCP do APP32 no Claude Code com:

- identidade associada ao usuário configurado no ambiente
- fallback de perfil para `colaborador` quando o role não puder ser resolvido
- CRUD seguro piloto sobre `ProjectTask`
- `soft delete` em `ProjectTask`
- limitação de mutações por janela de tempo
- leitura ampliada para análise e relatórios via surface `analytics`

## Variáveis de ambiente obrigatórias

Antes de abrir o Claude Code, configure:

- `APP32_MCP_USER_ID`
- `APP32_MCP_COMPANY_ID`

Opcionalmente:

- `APP32_MCP_FALLBACK_ROLE` (default: `colaborador`)
- `APP32_MCP_CREATE_LIMIT` (default: `20`)
- `APP32_MCP_UPDATE_LIMIT` (default: `50`)
- `APP32_MCP_DELETE_LIMIT` (default: `10`)
- `APP32_MCP_RESTORE_LIMIT` (default: `10`)
- `APP32_MCP_MUTATION_WINDOW_HOURS` (default: `24`)
- `APP32_MCP_MAX_UPDATE_FIELDS` (default: `6`)

## Configuração já preparada

O arquivo `C:\GestaoVersus\app32\.mcp.json` já define 3 servidores:

- `app32-user`
- `app32-admin`
- `app32-analytics`

## Como usar no Claude Code

Na raiz `C:\GestaoVersus\app32`, rode:

```powershell
$env:APP32_MCP_USER_ID="SEU_USER_ID"
$env:APP32_MCP_COMPANY_ID="SUA_COMPANY_ID"
claude
```

Depois, no Claude Code:

- use `/mcp` para verificar os servidores
- aprove os servidores de projeto
- interaja com:
  - `app32-user` para criar, listar e alterar atividades com privilégio do usuário
  - `app32-admin` para soft delete e restore com confirmação explícita
  - `app32-analytics` para leitura ampla e relatórios

## Tools novas deste MVP

### Surface `user`

- `list_project_tasks_secure`
- `create_project_task_secure`
- `update_project_task_secure`

### Surface `admin`

- `delete_project_task_secure`
- `restore_project_task_secure`
- `get_project_task_analytics_report`

### Surface `analytics`

- `get_project_task_analytics_report`

## Regras de segurança ativas

- multi-tenancy por `company_id`
- identidade resolvida por `APP32_MCP_USER_ID`
- política por surface/domínio/ação/risco
- `delete` exige `confirm=true`
- `restore` exige `confirm=true`
- mutações com quota auditável em `ai_mcp_audit_events`
- `ProjectTask` removida logicamente não aparece por padrão nas leituras operacionais

## Exemplo de chamadas

### Criar

```json
{
  "project_code": "AA.J.31",
  "task_name": "Validar operação MCP no Claude Code",
  "description": "Executar smoke do servidor stdio",
  "priority": "high"
}
```

### Atualizar

```json
{
  "task_id": 123,
  "changes": {
    "notes": "Teste validado no Claude Code",
    "stage": "executing"
  }
}
```

### Soft delete

```json
{
  "task_id": 123,
  "reason": "Teste encerrado",
  "confirm": true
}
```

### Relatório amplo

```json
{
  "project_id": 31,
  "include_deleted": true,
  "limit": 200
}
```

## Observação importante

Neste ciclo o `soft delete` foi operacionalizado de ponta a ponta para `ProjectTask`, que é a entidade piloto do MVP.  
O padrão está pronto para ser expandido para outros domínios.

