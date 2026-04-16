# Extensão Sapiens Workflow-First

## Quando usar junto da factory
Use esta extensão quando o workflow V3 também for um fluxo conversacional do Sapiens em web/WhatsApp.

## Acréscimos obrigatórios
1. Definir a intenção canônica
2. Mapear entidade, período, status, escopo e empresa explícita
3. Decidir se o fluxo é:
   - consulta determinística
   - mutação determinística
   - wizard
   - fallback agentic
4. Definir payload mínimo com hidratação de sessão
5. Definir política de confirmação
6. Definir comportamento por canal externo

## Checklist complementar
- a pergunta livre cai em workflow antes de LLM?
- a empresa explícita tem precedência sobre a empresa ativa?
- o fluxo funciona sem `current_user`?
- a sessão pendente sabe continuar, resetar ou desambiguar?
- o usuário informa apenas o indispensável?
- a resposta final é operacional e curta?

## Artefatos esperados
- heurística/intenção no `menu_engine.py` ou camada equivalente
- metadados de tool/fluxo claros para confirmação
- testes de conversa por canal
- evidência de que consulta simples não abriu wizard executivo
