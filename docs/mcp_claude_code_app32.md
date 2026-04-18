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

O arquivo `C:\GestaoVersus\app32\.mcp.json` agora define 6 servidores:

- `app32-user`
- `app32-admin`
- `app32-analytics`
- `app32-prod-user`
- `app32-prod-admin`
- `app32-prod-analytics`

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

## Como usar direto na produção via SSH

Além do modo local, os servidores `app32-prod-*` sobem o MCP diretamente no host produtivo via SSH e transportam o stdio para o Claude Code.

### Pré-requisitos locais

- OpenSSH cliente disponível no Windows
- PowerShell 7 em:
  - `C:\Program Files\PowerShell\7\pwsh.exe`
- chave privada de deploy disponível localmente

### Variáveis adicionais recomendadas

- `APP32_MCP_SSH_KEY_PATH`
- `APP32_MCP_PROD_HOST`
- `APP32_MCP_PROD_USER`
- `APP32_MCP_PROD_PORT`

Exemplo:

```powershell
$env:APP32_MCP_USER_ID="SEU_USER_ID"
$env:APP32_MCP_COMPANY_ID="SUA_COMPANY_ID"
$env:APP32_MCP_SSH_KEY_PATH="C:\GestaoVersus\app32\deploy_key_SECRETA.txt"
claude
```

No Claude Code, prefira:

- `app32-prod-user` para operação do dia a dia em produção
- `app32-prod-admin` para operações administrativas seguras
- `app32-prod-analytics` para leitura ampliada e relatórios

## Instalação em escopo de usuário, sem pasta do projeto

Para testar como usuário normal, sem depender de `C:\GestaoVersus\app32` na máquina, use o instalador:

- `C:\GestaoVersus\app32\app32\scripts\install_claude_mcp_app32_prod.ps1`

Ele faz 3 coisas:

1. cria um launcher persistente em `~\.app32-mcp\start_mcp_prod_ssh.ps1`
2. registra os servidores no Claude Code em `--scope user`
3. opcionalmente persiste `APP32_MCP_USER_ID`, `APP32_MCP_COMPANY_ID` e `APP32_MCP_SSH_KEY_PATH` no perfil do usuário Windows

### Exemplo recomendado

```powershell
pwsh -File C:\GestaoVersus\app32\app32\scripts\install_claude_mcp_app32_prod.ps1 `
  -SshKeyPath 'C:\Chaves\app32_prod' `
  -McpUserId 'SEU_USER_ID' `
  -McpCompanyId 'SUA_COMPANY_ID' `
  -PersistUserEnv
```

Depois disso, basta abrir:

```powershell
claude
```

E no Claude Code:

```text
/mcp
```

Os servidores globais disponíveis ficam:

- `app32-prod-user`
- `app32-prod-admin`
- `app32-prod-analytics`

### Se não quiser persistir identidade

Você também pode instalar sem `-PersistUserEnv`. Nesse caso, antes de cada sessão do Claude Code, defina:

```powershell
$env:APP32_MCP_USER_ID="SEU_USER_ID"
$env:APP32_MCP_COMPANY_ID="SUA_COMPANY_ID"
$env:APP32_MCP_FALLBACK_ROLE="colaborador"
$env:APP32_MCP_SSH_KEY_PATH="C:\Chaves\app32_prod"
claude
```

## Script local usado para o túnel stdio SSH

- `C:\GestaoVersus\app32\app32\scripts\start_mcp_prod_ssh.ps1`

Esse script:

- valida `APP32_MCP_USER_ID` e `APP32_MCP_COMPANY_ID`
- conecta no host produtivo com a chave configurada
- carrega `.env` da aplicação no servidor
- sobe `src/core/mcp_server.py` em modo stdio no ambiente produtivo
- seleciona a `surface` remota conforme o servidor MCP escolhido

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

## Referência oficial do Claude Code

Confirmei a sintaxe de configuração na documentação oficial:

- [Claude Code MCP](https://code.claude.com/docs/en/mcp)

Pontos relevantes da doc:

- `.mcp.json` em escopo de projeto é suportado
- servidores `stdio` são suportados
- o comando local pode ser qualquer executável, com `args`
- `/mcp` é o comando recomendado para checar status dos servidores
