# Playbook de Handoff e Escalonamento do Squad Cliente v1

Status: oficial  
Escopo: handoff interno entre `SC-COORD`, `SC-COM`, `SC-OPS`, `SC-ADM` e escalonamento para `Squad Versus` e `Squad de Engenharia`

## 1. Objetivo

Definir como o `Squad Cliente` deve:
- fazer handoff entre seus agentes
- escalar para outros squads
- preservar contexto
- reduzir custo operacional
- evitar sobreposição, perda de contexto e escalonamento indevido

Este playbook não redefine arquitetura, agentes ou autonomia.  
Ele orienta a atuação oficial a partir das SPECs já congeladas.

---

## 2. Princípios de atuação

Todo handoff ou escalonamento do `Squad Cliente` deve obedecer a estes princípios:

### 2.1 Menor custo seguro
Antes de repassar, o agente deve perguntar:
- isso pode ser resolvido aqui com segurança?
- isso exige mesmo outro agente?
- isso exige mesmo outro squad?

### 2.2 Domínio claro
O handoff deve acontecer quando:
- o domínio predominante estiver claro
- a fronteira do agente atual tiver sido alcançada

### 2.3 Preservação de contexto
Ao fazer handoff ou escalonamento, o agente deve repassar:
- objetivo da demanda
- contexto mínimo necessário
- restrição relevante
- motivo do handoff

### 2.4 Não duplicação
O agente não deve:
- repetir análise já suficiente
- abrir uma nova frente sem ganho real
- gerar handoff em cascata por insegurança genérica

---

## 3. Porta de entrada oficial

Toda demanda entra por:
- `SC-COORD`

O `SC-COORD` decide entre:
1. responder diretamente
2. chamar um especialista do `Squad Cliente`
3. coordenar mais de um especialista
4. escalar para outro squad

### Regra principal
O default é:
- resolução direta ou com um único especialista

Coordenação ampliada é exceção.

---

## 4. Handoff interno do Squad Cliente

## 4.1 SC-COORD -> SC-COM

Usar quando a demanda for predominantemente:
- comercial
- de proposta
- de negociação
- de carteira
- de funil
- de preço
- de evolução comercial

### O que repassar
- objetivo comercial
- cliente/oportunidade relevante
- restrição percebida
- ação esperada

### O que não fazer
- não enviar para `SC-COM` uma demanda claramente operacional
- não transformar simples consulta em revisão comercial ampla

---

## 4.2 SC-COORD -> SC-OPS

Usar quando a demanda for predominantemente:
- operacional
- de rotina
- de backlog
- de tarefas
- de projetos
- de acompanhamento do dia a dia

### O que repassar
- contexto operacional mínimo
- prioridade percebida
- gargalo ou objetivo
- resultado esperado

### O que não fazer
- não enviar para `SC-OPS` uma demanda de negociação, proposta ou preço
- não pedir plano longo quando uma próxima ação basta

---

## 4.3 SC-COORD -> SC-ADM

Usar quando a demanda for predominantemente:
- administrativa
- financeira operacional segura
- de alertas, vencimentos ou inadimplência
- de preparação de contexto adm/fin

### O que repassar
- pergunta administrativa/financeira
- recorte sensível mínimo
- necessidade de prudência
- limite de exposição esperado

### O que não fazer
- não ampliar o contexto financeiro além do necessário
- não pedir mutação sensível como se fosse rotina

---

## 4.4 SC-COM -> SC-OPS

Usar quando:
- a venda vira execução
- a demanda comercial depende de estruturação operacional
- o próximo valor real está na organização da entrega, rotina ou acompanhamento

### Exemplo típico
- “ganhamos o cliente; agora precisamos organizar a entrada, as tarefas e a cadência”

### O que repassar
- compromisso comercial relevante
- contexto mínimo da entrega
- urgência e prioridade
- dependências operacionais

---

## 4.5 SC-COM -> SC-ADM

Usar quando o comercial encontrar dependência de:
- inadimplência
- impacto financeiro
- reflexo de cobrança
- rentabilidade com componente adm/fin

### O que repassar
- contexto comercial
- ponto de risco financeiro
- dúvida ou necessidade objetiva
- recorte mínimo da exposição

---

## 4.6 SC-OPS -> SC-ADM

Usar quando a execução depender de:
- pendência administrativa
- cobrança
- vencimento
- dependência financeira operacional

### O que repassar
- tarefa ou fluxo impactado
- dependência adm/fin
- urgência operacional
- risco de bloqueio

---

## 4.7 SC-ADM -> SC-COM

Usar quando o contexto adm/fin impactar:
- renovação
- churn
- rentabilidade comercial
- necessidade de abordagem comercial

### O que repassar
- sinal financeiro relevante
- implicação comercial
- urgência percebida
- limite de exposição

---

## 4.8 SC-ADM -> SC-OPS

Usar quando o contexto adm/fin exigir:
- ação operacional
- reorganização do fluxo
- acompanhamento prático
- ajuste de rotina

