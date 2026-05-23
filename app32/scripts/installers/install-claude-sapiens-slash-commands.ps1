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
2. Verifique a conexão MCP da sessão.
3. Rode `bootstrap_session_context`.
4. Rode `resolve_app32_sapiens_activation_tool` com `squad=cliente`.
5. Execute integralmente a `startup_tools` retornada, na ordem.
5.1. Se o payload trouxer `activation_welcome_opening`, use exatamente essa mensagem na primeira resposta.
5.2. Se o usuário pedir instruções, mostre `activation_welcome_short`.
5.3. Se depois o usuário pedir mais detalhes, mostre `activation_welcome_full`.
6. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
7. Reconheça também `Sapiens Cliente On`, `sapiens cliente on` e `/sapiens-cliente-on` como a mesma ativação.
8. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Cliente não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
9. Se o bootstrap funcionar, confirme em resposta curta:
   - primeira linha exatamente: `Sapiens Cliente Ativado`
   - qual é o agente/harness de entrada
   - qual é a surface ativa
   - qual é a empresa padrão, se houver
10. Se o runtime suportar renomear a sessão/conversa, use o título `Sapiens Cliente On`.
11. Depois disso, permaneça operando como Sapiens Cliente até nova instrução ou até `Sapiens Off`.
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
2. Verifique a conexão MCP da sessão.
3. Rode `bootstrap_session_context`.
4. Rode `resolve_app32_sapiens_activation_tool` com `squad=consultor`.
5. Execute integralmente a `startup_tools` retornada, na ordem.
5.1. Se o payload trouxer `activation_welcome_opening`, use exatamente essa mensagem na primeira resposta.
5.2. Se o usuário pedir instruções, mostre `activation_welcome_short`.
5.3. Se depois o usuário pedir mais detalhes, mostre `activation_welcome_full`.
6. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
7. Reconheça também `Sapiens Consultor On`, `sapiens consultor on` e `/sapiens-consultor-on` como a mesma ativação.
8. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Consultor não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
9. Se o bootstrap funcionar, confirme em resposta curta:
   - primeira linha exatamente: `Sapiens Consultor Ativado`
   - qual é o agente/harness de entrada
   - qual é a surface ativa
10. Se o runtime suportar renomear a sessão/conversa, use o título `Sapiens Consultor On`.
11. Depois disso, permaneça operando como Sapiens Consultor até nova instrução ou até `Sapiens Off`.
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
2. Verifique a conexão MCP da sessão.
3. Rode `bootstrap_session_context`.
4. Rode `resolve_app32_sapiens_activation_tool` com `squad=engenharia`.
5. Execute integralmente a `startup_tools` retornada, na ordem.
5.1. Se o payload trouxer `activation_welcome_opening`, use exatamente essa mensagem na primeira resposta.
5.2. Se o usuário pedir instruções, mostre `activation_welcome_short`.
5.3. Se depois o usuário pedir mais detalhes, mostre `activation_welcome_full`.
6. Não invente ativação, não simule tool e não responda consulta operacional sem MCP real.
7. Reconheça também `Sapiens Engenharia On`, `sapiens engenharia on` e `/sapiens-engenharia-on` como a mesma ativação.
8. Se a conexão MCP não estiver disponível nesta sessão, responda exatamente:
   `A conexão MCP do Sapiens Engenharia não está disponível nesta sessão. Revise a instalação MCP no APP32 (/profile), reinstale os comandos slash oficiais e reinicie o Claude.`
9. Se o bootstrap funcionar, confirme em resposta curta:
   - primeira linha exatamente: `Sapiens Engenharia Ativado`
   - qual é o agente/harness de entrada
   - qual é a surface ativa
10. Se o runtime suportar renomear a sessão/conversa, use o título `Sapiens Engenharia On`.
11. Depois disso, permaneça operando como Sapiens Engenharia até nova instrução ou até `Sapiens Off`.
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

