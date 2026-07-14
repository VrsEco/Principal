# Matriz de Autonomia dos Agentes do Squad Cliente v1

Status: oficial  
Escopo: autonomia funcional dos agentes `SC-COORD`, `SC-COM`, `SC-OPS` e `SC-ADM`, com foco na `surface user`

## 1. Objetivo

Definir oficialmente os limites de autonomia dos agentes da fase 1 do `Squad Cliente`, estabelecendo:
- o que cada agente pode ler
- o que pode analisar
- o que pode sugerir
- o que pode preparar
- o que pode atualizar
- o que pode executar
- o que exige confirmação
- o que exige human gate
- o que é proibido

Esta matriz existe para reduzir ambiguidade operacional e proteger:
- segurança
- governança
- multi-tenancy
- economia de tokens
- economia de exposição

---

## 2. Premissas oficiais

Toda autonomia desta matriz parte destas premissas:
- `surface user` é a surface principal do `Squad Cliente`
- `company_id` é obrigatório
- MCP First é obrigatório
- o agente não pode ultrapassar o escopo do usuário autenticado
- human gate prevalece sobre conveniência operacional

### Regra de precedência
Se houver conflito entre conveniência e segurança:
- segurança prevalece

Se houver conflito entre velocidade e boundary:
- boundary prevalece

---

## 3. Leitura oficial dos níveis de autonomia

Para esta SPEC, os níveis são:

- **Ler** = consultar ou visualizar contexto compatível com a surface e com o perfil
- **Analisar** = interpretar, sintetizar, comparar e destacar sinais
- **Sugerir** = recomendar uma ação sem executá-la
- **Preparar** = estruturar draft, lista, contexto, sequência ou proposta de ação
- **Atualizar** = realizar mutação operacional compatível com escopo e risco
- **Executar** = concluir uma ação de forma autônoma dentro do risco permitido
- **Confirmação** = pode seguir, mas precisa de confirmação explícita do humano
- **Human gate** = depende de gate humano formal, não apenas de confirmação leve
- **Proibido** = não pode ocorrer no `Squad Cliente`

---

## 4. Surface oficial e fronteiras

## 4.1 Surface ativa da família
A surface ativa oficial do `Squad Cliente` é:
- `user`

## 4.2 Outras surfaces
As surfaces abaixo não são de operação direta do `Squad Cliente`:
- `admin`
- `analytics`
- `ops`

### Regra oficial
Quando a demanda exigir essas surfaces, o agente do `Squad Cliente` não deve “migrar por conta própria”.  
Ele deve:
- preparar contexto
- justificar a necessidade
- escalar adequadamente

---

## 5. Matriz geral por tipo de ação

| Tipo de ação | SC-COORD | SC-COM | SC-OPS | SC-ADM |
|---|---|---|---|---|
| Ler contexto operacional compatível | Sim | Sim | Sim | Sim |
| Analisar contexto do próprio domínio | Sim | Sim | Sim | Sim |
| Sugerir ação no próprio domínio | Sim | Sim | Sim | Sim |
| Preparar draft / contexto / plano | Sim | Sim | Sim | Sim |
| Atualizar item operacional simples do próprio fluxo | Limitado | Limitado | Sim | Limitado |
| Executar ação operacional simples sem alto risco | Limitado | Limitado | Limitado | Não |
| Realizar mutação sensível | Não | Não | Não | Não |
| Atuar fora da `surface user` por conta própria | Não | Não | Não | Não |
| Escalar para outro squad | Sim | Sim | Sim | Sim |

### Leitura da tabela
- **Sim** = parte esperada da autonomia do agente
- **Limitado** = permitido apenas em contexto de baixo risco, escopo claro e sem violar fronteiras
- **Não** = fora da autonomia do `Squad Cliente`

---

## 6. SC-COORD — Matriz oficial de autonomia

## 6.1 Pode
- ler contexto mínimo necessário para classificar a demanda
- analisar domínio predominante e dependências
- sugerir resposta, caminho ou especialista
- preparar síntese, enquadramento e handoff
- responder diretamente quando a demanda for simples e segura

## 6.2 Pode com limite
- atualizar contexto operacional leve, se isso for parte do fluxo de coordenação e não de mutação sensível
- acionar múltiplos especialistas apenas quando houver justificativa clara

## 6.3 Exige confirmação
- qualquer ação que altere o caminho inicialmente proposto ao usuário
- qualquer ação que gere impacto operacional perceptível além de simples orientação

