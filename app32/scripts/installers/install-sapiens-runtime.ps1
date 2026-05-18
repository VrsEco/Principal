param(
    [ValidateSet("claude", "codex", "antigravity", "other")]
    [string]$ClientRuntime = "other",
    [string]$ServerName = "sapiens-user",
    [string]$ServerUrl,
    [string]$BearerToken,
    [string]$Profile = "squad_cliente",
    [string]$Surface = "user",
    [string]$ExperienceLabel = "Sapiens Cliente",
    [string]$CanonicalLabel = "Squad Cliente",
    [string]$HarnessKey = "harness_coordenador_cliente_v1",
    [string]$HarnessLabel = "Harness Coordenador do Squad Cliente",
    [string]$CommandAlias = "/sapiens-cliente-on",
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command([string]$Name) {
    $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Comando obrigatório não encontrado: $Name"
    }
    return $command.Source
}

function Backup-IfExists([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = "$Path.bak_$timestamp"
    Copy-Item -LiteralPath $Path -Destination $backupPath -Force
    return $backupPath
}

function Ensure-ParentDirectory([string]$Path) {
    $parent = Split-Path -Path $Path -Parent
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function Set-UserEnv([string]$Name, [string]$Value) {
    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
    Set-Item -Path ("Env:" + $Name) -Value $Value
}

function Merge-JsonMcpServer([string]$ConfigPath, [string]$Name, [hashtable]$ServerConfig) {
    $root = @{ mcpServers = @{} }
    if (Test-Path -LiteralPath $ConfigPath) {
        $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
        if ($raw.Trim()) {
            $parsed = $raw | ConvertFrom-Json -Depth 30 -AsHashtable
            if ($parsed -is [hashtable]) {
                $root = $parsed
            }
        }
    }
    if (-not $root.ContainsKey("mcpServers") -or $null -eq $root.mcpServers) {
        $root.mcpServers = @{}
    }
    $root.mcpServers[$Name] = $ServerConfig
    Ensure-ParentDirectory -Path $ConfigPath
    ($root | ConvertTo-Json -Depth 30) | Set-Content -LiteralPath $ConfigPath -Encoding UTF8
}

function Merge-CodexToml([string]$ConfigPath, [string]$Name, [string]$Url, [string]$TokenEnvVar) {
    Ensure-ParentDirectory -Path $ConfigPath
    $raw = ""
    if (Test-Path -LiteralPath $ConfigPath) {
        $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
    }

    $escapedName = [Regex]::Escape($Name)
    $pattern = "(?ms)^\[mcp_servers\.$escapedName\]\s*.*?(?=^\[|\z)"
    $block = @(
        "[mcp_servers.$Name]"
        "url = ""$Url"""
        "bearer_token_env_var = ""$TokenEnvVar"""
        "startup_timeout_sec = 20"
        "tool_timeout_sec = 120"
    ) -join "`r`n"

    if ([string]::IsNullOrWhiteSpace($raw)) {
        Set-Content -LiteralPath $ConfigPath -Value ($block + "`r`n") -Encoding UTF8
        return
    }

    if ([Regex]::IsMatch($raw, $pattern)) {
        $updated = [Regex]::Replace($raw, $pattern, $block + "`r`n")
    }
    else {
        $separator = ""
        if (-not $raw.EndsWith("`n")) {
            $separator = "`r`n"
        }
        $updated = $raw + $separator + "`r`n" + $block + "`r`n"
    }
    Set-Content -LiteralPath $ConfigPath -Value $updated -Encoding UTF8
}

function Install-ClaudeRuntime {
    $null = Require-Command "claude"
    & claude mcp remove $ServerName *> $null
    & claude mcp add --scope user --transport http $ServerName $ServerUrl --header "Authorization: Bearer $BearerToken"
    return @{
        config_path = "~/.claude.json (ou equivalente gerenciado da instalação)"
        verify_command = "claude mcp list"
    }
}

function Install-CodexRuntime {
    $configPath = Join-Path $HOME ".codex\config.toml"
    $tokenEnvVar = ("APP32_MCP_TOKEN_{0}" -f ($ServerName.ToUpper().Replace("-", "_")))
    $backupPath = Backup-IfExists -Path $configPath
    Set-UserEnv -Name $tokenEnvVar -Value $BearerToken
    Merge-CodexToml -ConfigPath $configPath -Name $ServerName -Url $ServerUrl -TokenEnvVar $tokenEnvVar
    return @{
        config_path = $configPath
        backup_path = $backupPath
        verify_command = "codex mcp list"
        token_env_var = $tokenEnvVar
    }
}

function Install-AntigravityRuntime {
    $configPath = Join-Path $HOME ".gemini\antigravity\mcp_config.json"
    $tokenEnvVar = ("APP32_MCP_TOKEN_{0}" -f ($ServerName.ToUpper().Replace("-", "_")))
    $backupPath = Backup-IfExists -Path $configPath
    Set-UserEnv -Name $tokenEnvVar -Value $BearerToken
    Merge-JsonMcpServer -ConfigPath $configPath -Name $ServerName -ServerConfig @{
        command = "npx"
        args = @(
            "-y",
            "mcp-remote",
            $ServerUrl,
            "--header",
            ("Authorization: Bearer ${" + $tokenEnvVar + "}")
        )
        env = @{
            $tokenEnvVar = $BearerToken
        }
        metadata = @{
            profile = $Profile
            profile_label = $CanonicalLabel
            experience_label = $ExperienceLabel
            surface = $Surface
            harness_key = $HarnessKey
            harness_label = $HarnessLabel
        }
    }
    return @{
        config_path = $configPath
        backup_path = $backupPath
        verify_command = "Reabra o painel MCP do Antigravity e confira INSTALLED MCP SERVERS"
        token_env_var = $tokenEnvVar
    }
}

function Invoke-BasicSmoke([string]$Url) {
    $base = [Uri]$Url
    $healthUrl = "$($base.Scheme)://$($base.Authority)/mcp/healthz"
    return Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 30
}

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    throw "ServerUrl é obrigatório."
}
if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    throw "BearerToken é obrigatório."
}

