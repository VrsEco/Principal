[CmdletBinding()]
param(
    [string]$InstallRoot = (Join-Path $HOME ".app32-mcp"),
    [string]$ServerPrefix = "sapiens-prod",
    [string]$SshKeyPath,
    [string]$McpUserId,
    [string]$McpCompanyId,
    [string]$FallbackRole = "colaborador",
    [string]$ProdHost = "69.164.205.75",
    [string]$ProdUser = "app",
    [int]$ProdPort = 22122,
    [string]$RemoteAppDir = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32",
    [string]$RemotePython = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python",
    [switch]$PersistUserEnv
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$Name) {
    $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Comando obrigatório não encontrado: $Name"
    }
    return $command.Source
}

function Set-UserEnvironmentVariable([string]$Name, [string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }
    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
}

function Remove-McpServerIfExists([string]$ServerName) {
    try {
        & $script:ClaudeExe mcp remove $ServerName | Out-Null
    }
    catch {
        Write-Verbose "Servidor MCP '$ServerName' não existia no Claude Code."
    }
}

function Add-McpServer(
    [string]$ServerName,
    [string]$Surface,
    [string]$LauncherPath
) {
    Remove-McpServerIfExists -ServerName $ServerName

    $args = @(
        "mcp", "add",
        "--scope", "user",
        "--transport", "stdio",
        "--env", "APP32_MCP_PROD_HOST=$ProdHost",
        "--env", "APP32_MCP_PROD_USER=$ProdUser",
        "--env", "APP32_MCP_PROD_PORT=$ProdPort",
        "--env", "APP32_MCP_PROD_APP_DIR=$RemoteAppDir",
        "--env", "APP32_MCP_PROD_PYTHON=$RemotePython"
    )

    if (-not [string]::IsNullOrWhiteSpace($SshKeyPath)) {
        $args += @("--env", "APP32_MCP_SSH_KEY_PATH=$SshKeyPath")
    }

    $args += @(
        $ServerName,
        "--",
        $script:PwshExe,
        "-NoLogo",
        "-NoProfile",
        "-File",
        $LauncherPath,
        "-Surface",
        $Surface
    )

    & $script:ClaudeExe @args
}

Write-Host "== Sapiens MCP / Claude Code installer ==" -ForegroundColor Cyan

$script:ClaudeExe = Require-Command "claude"
$script:PwshExe = Require-Command "pwsh"
$null = Require-Command "ssh"

if (-not (Test-Path -LiteralPath $InstallRoot)) {
    New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
}

$launcherPath = Join-Path $InstallRoot "start_mcp_prod_ssh.ps1"
$launcherContent = @'
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("user", "admin", "analytics")]
    [string]$Surface
)

$ErrorActionPreference = "Stop"

function Require-Env([string]$Name) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Variável obrigatória ausente: $Name"
    }
    return $value
}

$userId = Require-Env "APP32_MCP_USER_ID"
$companyId = [Environment]::GetEnvironmentVariable("APP32_MCP_COMPANY_ID")

$fallbackRole = [Environment]::GetEnvironmentVariable("APP32_MCP_FALLBACK_ROLE")
if ([string]::IsNullOrWhiteSpace($fallbackRole)) {
    $fallbackRole = "colaborador"
}

$sshKeyPath = Require-Env "APP32_MCP_SSH_KEY_PATH"

$hostName = [Environment]::GetEnvironmentVariable("APP32_MCP_PROD_HOST")
if ([string]::IsNullOrWhiteSpace($hostName)) {
    $hostName = "69.164.205.75"
}

$hostUser = [Environment]::GetEnvironmentVariable("APP32_MCP_PROD_USER")
if ([string]::IsNullOrWhiteSpace($hostUser)) {
    $hostUser = "app"
}

$port = [Environment]::GetEnvironmentVariable("APP32_MCP_PROD_PORT")
if ([string]::IsNullOrWhiteSpace($port)) {
    $port = "22122"
}

$remoteAppDir = [Environment]::GetEnvironmentVariable("APP32_MCP_PROD_APP_DIR")
if ([string]::IsNullOrWhiteSpace($remoteAppDir)) {
    $remoteAppDir = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32"
}

$remotePython = [Environment]::GetEnvironmentVariable("APP32_MCP_PROD_PYTHON")
if ([string]::IsNullOrWhiteSpace($remotePython)) {
    $remotePython = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python"
}

$pythonSnippet = @"
import os, sys, runpy
from dotenv import load_dotenv
load_dotenv('.env')
sys.path.insert(0, '.')
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
runpy.run_path('src/core/mcp_server.py', run_name='__main__')
"@.Trim()

$escapedSnippet = $pythonSnippet.Replace('"', '\"').Replace("`r", "").Replace("`n", "; ")
$remoteCommand = @(
    "cd $remoteAppDir",
    "APP32_MCP_SURFACE='$Surface'",
    "APP32_MCP_USER_ID='$userId'",
    "APP32_MCP_FALLBACK_ROLE='$fallbackRole'",
    "APP32_MCP_CLIENT='claude_code'",
    "APP32_MCP_CHANNEL='claude_code'",
    "PYTHONIOENCODING='utf-8'",
    "$remotePython -c ""$escapedSnippet"""
) -join " && "

