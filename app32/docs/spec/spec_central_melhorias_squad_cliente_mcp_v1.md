# SPEC — Central de Melhorias e Diagnósticos via Squad Cliente

## Classificação

`SPEC`

## Decisão

A antiga tela de Análise BPMS passa a operar como Central de Melhorias e Diagnósticos. A interface registra um briefing curto e mantém o histórico; o Squad Cliente investiga o contexto autorizado via MCP e devolve uma sugestão estruturada para revisão humana.

## Contrato funcional

1. O usuário registra problema, oportunidade ou melhoria, resultado esperado, evidências e processo opcional.
2. A solicitação nasce com status `queued` e permanece vinculada ao `company_id` ativo.
3. O Squad Cliente lista as solicitações e obtém o contexto estruturado pelas tools MCP do domínio canônico `processes`.
4. Fatos, inferências, lacunas e recomendações devem ser diferenciados.
5. A gravação do resultado exige gate humano explícito.
6. A tela apresenta briefing, andamento e recomendações sem executar mudanças automaticamente.

## Tools MCP

- `list_process_improvement_requests_tool`: leitura tenant-safe do repositório.
- `get_process_improvement_analysis_context_tool`: briefing e contrato esperado da análise.
- `submit_process_improvement_analysis_tool`: persistência do resultado com confirmação humana.

## Estados

`draft`, `queued`, `analyzing`, `needs_input`, `ready`, `approved`, `archived`.

## Guardrails

- Toda leitura e escrita é escopada por `company_id`.
- A surface `user` não recebe acesso financeiro sensível nem SQL livre.
- Prompt textual é detalhe interno; o contrato persistente é estruturado.
- Recomendações não geram cards, projetos ou mutações operacionais sem decisão humana posterior.
