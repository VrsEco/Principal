param(
    [string[]]$AvailableSquads = @("squad_cliente")
)

$commandsDir = Join-Path $env:USERPROFILE ".claude\commands"
$skillsDir = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $commandsDir | Out-Null
New-Item -ItemType Directory -Force -Path $skillsDir | Out-Null

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

function Write-ClaudeSkill {
    param(
        [string]$SkillName,
        [string]$Description,
        [string]$Body
    )

    $skillPath = Join-Path (Join-Path $skillsDir $SkillName) "SKILL.md"
    New-Item -ItemType Directory -Force -Path (Split-Path $skillPath) | Out-Null

    $content = @"
---
name: $SkillName
description: $Description
disable-model-invocation: true
---

$Body
"@

    [System.IO.File]::WriteAllText($skillPath, $content, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Skill criada: $skillPath"
}

function Publish-ClaudeActivation {
    param(
        [string]$CommandName,
        [string]$Description,
        [string]$Body
    )

    Write-SlashCommand -FileName "$CommandName.md" -Description $Description -Body $Body
    Write-ClaudeSkill -SkillName $CommandName -Description $Description -Body $Body
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
    $clienteBody = @'
Ative o **Sapiens Cliente** nesta conversa.

Regras obrigatórias desta ativação:

1. Use obrigatoriamente a conexão MCP instalada do Sapiens Cliente antes de responder qualquer demanda operacional.
2. Faça o bootstrap oficial nesta ordem:
   - `describe_app32_squad_runtime_tool`
   - `list_user_app32_capabilities`
   - `describe_app32_profile_contracts_tool`
   - `describe_app32_surface_playbooks_tool`
   - `describe_app32_domain_playbooks_tool`
3. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
4. Nunca mande o usuário digitar `sapiens on` como texto livre.
5. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Cliente não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
6. Se o bootstrap funcionar, confirme em resposta curta:
   - que o Sapiens Cliente está ativo
   - qual é o agente/harness de entrada
   - qual é a surface ativa
   - qual é a empresa padrão, se houver
7. Depois disso, permaneça operando como Sapiens Cliente até nova instrução.
'@
    Publish-ClaudeActivation `
        -CommandName "sapiens-cliente-on" `
        -Description "Ativa o Sapiens Cliente e carrega o bootstrap oficial do Squad Cliente." `
        -Body $clienteBody
}

if ($normalizedSquads -contains "squad_versus") {
    $consultorBody = @'
Ative o **Sapiens Consultor** nesta conversa.

Regras obrigatórias desta ativação:

1. Use obrigatoriamente a conexão MCP instalada do Sapiens Consultor antes de responder qualquer demanda operacional.
2. Faça o bootstrap oficial nesta ordem:
   - `describe_app32_squad_runtime_tool`
   - `describe_app32_profile_contracts_tool`
   - `describe_app32_surface_playbooks_tool`
   - `describe_app32_domain_playbooks_tool`
3. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
4. Nunca mande o usuário digitar `sapiens on` como texto livre.
5. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Consultor não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
6. Se o bootstrap funcionar, confirme em resposta curta:
   - que o Sapiens Consultor está ativo
   - qual é o agente/harness de entrada
   - qual é a surface ativa
7. Depois disso, permaneça operando como Sapiens Consultor até nova instrução.
'@
    Publish-ClaudeActivation `
        -CommandName "sapiens-consultor-on" `
        -Description "Ativa o Sapiens Consultor e carrega o bootstrap oficial do Squad Versus." `
        -Body $consultorBody
}

if ($normalizedSquads -contains "engineering") {
    $engenhariaBody = @'
Ative o **Sapiens Engenharia** nesta conversa.

Regras obrigatórias desta ativação:

1. Use obrigatoriamente a conexão MCP instalada do Sapiens Engenharia antes de responder qualquer demanda operacional.
2. Faça o bootstrap oficial nesta ordem:
   - `describe_app32_squad_runtime_tool`
   - `describe_app32_profile_contracts_tool`
   - `describe_app32_surface_playbooks_tool`
   - `describe_app32_domain_playbooks_tool`
3. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
4. Nunca mande o usuário digitar `sapiens on` como texto livre.
5. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Engenharia não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
6. Se o bootstrap funcionar, confirme em resposta curta:
   - que o Sapiens Engenharia está ativo
   - qual é o agente/harness de entrada
   - qual é a surface ativa
7. Depois disso, permaneça operando como Sapiens Engenharia até nova instrução.
'@
    Publish-ClaudeActivation `
        -CommandName "sapiens-engenharia-on" `
        -Description "Ativa o Sapiens Engenharia e carrega o bootstrap oficial do Squad de Engenharia." `
        -Body $engenhariaBody
}

$availableLabels = @($normalizedSquads | ForEach-Object { Get-SquadLabel $_ })
$availableList = $availableLabels -join ", "

if ($normalizedSquads.Count -gt 1) {
    $sapiensOnBody = @'
Ative o **Sapiens** nesta conversa.

Os squads instalados nesta máquina são: **{0}**.

1. Antes de ativar, pergunte exatamente ao usuário: `Escolha entre: Cliente, Versus ou Engenharia.`
2. Se o usuário escolher Cliente, execute integralmente o fluxo de `/sapiens-cliente-on`.
3. Se o usuário escolher Consultor, execute integralmente o fluxo de `/sapiens-consultor-on`.
4. Se o usuário escolher Engenharia, execute integralmente o fluxo de `/sapiens-engenharia-on`.
5. Nunca assuma automaticamente quando houver mais de um Squad possível.
6. Nunca mande o usuário digitar `sapiens on` como texto livre.
7. Depois da ativação, confirme em resposta curta com a primeira linha exatamente no formato:
   - `Sapiens Cliente Ativado`
   - `Sapiens Consultor Ativado`
   - `Sapiens Engenharia Ativado`
8. Se o runtime suportar renomear a sessão/conversa, use como título:
   - `Sapiens Cliente On`
   - `Sapiens Consultor On`
   - `Sapiens Engenharia On`
'@ -f $availableList
    Publish-ClaudeActivation `
        -CommandName "sapiens-on" `
        -Description "Ativa o Sapiens e, se houver mais de um Squad disponível, pede confirmação antes de seguir." `
        -Body $sapiensOnBody
}
elseif ($normalizedSquads.Count -eq 1) {
    $onlyLabel = $availableLabels[0]
    $onlyCommand = switch ($normalizedSquads[0]) {
        "squad_cliente" { "/sapiens-cliente-on" }
        "squad_versus" { "/sapiens-consultor-on" }
        "engineering" { "/sapiens-engenharia-on" }
        default { "/sapiens-cliente-on" }
    }
    $singleSquadBody = @'
Ative o **{0}** nesta conversa.

Existe apenas um Squad Sapiens disponível nesta máquina.

Execute integralmente o fluxo equivalente a `{1}` e confirme a ativação ao usuário.

Use a primeira linha de confirmação exatamente no formato `{0} Ativado`.
'@ -f $onlyLabel, $onlyCommand

    Publish-ClaudeActivation `
        -CommandName "sapiens-on" `
        -Description "Ativa o único Squad Sapiens disponível nesta máquina." `
        -Body $singleSquadBody
}

    $sapiensAliasBody = @'
Ative o **Sapiens oficial do APP32** nesta conversa.

1. Nunca trate este comando como skill genérica solta.
2. Nunca mande o usuário digitar `sapiens on` como texto livre.
3. Se existir mais de um Squad Sapiens instalado nesta máquina, execute integralmente o fluxo de `/sapiens-on`.
4. Se existir apenas um Squad Sapiens instalado nesta máquina, execute integralmente o fluxo do comando oficial correspondente:
   - Cliente: `/sapiens-cliente-on`
   - Consultor: `/sapiens-consultor-on`
   - Engenharia: `/sapiens-engenharia-on`
'@
Publish-ClaudeActivation `
    -CommandName "sapiens" `
    -Description "Alias defensivo do Sapiens oficial para evitar ativação genérica incorreta." `
    -Body $sapiensAliasBody

Write-Host "Comandos oficiais instalados em $commandsDir e skills oficiais instaladas em $skillsDir"
