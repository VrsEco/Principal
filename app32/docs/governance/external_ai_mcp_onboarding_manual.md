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
| `user` | ChatGPT, Claude, Gemini, custom, internal | colaborador, cliente, administrador | menor privilégio, sem finance |
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

## Smokes de go-live

Resultado esperado:

```text
MCP_USER_ADMIN_RUNBOOK_SMOKE_OK True True
AI_MCP_RELEASE_CHECKLIST_OK 7 3
AI_MCP_TOOL_FREEZE_OK 7 4
AI_MCP_EXTERNAL_ONBOARDING_OK 4 5
```

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
