---
name: aa-j-31-card-execution
description: Use quando a execução tiver 3 ou mais etapas e precisar ser conduzida por passos com cards em AA.J.31 (Produção), executando, testando, corrigindo e concluindo um passo por vez.
---

# AA.J.31 Card Execution

Use esta skill quando a demanda exigir execução longa com 3 ou mais etapas.

## Obrigatório
- quebrar a execução em passos
- criar ou atualizar um card por passo em `AA.J.31 (Produção)` antes da execução
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

## Regras
- não pular criação de card quando houver 3+ etapas
- não executar passos em lote sem fechamento intermediário
- se a tarefa tiver 1 ou 2 etapas, esta skill não é obrigatória
- se não houver integração disponível com o sistema de cards na sessão, preparar explicitamente a lista de cards antes de iniciar a execução

## Referência
- `references/card-workflow.md`
