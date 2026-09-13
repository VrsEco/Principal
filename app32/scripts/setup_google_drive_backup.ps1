param(
    [Parameter(Mandatory = $true)]
    [string]$GoogleDrivePath
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path $GoogleDrivePath)) {
    New-Item -ItemType Directory -Path $GoogleDrivePath -Force | Out-Null
}
foreach ($name in 'database', 'code', 'uploads', 'manifests') {
    New-Item -ItemType Directory -Path (Join-Path $GoogleDrivePath $name) -Force | Out-Null
}
[Environment]::SetEnvironmentVariable('GV_BACKUP_LOCAL_DIR', $GoogleDrivePath, 'User')
[Environment]::SetEnvironmentVariable('GV_BACKUP_INTRADAY_RETENTION_DAYS', '30', 'User')
[Environment]::SetEnvironmentVariable('GV_BACKUP_DAILY_RETENTION_DAYS', '90', 'User')
[Environment]::SetEnvironmentVariable('GV_BACKUP_MONTHLY_RETENTION_DAYS', '365', 'User')
Write-Host "Google Drive preparado em: $GoogleDrivePath"
Write-Host 'A próxima execução do download_backups.py gravará nessa pasta.'
Write-Host 'Antes de executar, confirme no Google Drive para desktop que a pasta está sincronizada.'