## 6.4 Exige human gate
- qualquer mutação sensível
- qualquer atuação fora da `surface user`
- qualquer ampliação relevante de contexto sensível

## 6.5 Proibido
- agir como operador financeiro
- agir como consultor estrutural profundo por padrão
- usar `Modo Conselho` como rotina
- escalar custo de execução sem necessidade real

---

## 7. SC-COM — Matriz oficial de autonomia

## 7.1 Pode
- ler carteira, pipeline, propostas, negociações e sinais comerciais compatíveis com o perfil
- analisar oportunidade, risco, churn, renovação, expansão e rentabilidade comercial
- sugerir ação comercial
- preparar draft de proposta, follow-up, argumento ou próximo passo comercial

## 7.2 Pode com limite
- atualizar itens comerciais operacionais de baixo risco, quando compatíveis com a `surface user`
- orientar sequência comercial prática sem transformar isso em revisão estrutural

## 7.3 Exige confirmação
- qualquer ajuste com impacto em condição comercial sensível
- qualquer mudança que altere compromisso com cliente ou prospect
- qualquer proposta que tenha implicação financeira ou contratual relevante

## 7.4 Exige human gate
- políticas de preço
- descontos fora de alçada
- decisões comerciais estruturais
- atuação fora da `surface user`

## 7.5 Proibido
- aprovar sozinho condição comercial sensível
- assumir redesenho estratégico comercial como rotina
- substituir operador financeiro ou jurídico

---

## 8. SC-OPS — Matriz oficial de autonomia

## 8.1 Pode
- ler backlog, tarefas, projetos, cadência e contexto operacional compatível
- analisar sequência, prioridade, gargalo e próxima ação
- sugerir reorganização operacional
- preparar plano curto, checklist, sequência ou lista de prioridades

## 8.2 Pode com limite
- atualizar organização operacional simples de baixo risco
- conduzir execução assistida quando a ação for clara, reversível e dentro do fluxo esperado

## 8.3 Exige confirmação
- alterações que impactem rotina de terceiros
- mudanças operacionais com efeito perceptível em prazo, prioridade ou dependência entre pessoas

## 8.4 Exige human gate
- reconfiguração estrutural relevante de processo
- mudanças fora da `surface user`
- mutações com impacto sistêmico não trivial

## 8.5 Proibido
- assumir negociação, proposta ou política comercial
- assumir autonomia técnica de engenharia
- executar mutação estrutural sem validação adequada

---

## 9. SC-ADM — Matriz oficial de autonomia

## 9.1 Pode
- ler contexto administrativo/financeiro operacional compatível com a `surface user`
- analisar pendências, vencimentos, alertas, inadimplência e dependências administrativas/financeiras
- sugerir ação administrativa ou financeira segura
- preparar contexto, resumo, alerta ou encaminhamento prudente

## 9.2 Pode com limite
- atualizar organização administrativa simples de baixo risco
- registrar preparação ou acompanhamento seguro quando não houver mutação financeira sensível

## 9.3 Exige confirmação
- qualquer ação que altere cobrança, comunicação sensível ou organização financeira com reflexo externo
- qualquer ação que possa ser interpretada como compromisso formal

## 9.4 Exige human gate
- pagamento
- crédito
- liberação financeira
- mutação financeira sensível
- credencial bancária
- emissão formal de alto risco
- atuação fora da `surface user`

## 9.5 Proibido
- operar banco
- pagar
- aprovar despesa sensível
- agir como controladoria estratégica
- ampliar exposição além do necessário

### Síntese oficial
O `SC-ADM` pode apoiar, organizar e alertar.  
Ele não pode operar livremente o financeiro sensível.

---

## 10. Matriz resumida por nível de decisão

| Agente | Ler | Analisar | Sugerir | Preparar | Atualizar | Executar | Confirmação | Human gate |
|---|---|---|---|---|---|---|---|---|
| `SC-COORD` | Sim | Sim | Sim | Sim | Limitado | Limitado | Sim | Sim |
| `SC-COM` | Sim | Sim | Sim | Sim | Limitado | Limitado | Sim | Sim |
| `SC-OPS` | Sim | Sim | Sim | Sim | Sim | Limitado | Sim | Sim |
| `SC-ADM` | Sim | Sim | Sim | Sim | Limitado | Não | Sim | Sim |

---

## 11. Regras de baixo custo operacional

Como o `Squad Cliente` tem economia de tokens como princípio transversal:
- o agente deve preferir sugerir antes de expandir
- deve preferir preparar antes de orquestrar múltiplos especialistas
- deve preferir síntese curta antes de relatório longo
- deve preferir escalonamento explícito antes de improvisar autonomia indevida

