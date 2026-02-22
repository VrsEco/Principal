# 🤖 Configurar Backup Automático - APP31

**Tempo Estimado:** 15 minutos  
**Dificuldade:** ⭐⭐ (Fácil)

---

## 🎯 Objetivo

Configurar o Windows para executar backup automático do banco de dados todos os dias às 3:00 AM.

---

## 📋 Pré-requisitos

- ✅ Windows 10/11
- ✅ Docker Desktop rodando
- ✅ Scripts de backup criados (`backup_docker_completo.bat`)
- ✅ Acesso administrativo ao Windows

---

## 🚀 Método 1: Task Scheduler (Recomendado)

### Passo 1: Abrir Task Scheduler

```
1. Pressione Windows + R
2. Digite: taskschd.msc
3. Pressione Enter
```

### Passo 2: Criar Nova Tarefa

```
1. No painel direito, clique em "Create Task..."
2. Aba "General":
   - Name: Backup Docker APP31
   - Description: Backup automático diário do banco PostgreSQL
   - ✅ "Run whether user is logged on or not"
   - ✅ "Run with highest privileges"
```

### Passo 3: Configurar Trigger (Quando executar)

```
1. Vá para aba "Triggers"
2. Clique "New..."
3. Configure:
   - Begin the task: "On a schedule"
   - Settings: "Daily"
   - Start: [data de hoje]
   - Start time: 03:00:00 (3:00 AM)
   - Recur every: 1 days
   - ✅ Enabled
4. Clique "OK"
```

### Passo 4: Configurar Action (O que executar)

```
1. Vá para aba "Actions"
2. Clique "New..."
3. Configure:
   - Action: "Start a program"
   - Program/script: C:\Windows\System32\cmd.exe
   - Add arguments: /c "C:\GestaoVersus\app31\backup_docker_completo.bat"
   - Start in: C:\GestaoVersus\app31
4. Clique "OK"
```

**⚠️ IMPORTANTE:** Ajuste o caminho `C:\GestaoVersus\app31` para o caminho correto onde está seu projeto!

### Passo 5: Configurar Condições

```
1. Vá para aba "Conditions"
2. Desmarque: "Start the task only if the computer is on AC power"
3. Marque: "Wake the computer to run this task"
```

### Passo 6: Configurar Settings

```
1. Vá para aba "Settings"
2. Marque:
   - ✅ "Allow task to be run on demand"
   - ✅ "Run task as soon as possible after a scheduled start is missed"
   - ✅ "If the task fails, restart every: 1 minute, 3 times"
3. Desmarque:
   - ❌ "Stop the task if it runs longer than: 3 days"
```

### Passo 7: Salvar e Testar

```
1. Clique "OK" para salvar
2. Digite sua senha de administrador se solicitado
3. Localize a tarefa criada na lista
4. Clique com botão direito > "Run"
5. Verifique se backup foi criado em: C:\GestaoVersus\app31\backups
```

---

## 🚀 Método 2: Script PowerShell (Alternativo)

### Passo 1: Criar Script de Agendamento

Crie um arquivo: `agendar_backup.ps1`

```powershell
# Verificar se está executando como Administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "Execute como Administrador!"
    exit
}

# Configurações
$TaskName = "Backup Docker APP31"
$ScriptPath = "C:\GestaoVersus\app31\backup_docker_completo.bat"
$WorkingDir = "C:\GestaoVersus\app31"
$Time = "03:00"

# Criar ação
$Action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$ScriptPath`"" `
    -WorkingDirectory $WorkingDir

# Criar trigger (todo dia às 3:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Criar settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false

# Registrar tarefa
Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -User "SYSTEM" `
    -RunLevel Highest `
    -Force

Write-Host "✅ Tarefa agendada criada com sucesso!" -ForegroundColor Green
Write-Host "📅 Backup será executado todo dia às $Time" -ForegroundColor Cyan
Write-Host "📁 Backups serão salvos em: $WorkingDir\backups" -ForegroundColor Cyan
```

### Passo 2: Executar Script

```powershell
# Executar como Administrador
PowerShell -ExecutionPolicy Bypass -File agendar_backup.ps1
```

### Passo 3: Verificar Agendamento

```powershell
# Listar tarefas
Get-ScheduledTask -TaskName "Backup Docker APP31"

# Executar manualmente para testar
Start-ScheduledTask -TaskName "Backup Docker APP31"
```

---

## 🚀 Método 3: Script Batch Simples (Mais Simples)

### Passo 1: Criar Script de Agendamento

Crie um arquivo: `agendar_backup.bat`

