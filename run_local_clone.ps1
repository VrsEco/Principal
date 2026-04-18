param(
    [Nullable[int]]$Port,
    [switch]$SkipDockerStop
)

$ErrorActionPreference = "Stop"

if (-not $Port) {
    $Port = 5032
}

$workspaceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$delegateScript = Join-Path $workspaceRoot "app32\scripts\use_local_app.ps1"

if (-not (Test-Path -LiteralPath $delegateScript)) {
    throw "Script delegado não encontrado: $delegateScript"
}

Write-Host "Executando launcher local compatível do clone..." -ForegroundColor Cyan
& $delegateScript -Port $Port -SkipDockerStop:$SkipDockerStop
