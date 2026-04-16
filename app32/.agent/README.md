# Arquitetura de Agentes e Skills — Gestão Versus

Esta pasta agora separa explicitamente:

- `router/`: decisão e roteamento
- `agents/`: papéis especialistas curtos
- `skills/`: workflows reutilizáveis do núcleo ativo
- `references/`: documentação consultiva, checklists e políticas
- `scripts/`: validações e automações operacionais
- `vendor-skills/`: catálogo externo/legado isolado do contexto padrão
- `archive/`: histórico e artefatos antigos fora do fluxo ativo

## Regra central
O arquivo `skills/gestao_versus_core/SKILL.md` permanece como ponto de entrada obrigatório, mas agora atua apenas como plano de controle curto. A governança detalhada foi extraída para `router/` e `references/`.

## Ordem de consulta
1. `skills/gestao_versus_core/SKILL.md`
2. `router/orchestrator.md`
3. `router/routing-matrix.md`
4. `agents/<papel>.md`
5. `references/<tema>.md`

## Política de contexto
- Não carregar `vendor-skills/` por padrão.
- Não carregar `archive/` por padrão.
- Não colocar checklists longos em agentes.
- Não colocar documentação longa em skills.
- Não duplicar regras entre skill, agente e referência.
