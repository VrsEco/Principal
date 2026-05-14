# Paper Conceitual — Modo Conselho do Squad Cliente v1

Status: conceitual para amadurecimento  
Escopo: Squad Cliente, Sapiens Cliente, Agente Líder, deliberação multi-perspectiva e decisões de alto custo de erro

## 1. Objetivo

Explorar como o conceito de **Conselho de LLMs** pode ser aproveitado na arquitetura da Versus sem inflar artificialmente a malha de squads, agentes e harnesses.

Este paper não cria ainda:
- novo agente oficial
- novo harness oficial
- nova surface
- novo contrato operacional definitivo

Ele existe para amadurecer a decisão sobre:
- papel do conselho
- gatilhos de ativação
- relação com o Agente Líder
- relação com `Sapiens Cliente`
- impactos futuros em SPEC, playbook, runbook e harness

---

## 2. Tese central

O **Conselho** deve ser tratado como um **modo especial de deliberação**, e não como:
- novo squad
- novo conjunto fixo de agentes permanentes
- substituto do Coordenador
- rotina padrão de toda conversa

### Tese resumida
> No Squad Cliente, o Conselho deve funcionar como protocolo de análise multi-perspectiva acionado pelo **Agente Líder / Coordenador** quando houver incerteza real e alto custo de erro.

---

## 3. Problema que o Conselho resolve

No uso normal do Squad Cliente, uma única resposta pode ser suficiente para:
- consulta factual
- rotina simples
- direcionamento operacional
- execução assistida direta

Mas existe uma classe de perguntas em que:
- há mais de um caminho plausível
- a escolha errada custa caro
- existe conflito entre downside e upside
- a visão única do agente pode ocultar um ponto cego importante

Exemplos:
- contratar ou automatizar primeiro
- mudar preço ou manter preço
- reorganizar operação ou ampliar comercial
- decidir entre foco em venda, execução ou caixa

O Conselho surge como resposta para esse tipo de deliberação.

---

## 4. Enquadramento arquitetural correto

## 4.1 O Conselho não é um novo squad

Os squads oficiais continuam sendo:
- `Squad Cliente`
- `Squad Versus`
- `Squad de Engenharia`

O Conselho não substitui essa estrutura.

## 4.2 O Conselho não é um agente oficial permanente

Os agentes do `Squad Cliente` continuam sendo definidos por função de negócio:
- Líder / Coordenador
- Comercial
- Operacional
- Administrativo / Financeiro

O Conselho não deve gerar cinco novos “agentes bonitos de prompt” para sempre.

## 4.3 O Conselho é um protocolo especial de deliberação

O enquadramento recomendado é:
- **agente** = papel funcional
- **harness** = invólucro operacional
- **conselho** = protocolo especial de decisão

---

## 5. Posição do Conselho dentro do Squad Cliente

O melhor ponto de ancoragem do Conselho é o **Agente Líder / Coordenador do Squad Cliente**.

### Papel do Líder
O Líder deve:
- receber a demanda
- classificar o tipo de problema
- decidir se a resposta é simples, operacional ou deliberativa
- convocar o Conselho quando necessário
- sintetizar e devolver clareza ao usuário
- despachar eventual execução posterior para Comercial, Operacional ou Adm/Financeiro

### Conclusão
> O Conselho deve ser um modo do Líder, não um concorrente do Líder.

---

## 6. Quando o Conselho deve rodar

## 6.1 Situações adequadas

O Conselho deve ser usado quando houver:
- alto custo de erro
- múltiplos caminhos plausíveis
- dúvida estratégica real
- conflito entre áreas
- necessidade de ponderar risco, upside, clareza e executabilidade

### Exemplos adequados
- “Devo contratar alguém ou automatizar primeiro?”
- “Devo manter este preço ou mudar a proposta?”
- “Esse processo deve ser simplificado ou aprofundado?”
- “Vale priorizar venda, operação ou caixa agora?”

## 6.2 Situações inadequadas

O Conselho não deve ser usado para:
- perguntas factuais
- resumo
- execução direta
- tarefas mecânicas
- triagem simples
- rotina sem trade-off relevante

### Regra prática
Se a resposta depende mais de **julgamento** do que de **consulta**, o Conselho pode fazer sentido.

---

## 7. As cinco lentes recomendadas

O Conselho deve operar por **lentes de pensamento**, e não por cargos permanentes.

## 7.1 Lente Contrária
Procura:
- falhas
- risco oculto
- premissa fraca
- downside ignorado

## 7.2 Lente de Primeiros Princípios
Procura:
- problema real por trás da pergunta
- suposições escondidas
- enquadramento correto

## 7.3 Lente Expansionista
Procura:
- upside subestimado
- oportunidade adjacente
- possibilidade de ganho maior

## 7.4 Lente Forasteira
Procura:
- confusão
- excesso de jargão
- maldição do conhecimento
- o que não está claro para alguém de fora

