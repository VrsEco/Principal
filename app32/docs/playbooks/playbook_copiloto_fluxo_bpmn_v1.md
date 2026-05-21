# Playbook — Copiloto de Fluxo BPMN

Classe: Playbook

## 1. Quando usar

Use este playbook quando o pedido envolver:
- análise de fluxo BPMN;
- descoberta de automação por atividade;
- sugestão de conexão APP32/MCP/API;
- revisão de gaps entre lane, POP e contrato.

## 2. Sequência oficial

1. carregar processo e diagrama no tenant correto;
2. analisar lanes, atividades e gateways;
3. identificar POPs e contratos já existentes;
4. propor automação/conexão por atividade;
5. sinalizar explicitamente o que ainda depende de revisão humana.

## 3. Regra de resposta

Sempre separar em quatro blocos:
- diagnóstico do fluxo;
- oportunidades de automação APP32;
- oportunidades de integração externa;
- pendências de intervenção humana.

## 4. Regra de linguagem

Nunca apresentar sugestão como fato consumado.

Preferir expressões como:
- “o copiloto recomenda”
- “há aderência para”
- “o contrato rascunho sugerido é”
- “a publicação continua dependendo de validação humana”

## 5. Escalonamento interno

- semântica BPMN/gateway -> `@ARQUITETO`
- sugestão IA/MCP/API -> `@AI_ENGINEER`
- surface/capability/permissão -> `@BACKEND_API`

## 6. O que não fazer

- não automatizar layout fino;
- não publicar contrato sem humano;
- não ocultar risco de gateway;
- não usar lane como única verdade de executor real.
