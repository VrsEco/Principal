<#
    Executa backup LOCAL/DEV do PostgreSQL usando credenciais do .env.

    Uso restrito: este script NÃO é o processo oficial de backup de produção.
    Para evitar falso backup de produção, exige -AllowDevelopmentBackup.
#>

param(
    [switch]$AllowDevelopmentBackup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = (Resolve-Path (Join-Path $scriptRoot '..\..\..')).Path
$envFile = Join-Path $projectRoot '.env'
$oneDriveBackupDir = 'C:\Users\mff20\OneDrive\Versus\Versus Participações\Versus ERP\Backup_app\database'
$localFallbackDir = Join-Path $projectRoot 'backups\database'
$backupDir = if (Test-Path -LiteralPath (Split-Path -Parent $oneDriveBackupDir)) { $oneDriveBackupDir } else { $localFallbackDir }
$logDir = Join-Path $projectRoot 'logs'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$sqlPath = Join-Path $backupDir "backup_postgresql_${timestamp}.sql"
$gzPath = "${sqlPath}.gz"
$logPath = Join-Path $logDir 'postgres_backup_task.log'

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    Write-Output $line
}

function Get-EnvMapFromFile {
    param([string]$Path)
    $map = @{}
    foreach ($rawLine in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) {
            continue
        }

        $idx = $line.IndexOf('=')
        $key = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        $map[$key] = $value
    }
    return $map
}

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Arquivo .env não encontrado em $envFile"
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$envMap = Get-EnvMapFromFile -Path $envFile

if (-not $AllowDevelopmentBackup) {
    throw 'run_local_pg_backup.ps1 é apenas para dev/local. Use run_pg_backup.ps1 para sincronizar backup de PRODUÇÃO ou informe -AllowDevelopmentBackup explicitamente.'
}

$dbHost = $envMap['POSTGRES_HOST']
$dbPort = $envMap['POSTGRES_PORT']
$dbName = $envMap['POSTGRES_DB']
$dbUser = $envMap['POSTGRES_USER']
$dbPassword = $envMap['POSTGRES_PASSWORD']

$missing = @()
foreach ($pair in @{
    POSTGRES_HOST = $dbHost
    POSTGRES_PORT = $dbPort
    POSTGRES_DB = $dbName
    POSTGRES_USER = $dbUser
    POSTGRES_PASSWORD = $dbPassword
}.GetEnumerator()) {
    if ([string]::IsNullOrWhiteSpace($pair.Value)) {
        $missing += $pair.Key
    }
}

if ($missing.Count -gt 0) {
    throw "Credenciais PostgreSQL ausentes no .env: $($missing -join ', ')"
}

$pgDumpCmd = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDumpCmd) {
    $candidatePaths = @(
        'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe',
        'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
        'C:\Program Files\PostgreSQL\15\bin\pg_dump.exe',
        'C:\Program Files\PostgreSQL\14\bin\pg_dump.exe'
    )
    foreach ($candidate in $candidatePaths) {
        if (Test-Path -LiteralPath $candidate) {
            $pgDumpCmd = Get-Item -LiteralPath $candidate
            break
        }
    }
}

if (-not $pgDumpCmd) {
    throw 'pg_dump não encontrado no PATH nem nos caminhos padrão do PostgreSQL.'
}

$pgDumpPath = if ($pgDumpCmd.PSObject.Properties.Name -contains 'Source' -and $pgDumpCmd.Source) {
    $pgDumpCmd.Source
}
elseif ($pgDumpCmd.PSObject.Properties.Name -contains 'Path' -and $pgDumpCmd.Path) {
    $pgDumpCmd.Path
}
elseif ($pgDumpCmd -is [System.IO.FileInfo]) {
    $pgDumpCmd.FullName
}
else {
    throw 'Não foi possível resolver o executável do pg_dump.'
}

$env:PGPASSWORD = $dbPassword

try {
    Write-Log "Iniciando backup PostgreSQL em $backupDir"

    & $pgDumpPath `
        -h $dbHost `
        -p $dbPort `
        -U $dbUser `
        --no-owner `
        --no-privileges `
        -d $dbName `
        -f $sqlPath

    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $sqlPath)) {
        throw "pg_dump falhou com código $LASTEXITCODE"
    }

    @'
import gzip
import shutil
import sys

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "rb") as f_in, gzip.open(dst, "wb") as f_out:
    shutil.copyfileobj(f_in, f_out)
'@ | python - $sqlPath $gzPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $gzPath)) {
        throw 'Falha ao gerar o arquivo .gz do backup.'
    }

    Remove-Item -LiteralPath $sqlPath -Force

    Get-ChildItem -LiteralPath $backupDir -Filter 'backup_postgresql_*.sql.gz' |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 3 |
        Remove-Item -Force

    Write-Log "Backup concluído com sucesso: $gzPath"
}
catch {
    Write-Log "ERRO: $($_.Exception.Message)"
    throw
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