```batch
@echo off
REM Execute como Administrador!

set SCRIPT_PATH=%cd%\backup_docker_completo.bat
set HORA=03:00

echo Criando tarefa agendada...
schtasks /create ^
    /tn "Backup Docker APP31" ^
    /tr "\"%SCRIPT_PATH%\"" ^
    /sc daily ^
    /st %HORA% ^
    /rl highest ^
    /f

if %errorlevel% equ 0 (
    echo ✅ Tarefa criada com sucesso!
    echo 📅 Backup será executado todo dia às %HORA%
    echo.
    echo Para testar agora:
    echo schtasks /run /tn "Backup Docker APP31"
) else (
    echo ❌ Erro ao criar tarefa
    echo Execute este script como Administrador!
)

pause
```

### Passo 2: Executar

```
1. Clique com botão direito em "agendar_backup.bat"
2. Selecione "Run as administrator"
3. Confirme a criação da tarefa
```

---

## 📊 Verificar Backups

### Ver Últimos Backups

```batch
dir /o-d backups\db_backup_*.zip
```

### Espaço em Disco

```batch
# Ver tamanho total de backups
dir backups\db_backup_*.zip | find "File(s)"
```

### Limpar Backups Antigos

Crie: `limpar_backups_antigos.bat`

```batch
@echo off
REM Remove backups com mais de 30 dias

echo Removendo backups com mais de 30 dias...

forfiles /p "backups" /s /m db_backup_*.zip ^
    /d -30 /c "cmd /c del @path"

echo ✅ Limpeza concluída
pause
```

---

## 🔔 Notificações (Opcional)

### Receber E-mail com Status do Backup

Modifique o script `backup_docker_completo.bat` para incluir:

```batch
REM No final do script, adicionar:

REM Enviar e-mail de notificação (requer blat ou similar)
blat.exe -to seuemail@example.com ^
    -subject "Backup APP31 - %datetime%" ^
    -body "Backup concluído com sucesso" ^
    -attach "backups\db_backup_%datetime%.zip"
```

### Criar Log de Execução

```batch
REM Adicionar no início do script:
echo [%date% %time%] Iniciando backup... >> backups\backup.log

REM Adicionar no final:
echo [%date% %time%] Backup concluído >> backups\backup.log
```

---

## 🧪 Testar Backup Automático

### 1. Executar Tarefa Manualmente

```
Task Scheduler:
1. Encontre "Backup Docker APP31"
2. Botão direito > Run
3. Verifique logs e backup criado
```

**Ou via CMD:**
```batch
schtasks /run /tn "Backup Docker APP31"
```

### 2. Verificar Histórico

```
Task Scheduler:
1. Encontre "Backup Docker APP31"
2. Aba "History"
3. Veja execuções anteriores
```

### 3. Ver Logs

```batch
# Ver últimas 10 execuções
Get-WinEvent -FilterHashtable @{
    LogName='Microsoft-Windows-TaskScheduler/Operational'
    ID=100,102,200,201
} -MaxEvents 10 | Where-Object {$_.Message -match "Backup Docker APP31"}
```

---

## 🔧 Troubleshooting

### Problema: Tarefa não executa

**Soluções:**
```
1. Verificar se Docker Desktop está rodando
2. Verificar permissões do script
3. Verificar caminho do script
4. Executar manualmente para ver erros
```

### Problema: Backup falha

**Diagnóstico:**
```batch
# Executar manualmente e ver erros
backup_docker_completo.bat
```

### Problema: Sem espaço em disco

**Solução:**
```
1. Configurar limpeza automática de backups antigos
2. Usar compressão (já incluído no script)
3. Mover backups antigos para nuvem/HD externo
```

---

## 📋 Checklist Final

Após configurar, verifique:

- [ ] Tarefa criada no Task Scheduler
- [ ] Execução manual funciona
- [ ] Backup foi criado em `backups/`
- [ ] Backup está comprimido (.zip)
- [ ] Tamanho do backup é razoável (MB/GB)
- [ ] Docker Desktop configurado para iniciar com Windows
- [ ] Espaço em disco suficiente (pelo menos 10GB livres)

---

## 🎯 Próximos Passos

1. **Configurar Backup em Nuvem:**
   - Google Drive
   - Dropbox
   - AWS S3
   - OneDrive

2. **Implementar Retenção de Backups:**
   - Manter últimos 7 backups diários
   - Manter 4 backups semanais
   - Manter 12 backups mensais

3. **Monitoramento:**
   - Configurar alertas se backup falhar
   - Dashboard de status de backups
   - Relatórios mensais

---

## 📚 Referências

- [Task Scheduler Documentation](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
- [Docker Backup Best Practices](https://docs.docker.com/storage/volumes/#back-up-restore-or-migrate-data-volumes)
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)

---

## 🆘 Comandos Úteis

```batch
# Listar tarefas agendadas
schtasks /query /fo list

# Executar tarefa
schtasks /run /tn "Backup Docker APP31"

# Deletar tarefa
schtasks /delete /tn "Backup Docker APP31" /f

# Modificar horário
schtasks /change /tn "Backup Docker APP31" /st 04:00
```

---

**Elaborado por:** Cursor AI  
**Data:** 28/10/2025  
**Status:** ✅ Guia Completo


