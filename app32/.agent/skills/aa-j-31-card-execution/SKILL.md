---
name: aa-j-31-card-execution
description: Use quando a execução tiver 3 ou mais etapas e precisar de um card único por entrega, com checklist, evidências e conclusão somente após a validação final.
---

# Card Execution por Entrega

Use esta skill quando a demanda exigir execução longa com 3 ou mais etapas.

## Obrigatório
- quebrar a execução em passos
- criar ou atualizar um único card por entrega no projeto operacional vigente antes da execução
- nomear o card no padrão `[<nome da entrega>]`
- registrar todos os passos como checklist nas notas do card
- executar um passo por vez
- testar e corrigir antes de avançar
- registrar evidência ao concluir cada passo
- concluir o card somente depois do último passo e da validação final

## Sequência curta
1. Definir a lista de passos
2. Criar ou reutilizar o card único da entrega com o checklist correspondente
3. Executar o passo 1
4. Testar e corrigir
5. Atualizar o checklist e anexar a evidência do passo 1
6. Repetir até o fim e concluir o card da entrega

## Integração real
- usar `scripts/aa_j_31_cards_ssh.py` para listar, criar, atualizar ou concluir o card da entrega
- o script opera via SSH no app.gestaoversus.com.br sobre `ProjectTask` do projeto `AA.J.1`
- usar `scripts/aa_j_31_step_wrapper.py` como entrada preferencial quando já existir uma lista explícita de passos da execução

## Regras
- não pular criação do card da entrega quando houver 3+ etapas
- não criar cards separados para passos da mesma entrega
- não executar passos em lote sem evidência intermediária no checklist
- se a tarefa tiver 1 ou 2 etapas, esta skill não é obrigatória
- se o acesso SSH não estiver disponível na sessão, preparar explicitamente a lista de cards antes de iniciar a execução

## Fluxo preferencial
1. materializar o card e o checklist com `aa_j_31_step_wrapper.py materialize`
2. executar apenas o passo atual
3. testar e corrigir
4. registrar o passo com `aa_j_31_step_wrapper.py complete-step`
5. consultar status com `aa_j_31_step_wrapper.py status` antes de avançar

## Referências
- `references/card-workflow.md`
- `references/remote-integration.md`
