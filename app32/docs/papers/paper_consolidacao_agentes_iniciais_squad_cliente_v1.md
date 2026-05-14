# Paper Conceitual — Consolidação dos Agentes Iniciais do Squad Cliente v1

Status: conceitual de consolidação  
Escopo: `SC-COORD`, `SC-COM`, `SC-OPS`, `SC-ADM`, precedência interna, colaboração, economia de tokens, escalonamento e fronteiras do `Squad Cliente`

## 1. Objetivo

Consolidar, em uma visão única, os quatro agentes iniciais do `Squad Cliente`, validando sua coerência conjunta antes da passagem para SPEC oficial.

Este paper existe para responder:
- os quatro agentes se encaixam bem entre si?
- há sobreposição excessiva?
- a colaboração entre eles está clara?
- a economia de tokens foi preservada?
- a fronteira entre `Squad Cliente`, `Squad Versus` e `Squad de Engenharia` está suficientemente nítida?

---

## 2. Composição inicial do Squad Cliente

O `Squad Cliente`, em sua fase 1, é composto por:

- `SC-COORD` — Agente Líder / Coordenador
- `SC-COM` — Agente Comercial
- `SC-OPS` — Agente Operacional
- `SC-ADM` — Agente Administrativo / Financeiro

### Leitura correta
- `Sapiens Cliente` = experiência / front door
- `Squad Cliente` = família
- `Agentes` = papéis funcionais
- `Harnesses` = invólucros operacionais

---

## 3. Missão do conjunto

O `Squad Cliente` existe para ser o copiloto operacional do cliente no uso do APP32, ajudando a:

- entender a demanda
- organizar a ação
- orientar a execução
- melhorar a utilização do sistema
- apoiar decisões operacionais do dia a dia

Sem:
- substituir consultoria estrutural da Versus
- substituir engenharia
- transformar toda interação em deliberação cara

---

## 4. Papel de cada agente no conjunto

## 4.1 SC-COORD

É o:
- ponto de entrada funcional
- classificador
- roteador
- sintetizador
- guardião de contexto
- guardião da economia de tokens

## 4.2 SC-COM

É o especialista de:
- mercado
- carteira
- pipeline
- propostas
- negociação
- preço
- rentabilidade comercial

## 4.3 SC-OPS

É o especialista de:
- rotina
- backlog
- tarefas
- projetos
- cadência
- execução assistida

## 4.4 SC-ADM

É o especialista de:
- organização administrativa
- leitura financeira operacional
- alertas
- vencimentos
- resumo financeiro
- contexto sensível com baixa exposição

---

## 5. Princípio estrutural mais importante

> O `Squad Cliente` deve operar com especialização funcional e coordenação leve.

### Interpretação
Isso significa:
- especialistas profundos o suficiente para ajudar
- coordenador leve o suficiente para não ficar caro
- colaboração suficiente para integrar
- separação suficiente para evitar sobreposição

---

## 6. Economia de tokens como princípio transversal

## 6.1 Regra geral

O `Squad Cliente` deve obedecer à regra:

> **resolver o máximo com o menor custo cognitivo e computacional possível, sem sacrificar segurança nem qualidade mínima necessária**

## 6.2 Consequência por agente

### SC-COORD
- primeiro tenta resposta direta
- depois um especialista
- multiagente só quando justificado
- conselho apenas em casos caros

### SC-COM
- profundidade comercial prática
- sem derivar para consultoria estrutural por reflexo

### SC-OPS
- resposta operacional curta
- foco em próxima ação

### SC-ADM
- resposta curta
- baixa exposição
- minimal disclosure

## 6.3 Exceção oficial

O `Squad de Engenharia` permanece fora desta prioridade principal, porque sua meta é excelência técnica acima de economia operacional.

---

## 7. Precedência interna do Squad Cliente

## 7.1 Entrada

Toda demanda entra por:
- `SC-COORD`

## 7.2 Domínio inequívoco

Se o domínio estiver claro:
- `SC-COORD` chama um único especialista

## 7.3 Multi-domínio

Se a demanda exigir múltiplas perspectivas:
- `SC-COORD` coordena múltiplos especialistas
- sintetiza
- devolve resposta integrada

## 7.4 Deliberação cara

Se o custo de erro for alto:
- `SC-COORD` pode, no futuro, acionar `Modo Conselho`

Mas isso é exceção, não rotina.

---

