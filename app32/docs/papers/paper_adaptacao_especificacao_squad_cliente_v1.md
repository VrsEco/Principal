# Paper de Adaptação da Especificação do Squad Cliente v1

Status: conceitual para amadurecimento e fatiamento incremental dos agentes  
Origem base: `C:\Users\mff20\Downloads\squad-cliente-spec-v1.docx`  
Escopo: `Squad Cliente`, `Sapiens Cliente`, `SC-COORD`, `SC-COM`, `SC-OPS`, `SC-ADM`, economia de tokens, MCP e governança operacional

## 1. Objetivo

Adaptar a especificação-base recebida para a realidade arquitetural do APP32 / Gestão Versus, preservando o que está forte no documento e ajustando o que precisa aderir a:

- `MCP First`
- `company_id` obrigatório
- separação entre `Sapiens`, `Squad`, `Agente` e `Harness`
- operação prioritária em runtime/CLI do cliente
- governança por surface
- human gate
- trilha auditável
- economia de tokens como princípio de desenho

---

## 2. Leitura geral da especificação recebida

A especificação recebida está **boa e madura como base funcional inicial**.

### Pontos fortes do documento
- define com clareza os quatro agentes iniciais:
  - `SC-COORD`
  - `SC-COM`
  - `SC-OPS`
  - `SC-ADM`
- separa corretamente:
  - `Agente`
  - `Harness`
  - `Sapiens Cliente`
- posiciona corretamente o `APP32` como:
  - domínio
  - dados
  - services
  - MCP
  - governança
- posiciona corretamente o `Coordenador` como porta de entrada
- define bem as fronteiras iniciais do `SC-ADM`
- define bem a lógica de handoff entre especialistas

### Veredito
> A estrutura-base do documento pode ser aproveitada. O trabalho principal não é recomeçar do zero, e sim adaptar e calibrar.

---

## 3. Adaptação necessária para a realidade da Versus

## 3.1 O documento precisa ser lido como arquitetura em camadas

Para a realidade do APP32, a leitura correta é:

- `Sapiens Cliente` = nome de experiência / front door
- `Squad Cliente` = família canônica
- `Agentes` = papéis de negócio
- `Harnesses` = invólucros operacionais

### Regra
O texto da especificação não deve colapsar essas quatro camadas em uma coisa só.

---

## 3.2 O `Sapiens Cliente` precisa permanecer como experiência, não como agente

A especificação recebida já aponta isso corretamente, e essa decisão deve ser preservada:

- `Sapiens Cliente` **não** é um agente único
- `Sapiens Cliente` é a experiência de entrada do `Squad Cliente`

### Consequência
Toda evolução dos agentes deve manter:

- experiência simples para o usuário
- arquitetura explícita por baixo

---

## 3.3 O `SC-COORD` precisa nascer como agente econômico, não como superagente caro

O maior ajuste que precisamos fazer na adaptação é este:

> O `SC-COORD` não pode virar um orquestrador pesado que dispara múltiplos especialistas para tudo.

### Regra de desenho
O coordenador deve operar em três níveis:

1. **Resposta direta simples**
   - quando a demanda é clara, factual ou trivial
   - sem acionar especialista

2. **Delegação simples**
   - quando há domínio inequívoco
   - aciona um único especialista

3. **Orquestração multiagente**
   - apenas quando a demanda é genuinamente multi-domínio ou de alto impacto

### Regra de economia
O default deve ser:
- **menos agentes**
- **menos rodadas**
- **menos contexto**
- **mais objetividade**

---

## 4. Princípio novo e obrigatório: economia de tokens

## 4.1 Regra geral

Para a realidade da Versus, os agentes do `Squad Cliente` devem obedecer ao princípio:

> **resolver o máximo com o menor custo cognitivo e computacional possível, sem sacrificar segurança nem qualidade mínima necessária.**

