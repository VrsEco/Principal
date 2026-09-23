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
$fallbackRole = [Environment]::GetEnvironmentVariable("APP32_MCP_FALLBACK_ROLE")
if ([string]::IsNullOrWhiteSpace($fallbackRole)) {
    $fallbackRole = "colaborador"
}

$companyId = [Environment]::GetEnvironmentVariable("APP32_MCP_COMPANY_ID")

$sshKeyPath = [Environment]::GetEnvironmentVariable("APP32_MCP_SSH_KEY_PATH")
if ([string]::IsNullOrWhiteSpace($sshKeyPath)) {
    $sshKeyPath = "C:\GestaoVersus\app32\deploy_key_SECRETA.txt"
}

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
function Quote-Posix([string]$Value) {
    return "'" + $Value.Replace("'", "'`"'`"'") + "'"
}

# Encadear ``VAR=valor &&`` só cria variáveis de shell; não as exporta ao
# Python remoto. Isso fazia todas as surfaces caírem no default ``user``.
# ``env`` transmite explicitamente o contexto por processo e unbuffered evita
# atrasar o primeiro pacote JSON-RPC no túnel SSH.
$remoteEnv = @(
    "APP32_MCP_SURFACE=$(Quote-Posix $Surface)",
    "APP32_MCP_USER_ID=$(Quote-Posix $userId)",
    "APP32_MCP_FALLBACK_ROLE=$(Quote-Posix $fallbackRole)",
    "APP32_MCP_CLIENT='claude_code'",
    "APP32_MCP_CHANNEL='claude_code'",
    "PYTHONIOENCODING='utf-8'",
    "PYTHONUNBUFFERED='1'"
)
if (-not [string]::IsNullOrWhiteSpace($companyId)) {
    $remoteEnv += "APP32_MCP_COMPANY_ID=$(Quote-Posix $companyId)"
}

$remoteCommand = "cd $(Quote-Posix $remoteAppDir) && env $($remoteEnv -join ' ') $(Quote-Posix $remotePython) -c `"$escapedSnippet`""

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
