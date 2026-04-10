# Classificação do Runtime Sapiens / AI do APP32

Documento operacional da **AA.J.31.1317 — Mapear runtimes e grafos legados do Sapiens**.

## Runtime oficial

O runtime canônico e suportado para execução de IA/Sapiens no APP32 é:

- `src.intelligence.execution.run_agent_with_context`
- `src.intelligence.menu_engine.handle_menu_message`
- `src.intelligence.work_agents.graph.create_work_agent_workflow`
- `src.intelligence.tool_catalog.catalog`

Fluxo oficial:

`execution -> menu_engine -> work_agents.graph -> tool_catalog`

### Componentes oficiais

| Componente | Papel | Diretriz |
|---|---|---|
| `src.intelligence.execution.run_agent_with_context` | entrypoint auditável por usuário, empresa, canal e thread | novas entradas devem passar por este fluxo |
| `src.intelligence.menu_engine.handle_menu_message` | roteamento conversacional determinístico | evoluir intents e descoberta por aqui |
| `src.intelligence.work_agents.graph.create_work_agent_workflow` | grafo oficial Work Agents V2 | usar para novas capacidades agenticas |
| `src.intelligence.tool_catalog.catalog` | catálogo único Sapiens/MCP | registrar novas tools/capabilities MCP First aqui |

## Grafos legados

Os módulos abaixo permanecem somente para compatibilidade histórica, análise e eventual desativação controlada:

- `src.intelligence.graph`
- `src.intelligence.graphs.main_graph`

### Inventário legado

| Módulo | Situação | Risco | Próxima ação |
|---|---|---|---|
| `src.intelligence.graph.create_agent_workflow` | legado | duplica supervisor/tool node e mistura especialistas antigos | não evoluir; manter só compatibilidade até 1318 |
| `src.intelligence.graphs.main_graph.create_main_graph` | legado | roteador fiscal/financeiro simplificado e execução paralela ao runtime oficial | preparar depreciação com guard rails na 1318 |
| `src.intelligence.test_agent` | compatibilidade/test harness | pode confundir runtime produtivo com execução manual | substituir por pytest/fixtures |
| `src.intelligence.test_agent_mock` | compatibilidade/test harness | experimento local legado | manter fora de produção |

## Diretriz de uso

- Novas integrações de IA/MCP devem usar o runtime oficial.
- Grafos legados não devem receber novas funcionalidades.
- Auditoria, multi-tenancy e RBAC devem ser aplicados no runtime oficial primeiro.
- A depreciação real dos grafos legados iniciou na **AA.J.31.1318**, com guard rails em modo `warn-only` e sem remoção abrupta.
- Qualquer exceção deve registrar evidência de compatibilidade e não pode abrir bypass de `company_id`, RBAC ou tool catalog.

## Guard rails de depreciação — AA.J.31.1318

O módulo canônico de guarda é:

- `src.intelligence.runtime_guard`

Política vigente:

- padrão operacional: `warn-only`;
- variável de controle: `APP32_LEGACY_RUNTIME_GUARD_MODE`;
- modos aceitos: `warn`, `block`, `off`;
- `warn`: mantém compatibilidade, emite `DeprecationWarning` e log estruturado;
- `block`: bloqueia o uso com `LegacyRuntimeBlockedError`;
- `off`: escape hatch temporário para diagnóstico controlado.

Entrypoints legados com guarda explícita:

| Entrypoint | Guarda |
|---|---|
| `src.intelligence.graph.create_agent_workflow` | `create_workflow` |
| `src.intelligence.graphs.main_graph.create_main_graph` | `create_workflow` |
| `src.intelligence.graphs.main_graph.run_agent_interaction` | `run_interaction` |
| `src.intelligence.test_agent.run_integration_test` | `manual_test_harness` |
| `src.intelligence.test_agent_mock.run_mock_test` | `manual_test_harness` |

Próxima etapa recomendada: migrar compatibilidade de `run_agent_interaction` para o runtime oficial quando houver contexto seguro (`company_id`, `user_id`, `accessible_company_ids`) e adicionar gate estático para impedir novos imports dos grafos legados fora da allowlist.

## Fonte canônica em código

O inventário executável fica em:

- `src.intelligence.runtime_classification.RUNTIME_COMPONENTS`
- `src.intelligence.runtime_classification.describe_runtime_topology()`
- `src.intelligence.runtime_guard.require_legacy_runtime_access()`