### Isso significa
- não usar conselho por padrão
- não disparar múltiplos especialistas por reflexo
- não fazer análise longa para demanda simples
- não puxar contexto demais sem necessidade
- não transformar toda consulta em relatório

---

## 4.2 Exceção formal

O único squad que **não** deve seguir essa premissa como prioridade principal é:

- `Squad de Engenharia`

### Justificativa
No `Squad de Engenharia`, a prioridade é:
- excelência
- profundidade
- confiabilidade técnica
- investigação mais rigorosa

Mesmo ali, eficiência continua desejável, mas **não** no custo de qualidade.

---

## 4.3 Consequências práticas para o Squad Cliente

### O que evitar
- multiagente em toda conversa
- sumarizações excessivas
- análise consultiva pesada para rotina operacional
- rodadas de revisão para tarefas simples
- uso do `Modo Conselho` sem alta relevância

### O que priorizar
- classificação rápida
- resposta enxuta
- uso de um único especialista quando possível
- context window pequena e direcionada
- estruturas de saída curtas e acionáveis

---

## 5. Como essa economia de tokens deve aparecer nos agentes

## 5.1 SC-COORD

### Adaptação recomendada
O `SC-COORD` deve nascer com política explícita de:

- `minimal routing`
- `single-specialist first`
- `direct answer when safe`
- `multi-specialist only when justified`

### Regra operacional
Se a demanda puder ser resolvida com:
- uma resposta curta
- uma consulta simples
- um único especialista

o `SC-COORD` **não** deve expandir a execução.

---

## 5.2 SC-COM

### Adaptação recomendada
O `SC-COM` precisa ser forte, mas sem virar consultor estratégico profundo por padrão.

Ele deve priorizar:
- carteira
- funil
- propostas
- negociação
- rentabilidade comercial
- contexto de mercado do cliente

Mas deve evitar:
- derivar para revisão metodológica pesada
- disparar análises amplas sem necessidade

### Regra
No dia a dia, o `SC-COM` deve atuar mais como:
- analista comercial operacional
- preparador de contexto
- copiloto de ação

e menos como:
- estrategista consultivo profundo por default

---

## 5.3 SC-OPS

### Adaptação recomendada
O `SC-OPS` tende naturalmente a ser o agente mais econômico do squad.

Ele deve continuar sendo:
- prático
- objetivo
- orientado a próxima ação
- pouco verboso

### Regra
O `SC-OPS` deve sempre preferir:
- lista curta
- prioridade clara
- próxima ação concreta

em vez de:
- análise longa
- reflexão excessiva
- contextualização desnecessária

---

## 5.4 SC-ADM

### Adaptação recomendada
O `SC-ADM` deve ser conservador em **autonomia** e também em **expansão de contexto**.

Como lida com dados sensíveis, ele deve:
- mostrar só o necessário
- responder só ao contexto pedido
- evitar exposição ampla de informação financeira
- escalar cedo quando houver risco

### Regra
Aqui economia de tokens e economia de exposição andam juntas.

---

## 6. Ajustes arquiteturais importantes na especificação recebida

## 6.1 Surface precisa aparecer de forma mais canônica

O documento fala bem de CLI/runtime, mas na nossa realidade precisamos explicitar melhor:

- `Squad Cliente` opera prioritariamente sobre `surface user`
- não deve carregar mutação financeira sensível
- não deve usar `admin`, `analytics` ou `ops` como atalho

### Consequência
O `SC-ADM` precisa ser lido como:
- organizador financeiro assistido
- leitor operacional seguro
- escalador de temas sensíveis

e não como operador financeiro pleno.

---

## 6.2 O `Modo Conselho` não pode virar comportamento padrão do Líder

O `SC-COORD` pode futuramente acionar o `Modo Conselho`, mas isso deve ser:

- raro
- justificado
- associado a alto custo de erro

### Regra
`Modo Conselho` é protocolo especial.  
Não é rotina do coordenador.

---

