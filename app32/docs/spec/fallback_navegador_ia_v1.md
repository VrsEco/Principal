# SPEC — Fallback via Navegador para Agentes de IA v1

**Status:** vigente
**Classe:** SPEC
**Escopo:** agentes (Squad Cliente, Squad Versus, Squad Engenharia, Sapiens) que atuam no APP32/Gestão Versus via MCP e, quando aplicável, via navegador autenticado como o usuário.

## Decisão

MCP é o canal preferencial e obrigatório para qualquer ação operacional sempre que existir tool publicada (princípio MCP First já vigente). O navegador (Chrome ou navegador integrado, autenticado como o usuário) só pode ser usado como **fallback pontual**, nunca como substituto permanente de uma tool MCP ausente, e nunca para contornar um gate já modelado numa tool MCP existente.

Esta SPEC formaliza o critério decidido por Fabiano Diretor e ratificado pelo Squad Versus em 2026-09-27, originado da pendência de atualização do card `AA.J.23.1` no Sapiens (domínio `projects` do conector `mcp-versus` só expõe leitura, sem mutação).

## Por que o navegador não é equivalente ao MCP

Uma chamada MCP tem, por construção: RBAC revalidado a cada chamada, `company_id` obrigatório, `human_gate` seletivo por capability, validação de schema antes da mutação, e trilha de auditoria que distingue o ator (humano vs. agente) por identidade autenticada.

Uma ação via navegador roda com **toda a permissão da sessão humana logada**, sem diferenciação de risco por ação, sem `human_gate` seletivo, e sem trilha de auditoria que distinga IA de humano no log da aplicação. Além disso, um clique de UI não passa pela mesma validação de schema que uma tool MCP aplica antes de mutar — um erro de seletor ou de estado de tela pode mutar o registro errado sem a mesma proteção prévia (irreversibilidade sem dry-run).

## Regras normativas

1. **Precedência**: se existe tool MCP para a ação, ela é sempre usada — o navegador nunca é escolha preferencial.
2. **Condição de ativação do fallback**: o navegador só pode ser usado quando o MCP retornar erro, ou quando não houver tool configurada para a ação necessária.
3. **Nunca em lote**: uma ação via navegador exige uma confirmação humana explícita — nunca aprovação antecipada para várias ações de uma vez, mesmo quando relacionadas (ex.: preencher um formulário ainda exige confirmação por campo/submit, não por tela inteira).
4. **Gate já modelado nunca é contornado**: se uma mutação sensível já tem `human_gate=True` numa tool MCP existente, ela nunca é executada via navegador como atalho.
5. **Registro obrigatório**: toda ação feita via navegador deve ser registrada explicitamente (ex.: no handoff da tarefa) como "feito via navegador, não MCP", para não confundir trilha de auditoria futura com uma mutação MCP real.
6. **Regra anti-repetição (evitar que o fallback vire hábito permanente)**: todo uso do fallback via navegador gera um item de backlog obrigatório para criar ou expandir a tool MCP equivalente. A mesma ação só pode repetir o fallback via navegador **uma única vez** antes de exigir avanço desse item de backlog — na terceira necessidade da mesma ação, o fallback é bloqueado até a tool MCP existir.

## Preservação de qualidade

Esta SPEC não flexibiliza `company_id`, RBAC, isolamento por tenant, nem qualquer gate humano já existente em tool MCP. Fallback via navegador é uma válvula de escape pontual para gaps de cobertura MCP, não uma segunda via de execução permanente.

## Adoção

Referenciada por `app32/docs/papers/paper_manual_unificado_utilizacao_ia_usuario_app32_mcp_v1.md`, seção 9 (item 9.3) — o paper não duplica o texto normativo desta SPEC, apenas aponta para ela, conforme `politica_orcamento_contexto_v1.md` (evitar duplicar regra em múltiplos documentos).
