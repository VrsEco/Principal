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
$companyId = Require-Env "APP32_MCP_COMPANY_ID"
$fallbackRole = [Environment]::GetEnvironmentVariable("APP32_MCP_FALLBACK_ROLE")
if ([string]::IsNullOrWhiteSpace($fallbackRole)) {
    $fallbackRole = "colaborador"
}

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
$remoteCommand = @(
    "cd $remoteAppDir",
    "APP32_MCP_SURFACE='$Surface'",
    "APP32_MCP_USER_ID='$userId'",
    "APP32_MCP_COMPANY_ID='$companyId'",
    "APP32_MCP_FALLBACK_ROLE='$fallbackRole'",
    "APP32_MCP_CLIENT='claude_code'",
    "APP32_MCP_CHANNEL='claude_code'",
    "PYTHONIOENCODING='utf-8'",
    "$remotePython -c ""$escapedSnippet"""
) -join " && "

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
