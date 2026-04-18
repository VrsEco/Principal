param(
    [Nullable[int]]$Port,
    [switch]$SkipDockerStop
)

$ErrorActionPreference = "Stop"

if (-not $Port) {
    $Port = 5032
}

function Import-DotEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }

        $separatorIndex = $line.IndexOf("=")
        if ($separatorIndex -lt 1) {
            return
        }

        $name = $line.Substring(0, $separatorIndex).Trim()
        $value = $line.Substring($separatorIndex + 1).Trim()

        if (
            ($value.StartsWith('"') -and $value.EndsWith('"')) -or
            ($value.StartsWith("'") -and $value.EndsWith("'"))
        ) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

$appRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $appRoot
$appEntryPoint = Join-Path $appRoot "app.py"
$venvPython = Join-Path $workspaceRoot ".venv\Scripts\python.exe"
$outerEnvFile = Join-Path $workspaceRoot ".env"
$innerEnvFile = Join-Path $appRoot ".env"

if (-not (Test-Path -LiteralPath $appEntryPoint)) {
    throw "Entrypoint Flask não encontrado: $appEntryPoint"
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Python da virtualenv não encontrado em $venvPython. Crie a .venv na raiz do workspace."
}

Set-Location $appRoot

Import-DotEnvFile -Path $outerEnvFile

if ((Test-Path -LiteralPath $outerEnvFile) -and -not (Test-Path -LiteralPath $innerEnvFile)) {
    Write-Host "Usando variáveis de ambiente da raiz do workspace: $outerEnvFile" -ForegroundColor DarkCyan
}

if (-not $SkipDockerStop) {
    try {
        Write-Host "Parando container 'app' (docker compose stop app)..." -ForegroundColor Cyan
        docker compose stop app | Out-Null
    } catch {
        Write-Warning "Não foi possível parar o container via Docker (talvez não esteja em execução)."
    }
}

if (-not $env:FLASK_ENV) { $env:FLASK_ENV = "development" }
if (-not $env:FLASK_CONFIG) { $env:FLASK_CONFIG = "development" }
$env:FLASK_APP = "app.py"
$env:FLASK_RUN_PORT = "$Port"
$env:PORT = "$Port"
$env:PYTHONUNBUFFERED = "1"

Write-Host "Iniciando servidor local em http://127.0.0.1:$Port (CTRL+C para sair)..." -ForegroundColor Green
& $venvPython $appEntryPoint



















