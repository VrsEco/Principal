<#
    Registra tarefa agendada para publicar o repositório no GitHub
    diariamente às 18:00.
#>

param(
    [string]$TaskName = 'GestaoVersus_GitHub_Publish',
    [string]$ScriptPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
    $ScriptPath = Resolve-Path (Join-Path $scriptRoot 'auto_git_push.ps1')
}

if (-not (Test-Path -Path $ScriptPath -PathType Leaf)) {
    throw "Script de push automático não encontrado em $ScriptPath"
}

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date '18:00')

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description 'Publicação automática da aplicação GestaoVersus no GitHub (18h)' `
    -Force | Out-Null

Write-Output "Tarefa '$TaskName' registrada com sucesso."
