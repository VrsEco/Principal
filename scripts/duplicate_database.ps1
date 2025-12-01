param(
    [string]$SourceDb = "bd_app_versus_backup_restaurado",
    [string]$TargetDb = "bd_app_versus_backup_restaurado_copy",
    [string]$PgHost = "host.docker.internal",
    [int]$PgPort = 5432,
    [string]$PgUser = "postgres",
    [string]$PgPassword = "*Paraiso1978"
)

$pgAdminRuntime = "C:\Program Files\PostgreSQL\18\pgAdmin 4\runtime"
$psql = Join-Path $pgAdminRuntime "psql.exe"
$pgDump = Join-Path $pgAdminRuntime "pg_dump.exe"
$pgRestore = Join-Path $pgAdminRuntime "pg_restore.exe"

if (-not (Test-Path $psql -PathType Leaf)) {
    Write-Error "Não foi possível localizar o psql em '$psql'. Atualize o caminho conforme o seu ambiente."
    exit 1
}

$env:PGPASSWORD = $PgPassword

function Run-Psql($database, $sql) {
    Write-Host "psql:$database> $sql"
    & $psql -h $PgHost -p $PgPort -U $PgUser -d $database -c $sql
    if ($LASTEXITCODE -ne 0) { throw "Falha no comando psql contra o banco '$database'." }
}

function Run-PgDump($outputDump) {
    Write-Host "Gerando dump de '$SourceDb' em '$outputDump'..."
    & $pgDump -h $PgHost -p $PgPort -U $PgUser -F c -b -v -d $SourceDb -f $outputDump
    if ($LASTEXITCODE -ne 0) { throw "pg_dump falhou."; }
}

function Run-PgRestore($dumpFile) {
    Write-Host "Restaurando '$dumpFile' em '$TargetDb'..."
    & $pgRestore -h $PgHost -p $PgPort -U $PgUser -d $TargetDb -v $dumpFile
    if ($LASTEXITCODE -ne 0) { throw "pg_restore falhou."; }
}

try {
    Run-Psql "postgres" "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TargetDb';"
    Run-Psql "postgres" "DROP DATABASE IF EXISTS $TargetDb;"
    Run-Psql "postgres" "CREATE DATABASE $TargetDb;"

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tempDump = Join-Path $env:TEMP "dup_${SourceDb}_${timestamp}.dump"

    Run-PgDump $tempDump
    Run-PgRestore $tempDump

    Write-Host "Duplicação concluída: '$SourceDb' → '$TargetDb'."
} catch {
    Write-Error $_
} finally {
    if (Test-Path $tempDump) {
        Remove-Item $tempDump -Force
    }
}
