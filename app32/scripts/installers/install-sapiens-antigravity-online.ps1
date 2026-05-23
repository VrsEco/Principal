param(
    [int]$CompanyId = 0,
    [string]$BearerToken,
    [string]$ServerName = "sapiens-user",
    [string]$AppBaseUrl = "https://app.gestaoversus.com.br",
    [string]$ServerUrl,
    [string]$TokenEnvVar = "APP32_MCP_TOKEN_SAPIENS_USER",
    [string]$ConfigPath,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function ConvertTo-Hashtable {
    param([Parameter(ValueFromPipeline = $true)]$InputObject)

    process {
        if ($null -eq $InputObject) {
            return $null
        }

        if ($InputObject -is [System.Collections.IDictionary]) {
            $hash = @{}
            foreach ($key in $InputObject.Keys) {
                $hash[$key] = ConvertTo-Hashtable $InputObject[$key]
            }
            return $hash
        }

        if ($InputObject -is [System.Collections.IEnumerable] -and $InputObject -isnot [string]) {
            $items = @()
            foreach ($item in $InputObject) {
                $items += ConvertTo-Hashtable $item
            }
            return $items
        }

        if ($InputObject.PSObject -and $InputObject.PSObject.Properties.Count -gt 0) {
            $hash = @{}
            foreach ($property in $InputObject.PSObject.Properties) {
                $hash[$property.Name] = ConvertTo-Hashtable $property.Value
            }
            return $hash
        }

        return $InputObject
    }
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

function Ensure-ParentDirectory([string]$Path) {
    $parent = Split-Path -Path $Path -Parent
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
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

function Read-JsonRoot([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return @{ mcpServers = @{} }
    }

    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @{ mcpServers = @{} }
    }

    $parsed = $raw | ConvertFrom-Json -Depth 50
    $root = ConvertTo-Hashtable $parsed
    if ($null -eq $root -or $root -isnot [hashtable]) {
        return @{ mcpServers = @{} }
    }

    return $root
}

function Test-RequiredCommand([string]$Name) {
    $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Comando obrigatório não encontrado: $Name. Instale o Node.js antes de prosseguir."
    }
}

function Invoke-BasicSmoke([string]$Url) {
    $uri = [Uri]$Url
    $healthUrl = "$($uri.Scheme)://$($uri.Authority)/mcp/healthz"
    return Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 30
}

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    if ($CompanyId -le 0) {
        throw "Informe -CompanyId ou -ServerUrl."
    }

    $ServerUrl = "{0}/mcp/user/?company_id={1}" -f $AppBaseUrl.TrimEnd("/"), $CompanyId
}

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $HOME ".gemini\antigravity\mcp_config.json"
}

Write-Step "Instalação online do Sapiens Cliente no Antigravity"
Write-Host "Servidor MCP........: $ServerName"
Write-Host "URL.................: $ServerUrl"
Write-Host "Config Antigravity..: $ConfigPath"

Test-RequiredCommand "npx"

if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    $secureToken = Read-Host "Cole o token MCP pessoal do APP32" -AsSecureString
    $BearerToken = Get-PlainTextFromSecureString $secureToken
}

if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    throw "Bearer token obrigatório."
}

Write-Step "Preparando configuração local"
Ensure-ParentDirectory -Path $ConfigPath
$backupPath = Backup-IfExists -Path $ConfigPath
$root = Read-JsonRoot -Path $ConfigPath

if (-not $root.ContainsKey("mcpServers") -or $null -eq $root.mcpServers -or $root.mcpServers -isnot [hashtable]) {
    $root.mcpServers = @{}
}

[Environment]::SetEnvironmentVariable($TokenEnvVar, $BearerToken, "User")
Set-Item -Path ("Env:" + $TokenEnvVar) -Value $BearerToken

$headerValue = 'Authorization: Bearer ${' + $TokenEnvVar + '}'

$root.mcpServers[$ServerName] = @{
    command = "npx"
    args = @(
        "-y",
        "mcp-remote",
        $ServerUrl,
        "--header",
        $headerValue
    )
    env = @{
        $TokenEnvVar = $BearerToken
    }
    metadata = @{
        profile = "squad_cliente"
        profile_label = "Squad Cliente"
        experience_label = "Sapiens Cliente"
        surface = "user"
        harness_key = "harness_coordenador_cliente_v1"
        harness_label = "Harness Coordenador do Squad Cliente"
    }
}

($root | ConvertTo-Json -Depth 50) | Set-Content -LiteralPath $ConfigPath -Encoding UTF8

$smoke = $null
if (-not $SkipSmoke) {
    Write-Step "Validando endpoint público do MCP"
    $smoke = Invoke-BasicSmoke -Url $ServerUrl
}

Write-Step "Instalação concluída"
Write-Host "Experiência.........: Sapiens Cliente"
Write-Host "Família canônica....: Squad Cliente"
Write-Host "Profile.............: squad_cliente"
Write-Host "Surface.............: user"
Write-Host "Harness inicial.....: Harness Coordenador do Squad Cliente"
Write-Host "Servidor MCP........: $ServerName"
Write-Host "Config..............: $ConfigPath"
Write-Host "Token env var.......: $TokenEnvVar"
if ($backupPath) {
    Write-Host "Backup anterior.....: $backupPath"
}
if ($smoke -and $smoke.ok -eq $true) {
    Write-Host "Smoke...............: OK"
}

Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "1. Feche e reabra o Antigravity."
Write-Host "2. Confira se o servidor MCP '$ServerName' aparece como instalado/conectado."
Write-Host "3. Abra uma nova conversa e use o prompt oficial de ativação do Sapiens Cliente."
