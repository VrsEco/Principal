# Arquitetura Operacional do Squad Cliente v1

## Objetivo
Formalizar o primeiro perfil de runtime externo do **Squad Cliente** consumindo o APP32 por MCP, com menor privilégio, utilização assistida e foco na operação do cliente.

## Decisão
O **Squad Cliente** opera inicialmente na **surface `user`**, conectado ao tenant ativo do cliente e sem acesso a `admin`, `analytics` ou `ops`.

## Perfil publicado
- `profile`: `squad_cliente`
- `url` padrão: `https://app.gestaoversus.com.br/mcp/user`
- `surface`: `user`
- owner operacional: usuário da empresa cliente em runtime externo

## Startup obrigatório
Antes de operar, o runtime deve executar:
1. `bootstrap_session_context`
2. `list_user_app32_capabilities`
3. `describe_app32_surface_playbooks_tool`

## Guardrails
- operar com menor privilégio
- usar sempre o tenant ativo do cliente
- não acessar `admin`, `analytics` ou `ops`
- não tentar contornar restrições por prompt
- manter a lógica de utilização assistida e coprodução humano + agente

## Materialização no APP32
A integração foi materializada em:
- `C:\GestaoVersus\app32\app32\services\mcp_connection_snippet_service.py`
- `C:\GestaoVersus\app32\app32\services\ai_mcp_console_service.py`

## Evidência esperada no console
O frontend state do console IA/MCP deve expor:
- `connection_generator.profiles.squad_cliente`
- `external_runtime_profiles.squad_cliente`
- URL padrão `/mcp/user`
- startup tools obrigatórias

## Próximo passo
Conectar o modelo de utilização assistida e os sinais iniciais de maturidade assistida à experiência desses perfis externos.
