# Manual de Onboarding de IAs Externas via MCP — APP32

Documento operacional da **AA.J.31.1325 — Organização IA/MCP - Grupo 08 - Criar manual de onboarding de IAs externas via MCP**.

## Fonte canônica

- Manifesto: `src.intelligence.mcp_contracts.external_ai_onboarding.APP32_EXTERNAL_AI_ONBOARDING_MANIFEST`
- Tool MCP: `describe_app32_external_ai_onboarding_tool`
- Registrador: `src.core.mcp_external_ai_onboarding_tools.register_external_ai_onboarding_tools`

## Fases do onboarding

1. **Intake:** identificar provider, finalidade, canal, perfil, surface, domínios e `company_id`.
2. **Desenho de acesso:** aplicar menor privilégio usando contratos de perfil/surface/domínio.
3. **Registro:** configurar cliente MCP sem expor segredos em prompt/log/metadata.
4. **Validação:** executar smokes de go-live.
5. **Operação:** monitorar uso IA/MCP e aplicar congelamento se houver trigger crítico.

## Regras por surface

| Surface | Providers permitidos | Perfis | Observação |
|---|---|---|---|
| `user` | ChatGPT, Claude, Gemini, custom, internal | colaborador, cliente, administrador | menor privilégio, `finance` permission-aware |
| `admin` | custom, internal | administrador, admin_tecnico | exige aprovação humana |
| `analytics` | custom, internal | administrador, admin_tecnico | somente read models/catálogo |
| `ops` | internal | admin_tecnico | uso técnico e incidentes |

## Discovery obrigatório

Toda IA externa deve consultar:

- `list_app32_capabilities`;
- `describe_app32_profile_contracts_tool`;
- `describe_app32_surface_playbooks_tool`;
- `describe_app32_domain_playbooks_tool`;
- `describe_app32_release_checklist_tool`;
- `describe_app32_tool_freeze_procedure_tool`.

## Proibições

- Não liberar SQL livre para IA externa.
- Não compartilhar tokens, cookies, senhas ou chaves em prompt.
- Não conceder admin/ops a provider genérico sem aprovação humana.
- Não executar operação sem `company_id` explícito quando o contrato exigir.

## Diretriz canônica para Claude

- Para cliente final, o caminho homologado é **Usuário Normal — Claude Windows Desktop** com instalador APP32 e proxy `stdio`.
- Para usuário técnico, o caminho homologado é **Usuário Avançado — Claude CLI / Claude Code**.
- O onboarding deve privilegiar:
  1. no Usuário Normal, `install-sapiens-claude-desktop-windows.ps1` + smoke `initialize`;
  2. no Usuário Avançado, `claude mcp add ...` + validação com `claude mcp list`;
  3. prompt de bootstrap/ativação.
- O APP32 não deve exibir comando executável quando o token ainda for placeholder; o usuário precisa clicar em **Criar token** ou **Renovar** e copiar o comando final com token real.
- O instalador Desktop deve rejeitar explicitamente `TOKEN_GERADO_APENAS_NA_RENOVACAO` para evitar falsa instalação e erro genérico no Claude.
- Slash commands personalizados podem existir, mas são **opcionais**.

## Regra de permissão real do usuário

- A IA externa não deve assumir que `surface=user` implica bloqueio automático de `finance`.
- O comportamento correto é refletir a mesma permissão efetiva da senha do usuário no APP32.
- Exemplos de permissões efetivas:
  - `financial.view`
  - `financial.create`
  - `financial.edit`
  - `financial.delete`
- Se a permissão real não existir, a IA deve bloquear a ação mesmo que a tool exista no catálogo.

## Smokes de go-live

Resultado esperado:

```text
MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True
AI_MCP_RELEASE_CHECKLIST_OK 7 3
AI_MCP_TOOL_FREEZE_OK 7 4
AI_MCP_EXTERNAL_ONBOARDING_OK 4 5
```

Checklist adicional de homologação Claude:

- no Usuário Normal, o Claude Desktop mostra `Sapiens Cliente` como conector local sem erro;
- no Usuário Avançado, `claude mcp list` mostra o servidor esperado como `Connected`;
- bootstrap MCP consegue chamar tools explícitas, não apenas reconhecer o servidor.

## Uso via MCP

```text
describe_app32_external_ai_onboarding_tool()
describe_app32_external_ai_onboarding_tool(surface='user')
describe_app32_external_ai_onboarding_tool(surface='admin')
```

## Smoke pós-deploy

```powershell
python -c "import app; from src.intelligence.mcp_contracts import APP32_EXTERNAL_AI_ONBOARDING_MANIFEST; print('AI_MCP_EXTERNAL_ONBOARDING_OK', len(APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.surface_access_rules), len(APP32_EXTERNAL_AI_ONBOARDING_MANIFEST.steps))"
```

Resultado esperado:

```text
AI_MCP_EXTERNAL_ONBOARDING_OK 4 5
```

---

## Complemento MCP-02 — Jornada oficial de conexão

Fonte oficial: `app32/docs/spec/experiencia_conexao_app32_cli_ia_mcp_api_v1.md`.

A partir da SPEC MCP-02, o onboarding de IA externa deve seguir a jornada:

1. usuário acessa `/channels`;
2. escolhe runtime, empresa padrão, squad/perfil e surface;
3. gera ou renova credencial;
4. copia snippet específico do runtime;
5. instala no CLI/IA;
6. executa teste de conexão;
7. confirma empresa ativa e último uso;
8. usa MCP com contexto tenant-safe;
9. registra resultado/validação no APP32 quando aplicável.

Separação obrigatória:

- `/channels`: tela única de Conexões para canais externos, provedores e CLI/IA via MCP;
- `/profile`: modo detalhado/fallback de instalação pessoal MCP;
- `/api-mcp`: catálogo e contratos;
- console técnico: diagnóstico, readiness e operação de Engenharia.

Anti-padrão: duplicar regra de token/canal no frontend ou forçar o usuário a alternar entre várias telas para uma conexão simples.

