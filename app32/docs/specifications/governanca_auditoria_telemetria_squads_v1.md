# Governança, Auditoria e Telemetria dos Squads v1

## Objetivo
Endurecer o uso dos squads externos com trilha mínima obrigatória por ator, runtime, surface, capability e status, sem depender apenas de logs genéricos.

## Entrega publicada
A entrega materializou três reforços:

1. **Contexto HTTP/MCP ampliado**
   - `runtime_profile`
   - `actor_type`
   - `client_id`
   - `token_subject`

2. **Auditoria MCP enriquecida**
   Os eventos IA/MCP agora persistem metadata suficiente para análise por:
   - papel do ator
   - surface
   - profile de runtime
   - client_id

3. **Telemetria executiva no console IA/MCP**
   O frontend state agora expõe `governance_telemetry` com:
   - resumo por status
   - contagem por runtime
   - contagem por actor_role
   - contagem por surface
   - contagem por runtime_profile
   - top tools auditadas

## Arquivos alterados
- `C:\GestaoVersus\app32\app32\src\core\mcp_http_auth.py`
- `C:\GestaoVersus\app32\app32\src\core\mcp_runtime.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\tool_catalog.py`
- `C:\GestaoVersus\app32\app32\services\operational_audit_service.py`
- `C:\GestaoVersus\app32\app32\services\ai_mcp_console_service.py`

## Resultado arquitetural
Agora o APP32 passa a ter um contrato mínimo melhor para responder:
- qual squad usou a plataforma
- em qual runtime
- com qual surface
- com qual papel
- em qual tenant
- com qual capability
- com qual resultado

## Próximo passo
Usar essa telemetria endurecida no piloto ponta a ponta para validar fricção, aderência ao menor privilégio e qualidade do uso assistido.
