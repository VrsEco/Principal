<#
    GestaoVersus - PostgreSQL backup helper
    Executa pg_dump usando a instalação nativa do PostgreSQL (Windows 18)
    e comprime o resultado no diretório de backups do projeto.
#>

param(
    [string]$PgBinPath = 'C:\Program Files\PostgreSQL\18\bin',
    [string]$OutputDirectory = '',
    [string]$EnvFilePath = ''
)

# Monta o caminho padrão sem depender de caracteres especiais no arquivo.
$versusParticipacoes = 'Versus ' + 'Participa' + [char]0xE7 + [char]0xF5 + 'es'
$DefaultBackupPath = [System.IO.Path]::Combine(
    $env:USERPROFILE,
    'OneDrive',
    'Versus',
    $versusParticipacoes,
    'Versus ERP',
    'Back-up_BD_App'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-EnvDictionary {
    param([string]$Path)

    $result = @{}
    if (-not (Test-Path -Path $Path -PathType Leaf)) {
        return $result
    }

    foreach ($line in [System.IO.File]::ReadLines($Path)) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith('#')) {
            continue
        }

        $parts = $trimmed.Split('=', 2)
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if (-not [string]::IsNullOrWhiteSpace($key)) {
            $result[$key] = $value
        }
    }

    return $result
}

try {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $projectRoot = Resolve-Path (Join-Path $scriptRoot '..\..')

    if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
        $OutputDirectory = $DefaultBackupPath
    }

    if ([string]::IsNullOrWhiteSpace($EnvFilePath)) {
        $EnvFilePath = Join-Path $projectRoot '.env'
    }

    $envData = Get-EnvDictionary -Path $EnvFilePath

    $pgHost = $envData['POSTGRES_HOST']
    if ([string]::IsNullOrWhiteSpace($pgHost)) { $pgHost = 'localhost' }
    elseif ($pgHost -eq 'host.docker.internal') { $pgHost = 'localhost' }

    $pgPort = $envData['POSTGRES_PORT']
    if ([string]::IsNullOrWhiteSpace($pgPort)) { $pgPort = '5432' }

    $pgDatabase = $envData['POSTGRES_DB']
    if ([string]::IsNullOrWhiteSpace($pgDatabase)) { $pgDatabase = 'bd_app_versus' }

    $pgUser = $envData['POSTGRES_USER']
    if ([string]::IsNullOrWhiteSpace($pgUser)) { $pgUser = 'postgres' }

    $pgPassword = $envData['POSTGRES_PASSWORD']
    if ([string]::IsNullOrWhiteSpace($pgPassword)) {
        throw 'POSTGRES_PASSWORD não definido no arquivo .env ou parâmetros.'
    }

    $pgDumpPath = Join-Path $PgBinPath 'pg_dump.exe'
    if (-not (Test-Path -Path $pgDumpPath -PathType Leaf)) {
        throw "pg_dump não localizado em: $pgDumpPath"
    }

    if (-not (Test-Path -Path $OutputDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
    }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $sqlPath = Join-Path $OutputDirectory ("postgres_backup_{0}.sql" -f $timestamp)
    $zipPath = "$sqlPath.zip"
    $logPath = Join-Path $OutputDirectory 'postgres_backup.log'

    $env:PGPASSWORD = $pgPassword

    $arguments = @(
        "--host=$pgHost"
        "--port=$pgPort"
        "--username=$pgUser"
        "--format=plain"
        "--file=""$sqlPath"""
        $pgDatabase
    ) -join ' '

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $pgDumpPath
    $startInfo.Arguments = $arguments
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.UseShellExecute = $false

    $process = [System.Diagnostics.Process]::Start($startInfo)
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

    if (-not [string]::IsNullOrWhiteSpace($stdout)) {
        Add-Content -Path $logPath -Value "[${timestamp}] STDOUT:`n$stdout"
    }

    if ($process.ExitCode -ne 0) {
        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            Add-Content -Path $logPath -Value "[${timestamp}] STDERR:`n$stderr"
        }
        throw "pg_dump retornou código $($process.ExitCode)"
    }

    Compress-Archive -Path $sqlPath -DestinationPath $zipPath -Force
    Remove-Item -Path $sqlPath -ErrorAction SilentlyContinue
    Add-Content -Path $logPath -Value "[${timestamp}] Backup gerado: $zipPath"
}
catch {
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $message = "[${timestamp}] ERRO: $($_.Exception.Message)"
    if (-not [string]::IsNullOrWhiteSpace($logPath)) {
        Add-Content -Path $logPath -Value $message
    }
    else {
        Write-Error $message
    }
    exit 1
}