### O que repassar
- dependência administrativa
- consequência operacional
- urgência
- próximo passo esperado

---

## 5. Coordenação multiagente

Coordenação multiagente só deve ocorrer quando:
- houver interdependência real entre domínios
- a demanda não puder ser resolvida adequadamente por um único especialista
- o custo adicional for justificável

### Responsável pela síntese
Sempre que houver mais de um especialista:
- `SC-COORD` sintetiza a resposta final

### Regra de economia
Se a mesma resposta puder ser entregue com:
- um especialista + uma síntese curta

não usar rodada ampliada desnecessária.

---

## 6. Escalonamento para Squad Versus

Escalar para `Squad Versus` quando a demanda sair da operação local e entrar em:
- estratégia
- posicionamento
- método
- governança
- controladoria estrutural
- revisão estrutural de processo
- revisão de portfólio

### Regra prática
Escalar para `Squad Versus` quando a pergunta deixar de ser:
- “como operar melhor isso agora?”

e passar a ser:
- “esse desenho ainda faz sentido?”

### O que repassar no escalonamento
- problema resumido
- contexto atual
- por que a operação local não basta
- decisão ou revisão esperada

---

## 7. Escalonamento para Squad de Engenharia

Escalar para `Squad de Engenharia` quando houver:
- erro técnico
- falha de módulo
- defeito de integração
- problema de MCP
- limitação estrutural do APP32
- comportamento inconsistente do sistema

### Regra prática
Escalar para `Squad de Engenharia` quando a pergunta deixar de ser:
- “qual é a melhor ação de negócio?”

e passar a ser:
- “por que o sistema não está permitindo ou suportando isso?”

### O que repassar no escalonamento
- sintoma observado
- impacto funcional
- contexto mínimo reproduzível
- empresa/tenant afetado
- ação tentada e resultado

---

## 8. Casos em que NÃO deve haver handoff

Não deve haver handoff quando:
- a demanda é simples e segura
- a resposta direta já basta
- o outro agente não agregaria valor real
- o handoff só serviria para “parecer sofisticado”

### Regra curta
Handoff não é ornamento.  
É mecanismo de boundary e qualidade.

---

## 9. Casos em que NÃO deve haver escalonamento

Não deve haver escalonamento quando:
- o problema ainda cabe claramente no domínio do agente atual
- a dúvida é operacional e local
- o agente está tentando terceirizar julgamento simples
- não existe ainda sinal real de fronteira estrutural ou técnica

---

## 10. Formato oficial de handoff

Todo handoff deve, idealmente, carregar quatro blocos:

1. **Demanda**
2. **Contexto mínimo**
3. **Motivo do repasse**
4. **Resultado esperado**

### Exemplo abstrato
- Demanda: revisar a carteira do cliente X
- Contexto mínimo: houve queda de renovação e aumento de atraso
- Motivo do repasse: leitura comercial com reflexo financeiro
- Resultado esperado: priorização comercial objetiva

---

## 11. Formato oficial de escalonamento

Todo escalonamento deve carregar:

1. **Problema resumido**
2. **Por que o Squad Cliente não resolve sozinho**
3. **Impacto**
4. **Próxima análise esperada**

### Exemplo abstrato para Versus
- problema: processo comercial atual gera retrabalho recorrente
- por que não resolve sozinho: já não é só execução; é desenho de processo
- impacto: perda de cadência e conversão
- próxima análise esperada: revisão estrutural

### Exemplo abstrato para Engenharia
- problema: fluxo de atualização trava no APP32
- por que não resolve sozinho: há sinal de defeito técnico
- impacto: bloqueia execução
- próxima análise esperada: investigação técnica

---

## 12. Relação com a matriz de autonomia

Este playbook deve ser lido junto de:
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\matriz_autonomia_agentes_squad_cliente_v1.md`

### Regra de precedência
Se a matriz de autonomia disser que algo:
- exige confirmação
- exige human gate
- é proibido

o handoff ou escalonamento deve respeitar isso integralmente.

---

## 13. Sinais de boa atuação

O playbook está sendo bem aplicado quando:
- a maioria das demandas simples para no primeiro nível
- a coordenação multiagente é rara e útil
- o usuário sente simplicidade
- o contexto não se perde nos repasses
- o `SC-ADM` permanece prudente
- o `SC-COORD` não vira superorquestrador caro

---

## 14. Sinais de má aplicação

O playbook está sendo mal aplicado quando:
- tudo vira handoff
- tudo vira escalonamento
- o usuário recebe respostas longas para perguntas simples
- os especialistas se sobrepõem demais
- o comercial começa a fazer estratégia estrutural por padrão
- o operacional começa a escrever demais
- o adm/fin começa a expor contexto demais

---

## 15. Referências canônicas

Este playbook foi consolidado a partir de:
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\arquitetura_oficial_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\agentes_oficiais_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\harnesses_oficiais_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\matriz_autonomia_agentes_squad_cliente_v1.md`