1. Reconheça `Sapiens On`, `sapiens on` e `/sapiens-on` como o mesmo comando de entrada.
2. Verifique a conexão com o MCP sapiens-user.
3. Rode `bootstrap_session_context`.
4. Rode `describe_app32_available_sapiens_squads_tool`.
5. Pergunte exatamente ao usuário: `Com qual squad você vai trabalhar? Cliente / Consultor / Engenharia`
6. Quando o usuário responder, rode `resolve_app32_sapiens_activation_tool` com o squad escolhido.
7. Execute integralmente a `startup_tools` retornada, na ordem, sem depender de ToolSearch manual.
7.1. Se o payload trouxer `activation_welcome_opening`, use exatamente essa mensagem na primeira resposta.
7.2. Se o usuário pedir instruções, mostre `activation_welcome_short`.
7.3. Se depois o usuário pedir mais detalhes, mostre `activation_welcome_full`.
8. Nunca assuma automaticamente quando houver mais de um Squad possível.
9. Não exija empresa na abertura da sessão. Use empresa padrão apenas se já existir contexto explícito.
10. Para leituras pessoais transversais, opere em todas as empresas autorizadas e responda agrupando por empresa quando houver múltiplas.
11. Para mutações, ações operacionais específicas ou ambiguidades, peça empresa somente quando precisar de escopo único.
12. Depois da ativação, confirme em resposta curta com a primeira linha exatamente no formato:
   - `Sapiens Cliente Ativado`
   - `Sapiens Consultor Ativado`
   - `Sapiens Engenharia Ativado`
13. Se o runtime suportar renomear a sessão/conversa, use como título:
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

Reconheça `Sapiens On`, `sapiens on` e `/sapiens-on` como a entrada desta ativação.
Rode `bootstrap_session_context`, depois `describe_app32_available_sapiens_squads_tool`, em seguida `resolve_app32_sapiens_activation_tool` e execute a `startup_tools` retornada.
Não pergunte squad: existe apenas um disponível e você deve baixar somente este.
Não exija empresa na abertura da sessão. Leituras pessoais podem operar no escopo autorizado; ações específicas pedem empresa apenas quando necessário.
Se o payload trouxer `activation_welcome_opening`, use exatamente essa mensagem na primeira resposta.
Se o usuário pedir instruções, mostre `activation_welcome_short`.
Se depois o usuário pedir mais detalhes, mostre `activation_welcome_full`.
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
2. Reconheça `Sapiens On` e `Sapiens Off` como comandos oficiais desta skill.
3. Se existir mais de um Squad Sapiens instalado nesta máquina, execute integralmente o fluxo de `/sapiens-on` e pergunte o squad antes de baixar qualquer bundle.
4. Se existir apenas um Squad Sapiens instalado nesta máquina, execute integralmente o fluxo do comando oficial correspondente sem perguntar o squad e baixe somente ele:
   - Cliente: `/sapiens-cliente-on`
   - Consultor: `/sapiens-consultor-on`
   - Engenharia: `/sapiens-engenharia-on`
'@
Publish-ClaudeActivation `
    -CommandName "sapiens" `
    -Description "Alias defensivo do Sapiens oficial para evitar ativação genérica incorreta." `
    -Body $sapiensAliasBody

$sapiensOffBody = @'
Desative o **Sapiens** nesta conversa.

1. Reconheça `Sapiens Off`, `sapiens off` e `/sapiens-off` como o mesmo comando.
2. Remova o badge/título de sessão ativa, se o runtime suportar.
3. Descarte o bundle e o contexto do squad ativo desta conversa.
4. Mantenha a sessão aberta normalmente, sem conexão ao squad.
5. Responda curto confirmando que o Sapiens foi desligado.
'@
Publish-ClaudeActivation `
    -CommandName "sapiens-off" `
    -Description "Encerra o squad Sapiens ativo e remove o badge/contexto da sessão." `
    -Body $sapiensOffBody

if ($normalizedSquads -contains "squad_cliente") {
    Publish-ClaudeActivation `
        -CommandName "sapiens-cliente-off" `
        -Description "Encerra explicitamente a sessão do Sapiens Cliente." `
        -Body "Desative o Sapiens Cliente nesta conversa, remova o badge `Sapiens Cliente On`, descarte o contexto ativo do squad e mantenha a sessão aberta."
}

if ($normalizedSquads -contains "squad_versus") {
    Publish-ClaudeActivation `
        -CommandName "sapiens-consultor-off" `
        -Description "Encerra explicitamente a sessão do Sapiens Consultor." `
        -Body "Desative o Sapiens Consultor nesta conversa, remova o badge `Sapiens Consultor On`, descarte o contexto ativo do squad e mantenha a sessão aberta."
}

if ($normalizedSquads -contains "engineering") {
    Publish-ClaudeActivation `
        -CommandName "sapiens-engenharia-off" `
        -Description "Encerra explicitamente a sessão do Sapiens Engenharia." `
        -Body "Desative o Sapiens Engenharia nesta conversa, remova o badge `Sapiens Engenharia On`, descarte o contexto ativo do squad e mantenha a sessão aberta."
}

Write-Host "Comandos oficiais instalados em $commandsDir e skills oficiais instaladas em $skillsDir"
