<#
    Registra tarefa agendada para executar o backup do PostgreSQL
    às 12:00, 18:00 e 22:00 todos os dias.
#>

param(
    [string]$TaskName = 'GestaoVersus_Postgres_Backup',
    [string]$ScriptPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Resolve-Path (Join-Path $scriptRoot 'run_pg_backup.ps1')
}

if (-not (Test-Path -Path $ScriptPath -PathType Leaf)) {
    throw "Script de backup não encontrado em $ScriptPath"
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$triggers = @(
    New-ScheduledTaskTrigger -Daily -At (Get-Date '12:00')
    New-ScheduledTaskTrigger -Daily -At (Get-Date '18:00')
    New-ScheduledTaskTrigger -Daily -At (Get-Date '22:00')
)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Principal $principal `
    -Settings $settings `
    -Description 'Backup automático do PostgreSQL GestaoVersus (12h/18h/22h)' `
    -Force | Out-Null

Write-Output "Tarefa '$TaskName' registrada com sucesso."
