<#
    GestaoVersus - Publicação automática para GitHub
    Adiciona alterações, cria commit padrão e realiza push para o repositório remoto.
#>

param(
    [string]$RepositoryPath = '',
    [string]$LogFilePath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param([string]$Message)

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    Add-Content -Path $script:LogFilePath -Value "[${timestamp}] $Message"
}

$exitCode = 0
$locationPushed = $false

try {
    if ([string]::IsNullOrWhiteSpace($RepositoryPath)) {
        $RepositoryPath = Resolve-Path (Join-Path $PSScriptRoot '..\..')
    }

    if ([string]::IsNullOrWhiteSpace($LogFilePath)) {
        $LogDir = Join-Path $RepositoryPath 'logs'
        if (-not (Test-Path -Path $LogDir -PathType Container)) {
            New-Item -Path $LogDir -ItemType Directory | Out-Null
        }
        $LogFilePath = Join-Path $LogDir 'git_automation.log'
    }

    $script:LogFilePath = $LogFilePath

    if (-not (Test-Path -Path $RepositoryPath -PathType Container)) {
        throw "Repositório não encontrado em $RepositoryPath"
    }

    Push-Location $RepositoryPath
    $locationPushed = $true

    $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw 'Não foi possível identificar a branch atual.'
    }

    $status = git status --porcelain | Out-String
    if ([string]::IsNullOrWhiteSpace($status.Trim())) {
        Write-Log "Nenhuma alteração detectada na branch '$branch'. Nenhum push necessário."
    }
    else {
        git add -A | Out-Null

        $commitMessage = "Daily automated sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        $commitOutput = git commit -m $commitMessage 2>&1

        if ($LASTEXITCODE -ne 0) {
            if ($commitOutput -match 'nothing to commit') {
                Write-Log "Alterações revertidas durante o processo. Nada para publicar."
            }
            else {
                throw "Erro ao criar commit: $commitOutput"
            }
        }
        else {
            $pushOutput = git push 2>&1
            if ($LASTEXITCODE -ne 0) {
                throw "Erro ao executar git push: $pushOutput"
            }

            Write-Log "Publicação concluída na branch '$branch'. Commit: '$commitMessage'."
        }
    }
}
catch {
    $exitCode = 1
    if (-not [string]::IsNullOrWhiteSpace($script:LogFilePath)) {
        Write-Log "ERRO: $($_.Exception.Message)"
    }
    else {
        Write-Error $_.Exception.Message
    }
}
finally {
    if ($locationPushed) {
        Pop-Location
    }
}

exit $exitCode