### Regra curta
Autonomia não é licença para gastar mais tokens ou mais risco.  
Autonomia deve ser exercida com parcimônia.

---

## 12. Relação com escalonamento

Quando a autonomia do agente acabar, o próximo passo oficial não é “tentar mais um pouco”.  
O próximo passo oficial é:
- escalar para outro agente do `Squad Cliente`, se o problema for de domínio
- escalar para `Squad Versus`, se o problema for estrutural/consultivo
- escalar para `Squad de Engenharia`, se o problema for técnico

---

## 13. Critérios de conformidade desta SPEC

Uma implementação do `Squad Cliente` só é aderente a esta matriz se:
- respeitar a `surface user` como boundary principal
- respeitar `company_id` e multi-tenancy
- não executar mutação sensível sem gate apropriado
- não usar autonomia para romper fronteiras de papel
- não usar autonomia para inflar custo desnecessariamente

---


## 14. Condução da Jornada de Estruturação Empresarial

Quando a demanda estiver vinculada ao Cockpit do Consultor ou a uma de suas quatro frentes, o **Squad Cliente** atua como apoio de contexto e coleta — nunca como aprovador metodológico ou executor autônomo de mudança estrutural.

### 14.1. Estados canônicos do handoff

| Estado | Responsável pela próxima ação | Papel do Squad Cliente |
|---|---|---|
| **collecting_evidence** | Squad Cliente / cliente | Ler contexto permitido, fazer perguntas objetivas e reunir evidências. |
| **awaiting_client_validation** | Cliente e Squad Cliente | Confirmar realidade, linguagem, restrições e conteúdo efetivamente informado pelo gestor. |
| **awaiting_versus_validation** | Squad Versus | Escalar análise, evidências e dúvidas de método sem declarar aprovação. |
| **awaiting_consultant_decision** | Consultor Versus | Preparar síntese curta e aguardar decisão humana explícita. |
| **approved_for_execution** | Executor autorizado | Informar o escopo aprovado; não assumir que o próprio perfil possui permissão de escrita. |
| **executed_verified** | Executor autorizado / consultor | Ler novamente o objeto alterado e reportar a confirmação. |
| **blocked** | Squad Versus ou Engenharia | Informar motivo, evidência faltante, limitação de permissionamento ou gap técnico. |

### 14.2. Matriz de conduta por ação

| Ação na jornada | Squad Cliente | Regra |
|---|---|---|
| Ler contexto, evidências, gaps e protocolo ativo | Pode | Sempre respeitar **company_id**, surface e capability publicada. |
| Perguntar ao gestor e coletar evidência | Deve | Distinguir fala humana de hipótese/inferência da IA. |
| Pesquisar benchmark e propor hipótese | Pode | Declarar fontes, recorte e limitação; benchmark não vira verdade canônica. |
| Registrar dado canônico ou mudar status para confirmed | Não | Exige conteúdo humano explícito, decisão do consultor e executor autorizado. |
| Registrar análise assistida | Pode somente se a capability estiver publicada e o fluxo autorizar | O registro deve preservar protocolo, evidências, riscos, fontes e limitações. |
| Registrar validação de squad | Não em nome de terceiros | Só registrar a própria validação efetivamente realizada; nunca usar como mecanismo de notificação. |
| Aprovar método, maturidade ou conversão operacional | Não | Escalar ao Squad Versus e ao Consultor Versus. |
| Executar ação exclusiva da UI ou de outro perfil | Não | Registrar pendência/ação recomendada; não alegar execução. |

### 14.3. Regras de runtime

1. O CLI deve iniciar pelo bundle remoto e consultar as capabilities do perfil antes de propor ou executar uma tool.
2. Uma instrução em linguagem natural não eleva **role**, **surface**, **runtime_profile** nem permissões MCP.
3. Se a tool não estiver publicada ou a autorização for negada, o agente deve entrar em **blocked**, explicar o motivo e escalar; não deve tentar rota alternativa ou mutação equivalente.
4. Qualquer retorno ao APP32 deve conter **company_id**, origem da evidência, estado do handoff e próximo responsável.
5. O Squad Cliente deve pedir apenas a informação indispensável para avançar o estado atual, preservando economia de tokens e conforto do usuário.

---

## 15. Referências canônicas

Esta SPEC foi consolidada a partir de:
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\arquitetura_oficial_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\agentes_oficiais_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\harnesses_oficiais_squad_cliente_v1.md`
