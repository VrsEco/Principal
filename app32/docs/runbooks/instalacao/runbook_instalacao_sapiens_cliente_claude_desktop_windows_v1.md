# Runbook de Instalação do Sapiens Cliente no Claude Desktop Windows v2

Status: oficial
Classe documental: Runbook
Escopo: instalar o `Sapiens Cliente` no `Claude Windows Desktop` para usuário final, sem exigir `claude` CLI.

## 1. Decisão oficial

O padrão para cliente final é:

- **Usuário Normal — Claude Windows Desktop**;
- instalador PowerShell oficial do APP32;
- proxy `stdio -> StreamableHTTP/SSE` versionado em `%APPDATA%\Claude\sapiens-proxy.js`;
- configuração em `claude_desktop_config.json` com `command`, `args` e `env`;
- autenticação por Bearer Token pessoal do APP32.

O uso direto de `mcp-remote` no `claude_desktop_config.json` fica como legado/fallback técnico, não como caminho oficial.

---

## 2. Quando usar este runbook

Use este runbook quando o usuário operar no aplicativo Claude instalado no Windows e não quiser/não souber usar terminal avançado do Claude.

Para usuário técnico que usa Claude Code, Claude CLI ou aba Code, usar o modo:

- **Usuário Avançado — Claude CLI via PowerShell**;
- uma linha PowerShell gerada pelo APP32;
- registro via `claude mcp add --scope user --transport http`.

---

## 3. Pré-requisitos

Confirmar:

1. conta ativa no APP32;
2. acesso à empresa correta;
3. token MCP pessoal ativo/recém-gerado;
4. Claude Desktop instalado no Windows;
5. Node.js LTS disponível com `node --version`.

Se Node.js estiver ausente, instalar em:

- https://nodejs.org

Depois da instalação, fechar e reabrir o PowerShell.

---

## 4. Comando oficial — Usuário Normal

Na tela `/profile`, escolher:

1. ferramenta: `Claude`;
2. squad: `Cliente`;
3. modo: `Usuário Normal`;
4. criar/renovar token;
5. copiar o comando gerado.

O comando baixa e executa:

```text
app32/scripts/installers/install-sapiens-claude-desktop-windows.ps1
```

Parâmetros principais:

- `-ServerName 'Sapiens Cliente'`
- `-ServerUrl 'https://app.gestaoversus.com.br/mcp/user/'`
- `-BearerToken '<token pessoal>'`
- `-Profile 'squad_cliente'`
- `-Surface 'user'`
- `-HarnessKey 'harness_coordenador_cliente_v1'`

---

## 5. O que o instalador faz

O instalador:

1. valida Node.js 18+;
2. resolve o `claude_desktop_config.json` em `%APPDATA%\Claude` ou no pacote Windows Store `LocalCache\Roaming\Claude`;
3. cria backup do config existente;
4. grava `sapiens-proxy.js` no diretório do Claude;
5. atualiza somente a entrada `mcpServers['Sapiens Cliente']`, preservando outras configurações;
6. injeta token por `env`, não hardcoded no proxy;
7. executa smoke `initialize` antes do restart.

Configuração esperada:

```json
{
  "mcpServers": {
    "Sapiens Cliente": {
      "command": "C:\Program Files\nodejs\node.exe",
      "args": ["C:\Users\usuario\AppData\Roaming\Claude\sapiens-proxy.js"],
      "env": {
        "SAPIENS_MCP_URL": "https://app.gestaoversus.com.br/mcp/user/",
        "SAPIENS_MCP_TOKEN": "mcpu_..."
      }
    }
  }
}
```

---

## 6. Regras do proxy

O proxy oficial deve:

- ler JSON-RPC newline-delimited do `stdin`;
- fazer `POST` para o MCP remoto com Bearer Token;
- aceitar `text/event-stream`;
- normalizar `

` para `
` antes de separar blocos SSE;
- retornar no `stdout` somente JSON-RPC;
- cancelar/destruir a leitura SSE após receber a resposta do `id` esperado;
- não encerrar antes de esvaziar fila e detectar `stdin` fechado.

Essas regras existem porque o Claude Desktop local usa MCP por `stdio` e o servidor APP32 responde por StreamableHTTP/SSE.

---

## 7. Validação pós-instalação

Depois do instalador:

1. fechar o Claude Desktop completamente, inclusive bandeja do sistema;
2. abrir novamente;
3. entrar em `Configurações > Conectores`;
4. confirmar `Sapiens Cliente` sem erro;
5. abrir conversa nova e usar o prompt/entrada oficial `Sapiens On`.

Startup esperado:

- `bootstrap_session_context`;
- `describe_app32_available_sapiens_squads_tool`;
- `resolve_app32_sapiens_activation_tool`;
- `resolve_app32_instruction_bundle_tool`;
- `describe_app32_squad_runtime_tool`;
- `list_user_app32_capabilities`.

Resultado esperado:

```text
Sapiens Cliente On
```

---

## 8. Erros comuns

### Node.js ausente

Sinal:

- instalador falha em `Node.js não encontrado`.

Ação:

- instalar Node.js LTS;
- reabrir PowerShell;
- executar o comando novamente.

### Configuração inválida ignorada pelo Claude

Sinal:

- Claude informa que a configuração MCP foi ignorada.

Causa provável:

- uso manual de `type: http` ou `url` sem `command` em `claude_desktop_config.json`.

Ação:

- reinstalar usando o modo `Usuário Normal` do APP32.

### Token inválido ou expirado

Sinal:

- smoke falha com HTTP 401/403.

Ação:

- voltar ao `/profile`;
- renovar token;
- executar novamente o comando de instalação.

---

## 9. Relação com Usuário Avançado

O modo avançado continua suportado e é o caminho correto para Claude CLI/Claude Code:

```powershell
claude mcp add --scope user --transport http sapiens-user "https://app.gestaoversus.com.br/mcp/user/" --header "Authorization: Bearer <token>"
```

Na UI, ele aparece como:

- **Usuário Avançado — Claude CLI via PowerShell**.

Não usar esse modo como padrão para usuário final do Claude Windows Desktop.

---

## 10. Critério de aceite

A instalação está aprovada quando:

1. o instalador conclui sem erro;
2. o smoke `initialize` retorna `serverInfo`;
3. o Claude Desktop reabre com `Sapiens Cliente` ativo;
4. `Sapiens On` executa o bootstrap real;
5. a sessão expõe `Squad Cliente`, `surface=user` e `harness_coordenador_cliente_v1`.
