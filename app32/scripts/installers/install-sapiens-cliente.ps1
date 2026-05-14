param(
    [string]$Email,
    [string]$Token,
    [int]$CompanyId = 0,
    [ValidateSet("claude", "codex", "antigravity", "other")]
    [string]$ClientRuntime = "claude",
    [string]$WorkspaceRoot = (Get-Location).Path,
    [string]$ConfigPath,
    [string]$AppBaseUrl = "https://app.gestaoversus.com.br",
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"

$genericInstaller = Join-Path $PSScriptRoot "install-sapiens-runtime.ps1"
if (-not (Test-Path -LiteralPath $genericInstaller)) {
    throw "Instalador base não encontrado em: $genericInstaller"
}

& $genericInstaller `
    -Email $Email `
    -Token $Token `
    -CompanyId $CompanyId `
    -ClientRuntime $ClientRuntime `
    -Profile "squad_cliente" `
    -Surface "user" `
    -ExperienceLabel "Sapiens Cliente" `
    -CanonicalLabel "Squad Cliente" `
    -HarnessKey "harness_coordenador_cliente_v1" `
    -HarnessLabel "Harness Coordenador do Squad Cliente" `
    -ServerName "sapiens-cliente" `
    -CommandAlias "sapiens cliente on" `
    -AppBaseUrl $AppBaseUrl `
    -WorkspaceRoot $WorkspaceRoot `
    -ConfigPath $ConfigPath `
    -SkipSmoke:$SkipSmoke
