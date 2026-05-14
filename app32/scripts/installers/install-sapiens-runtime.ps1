param(
    [string]$Email,
    [string]$Token,
    [int]$CompanyId = 0,
    [ValidateSet("claude", "codex", "antigravity", "other")]
    [string]$ClientRuntime = "other",
    [string]$Profile = "squad_cliente",
    [string]$Surface = "user",
    [string]$ExperienceLabel = "Sapiens Cliente",
    [string]$CanonicalLabel = "Squad Cliente",
    [string]$HarnessKey = "harness_coordenador_cliente_v1",
    [string]$HarnessLabel = "Harness Coordenador do Squad Cliente",
    [string]$ServerName = "sapiens-cliente",
    [string]$CommandAlias = "sapiens cliente on",
    [string]$AppBaseUrl = "https://app.gestaoversus.com.br",
    [string]$WorkspaceRoot = (Get-Location).Path,
    [string]$ConfigPath,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
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

function Resolve-WorkspaceMcpConfigPath([string]$StartPath) {
    $current = [IO.Path]::GetFullPath($StartPath)
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        $candidate = Join-Path $current ".mcp.json"
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
        $parent = Split-Path -Path $current -Parent
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $current) {
            break
        }
        $current = $parent
    }
    return (Join-Path ([IO.Path]::GetFullPath($StartPath)) ".mcp.json")
}

function Resolve-TargetConfigPath([string]$ExplicitPath, [string]$StartPath) {
    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
        return [IO.Path]::GetFullPath($ExplicitPath)
    }
    return Resolve-WorkspaceMcpConfigPath -StartPath $StartPath
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

Write-Step "Instalação guiada do $ExperienceLabel"
Write-Host "Cliente alvo........: $ClientRuntime"

if ([string]::IsNullOrWhiteSpace($Email)) {
    $Email = $env:GV_USER_EMAIL
}
if ([string]::IsNullOrWhiteSpace($Email)) {
    $Email = Read-Host "Informe o e-mail do usuário APP32"
}
if ([string]::IsNullOrWhiteSpace($Email)) {
    throw "E-mail obrigatório."
}

$configPath = Resolve-TargetConfigPath -ExplicitPath $ConfigPath -StartPath $WorkspaceRoot
$serverUrl = "{0}/mcp/{1}/" -f $AppBaseUrl.TrimEnd('/'), $Surface
if ($CompanyId -gt 0) {
    $serverUrl = "${serverUrl}?company_id=$CompanyId"
}

Write-Step "Localizando arquivo de configuração MCP do cliente"
Write-Host "Arquivo alvo........: $configPath"
Write-Host "Profile.............: $Profile"
Write-Host "Surface.............: $Surface"
Write-Host "Harness inicial.....: $HarnessLabel"
Write-Host "URL.................: $serverUrl"
Write-Host ""
Write-Host "No próximo passo você precisará colar o token MCP gerado no APP32." -ForegroundColor Yellow
Write-Host "Abra o APP32 > Meu perfil > Instalar Squad, gere ou renove o token e volte para este terminal." -ForegroundColor Yellow

if ([string]::IsNullOrWhiteSpace($Token)) {
    $Token = $env:GV_MCP_TOKEN
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    $secureToken = Read-Host "Cole agora o token MCP gerado no APP32" -AsSecureString
    $Token = Get-PlainTextFromSecureString $secureToken
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "Token MCP obrigatório."
}

Write-Step "Preparando .mcp.json local"
$backupPath = Backup-IfExists -Path $configPath

$serverConfig = @{
    transport = "http"
    url = $serverUrl
    metadata = @{
        profile = $Profile
        profile_label = $CanonicalLabel
        experience_label = $ExperienceLabel
        surface = $Surface
        company_id = $(if ($CompanyId -gt 0) { $CompanyId } else { $null })
        harness_key = $HarnessKey
        harness_label = $HarnessLabel
        email = $Email
    }
    headers = @{
        Authorization = "Bearer $Token"
    }
}

Merge-McpConfig -ConfigPath $configPath -Name $ServerName -ServerConfig $serverConfig
$Token = $null

$smokeResult = $null
if (-not $SkipSmoke) {
    Write-Step "Executando smoke básico do endpoint MCP"
    $smokeResult = Invoke-BasicSmoke -BaseUrl $AppBaseUrl
}

Write-Step "Instalação concluída"
Write-Host "Nome visível.........: $ExperienceLabel"
Write-Host "Família canônica.....: $CanonicalLabel"
Write-Host "Profile..............: $Profile"
Write-Host "Surface..............: $Surface"
Write-Host "Company ID...........: $(if ($CompanyId -gt 0) { $CompanyId } else { 'não definido' })"
Write-Host "Harness inicial......: $HarnessLabel"
Write-Host "Alias sugerido.......: $CommandAlias"
Write-Host "MCP config...........: $configPath"
if ($backupPath) {
    Write-Host "Backup do .mcp.json..: $backupPath"
}
if ($smokeResult) {
    Write-Host "Smoke................: OK"
    Write-Host "Public base URL......: $($smokeResult.public_base_url)"
}

Write-Host ""
Write-Host "Próximo passo:" -ForegroundColor Yellow
Write-Host "1. Abra o cliente/CLI no contexto correto."
Write-Host "2. Use a entrada visível: $ExperienceLabel"
Write-Host "3. Se o cliente suportar alias textual, teste: $CommandAlias"
Write-Host "4. Confirme a sequência de startup e o agente coordenador inicial."
