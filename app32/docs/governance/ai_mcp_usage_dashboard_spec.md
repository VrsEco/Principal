# Dashboard e Relatório de Uso IA/MCP — APP32

Documento operacional da **AA.J.31.1322 — Organização IA/MCP - Grupo 07 - Definir dashboard/relatório de uso IA/MCP**.

## 1. Objetivo

Definir a especificação canônica do dashboard/relatório de uso IA/MCP para acompanhar adoção, qualidade, segurança e operação das integrações de IA do APP32.

O dashboard deve responder:

- quanto o Sapiens e o MCP estão sendo usados por empresa e período;
- quais surfaces, tools e domínios concentram uso;
- qual a taxa de erro/bloqueio;
- se há sinais de risco multi-tenant ou uso fora de policy;
- se os workflows conversacionais estão sendo resolvidos ou gerando gaps.

## 2. Fonte canônica em código

- Manifesto: `src.intelligence.mcp_contracts.usage_dashboard.APP32_USAGE_DASHBOARD_MANIFEST`
- Tool MCP de descoberta: `describe_app32_usage_dashboard_tool`
- Registrador MCP: `src.core.mcp_usage_dashboard_tools.register_usage_dashboard_tools`
- Catálogo MCP/Sapiens: `src.intelligence.tool_catalog.catalog`

## 3. Fontes de dados

| Fonte | Uso | Observação |
|---|---|---|
| `ai_audit_log` | eventos de runtime Sapiens/MCP, tools, status e segurança | fonte alvo conforme plano de persistência IA/MCP |
| `workflow_usage` | resolução de workflows, descoberta, confiança e interceptações | baseado em `WorkflowExecutionLog` |
| `agent_messages` | volume de mensagens por canal/agente/modelo | não deve expor conteúdo integral por padrão |
| `tool_catalog` | cobertura de capabilities por surface/domínio/risco | fonte canônica atual de capabilities |

## 4. Filtros obrigatórios

Todo relatório operacional deve exigir:

- `company_id`;
- `date_from`;
- `date_to`.

Exceção: cobertura estática de catálogo pode exigir apenas `company_id`, pois não consulta eventos temporais.

## 5. Métricas canônicas

| Métrica | Fonte | Tipo | Finalidade |
|---|---|---|---|
| `ai_mcp_calls_total` | `ai_audit_log` | counter | volume de chamadas IA/MCP |
| `ai_mcp_error_rate` | `ai_audit_log` | ratio | taxa de erro, bloqueio e falha |
| `mcp_tool_usage_by_domain` | `ai_audit_log` | table | ranking de tools por domínio/surface/status |
| `workflow_resolution_trace` | `workflow_usage` | timeseries | resolução de workflows, confiança e descoberta |
| `agent_messages_volume` | `agent_messages` | counter | mensagens por canal/agente/modelo |
| `catalog_surface_coverage` | `tool_catalog` | table | cobertura de capabilities por surface/domínio/risco |

## 6. Painéis

### 6.1 Visão executiva IA/MCP

Métricas:

- `ai_mcp_calls_total`;
- `ai_mcp_error_rate`;
- `agent_messages_volume`.

Uso: acompanhar adoção, estabilidade e volume por empresa/canal.

### 6.2 Operação MCP por domínio e tool

Métricas:

- `mcp_tool_usage_by_domain`;
- `catalog_surface_coverage`.

Uso: identificar tools mais usadas, domínio de maior risco, surfaces com falhas e cobertura de catálogo.

### 6.3 Resolução de workflows Sapiens

Métricas:

- `workflow_resolution_trace`;
- `agent_messages_volume`.

Uso: medir descoberta, interceptação, confiança, status e gaps de workflows.

## 7. Regras de segurança

- `company_id` é obrigatório em toda consulta de eventos.
- SQL livre é proibido; usar read models, queries whitelisted ou agregações do serviço oficial.
- Conteúdo integral de prompt/mensagem não deve aparecer por padrão.
- Perfis não administrativos não acessam visão consolidada multi-tool.
- Eventos bloqueados por tenant/security devem aparecer como alerta, nunca ser filtrados silenciosamente.
- Métricas financeiras ou sensíveis devem ser agregadas.

## 8. Alertas operacionais

Criar alertas quando:

- taxa de erro IA/MCP superar 5% no período;
- houver evento bloqueado por tenant/security;
- tool sensível for usada fora da surface esperada;
- ocorrer queda abrupta de interceptação de workflows após deploy;
- uma tool aparecer no audit log sem capability correspondente no catálogo.

## 9. Roadmap de implementação

1. **1322 — Especificação e manifesto:** manifesto MCP consultável, documentação e testes de contrato.
2. **Próxima fase — Read model:** serviço com agregações tenant-safe por `company_id/date_from/date_to`.
3. **Próxima fase — API/MCP:** endpoint/API e tool de execução do relatório.
4. **Próxima fase — UI:** tela admin/analytics com cards, tabelas e filtros.
5. **Próxima fase — Alertas:** thresholds e congelamento de tool por sinais de risco.

## 10. Smoke pós-deploy

```powershell
python -c "import app; from src.intelligence.mcp_contracts import APP32_USAGE_DASHBOARD_MANIFEST; print('AI_MCP_USAGE_DASHBOARD_SPEC_OK', len(APP32_USAGE_DASHBOARD_MANIFEST.metrics), len(APP32_USAGE_DASHBOARD_MANIFEST.panels))"
```

Resultado esperado:

```text
AI_MCP_USAGE_DASHBOARD_SPEC_OK 6 3
```