if (-not [string]::IsNullOrWhiteSpace($companyId)) {
    $remoteCommand = $remoteCommand.Replace(
        "APP32_MCP_FALLBACK_ROLE='$fallbackRole'",
        "APP32_MCP_COMPANY_ID='$companyId' && APP32_MCP_FALLBACK_ROLE='$fallbackRole'"
    )
}

$sshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
if (-not (Test-Path $sshExe)) {
    $sshExe = "ssh"
}

& $sshExe `
    -T `
    -o BatchMode=yes `
    -o StrictHostKeyChecking=accept-new `
    -i $sshKeyPath `
    -p $port `
    "$hostUser@$hostName" `
    $remoteCommand

exit $LASTEXITCODE
'@

Set-Content -LiteralPath $launcherPath -Value $launcherContent -Encoding UTF8

$readmePath = Join-Path $InstallRoot "README_APP32_MCP.txt"
$readme = @"
Sapiens MCP para Claude Code
==========================

Launcher instalado em:
$launcherPath

Servidores registrados:
- $ServerPrefix-user
- $ServerPrefix-admin
- $ServerPrefix-analytics

Se você não usou -PersistUserEnv, defina estas variáveis antes de abrir o Claude Code:
  `$env:APP32_MCP_USER_ID=""SEU_USER_ID""
  `$env:APP32_MCP_FALLBACK_ROLE=""$FallbackRole""

`APP32_MCP_COMPANY_ID` é opcional e só deve ser usada quando você quiser pinar uma única empresa
de forma consciente. O padrão recomendado é deixar a empresa ser resolvida por request/payload.

Depois rode:
  claude

No Claude Code:
  /mcp
"@
Set-Content -LiteralPath $readmePath -Value $readme -Encoding UTF8

if (-not [string]::IsNullOrWhiteSpace($SshKeyPath) -and -not (Test-Path -LiteralPath $SshKeyPath)) {
    throw "A chave SSH informada não existe: $SshKeyPath"
}

if ($PersistUserEnv) {
    if ([string]::IsNullOrWhiteSpace($McpUserId)) {
        throw "Para usar -PersistUserEnv, informe pelo menos -McpUserId."
    }
    Set-UserEnvironmentVariable -Name "APP32_MCP_USER_ID" -Value $McpUserId
    if ([string]::IsNullOrWhiteSpace($McpCompanyId)) {
        [Environment]::SetEnvironmentVariable("APP32_MCP_COMPANY_ID", $null, "User")
    }
    else {
        Set-UserEnvironmentVariable -Name "APP32_MCP_COMPANY_ID" -Value $McpCompanyId
    }
    Set-UserEnvironmentVariable -Name "APP32_MCP_FALLBACK_ROLE" -Value $FallbackRole
    if (-not [string]::IsNullOrWhiteSpace($SshKeyPath)) {
        Set-UserEnvironmentVariable -Name "APP32_MCP_SSH_KEY_PATH" -Value $SshKeyPath
    }
}

$servers = @(
    @{ Name = "$ServerPrefix-user"; Surface = "user" },
    @{ Name = "$ServerPrefix-admin"; Surface = "admin" },
    @{ Name = "$ServerPrefix-analytics"; Surface = "analytics" }
)

foreach ($server in $servers) {
    Add-McpServer -ServerName $server.Name -Surface $server.Surface -LauncherPath $launcherPath
}

Write-Host ""
Write-Host "Instalação concluída." -ForegroundColor Green
Write-Host "Launcher persistente:" -ForegroundColor Cyan
Write-Host "  $launcherPath"
Write-Host ""
Write-Host "Servidores MCP registrados no Claude Code:" -ForegroundColor Cyan
foreach ($server in $servers) {
    Write-Host "  - $($server.Name)"
}
Write-Host ""

if ($PersistUserEnv) {
    Write-Host "As variáveis APP32_MCP_USER_ID / APP32_MCP_COMPANY_ID foram persistidas no escopo do usuário." -ForegroundColor Yellow
}
else {
    Write-Host "Antes de abrir o Claude Code, defina na sessão atual:" -ForegroundColor Yellow
    Write-Host "  `$env:APP32_MCP_USER_ID=""SEU_USER_ID"""
    Write-Host "  `$env:APP32_MCP_FALLBACK_ROLE=""$FallbackRole"""
    Write-Host "  # Opcional: `$env:APP32_MCP_COMPANY_ID=""SUA_COMPANY_ID""" -ForegroundColor DarkYellow
    if ([string]::IsNullOrWhiteSpace($SshKeyPath)) {
        Write-Host "  `$env:APP32_MCP_SSH_KEY_PATH=""C:\caminho\para\sua_chave"""
    }
}

Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Cyan
Write-Host "  1. Abra o Claude Code com 'claude'"
Write-Host "  2. Rode '/mcp'"
Write-Host "  3. Teste: $ServerPrefix-user / $ServerPrefix-admin / $ServerPrefix-analytics"
