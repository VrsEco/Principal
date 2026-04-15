# Sapiens Factory Assistant

## Objetivo
Estabelecer o **Sapiens Factory** como assistente oficial de evolução técnica controlada do APP32.

## Regra canônica
`Service -> Tool + contrato -> REST/MCP -> Workflow -> UI/Sapiens`

## Papel da LLM
- interpretar a linguagem natural;
- ajudar na classificação e no plano;
- **não** substituir governança, RBAC, tenant-scope ou execução determinística.

## Modos operacionais
- `diagnose`
- `plan`
- `prepare`
- `execute_controlled`

## Guardrails
- tenant-scope obrigatório;
- RBAC obrigatório;
- trilha de auditoria em toda operação;
- human gate obrigatório para ativar/desativar e para risco alto.

## Casos de uso iniciais
- corrigir workflow;
- melhorar cognição do Sapiens;
- criar nova capacidade ponta a ponta;
- corrigir tool existente.
