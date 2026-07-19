param(
    [string]$ServerName = "Sapiens Cliente",
    [string]$ServerUrl,
    [string]$BearerToken,
    [string]$Profile = "squad_cliente",
    [string]$Surface = "user",
    [string]$ExperienceLabel = "Sapiens Cliente",
    [string]$CanonicalLabel = "Squad Cliente",
    [string]$HarnessKey = "harness_coordenador_cliente_v1",
    [string]$HarnessLabel = "Harness Coordenador do Squad Cliente",
    [string]$CommandAlias = "/sapiens-cliente-on",
    [string]$ConfigPath,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$ProxyVersion = "1.1.0"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Ensure-ParentDirectory([string]$Path) {
    $parent = Split-Path -Path $Path -Parent
    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
}

function Backup-IfExists([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupPath = "$Path.bak_$timestamp"
    Copy-Item -LiteralPath $Path -Destination $backupPath -Force
    return $backupPath
}

function ConvertTo-HashtableCompat($InputObject) {
    if ($null -eq $InputObject) {
        return $null
    }
    if ($InputObject -is [System.Collections.IDictionary]) {
        $hash = [ordered]@{}
        foreach ($key in $InputObject.Keys) {
            $hash[$key] = ConvertTo-HashtableCompat $InputObject[$key]
        }
        return $hash
    }
    if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
        $items = @()
        foreach ($item in $InputObject) {
            $items += ,(ConvertTo-HashtableCompat $item)
        }
        return $items
    }
    if ($InputObject.PSObject -and $InputObject.PSObject.Properties.Count -gt 0 -and $InputObject.GetType().FullName -like "System.Management.Automation.PSCustomObject*") {
        $hash = [ordered]@{}
        foreach ($property in $InputObject.PSObject.Properties) {
            $hash[$property.Name] = ConvertTo-HashtableCompat $property.Value
        }
        return $hash
    }
    return $InputObject
}

function Read-JsonConfig([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        return [ordered]@{ mcpServers = [ordered]@{} }
    }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return [ordered]@{ mcpServers = [ordered]@{} }
    }
    $parsed = $raw | ConvertFrom-Json
    $root = ConvertTo-HashtableCompat $parsed
    if ($null -eq $root) {
        $root = [ordered]@{}
    }
    if (-not $root.Contains("mcpServers") -or $null -eq $root.mcpServers) {
        $root.mcpServers = [ordered]@{}
    }
    return $root
}

function Resolve-NodePath {
    $nodeCommand = Get-Command -Name "node" -ErrorAction SilentlyContinue
    if (-not $nodeCommand) {
        throw "Node.js não encontrado. Instale o Node.js LTS em https://nodejs.org, feche e reabra o PowerShell e execute novamente."
    }
    $nodePath = $nodeCommand.Source
    $versionText = (& $nodePath --version) -replace "^v", ""
    $major = [int](($versionText -split "\.")[0])
    if ($major -lt 18) {
        throw "Node.js $versionText encontrado, mas o proxy exige Node.js 18+ por causa do fetch nativo. Instale Node.js LTS e execute novamente."
    }
    return $nodePath
}

function Resolve-ClaudeDesktopConfigPath {
    if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
        return $ConfigPath
    }

    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:APPDATA) {
        $candidates.Add((Join-Path $env:APPDATA "Claude\claude_desktop_config.json"))
    }
    if ($env:LOCALAPPDATA) {
        $packagesRoot = Join-Path $env:LOCALAPPDATA "Packages"
        if (Test-Path -LiteralPath $packagesRoot) {
            $packages = Get-ChildItem -LiteralPath $packagesRoot -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like "Claude*" } |
                Sort-Object LastWriteTime -Descending
            foreach ($package in $packages) {
                $candidates.Add((Join-Path $package.FullName "LocalCache\Roaming\Claude\claude_desktop_config.json"))
            }
        }
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    if ($candidates.Count -gt 0) {
        return $candidates[0]
    }
    throw "Não foi possível resolver APPDATA/LOCALAPPDATA para gravar claude_desktop_config.json."
}