Write-Step "Instalação automática do $ExperienceLabel"
Write-Host "Runtime alvo........: $ClientRuntime"
Write-Host "Servidor MCP.......: $ServerName"
Write-Host "URL................: $ServerUrl"

$result = $null
switch ($ClientRuntime) {
    "claude" { $result = Install-ClaudeRuntime; break }
    "codex" { $result = Install-CodexRuntime; break }
    "antigravity" { $result = Install-AntigravityRuntime; break }
    default { throw "Runtime '$ClientRuntime' ainda não possui instalador automático oficial." }
}

$smoke = $null
if (-not $SkipSmoke) {
    Write-Step "Validando endpoint MCP público"
    $smoke = Invoke-BasicSmoke -Url $ServerUrl
}

Write-Step "Instalação concluída"
Write-Host "Experiência.........: $ExperienceLabel"
Write-Host "Família canônica....: $CanonicalLabel"
Write-Host "Profile.............: $Profile"
Write-Host "Surface.............: $Surface"
Write-Host "Harness inicial.....: $HarnessLabel"
Write-Host "Comando Sapiens On..: $CommandAlias"
Write-Host "Config alvo.........: $($result.config_path)"
if ($result.backup_path) {
    Write-Host "Backup..............: $($result.backup_path)"
}
if ($result.token_env_var) {
    Write-Host "Token persistido....: $($result.token_env_var) (escopo do usuário)"
}
if ($smoke -and $smoke.ok -eq $true) {
    Write-Host "Smoke...............: OK"
}

Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "1. Verifique a conexão no cliente: $($result.verify_command)"
Write-Host "2. Abra uma nova sessão e execute: $CommandAlias"
Write-Host "3. Confirme o bootstrap remoto do Sapiens On"
