# Harness Simulado de Agente para Validação de Escopo

A atividade **AA.J.31.1327** cria um harness interno para validar decisões de escopo de agentes IA/MCP sem depender de LLM, LangGraph real ou execução efetiva de tools.

## Objetivo

Validar de forma determinística:

- tenant scope
- role/permissão efetivos do usuário do sistema
- surface MCP
- runtime profile / harness do cliente remoto
- habilitação MCP e treinamento obrigatório
- domínio permitido
- presença da tool no manifest da surface
- gate humano para mutações de risco

## Arquivo canônico

- `src.intelligence.simulated_agent_harness`

## Componentes

### `SimulatedAgentScenario`
Entrada declarativa do cenário:
- `user_id`
- `role`
- `surface`
- `tool_name`
- `domain`
- `action`
- `requested_company_id`
- `accessible_company_ids`
- `risk`
- `confirmed_mutation`
- `runtime_profile`
- `actor_type`
- `mcp_enabled`
- `training_completed`

### `evaluate_simulated_agent_scenario(...)`
Executa a avaliação em cima de camadas puras do APP32:

1. `build_runtime_security_snapshot(...)`
2. `APP32_PROFILE_CONTRACTS_MANIFEST`
3. `APP32_SURFACE_PLAYBOOKS_MANIFEST`
4. `get_surface_manifest(...)`
5. `evaluate_tool_policy(...)`
6. `evaluate_mcp_channel_gate(...)`

### `SimulatedAgentHarnessResult`
Retorna:
- `allowed`
- `reason`
- `resolved_surface`
- `resolved_company_id`
- snapshot de runtime
- decisão de policy
- presença da tool no manifest da surface
- trilha de checks

## Regras práticas

- O harness **não executa** tools reais.
- O harness **não chama** LLM.
- O harness **não depende** do grafo LangGraph para decidir escopo.
- O harness trata o **Harness Squad Cliente** como metadata operacional do runtime, não como substituto do papel/permissão real do usuário.
- O harness só permite cenário quando:
  - o tenant é válido;
  - o papel/permissão do usuário é suportado;
  - a surface existe;
  - o runtime profile/harness é coerente com a surface MCP;
  - o usuário está habilitado para MCP e, quando exigido, com treinamento concluído;
  - o domínio é permitido pelo playbook da surface;
  - a tool existe no manifest da surface;
  - a tool policy autoriza o uso.

## Casos mínimos cobertos

- colaborador na surface `user` com tool/dominio permitidos
- bloqueio de `admin` para colaborador
- bloqueio de mutação em `analytics`
- exigência de `company_id` explícito em contexto multiempresa administrativo
- exigência de confirmação para mutação high/critical
- bloqueio quando a tool não pertence ao manifest da surface
- bloqueio quando o runtime profile diverge da surface
- bloqueio quando a habilitação/treinamento MCP não foi concluída

## Relação com o runtime oficial

O runtime oficial continua validado por:
- `tests/test_official_runtime_smoke.py`
- `tests/test_execution_menu_metadata.py`

O harness da 1327 complementa isso cobrindo a **policy pura de escopo** e a **porta de entrada MCP orientada por harness/runtime profile**.

## Smoke de aceite da entrega

Referência esperada:
- `AI_MCP_SIMULATED_HARNESS_OK 6`