function Write-SapiensProxy([string]$ProxyPath) {
    Ensure-ParentDirectory -Path $ProxyPath
    $proxySource = @'
#!/usr/bin/env node
// Sapiens Cliente stdio -> StreamableHTTP/SSE proxy
// Version: 1.1.0

const VERSION = "1.1.0";
const targetUrl = process.env.SAPIENS_MCP_URL;
const bearerToken = process.env.SAPIENS_MCP_TOKEN;
const timeoutMs = Number(process.env.SAPIENS_MCP_TIMEOUT_MS || "60000");
let sessionId = process.env.SAPIENS_MCP_SESSION_ID || null;
const RETRYABLE_METHODS = new Set(["initialize", "tools/list", "prompts/list", "resources/list"]);
const RETRY_BACKOFF_MS = [500, 1500];

if (!targetUrl || !bearerToken) {
  process.stderr.write("SAPIENS_MCP_URL e SAPIENS_MCP_TOKEN são obrigatórios.\n");
  process.exit(2);
}

let inputBuffer = "";
let queue = [];
let active = false;
let stdinDone = false;

function debug(message) {
  if (process.env.SAPIENS_PROXY_DEBUG === "1") {
    process.stderr.write(`[sapiens-proxy ${VERSION}] ${message}\n`);
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function describeFetchError(error) {
  const causes = Array.isArray(error?.cause?.errors)
    ? error.cause.errors.map((item) => `${item.code || "error"}@${item.address || "unknown"}:${item.port || "?"}`)
    : [];
  return [error?.message || String(error), ...causes].join(" | ");
}

function writeJson(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function writeJsonRpcError(id, code, message) {
  writeJson({
    jsonrpc: "2.0",
    id: id ?? null,
    error: { code, message: String(message || "Erro no proxy Sapiens") },
  });
}

function maybeExit() {
  if (stdinDone && !active && queue.length === 0) {
    process.exit(0);
  }
}

function enqueueLine(line) {
  const trimmed = String(line || "").trim();
  if (!trimmed) return;
  try {
    queue.push(JSON.parse(trimmed));
    pumpQueue();
  } catch (error) {
    writeJsonRpcError(null, -32700, `JSON inválido no stdin: ${error.message}`);
  }
}

process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  inputBuffer += chunk;
  const parts = inputBuffer.split(/\r?\n/);
  inputBuffer = parts.pop() || "";
  for (const part of parts) enqueueLine(part);
});

process.stdin.on("end", () => {
  if (inputBuffer.trim()) enqueueLine(inputBuffer);
  stdinDone = true;
  maybeExit();
});

async function pumpQueue() {
  if (active) return;
  const message = queue.shift();
  if (!message) {
    maybeExit();
    return;
  }
  active = true;
  try {
    const response = await postJsonRpc(message);
    if (response) writeJson(response);
  } catch (error) {
    debug(error.stack || error.message);
    writeJsonRpcError(message.id, -32000, error.message);
  } finally {
    active = false;
    setImmediate(pumpQueue);
  }
}

async function postJsonRpc(message) {
  const headers = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
    "authorization": `Bearer ${bearerToken}`,
    "user-agent": `app32-sapiens-claude-desktop-proxy/${VERSION}`,
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  let response;
  const maxAttempts = RETRYABLE_METHODS.has(message.method) ? 3 : 1;
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      response = await fetch(targetUrl, {
        method: "POST",
        headers,
        body: JSON.stringify(message),
        signal: controller.signal,
      });
      break;
    } catch (error) {
      debug(`tentativa ${attempt}/${maxAttempts} falhou em ${message.method}: ${describeFetchError(error)}`);
      if (attempt >= maxAttempts) throw error;
      await sleep(RETRY_BACKOFF_MS[attempt - 1]);
    } finally {
      clearTimeout(timeout);
    }
  }

  const returnedSessionId = response.headers.get("mcp-session-id");
  if (returnedSessionId) sessionId = returnedSessionId;

  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status} ${response.statusText}: ${text.slice(0, 500)}`);
  }
  if (response.status === 202 || response.status === 204 || message.id === undefined || message.id === null) {
    await response.body?.cancel().catch(() => {});
    return null;
  }
  if (contentType.includes("text/event-stream")) {
    return await readSseUntilResponse(response, message.id);
  }
  const text = await response.text();
  return text.trim() ? JSON.parse(text) : null;
}

function parseSseBlock(block) {
  const dataLines = [];
  for (const rawLine of block.split("\n")) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  return dataLines.join("\n");
}

async function readSseUntilResponse(response, expectedId) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n").replace(/\r/g, "\n");
      let splitAt = buffer.indexOf("\n\n");
      while (splitAt !== -1) {
        const block = buffer.slice(0, splitAt);
        buffer = buffer.slice(splitAt + 2);
        const data = parseSseBlock(block);
        if (data && data !== "[DONE]") {
          const parsed = JSON.parse(data);
          if (expectedId === undefined || expectedId === null || parsed.id === expectedId) {
            await reader.cancel().catch(() => {});
            return parsed;
          }
        }
        splitAt = buffer.indexOf("\n\n");
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
  throw new Error(`Resposta SSE encerrada sem payload para id ${expectedId}`);
}
'@
    [System.IO.File]::WriteAllText($ProxyPath, $proxySource, [System.Text.UTF8Encoding]::new($false))
}

function Merge-ClaudeConfig(
    [string]$Path,
    [string]$NodePath,
    [string]$ProxyPath
) {
    $root = Read-JsonConfig -Path $Path
    $root.mcpServers[$ServerName] = [ordered]@{
        command = $NodePath
        args = @($ProxyPath)
        env = [ordered]@{
            SAPIENS_MCP_URL = $ServerUrl
            SAPIENS_MCP_TOKEN = $BearerToken
            SAPIENS_MCP_TIMEOUT_MS = "60000"
        }
        metadata = [ordered]@{
            proxy_version = $ProxyVersion
            profile = $Profile
            profile_label = $CanonicalLabel
            experience_label = $ExperienceLabel
            surface = $Surface
            harness_key = $HarnessKey
            harness_label = $HarnessLabel
            command_alias = $CommandAlias
        }
    }
    Ensure-ParentDirectory -Path $Path
    $json = $root | ConvertTo-Json -Depth 40
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

function Invoke-ProxySmoke([string]$NodePath, [string]$ProxyPath) {
    $payload = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"app32-installer","version":"1.1.0"}}}'
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $NodePath
    $psi.Arguments = '"' + $ProxyPath.Replace('"', '\"') + '"'
    $psi.UseShellExecute = $false
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.EnvironmentVariables["SAPIENS_MCP_URL"] = $ServerUrl
    $psi.EnvironmentVariables["SAPIENS_MCP_TOKEN"] = $BearerToken
    $psi.EnvironmentVariables["SAPIENS_MCP_TIMEOUT_MS"] = "60000"

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void]$process.Start()
    $process.StandardInput.WriteLine($payload)
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(190000)) {
        try { $process.Kill() } catch {}
        throw "Smoke do proxy excedeu 190s. Verifique rede, token e endpoint MCP."
    }
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    if ($process.ExitCode -ne 0) {
        throw "Proxy encerrou com código $($process.ExitCode): $stderr"
    }
    if ([string]::IsNullOrWhiteSpace($stdout)) {
        throw "Smoke do proxy não retornou JSON. STDERR: $stderr"
    }
    $firstLine = (($stdout -split "`r?`n") | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
    $json = $firstLine | ConvertFrom-Json
    if (-not $json.result -or -not $json.result.serverInfo) {
        throw "Smoke do proxy respondeu, mas não trouxe serverInfo: $firstLine"
    }
    return $json.result.serverInfo.name
}

if ([string]::IsNullOrWhiteSpace($ServerUrl)) {
    throw "ServerUrl é obrigatório."
}
if ([string]::IsNullOrWhiteSpace($BearerToken)) {
    throw "BearerToken é obrigatório."
}

Write-Step "Instalação do $ExperienceLabel no Claude Windows Desktop"
$nodePath = Resolve-NodePath
$configPathResolved = Resolve-ClaudeDesktopConfigPath
$claudeDataDir = Split-Path -Path $configPathResolved -Parent
$proxyPath = Join-Path $claudeDataDir "sapiens-proxy.js"
$backupPath = Backup-IfExists -Path $configPathResolved

Write-Host "Node.js............: $nodePath"
Write-Host "Config Claude......: $configPathResolved"
Write-Host "Proxy Sapiens......: $proxyPath"
Write-Host "Servidor MCP.......: $ServerUrl"

Write-Step "Gravando proxy stdio"
Write-SapiensProxy -ProxyPath $proxyPath

Write-Step "Atualizando claude_desktop_config.json"
Merge-ClaudeConfig -Path $configPathResolved -NodePath $nodePath -ProxyPath $proxyPath

$serverInfoName = $null
if (-not $SkipSmoke) {
    Write-Step "Validando proxy antes do restart"
    $serverInfoName = Invoke-ProxySmoke -NodePath $nodePath -ProxyPath $proxyPath
}

Write-Step "Instalação concluída"
Write-Host "Experiência.........: $ExperienceLabel"
Write-Host "Família canônica....: $CanonicalLabel"
Write-Host "Surface.............: $Surface"
Write-Host "Harness inicial.....: $HarnessLabel"
Write-Host "Entrada MCP.........: $ServerName"
if ($backupPath) {
    Write-Host "Backup..............: $backupPath"
}
if ($serverInfoName) {
    Write-Host "Smoke...............: OK ($serverInfoName)"
}

Write-Host ""
Write-Host "Próximos passos:" -ForegroundColor Yellow
Write-Host "1. Feche o Claude Desktop completamente, inclusive pela bandeja do sistema."
Write-Host "2. Abra o Claude Desktop novamente."
Write-Host "3. Confirme a conexão $ServerName em Configurações > Conectores."
Write-Host "4. Abra uma conversa e use: Sapiens On"
