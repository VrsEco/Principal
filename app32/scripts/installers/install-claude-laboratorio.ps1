param(
    [string]$Email,
    [string]$Token,
    [int]$CompanyId = 10,
    [string]$Profile = "squad_cliente",
    [string]$Surface = "user",
    [string]$ServerName = "app32-laboratorio-user",
    [string]$AppBaseUrl = "https://app.gestaoversus.com.br",
    [string]$WorkspaceRoot = (Get-Location).Path,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Get-PlainTextFromSecureString([Security.SecureString]$SecureValue) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
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

function Merge-McpConfig([string]$ConfigPath, [string]$Name, [hashtable]$ServerConfig) {
    $root = @{ mcpServers = @{} }
    if (Test-Path -LiteralPath $ConfigPath) {
        $raw = Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8
        if ($raw.Trim()) {
            $parsed = $raw | ConvertFrom-Json -Depth 20 -AsHashtable
            if ($parsed -is [hashtable]) {
                $root = $parsed
            }
        }
    }
    if (-not $root.ContainsKey("mcpServers") -or $null -eq $root.mcpServers) {
        $root.mcpServers = @{}
    }
    $root.mcpServers[$Name] = $ServerConfig
    $json = $root | ConvertTo-Json -Depth 20
    Set-Content -LiteralPath $ConfigPath -Value $json -Encoding UTF8
}

function Invoke-BasicSmoke([string]$BaseUrl) {
    $healthUrl = "$($BaseUrl.TrimEnd('/'))/mcp/healthz"
    $response = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 30
    return @{
        ok = ($response.ok -eq $true)
        public_base_url = $response.public_base_url
        surfaces = $response.surfaces
    }
}

Write-Step "Instalação do Claude para o laboratório Versus"

if ([string]::IsNullOrWhiteSpace($Email)) {
    $Email = $env:GV_USER_EMAIL
}
if ([string]::IsNullOrWhiteSpace($Email)) {
    $Email = Read-Host "Informe o e-mail do usuário APP32"
}
if ([string]::IsNullOrWhiteSpace($Email)) {
    throw "E-mail obrigatório."
}

if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = $env:GV_MCP_TOKEN
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    $secureToken = Read-Host "Cole o token MCP gerado no APP32" -AsSecureString
    $token = Get-PlainTextFromSecureString $secureToken
}
else {
    $token = $Token
}
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Token MCP obrigatório."
}

$configPath = Join-Path $WorkspaceRoot ".mcp.json"
$harnessPath = Join-Path $WorkspaceRoot "app32\.ai\claude-squad-cliente-laboratorio.md"
$serverUrl = "{0}/mcp/{1}?company_id={2}" -f $AppBaseUrl.TrimEnd('/'), $Surface, $CompanyId

Write-Step "Preparando .mcp.json local"
$backupPath = Backup-IfExists -Path $configPath

$serverConfig = @{
    transport = "http"
    url = $serverUrl
    metadata = @{
        profile = $Profile
        profile_label = "Squad Cliente"
        surface = $Surface
        company_id = $CompanyId
        project = "AA.J.16"
        email = $Email
    }
    headers = @{
        Authorization = "Bearer $token"
    }
}

Merge-McpConfig -ConfigPath $configPath -Name $ServerName -ServerConfig $serverConfig

if (-not (Test-Path -LiteralPath $harnessPath)) {
    throw "Harness do Claude não encontrado em: $harnessPath"
}

$smokeResult = $null
if (-not $SkipSmoke) {
    Write-Step "Executando smoke básico do endpoint MCP"
    $smokeResult = Invoke-BasicSmoke -BaseUrl $AppBaseUrl
}

Write-Step "Instalação concluída"
Write-Host "E-mail..............: $Email"
Write-Host "Company ID..........: $CompanyId"
Write-Host "Profile.............: $Profile"
Write-Host "Surface.............: $Surface"
Write-Host "Server name.........: $ServerName"
Write-Host "MCP config..........: $configPath"
Write-Host "Harness.............: $harnessPath"
if ($backupPath) {
    Write-Host "Backup do .mcp.json.: $backupPath"
}
if ($smokeResult) {
    Write-Host "Smoke...............: OK"
    Write-Host "Public base URL.....: $($smokeResult.public_base_url)"
}

Write-Host ""
Write-Host "Próximo passo:" -ForegroundColor Yellow
Write-Host "1. Abra o Claude no contexto correto."
Write-Host "2. Use o harness: $harnessPath"
Write-Host "3. Valide a sequência de startup do Squad Cliente."
