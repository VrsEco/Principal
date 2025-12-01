$ErrorActionPreference = "Stop"

param(
    [int]$Port = 5003,
    [switch]$SkipDockerStop
)

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $SkipDockerStop) {
    try {
        Write-Host "Parando container 'app' (docker compose stop app)..." -ForegroundColor Cyan
        docker compose stop app | Out-Null
    } catch {
        Write-Warning "Não foi possível parar o container via Docker (talvez não esteja em execução)."
    }
}

$venvActivate = Join-Path $repoRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvActivate)) {
    throw "Virtualenv não encontrado em .\.venv. Crie com 'python -m venv .venv' e instale as dependências."
}

& $venvActivate

$env:FLASK_ENV = "development"
$env:FLASK_APP = "app_pev.py"
$env:FLASK_RUN_PORT = $Port
$env:PYTHONUNBUFFERED = "1"

Write-Host "Iniciando servidor local em http://127.0.0.1:$Port (CTRL+C para sair)..." -ForegroundColor Green
python app_pev.py







