# Arquitetura Oficial — Copiloto de Fluxo BPMN MCP

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a arquitetura oficial do copiloto de Fluxo BPMN do APP32 para:

- analisar diagramas BPMN por tenant;
- apontar gaps de modelagem e operação;
- sugerir automações e conexões APP32/MCP/API;
- manter intervenção humana obrigatória antes da publicação.

## 2. Princípios

1. **BPMN é a fonte canônica do Fluxo**
2. **MCP opera sobre read model derivado**
3. **layout visual não é automatizado pelo copiloto**
4. **gateway complexo exige revisão humana**
5. **company_id é obrigatório em toda leitura**
6. **sugestão de automação não equivale a publicação**

## 3. Componentes oficiais

### 3.1 Parser de grafo BPMN
Arquivo:
- `C:\GestaoVersus\app32\app32\services\process_bpmn_graph_service.py`

Responsabilidade:
- parsear `bpmn_xml`;
- extrair nós, edges e lanes;
- identificar atividades executáveis, gateways e eventos;
- preparar metadados para análise MCP.

### 3.2 Serviço do copiloto de fluxo
Arquivo:
- `C:\GestaoVersus\app32\app32\services\process_flow_copilot_service.py`

Responsabilidade:
- cruzar BPMN com `ProcessRoutine` e `ProcessActivityExecutionContract`;
- calcular gaps de lane, POP e contrato;
- sugerir templates APP32;
- sugerir integrações externas;
- sugerir automações internas existentes.

### 3.3 Tooling MCP do copiloto
Arquivo:
- `C:\GestaoVersus\app32\app32\src\core\mcp_process_flow_tools.py`

Tools oficiais:
- `analyze_process_flow_copilot_tool`
- `suggest_process_flow_activity_automation_tool`

## 4. Read model derivado oficial

O copiloto deve operar sobre um grafo derivado com:

- `nodes`
- `edges`
- `lanes`
- `activities`
- `gateways`
- `events`

Cada atividade deve expor no mínimo:
- `element_id`
- `element_name`
- `element_type`
- `lane_name`
- `incoming_count`
- `outgoing_count`
- `has_pop`
- `current_contract`
- `automation_score`
- `automation_candidates`
- `integration_candidates`
- `warnings`

## 5. Regra oficial de automação

O copiloto pode sugerir:

- `human_task`
- `open_form`
- `open_app32_page`
- `mcp_task`
- `api_task`
- `ai_task`
- `ai_decision`

Mas **não pode**:
- publicar contrato automaticamente;
- assumir executor final apenas por texto de lane;
- reescrever layout do BPMN;
- fechar split/join ambíguo sem humano.

## 6. Regra oficial de intervenção humana

Intervenção humana é obrigatória quando houver:

- gateway com múltiplas saídas sem condição clara;
- mistura de fan-in e fan-out no mesmo gateway;
- atividade sem lane;
- atividade sem POP em fluxo crítico;
- proposta de integração externa sensível;
- impacto financeiro ou regulatório.

## 7. Decisão oficial sobre agentes

Não nasce agente novo nesta fase.

Responsabilidade oficial:
- `@ARQUITETO`: semântica BPMN, boundaries e governança;
- `@AI_ENGINEER`: copiloto MCP, heurísticas e sugestões;
- `@BACKEND_API`: surface, catálogo e contratos MCP.

## 8. Registro oficial em catálogo MCP

O catálogo MCP do projeto deve reconhecer a feature:
- `processos_copiloto_fluxo`

E as capabilities:
- `analyze_process_flow_copilot_tool`
- `suggest_process_flow_activity_automation_tool`

## 9. Ordem de evolução

1. leitura e análise do fluxo;
2. sugestões de automação/conexão;
3. rascunho de contrato de execução;
4. revisão humana;
5. publicação manual controlada.
