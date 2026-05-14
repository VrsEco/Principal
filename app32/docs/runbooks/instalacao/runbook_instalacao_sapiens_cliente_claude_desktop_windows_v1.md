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
3. abra uma conversa e teste:

```text
Use o Sapiens Cliente e rode describe_app32_squad_runtime_tool.
```

---

## 11. Observações importantes

- a configuração do `claude_desktop_config.json` vale para o usuário Windows local
- o token é pessoal do APP32; cada pessoa deve usar o seu
- se aparecer erro com `C:\Program`, o caminho do `npx` usado está com espaço
- o pacote correto é `mcp-remote`, sem prefixo `@anthropic/`

