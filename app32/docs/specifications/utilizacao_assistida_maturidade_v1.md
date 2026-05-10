# Utilização Assistida e Maturidade Assistida v1

## Objetivo
Materializar no APP32 um estado executável mínimo para orientar a adoção dos squads sem cair em paternalismo.

## Entrega publicada
O console IA/MCP agora expõe dois blocos estruturados no frontend state:
- `assisted_usage`
- `maturity_model`

## assisted_usage
Define três fases operacionais:
1. `conducao_forte`
2. `coproducao_orientada`
3. `autonomia_assistida`

Também publica anti-patterns explícitos para evitar dependência do usuário em relação ao squad.

## maturity_model
Publica:
- níveis: `assistido`, `orientado`, `copiloto`, `autonomo`, `multiplicador`
- sinais iniciais para:
  - `consultor_versus`
  - `usuario_cliente`
- regra central: maturidade deve aumentar autonomia com responsabilidade

## Materialização técnica
- `C:\GestaoVersus\app32\app32\services\ai_mcp_console_service.py`
- `C:\GestaoVersus\app32\app32\tests\test_ai_mcp_console_route.py`

## Papel desta entrega
Esta etapa ainda não calcula score automático por usuário. Ela publica o contrato inicial que passa a orientar:
- onboarding
- uso assistido
- progressão esperada
- rollout futuro de gamificação/maturidade

## Próximo passo
Ligar esses sinais a telemetria e auditoria para começar a medir evidências reais de maturidade por ator e runtime.
