# Runbook de Instalação do Sapiens Cliente no Claude Desktop (Windows) v1

Status: oficial  
Escopo: instalar o `Sapiens Cliente` no `Claude Desktop (Windows)` usando `mcp-remote` e Bearer Token pessoal

## 1. Objetivo

Descrever o fluxo oficial validado em campo para conectar o `Sapiens Cliente` ao `Claude Desktop (Windows)` sem OAuth, usando:

- `mcp-remote`
- `npx.cmd`
- `claude_desktop_config.json`
- Bearer Token pessoal do APP32

---

## 2. Resultado esperado

Ao final deste runbook, o usuário deve ter:

- o `Claude Desktop` com uma conexão MCP chamada `Sapiens Cliente`
- a conexão apontando para `https://app.gestaoversus.com.br/mcp/user/`
- autenticação por Bearer Token pessoal
- entrada inicial pelo `Harness Coordenador do Squad Cliente`
- bootstrap remoto do bundle mínimo via `resolve_app32_instruction_bundle_tool`

---

## 3. Pré-requisitos

Antes da instalação, validar:

1. acesso ao `/profile` do APP32
2. token MCP pessoal ativo
3. Windows com `node` e `npm` instalados
4. `npx` disponível
5. `Claude Desktop` instalado no mesmo usuário Windows

---

## 4. Validar Node.js

No PowerShell:

```powershell
node --version
npm --version
```

Se falhar, instalar Node.js em:

