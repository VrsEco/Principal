# External LLM Factory Surface

## Objetivo
Permitir que clientes como Codex/CLI e outras LLMs externas usem a **Sapiens Factory** via MCP/API sem consumir os tokens internos do APP32.

## Estratégia atual
**Uma surface única focada na Factory, preparada para split futuro.**

## Evolução prevista
### Fase atual
- diagnóstico;
- discovery;
- avaliação de risco;
- preparação de plano.

### Fase futura
- financeiro;
- rotina;
- planejamento;
- processos;
- analytics.

## Decisão arquitetural
Não separar em duas surfaces agora.  
Separar depois em:
- `factory surface`
- `operations surface`

quando houver diferença suficiente de política, risco e catálogo.

## Guardrails
- sem acesso direto ao banco por LLM externa;
- APP32 continua validando identidade, `company_id`, RBAC e human gate;
- contratos devem permanecer estáveis durante a separação futura.
