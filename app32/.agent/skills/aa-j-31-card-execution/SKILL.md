---
name: aa-j-31-card-execution
description: Use quando a execução tiver 3 ou mais etapas e precisar ser conduzida por passos com cards em AA.J.1 (Produção), executando, testando, corrigindo e concluindo um passo por vez.
---

# AA.J.1 Card Execution

Use esta skill quando a demanda exigir execução longa com 3 ou mais etapas.

## Obrigatório
- quebrar a execução em passos
- criar ou atualizar um card por passo em `AA.J.1 (Produção)` antes da execução
- nomear o card no padrão `[<nome da etapa> - Passo X de N]`
- executar um passo por vez
- testar e corrigir antes de avançar
- concluir o card atual antes do próximo

## Sequência curta
1. Definir a lista de passos
2. Criar os cards correspondentes
3. Executar o passo 1
4. Testar e corrigir
5. Concluir o card do passo 1
6. Repetir até o fim

## Integração real
- usar `scripts/aa_j_31_cards_ssh.py` para listar, criar, concluir ou materializar passos em `AA.J.1`
- o script opera via SSH no app.gestaoversus.com.br sobre `ProjectTask` do projeto `AA.J.1`
- usar `scripts/aa_j_31_step_wrapper.py` como entrada preferencial quando já existir uma lista explícita de passos da execução

## Regras
- não pular criação de card quando houver 3+ etapas
- não executar passos em lote sem fechamento intermediário
- se a tarefa tiver 1 ou 2 etapas, esta skill não é obrigatória
- se o acesso SSH não estiver disponível na sessão, preparar explicitamente a lista de cards antes de iniciar a execução

## Fluxo preferencial
1. materializar os passos com `aa_j_31_step_wrapper.py materialize`
2. executar apenas o passo atual
3. testar e corrigir
4. concluir o passo com `aa_j_31_step_wrapper.py complete-step`
5. consultar status com `aa_j_31_step_wrapper.py status` antes de avançar

## Referências
- `references/card-workflow.md`
- `references/remote-integration.md`
