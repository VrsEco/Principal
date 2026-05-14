# Arquitetura Operacional do Squad Versus v1

## Objetivo
Formalizar o primeiro perfil de runtime externo do **Squad Versus** consumindo o APP32 por MCP, com governança, discovery inicial e surface privilegiada controlada.

## Decisão
O **Squad Versus** opera inicialmente como runtime externo consultivo na **surface `admin`**, usando `company_id` explícito quando exigido e começando sempre por discovery antes de qualquer mutação.

## Nomenclatura padronizada
Separar sempre:

- **nome de experiência**: `Sapiens Consultor`
- **família canônica**: `Squad Versus`
- **profile técnico**: `squad_versus`
- **harness inicial**: `harness_coordenador_versus_v1`

Regra:
- o consultor enxerga `Sapiens Consultor` no CLI
- specs, policy, RBAC e telemetry continuam usando `Squad Versus` / `squad_versus`

## Perfil publicado
- `profile`: `squad_versus`
- `url` padrão: `https://app.gestaoversus.com.br/mcp/admin`
- `surface`: `admin`
- owner operacional: consultor da Versus em runtime externo

## Startup obrigatório
Antes de operar, o runtime deve executar:
1. `list_admin_app32_capabilities`
2. `describe_app32_profile_contracts_tool`
3. `describe_app32_surface_playbooks_tool`
4. `describe_app32_domain_playbooks_tool`

## Guardrails
- usar `company_id` explícito em surface privilegiada
- não pular discovery inicial
- não mutar sem necessidade operacional clara
- manter trilha auditável por ator, runtime e capability
- não usar `ops` como atalho de governança

## Materialização no APP32
A integração foi materializada em:
- `C:\GestaoVersus\app32\app32\services\mcp_connection_snippet_service.py`
- `C:\GestaoVersus\app32\app32\services\ai_mcp_console_service.py`

## Evidência esperada no console
O frontend state do console IA/MCP deve expor:
- `connection_generator.profiles.squad_versus`
- `external_runtime_profiles.squad_versus`
- URL padrão `/mcp/admin`
- startup tools obrigatórias

## Próximo passo
Expandir a mesma lógica para o **Squad Cliente**, preservando menor privilégio e utilização assistida.
