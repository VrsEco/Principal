# Método BPMN da Metodologia Versus

## 1. Contrato antes do desenho

Não iniciar pelo canvas. Confirmar objetivo, fronteira, gatilho, entradas, saída, recebedor, responsável único, times executores, exceções e encerramento. Se não estiverem claros, retornar à arquitetura do processo.

## 2. Tradução para BPMN

| Conceito Versus | Representação preferencial |
|---|---|
| Gatilho | evento de início simples, mensagem, tempo ou condição |
| Time ou papel executor | lane; pool separado apenas para participante independente |
| Microentrega executável | task com código e nome concreto |
| Decisão | gateway com pergunta e saídas rotuladas |
| Espera relevante | evento intermediário apropriado |
| Saída entregue | evento de fim com resultado explícito |
| Documento/dado relevante | data object ou artefato APP32 associado |

Usar `userTask` para trabalho humano assistido por sistema, `manualTask` para trabalho humano fora do sistema, `serviceTask` somente com execução automática definida e `sendTask`/`receiveTask` quando a mensagem for a própria atividade.

## 3. Responsabilidade

O responsável pelo processo responde pelo resultado ponta a ponta e permanece metadado do processo. A lane informa quem executa a atividade. Uma lane “todos” só é válida quando não elimina accountability.

## 4. POP seletivo e compartilhado

Criar POP quando risco, conformidade, qualidade, baixa frequência, treinamento ou alta variabilidade exigirem passos prescritos. Não criar POP para atividade autoexplicativa e de baixo impacto.

Quando várias atividades usarem a mesma instrução:

```text
POP — <código atividade 1> - <nome 1> | <código atividade 2> - <nome 2> | ...
```

Os vínculos apontam para a mesma definição de POP. Não duplicar conteúdo para satisfazer limitação de interface.

## 5. Rotina e indicadores

- A rotina declara quando o processo é disparado: periodicidade, evento, demanda ou condição.
- O evento de início expressa o gatilho operacional quando isso melhorar a leitura.
- Indicadores medem o processo ou uma entrega relevante; preferir poucos indicadores de resultado e controle.
- Atividade sem indicador próprio não constitui gap.

## 6. Qualidade

Validar ids únicos; códigos coerentes; caminhos completos entre início e fim; gateways claros; loops compreensíveis; tarefas automáticas com contrato; raias sem substituir o responsável; POPs, rotinas e indicadores por necessidade; leitura simples do diagrama.

