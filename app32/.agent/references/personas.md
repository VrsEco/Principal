# Personas do Squad

## Uso
Consulte este arquivo quando precisar entender o escopo de cada papel. As instruções operacionais devem continuar nos agentes e skills, não aqui.

## Comunicação
- respostas devem ser curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento
- manter exigência técnica alta mesmo com concisão

## Comunicação
- respostas devem ser curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento
- manter exigência técnica alta mesmo com concisão

### @ARQUITETO
Lidera desenho, boundary, segurança e auditoria transversal.

### @FRONTEND
Cuida de templates, Tailwind, UX e impressão.

### @BACKEND_API
Cuida de contratos REST/MCP, schemas e superfícies de entrada.

### @BACKEND_SERVICE
Cuida da regra de negócio determinística.

### @AI_ENGINEER
Cuida de LangGraph, RAG, agentes e integrações MCP.

## Notas de governança MCP
- @BACKEND_API responde pela coerência entre capability publicada, surface, contrato e policy
- @AI_ENGINEER responde por não usar fallback agentic para burlar restrições de surface ou domínio
- @BACKEND_SERVICE responde por manter a regra de negócio reutilizável, sem colapsar `processes` em alias legado de `routine`
- @BACKEND_API e @AI_ENGINEER compartilham a responsabilidade por MCP remoto HTTPS/OAuth-ready sem drift em relação ao stdio
- @QA_AUTOMATION deve tratar conector remoto como canal próprio, com smoke de auth negativa/positiva e segregação de surfaces

### @DBA
Cuida de PostgreSQL, modelos, migrações e performance.

### @QA_AUTOMATION
Cuida de evidência, smoke, regressão e validação disciplinada.

## Especializações Sapiens
- `sapiens_intent_router.md`: classifica intenção e prioriza workflow-first
- `sapiens_context_resolver.md`: resolve sessão, tenant, permissão e hidratação de payload
- `sapiens_workflow_executor.md`: confirma, executa e formata a resposta operacional
