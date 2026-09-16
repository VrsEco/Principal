# Manifesto — Identidade única e operação MCP governada

**Classe documental:** Manifesto  
**Status:** vigente  
**Data:** 2026-09-16

## Compromisso

O APP32 reconhece a pessoa uma única vez. Ela pode trabalhar pela interface,
por um CLI ou por uma IA conectada, mas sua identidade, vínculos empresariais e
responsabilidade permanecem as mesmas.

## Princípios

1. OAuth prova identidade; o APP32 decide autorização de negócio.
2. Nenhum token, e-mail ou `company_id` fornecido pelo cliente cria acesso.
3. Todo dado empresarial é revalidado por `company_id`, grant e policy a cada
   chamada MCP.
4. A surface `user` é a menor superfície necessária; ela não é atalho para
   finanças sensíveis, administração ou análise privilegiada.
5. `mcp_permissions` só pode reduzir um acesso já existente no APP32; nunca
   elevá-lo.
6. A IA pode explicar, preparar e solicitar confirmação; não pode contornar
   gates, auditoria ou autorização do servidor.
7. O nome público é `mcp-versus`; client OAuth, role e tenant são conceitos
   distintos e nunca devem ser confundidos.

## Resultado esperado

Usuário, CLI e APP32 trabalham juntos, com conveniência na experiência e
decisão de acesso centralizada, rastreável e revogável no servidor.
