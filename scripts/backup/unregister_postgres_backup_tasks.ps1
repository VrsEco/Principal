<#
    Remove a tarefa agendada responsável pelos backups automáticos
    do PostgreSQL no Windows Task Scheduler.
#>

param(
    [string]$TaskName = 'GestaoVersus_Postgres_Backup'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module ScheduledTasks -ErrorAction Stop

try {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
}
catch {
    Write-Warning "Nenhuma tarefa com o nome '$TaskName' foi encontrada. Nada a remover."
    return
}

if ($task.State -eq 'Running') {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false

Write-Output "Tarefa '$TaskName' removida com sucesso."


















