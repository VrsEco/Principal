<#
    Executa a sincronização de BACKUP DE PRODUÇÃO a partir do servidor Configr.

    Importante:
    - Este script NÃO executa pg_dump no ambiente local/dev.
    - Ele chama scripts/download_backups.py, que usa SSH/SCP para baixar os
      artefatos de produção de /home/app/backups.
    - Credenciais devem vir de variáveis de ambiente ou secret store do Windows,
      nunca hardcoded no repositório.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..\..')).Path
$downloadScript = Join-Path $projectRoot 'app32\scripts\download_backups.py'
$logDir = Join-Path $projectRoot 'logs'
$logPath = Join-Path $logDir 'postgres_backup_task.log'
$localBackupDir = Join-Path $projectRoot 'backups'

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    Write-Output $line
}

if (-not (Test-Path -LiteralPath $downloadScript -PathType Leaf)) {
    throw "Script de sincronização de produção não encontrado em $downloadScript"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
New-Item -ItemType Directory -Force -Path $localBackupDir | Out-Null

# Caminho canônico local para consulta operacional do agente/Codex.
# Pode ser sobrescrito por GV_BACKUP_LOCAL_DIR quando o alvo for OneDrive/NAS.
if ([string]::IsNullOrWhiteSpace($env:GV_BACKUP_LOCAL_DIR)) {
    $env:GV_BACKUP_LOCAL_DIR = $localBackupDir
}

try {
    Write-Log "Iniciando sincronização de backup de PRODUÇÃO (Configr) para $env:GV_BACKUP_LOCAL_DIR"
    python $downloadScript
    if ($LASTEXITCODE -ne 0) {
        throw "download_backups.py falhou com código $LASTEXITCODE"
    }
    Write-Log "Backup de PRODUÇÃO sincronizado com sucesso em $env:GV_BACKUP_LOCAL_DIR"
}
catch {
    Write-Log "ERRO: $($_.Exception.Message)"
    throw
}
