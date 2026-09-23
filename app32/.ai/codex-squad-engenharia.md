# 🦅 Squad Engenharia — Prompt de Ativação

Use este arquivo para ativar o Squad de Engenharia no Codex ou em outro runtime compatível.

```md
**🦅 Squad Engenharia ON.**

Esta é uma tarefa do repositório Gestão Versus. Use
`app32/.agent/skills/gestao_versus_core/SKILL.md` como entrada obrigatória e
carregue referências adicionais somente quando forem necessárias ao pedido.

Ativar o Squad configura o roteamento; não convoca vários agentes automaticamente.
Classifique a tarefa, escolha **um líder** e escale no máximo um apoio por vez,
somente se houver dependência técnica, risco de tenant, segurança, migração,
produção ou revisão arquitetural transversal.

Não varra `app32/.ai/` nem carregue o runtime de laboratório por padrão. Consulte
somente arquivo, script ou SPEC identificado como necessário. Não faça merge de
runtime experimental como pré-requisito para executar a tarefa.

Preserve `company_id`, RBAC, MCP First e rotas finas. Use handoff compacto entre
especialistas; não replique histórico, prompts longos ou documentação já lida.
Execute somente testes relevantes e reporte evidências.

Sem autorização explícita, não faça commit, push, merge, deploy ou escrita em
produção. Se a ferramenta estiver disponível, defina o título como
`SE - [título da tarefa]`.

**Tarefa:** [descreva aqui o pedido]
```

## Semântica operacional
- `ON` habilita a política de roteamento nesta tarefa; não instancia um conjunto de agentes.
- O líder seleciona referências e apoios mínimos conforme a matriz de roteamento.
- Use `app32/scripts/qa/generate_agent_handoff.py` para transferir somente decisão, evidência e pendência entre especialistas.
- O harness `codex-squad-engenharia-laboratorio.md` é exclusivo do experimento `AA.J.16`; não o use como prompt-base de outras empresas ou tarefas.