## 7.5 Lente Executora
Procura:
- caminho prático
- próxima ação viável
- concretude
- o que acontece na segunda-feira de manhã

## 7.6 Síntese do Presidente
Integra:
- convergências
- tensões
- pontos cegos
- recomendação final
- primeiro passo único

---

## 8. Benefícios esperados

Se bem aplicado, o Conselho pode:
- reduzir decisões frágeis baseadas em uma única leitura
- aumentar qualidade de decisões comerciais e operacionais relevantes
- expor pontos cegos antes da execução
- melhorar a clareza entregue ao cliente
- reforçar o valor do `Sapiens Cliente` como copiloto de gestão

---

## 9. Riscos se o Conselho for mal desenhado

## 9.1 Virar rotina padrão
Se tudo virar Conselho:
- a UX fica lenta
- o custo sobe
- o sistema perde objetividade

## 9.2 Inflar a arquitetura
Se cada lente virar agente fixo:
- aumenta complexidade desnecessária
- confunde papel funcional com estilo cognitivo
- piora a governança

## 9.3 Gerar falsa sofisticação
Cinco vozes não garantem verdade.

Sem bom enquadramento, o Conselho pode produzir apenas:
- verbosidade
- teatro de análise
- sensação de rigor sem ganho real

## 9.4 Falhar em auditabilidade
Se não houver trilha clara de:
- pergunta enquadrada
- contexto usado
- lentes acionadas
- síntese final

o Conselho vira caixa-preta.

---

## 10. Relação com Sapiens Cliente

No contexto do cliente, o Conselho deve ser lido como parte da experiência do **Sapiens Cliente**.

### Leitura correta
- `Sapiens Cliente` = front door / experiência
- `Squad Cliente` = família canônica
- `Agente Líder` = orquestrador da conversa
- `Conselho` = modo especial de deliberação

### Consequência
O usuário não precisa entender a estrutura interna.

Para ele, a experiência pode ser simplesmente:
- “convocar conselho”
- “analisar melhor essa decisão”
- “quero uma recomendação mais criteriosa”

---

## 11. Relação com os demais especialistas

Após a deliberação:
- o `Agente Comercial` pode executar o desdobramento comercial
- o `Agente Operacional` pode executar o desdobramento operacional
- o `Agente Adm/Financeiro` pode organizar o desdobramento administrativo/financeiro

Ou seja:
> o Conselho decide melhor; os especialistas executam melhor.

---

## 12. Relação com Squad Versus e Engenharia

## 12.1 Escalonamento para Squad Versus
O Conselho pode concluir que a decisão:
- saiu do nível operacional local
- exige visão consultiva mais profunda
- envolve governança, estratégia ou controladoria além do escopo do cliente

Nesses casos, o Líder deve escalar para `Squad Versus`.

## 12.2 Escalonamento para Engenharia
O Conselho pode identificar que o problema:
- não é de gestão
- não é de decisão operacional
- é limitação técnica, defeito, integração ou arquitetura

Nesses casos, o Líder deve escalar para `Squad de Engenharia`.

---

## 13. Hipótese de ativação operacional

Uma hipótese forte para implementação futura é:

### Modo normal
- triagem
- resposta direta
- roteamento simples
- execução assistida

### Modo Conselho
- enquadramento da decisão
- deliberação multi-perspectiva
- síntese presidencial
- recomendação clara

---

## 14. Saída ideal do Conselho

O formato final recomendado é:
- onde o conselho concorda
- onde o conselho se choca
- pontos cegos identificados
- recomendação
- única coisa a fazer primeiro

Esse formato é superior a:
- relatório longo
- múltiplas sugestões sem priorização
- resposta ambígua

---

## 15. Questões ainda em aberto

Este paper ainda não fecha:

1. quais gatilhos serão automáticos e quais serão explícitos
2. se o Conselho terá limite de custo/frequência por usuário
3. como será a telemetria formal da deliberação
4. como será a persistência da transcrição
5. se o Conselho será primeiro exclusivo do `Squad Cliente` ou nascerá já como padrão extensível para `Squad Versus` e `Squad de Engenharia`

---

## 16. Recomendação atual

A recomendação atual deste paper é:

1. **não** transformar o Conselho em novos agentes permanentes
2. tratá-lo como **protocolo especial de deliberação**
3. ancorá-lo no **Agente Líder / Coordenador do Squad Cliente**
4. usá-lo apenas em decisões com incerteza real e alto custo de erro
5. amadurecer isso primeiro como **Paper**, antes de congelar em SPEC

---

## 17. Próximo passo recomendado

Se esta direção continuar fazendo sentido, o próximo passo é produzir:

- uma **SPEC oficial do Modo Conselho**
- um **Playbook do Modo Conselho do Squad Cliente**
- uma **matriz de ativação do Conselho**
- uma **matriz de autonomia e escalonamento associada**

Mas isso só deve acontecer depois do amadurecimento suficiente deste paper.
