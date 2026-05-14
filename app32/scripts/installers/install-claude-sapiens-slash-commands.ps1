param(
    [string[]]$AvailableSquads = @("squad_cliente")
)

$commandsDir = Join-Path $env:USERPROFILE ".claude\commands"
New-Item -ItemType Directory -Force -Path $commandsDir | Out-Null

function Write-SlashCommand {
    param(
        [string]$FileName,
        [string]$Description,
        [string]$Body
    )

    $content = @"
---
description: $Description
---

$Body
"@

    $path = Join-Path $commandsDir $FileName
    [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Comando criado: $path"
}

function Get-SquadLabel {
    param([string]$Squad)
    switch ($Squad) {
        "squad_cliente" { return "Sapiens Cliente" }
        "squad_versus" { return "Sapiens Consultor" }
        "engineering" { return "Sapiens Engenharia" }
        default { return $Squad }
    }
}

$normalizedSquads = @(
    $AvailableSquads |
        ForEach-Object { "$_" -split "," } |
        ForEach-Object { "$_".Trim().ToLower() } |
        Where-Object { $_ }
)

if ($normalizedSquads -contains "squad_cliente") {
    Write-SlashCommand `
        -FileName "sapiens-cliente-on.md" `
        -Description "Ativa o Sapiens Cliente e carrega o bootstrap oficial do Squad Cliente." `
        -Body @"
Ative o **Sapiens Cliente** nesta conversa.

1. Use a conexão MCP do Sapiens Cliente.
2. Rode `describe_app32_squad_runtime_tool`.
3. Rode `list_user_app32_capabilities`.
4. Rode `describe_app32_profile_contracts_tool`.
5. Rode `describe_app32_surface_playbooks_tool`.
6. Confirme a ativação com uma resposta curta dizendo:
   - que o Sapiens Cliente está ativo
   - qual é o agente de entrada
   - qual é a surface ativa
   - qual é a empresa padrão, se houver
7. Depois pergunte objetivamente qual demanda o usuário quer tratar agora.

Se a conexão MCP não estiver disponível, explique isso claramente e oriente o usuário a revisar a instalação do Sapiens Cliente.
"@
}

if ($normalizedSquads -contains "squad_versus") {
    Write-SlashCommand `
        -FileName "sapiens-consultor-on.md" `
        -Description "Ativa o Sapiens Consultor e carrega o bootstrap oficial do Squad Versus." `
        -Body @"
Ative o **Sapiens Consultor** nesta conversa.

1. Use a conexão MCP do Sapiens Consultor.
2. Rode `describe_app32_squad_runtime_tool`.
3. Rode `describe_app32_profile_contracts_tool`.
4. Rode `describe_app32_surface_playbooks_tool`.
5. Confirme a ativação com uma resposta curta dizendo:
   - que o Sapiens Consultor está ativo
   - qual é o agente de entrada
   - qual é a surface ativa
6. Depois pergunte qual frente consultiva o usuário deseja tratar agora.

Se a conexão MCP não estiver disponível, explique isso claramente e oriente o usuário a revisar a instalação do Sapiens Consultor.
"@
}

if ($normalizedSquads -contains "engineering") {
    Write-SlashCommand `
        -FileName "sapiens-engenharia-on.md" `
        -Description "Ativa o Sapiens Engenharia e carrega o bootstrap oficial do Squad de Engenharia." `
        -Body @"
Ative o **Sapiens Engenharia** nesta conversa.

1. Use a conexão MCP do Sapiens Engenharia.
2. Rode `describe_app32_squad_runtime_tool`.
3. Rode `describe_app32_profile_contracts_tool`.
4. Rode `describe_app32_surface_playbooks_tool`.
5. Confirme a ativação com uma resposta curta dizendo:
   - que o Sapiens Engenharia está ativo
   - qual é o agente de entrada
   - qual é a surface ativa
6. Depois pergunte qual demanda técnica o usuário deseja tratar agora.

Se a conexão MCP não estiver disponível, explique isso claramente e oriente o usuário a revisar a instalação do Sapiens Engenharia.
"@
}

$availableLabels = @($normalizedSquads | ForEach-Object { Get-SquadLabel $_ })
$availableList = $availableLabels -join ", "

if ($normalizedSquads.Count -gt 1) {
    Write-SlashCommand `
        -FileName "sapiens-on.md" `
        -Description "Ativa o Sapiens e, se houver mais de um Squad disponível, pede confirmação antes de seguir." `
        -Body @"
Ative o **Sapiens** nesta conversa.

Os squads instalados nesta máquina são: **$availableList**.

1. Antes de ativar, pergunte ao usuário qual Squad ele quer usar agora.
2. Se o usuário escolher Cliente, execute o fluxo equivalente a `/sapiens-cliente-on`.
3. Se o usuário escolher Consultor, execute o fluxo equivalente a `/sapiens-consultor-on`.
4. Se o usuário escolher Engenharia, execute o fluxo equivalente a `/sapiens-engenharia-on`.
5. Nunca assuma automaticamente quando houver mais de um Squad possível.
"@
}
elseif ($normalizedSquads.Count -eq 1) {
    $onlyLabel = $availableLabels[0]
    $onlyCommand = switch ($normalizedSquads[0]) {
        "squad_cliente" { "/sapiens-cliente-on" }
        "squad_versus" { "/sapiens-consultor-on" }
        "engineering" { "/sapiens-engenharia-on" }
        default { "/sapiens-cliente-on" }
    }

    Write-SlashCommand `
        -FileName "sapiens-on.md" `
        -Description "Ativa o único Squad Sapiens disponível nesta máquina." `
        -Body @"
Ative o **$onlyLabel** nesta conversa.

Existe apenas um Squad Sapiens disponível nesta máquina.

Execute o fluxo equivalente a `$onlyCommand` e confirme a ativação ao usuário.
"@
}

Write-Host "Comandos oficiais de ativação do Sapiens instalados em $commandsDir"
