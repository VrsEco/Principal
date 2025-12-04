$ErrorActionPreference = "Stop"

param(
    [switch]$NoCache,
    [switch]$SkipBuild
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $SkipBuild) {
    if ($NoCache) {
        Write-Host "Executando build completo do serviço 'app' (sem cache)..." -ForegroundColor Cyan
        docker compose build --no-cache app
    } else {
        Write-Host "Executando build incremental do serviço 'app'..." -ForegroundColor Cyan
        docker compose build app
    }
} else {
    Write-Host "Pulando etapa de build conforme solicitado." -ForegroundColor Yellow
}

Write-Host "Subindo container 'app' com docker compose..." -ForegroundColor Cyan
docker compose up -d app

Write-Host "Container em execução. Logs recentes:" -ForegroundColor Green
docker compose logs --tail 50 app


