## 6.3 O documento ainda deve ser lido como fase 1

A especificação recebida está ótima para a **família inicial** do `Squad Cliente`.

Mas, para a Versus, o correto é ler isso como:

- **fase 1 oficial**

e não como desenho final completo.

### Em aberto para fase posterior
- `estrategico_cliente`
- `pessoas_capacidade_cliente`
- detalhamento fino de autonomia por surface
- council mode operacional

---

## 7. Adaptação recomendada dos quatro agentes

## 7.1 SC-COORD

### Manter
- porta de entrada
- classificador
- roteador
- sintetizador

### Ajustar
- explicitar regra de economia de tokens
- explicitar resposta direta simples
- explicitar “não invocar especialista sem necessidade real”

---

## 7.2 SC-COM

### Manter
- mercado
- público
- oferta
- preço
- proposta
- negociação
- funil
- carteira
- rentabilidade comercial

### Ajustar
- segurar derivação consultiva por padrão
- escalar para `Squad Versus` quando o tema virar revisão estrutural de posicionamento, portfólio ou estratégia

---

## 7.3 SC-OPS

### Manter
- rotina
- backlog
- tarefas
- projetos
- execução assistida
- cadência

### Ajustar
- reforçar que é o agente mais “segunda-feira de manhã”
- saída deve ser curta, prática e acionável

---

## 7.4 SC-ADM

### Manter
- apoio administrativo
- leitura financeira operacional
- preparação de contexto
- alertas
- escalonamento cuidadoso

### Ajustar
- reforçar ainda mais a fronteira de sensibilidade financeira
- explicitar minimal disclosure
- impedir qualquer leitura “larga demais” sem pedido claro

---

## 8. Recomendações de produto e arquitetura

## 8.1 Produto

A experiência do `Sapiens Cliente` deve comunicar:
- simplicidade
- utilidade
- rapidez

e não sofisticação cara por padrão.

### Tradução
O usuário deve sentir:
- “resolve rápido”
- “me entende”
- “me ajuda a agir”

antes de sentir:
- “faz análise profunda o tempo todo”

---

## 8.2 Arquitetura

O `Squad Cliente` deve ser desenhado com:

- **economia por padrão**
- **expansão por exceção**

### Regra formal
1. resolver diretamente se seguro
2. chamar um especialista se necessário
3. chamar mais de um só quando houver justificativa clara
4. usar Conselho apenas quando o custo do erro justificar

---

## 8.3 Engenharia

O `Squad de Engenharia` permanece como exceção formal:

- pode usar mais profundidade
- pode usar mais raciocínio
- pode usar mais exploração

porque ali a prioridade é:
- excelência técnica
- precisão estrutural
- qualidade superior de solução

---

## 9. Recomendação final desta adaptação

### Decisão
A especificação recebida deve ser aproveitada como **base funcional válida** do `Squad Cliente`, com os seguintes ajustes obrigatórios:

1. explicitar `Sapiens Cliente` como experiência
2. preservar separação entre `Agente` e `Harness`
3. reforçar `surface user` como boundary principal
4. endurecer ainda mais a fronteira financeira do `SC-ADM`
5. adicionar **economia de tokens** como princípio transversal do `Squad Cliente`
6. impedir multiagente e conselho como comportamento padrão
7. formalizar isso como **fase 1** da família de agentes do cliente

---

## 10. Próximo passo recomendado

O próximo passo ideal é transformar esta adaptação em:

- uma versão canônica revisada de **agentes oficiais do Squad Cliente**

mas fazendo isso **um agente por vez**, nesta ordem:

1. `SC-COORD`
2. `SC-COM`
3. `SC-OPS`
4. `SC-ADM`

com revisão explícita de:
- escopo
- fronteiras
- autonomia
- surface
- custo cognitivo/token

### Primeiro desdobramento já materializado
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_coord_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_ops_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_adm_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\papers\paper_sc_com_squad_cliente_v1.md`