## 8. Fronteiras entre os especialistas

## 8.1 SC-COM não deve virar SC-OPS

O Comercial não deve absorver:
- execução de entrega
- backlog
- cadência operacional

Quando a venda vira entrega:
- handoff para `SC-OPS`

## 8.2 SC-OPS não deve virar SC-COM

O Operacional não deve absorver:
- proposta
- preço
- negociação
- carteira

Quando a execução depende do comercial:
- handoff para `SC-COM`

## 8.3 SC-ADM não deve virar operador financeiro pleno

O Administrativo / Financeiro não deve absorver:
- pagamento
- aprovação de despesa
- crédito
- execução financeira irrestrita

## 8.4 SC-COM e SC-ADM podem cooperar

Especialmente em:
- rentabilidade comercial
- inadimplência
- impacto financeiro em renovação/proposta

Mas sem colapsar os dois papéis em um só.

---

## 9. Relação com Sapiens Cliente

Para o usuário:
- a entrada é `Sapiens Cliente`

Para a arquitetura:
- `Sapiens Cliente` não é um único agente
- ele é a experiência que dá acesso ao `Squad Cliente`

### Consequência prática
O usuário não precisa escolher manualmente entre os quatro agentes no início.  
O sistema deve preferir:
- simplicidade de entrada
- roteamento interno

---

## 10. Relação com Squad Versus

O `Squad Cliente` deve escalar para o `Squad Versus` quando o problema sair da operação local e entrar em:

- estratégia
- método
- governança
- controladoria estrutural
- revisão de processo
- posicionamento
- revisão de portfólio

### Regra curta
`Squad Cliente` opera melhor o contexto atual.  
`Squad Versus` ajuda a redesenhar o contexto quando ele já não serve.

---

## 11. Relação com Squad de Engenharia

O `Squad Cliente` deve escalar para `Squad de Engenharia` quando houver:

- erro técnico
- falha do MCP
- inconsistência de integração
- defeito em fluxo ou módulo
- limitação estrutural do APP32

### Regra curta
Problema de negócio fica no `Squad Cliente`.  
Problema técnico sobe para `Squad de Engenharia`.

---

## 12. Matriz curta de foco

| Agente | Foco principal | Estilo esperado | Risco principal |
|---|---|---|---|
| `SC-COORD` | triagem, roteamento, síntese | leve, direto, econômico | over-orquestração |
| `SC-COM` | mercado, proposta, carteira, negociação | comercial, objetivo, útil | derivar para consultoria estrutural ou decidir condição sensível |
| `SC-OPS` | rotina, backlog, tarefas, execução | prático, curto, acionável | virar burocrata ou analista prolixo |
| `SC-ADM` | leitura administrativa/financeira operacional | prudente, contido, preciso | exposição excessiva ou autonomia indevida |

---

## 13. Coerência da família inicial

### Pontos fortes
- cobertura funcional boa para fase 1
- separação razoável entre domínios
- coordenador bem posicionado
- espaço claro para handoff
- aderência boa ao desenho `Sapiens -> Squad -> Agente -> Harness`

### Riscos de implementação
- `SC-COORD` virar pesado demais
- `SC-COM` virar consultor de estratégia por padrão
- `SC-OPS` produzir texto demais
- `SC-ADM` expor mais do que deveria

### Conclusão
> A família inicial está coerente e aproveitável, desde que a implementação preserve as fronteiras e a economia de tokens.

---

## 14. O que ainda não está fechado

Este paper ainda não congela:

1. matriz oficial de autonomia por action/surface
2. triggers formais de `Modo Conselho`
3. playbooks de handoff detalhados
4. runbooks operacionais por harness
5. decisão sobre entrada futura de:
   - `estrategico_cliente`
   - `pessoas_capacidade_cliente`

---

## 15. Recomendação final

A recomendação desta consolidação é:

1. considerar os quatro agentes iniciais como **família funcional coerente**
2. levar agora essa família para **SPEC oficial**
3. preservar desde a SPEC:
   - economia de tokens
   - surface `user`
   - `company_id` obrigatório
   - human gate
   - baixa exposição financeira
   - separação clara entre operação local, consultoria e engenharia

---

## 16. Próximo passo recomendado

Depois desta consolidação, o próximo passo correto é criar:

- `arquitetura_oficial_squad_cliente_v1`
- `agentes_oficiais_squad_cliente_v1`

em `docs/spec/`