- [https://nodejs.org](https://nodejs.org)

---

## 5. Localizar o `npx.cmd` correto

No PowerShell:

```powershell
where.exe npx
```

Preferir o caminho sem espaços, normalmente:

```text
C:\Users\{usuario}\AppData\Roaming\npm\npx.cmd
```

### Regra
Evitar `C:\Program Files\nodejs\npx.cmd` quando houver alternativa sem espaço no caminho.

---

## 6. Testar o proxy `mcp-remote`

Use o token gerado no APP32:

```powershell
npx -y mcp-remote https://app.gestaoversus.com.br/mcp/user/ --header "Authorization:Bearer TOKEN_DO_USUARIO"
```

### Resultado esperado

Algo equivalente a:

```text
Connected to remote server using StreamableHTTPClientTransport
Local STDIO server running
Proxy established successfully...
```

Depois do teste:

- pressione `Ctrl+C`

---

## 7. Localizar o arquivo do Claude Desktop

O arquivo fica em:

```text
C:\Users\{usuario}\AppData\Local\Packages\Claude_XXXXX\LocalCache\Roaming\Claude\claude_desktop_config.json
```

Para localizar a pasta `Claude_*`:

```powershell
Get-ChildItem "$env:LOCALAPPDATA\Packages" | Where-Object { $_.Name -like "Claude*" } | Select-Object Name
```

---

## 8. Gravar a conexão MCP

Exemplo oficial:

```powershell
$npxPath = "C:\Users\$env:USERNAME\AppData\Roaming\npm\npx.cmd"
$configPath = (Get-ChildItem "$env:LOCALAPPDATA\Packages" | Where-Object { $_.Name -like "Claude*" } | Select-Object -First 1 -ExpandProperty FullName) + "\LocalCache\Roaming\Claude\claude_desktop_config.json"
$token = "TOKEN_DO_USUARIO"

if (Test-Path $configPath) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Force -Path (Split-Path $configPath) | Out-Null
    $config = [PSCustomObject]@{}
}

if (-not $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
}

$server = [PSCustomObject]@{
    command = $npxPath
    args    = @(
        "-y",
        "mcp-remote",
        "https://app.gestaoversus.com.br/mcp/user/",
        "--header",
        "Authorization:Bearer $token"
    )
}

$config.mcpServers | Add-Member -MemberType NoteProperty -Name "Sapiens Cliente" -Value $server -Force

$json = $config | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($configPath, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "MCP Sapiens Cliente configurado com sucesso. Reinicie o Claude Desktop."
```

---

## 9. Reiniciar o Claude Desktop

Depois de gravar:

1. feche o Claude completamente
2. feche também pela bandeja do sistema, se ele permanecer aberto
3. abra o Claude novamente

---

## 10. Validação

Depois do restart:

1. abra `Configurações → Conectores`
2. confirme que `Sapiens Cliente` apareceu em `Desktop`
3. abra uma conversa e cole o prompt de ativação canônico:

```text
Use a conexão MCP Sapiens Cliente desta sessão.

Antes de responder, rode nesta ordem:
1. resolve_app32_instruction_bundle_tool
2. describe_app32_squad_runtime_tool
3. list_user_app32_capabilities
4. describe_app32_profile_contracts_tool
5. describe_app32_surface_playbooks_tool
6. describe_app32_domain_playbooks_tool

Se o bootstrap funcionar, confirme na primeira linha exatamente `Sapiens Cliente Ativado`.
Se o runtime suportar título de sessão, prefira `Sapiens Cliente On`.
Depois disso, responda dizendo qual squad, surface e harness de entrada estão ativos.
```

### Resultado esperado

O Claude deve:

1. usar a conexão MCP instalada
2. carregar o bundle mínimo remoto
3. executar o bootstrap oficial
4. responder com confirmação curta de ativação

---

## 11. Ativação canônica e comandos opcionais

### Caminho canônico

No Claude Code / aba Code do Claude Desktop, o caminho canônico de ativação é:

- usar a conexão MCP registrada
- colar o prompt de ativação canônico do APP32
- confirmar o bootstrap real da sessão

### Comandos opcionais

Além da conexão MCP, o Claude Desktop/Code pode receber comandos slash oficiais para ativação, em modo best effort:

- `/sapiens-cliente-on`
- `/sapiens-on`

Quando houver mais de um Squad instalado na mesma máquina, o comando genérico `/sapiens-on` deve pedir confirmação do usuário antes de ativar o Squad correto.

Pergunta esperada:

```text
Escolha entre: Cliente, Versus ou Engenharia.
```

### Instalação dos comandos slash

Script canônico versionado no APP32:

- `C:\GestaoVersus\app32\app32\scripts\installers\install-claude-sapiens-slash-commands.ps1`

Exemplo:

```powershell
powershell -ExecutionPolicy Bypass -File ".\app32\scripts\installers\install-claude-sapiens-slash-commands.ps1" -AvailableSquads squad_cliente,squad_versus
```

### Regra importante

Ativação oficial usa barra inicial.

Correto:

- `/sapiens-cliente-on`
- `/sapiens-on`

Não tratar texto livre como comando instalado:

- `sapiens on`
- `sapiens cliente on`

### Regra de fallback

Se a instalação específica do Claude não carregar os custom commands locais, a homologação continua válida desde que:

1. `claude mcp list` mostre `Sapiens Cliente` como `Connected`
2. o prompt canônico consiga carregar o bundle e o runtime
3. a sessão confirme `Sapiens Cliente Ativado`

---

## 12. Limpeza controlada antes da reinstalação

Se houver suspeita de instalação antiga, drift ou comandos slash desatualizados, fazer este reset antes de reinstalar:

1. fechar o Claude Desktop completamente
2. remover os comandos/skills antigos em:
   - `%USERPROFILE%\.claude\commands`
   - `%USERPROFILE%\.claude\skills`
3. revisar o `claude_desktop_config.json` e remover entradas antigas do `Sapiens Cliente`, se houver
4. reinstalar a conexão MCP
5. reinstalar os comandos slash oficiais
6. reabrir o Claude

### Critério

Se o objetivo for homologar o novo modelo como cliente real, a limpeza controlada é recomendada.

---

## 13. Observações importantes

- a configuração do `claude_desktop_config.json` vale para o usuário Windows local
- o token é pessoal do APP32; cada pessoa deve usar o seu
- se aparecer erro com `C:\Program`, o caminho do `npx` usado está com espaço
- o pacote correto é `mcp-remote`, sem prefixo `@anthropic/`
- alguns builds do Claude Code podem conectar MCP normalmente e ainda assim não catalogar arquivos locais em `~/.claude/commands` ou `.claude/commands`
- nesses casos, o APP32 deve tratar os slash commands como opcionais e manter o prompt de ativação como caminho operacional canônico

---

## 14. Homologação de campo validada em 2026-05-17

Resultado observado na instalação validada:

1. `claude mcp list` retornou `Sapiens Cliente ... ✓ Connected`
2. o bootstrap real carregou:
   - `Squad Cliente`
   - `surface user`
   - `SC-COORD`
   - `harness_coordenador_cliente_v1`
   - bundle `2026-05-17.2`
3. os custom commands locais do Claude não foram catalogados nessa instalação específica
4. o prompt de ativação canônico funcionou integralmente

### Decisão operacional

Para Claude Code / aba Code do Claude Desktop:

- MCP + prompt canônico = caminho oficial e robusto
- slash commands = conveniência opcional, sem dependência operacional
