@echo off
title Configurar Backup Automatico Diario (APP32)
echo ==================================================
echo   CONFIGURACAO DE BACKUP AUTOMATICO - APP32
echo ==================================================
echo.
echo Este script vai configurar o Windows para executar
echo o backup automaticamente todos os dias as 18:30.
echo.
echo Pressione qualquer tecla para continuar...
pause > nul

echo.
echo Registrando tarefa no Agendador de Tarefas...
schtasks /Create /TN "GestaoVersus_Backup_Diario" /XML "%~dp0BackupDiario_Task.xml" /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==================================================
    echo   SUCESSO! Backup automatico configurado.
    echo ==================================================
    echo.
    echo Configuracao:
    echo   - Horario: Todos os dias as 18:30
    echo   - Retencao: Ultimos 3 backups
    echo   - Destino: OneDrive ^(sincronizacao automatica^)
    echo.
    echo Para verificar ou modificar:
    echo   1. Abra o "Agendador de Tarefas" do Windows
    echo   2. Procure por "GestaoVersus_Backup_Diario"
    echo.
    echo Para desativar o backup automatico:
    echo   Execute: schtasks /Delete /TN "GestaoVersus_Backup_Diario" /F
    echo.
) else (
    echo.
    echo ==================================================
    echo   ERRO ao configurar a tarefa!
    echo ==================================================
    echo.
    echo Verifique se voce executou como Administrador.
    echo Clique com botao direito e escolha "Executar como administrador"
    echo.
)

echo.
echo Pressione qualquer tecla para fechar...
pause > nul
