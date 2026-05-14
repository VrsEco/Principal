# Plano de Correção Arquitetural dos Squads v1

Status: oficial para execução incremental  
Escopo: Squad Cliente, Squad Versus, Squad de Engenharia, Sapiens, agentes, harnesses, precedência, autonomia e coprodução

## 1. Objetivo

Fechar os principais gaps entre:
- o paper conceitual dos squads/agentes
- o mapa formal da Versus
- a construção atual de runtime profiles, harnesses, policy e experiência de instalação

Este plano existe para transformar a arquitetura atual, já bem encaminhada em runtime/harness, em uma arquitetura também madura no nível de:
- agentes oficiais
- fronteiras entre squads
- precedência
- autonomia
- coprodução humano + agente
- documentação canônica

---

## 2. Diagnóstico resumido

### 2.1 O que já está alinhado
- três famílias formais: `Squad Cliente`, `Squad Versus`, `Squad de Engenharia`
- runtime externo como padrão de reasoning
- `APP32 + MCP` como núcleo operacional e contrato canônico
- separação entre **agente** e **harness**
- uso de coordenador como entrada do runtime

### 2.2 O que ainda está incompleto
- agentes oficiais ainda não estão suficientemente formalizados
- o `Agente Comercial` ainda está subdefinido
- a precedência entre `Squad Cliente`, `Squad Versus` e `Squad de Engenharia` ainda não está explícita o bastante
- o papel de `Sapiens` ainda tem leituras concorrentes
- o modelo de autonomia e coprodução ainda não está fechado por agente
- a regra de auditoria `read-only` ainda precisa ser consolidada em documentação e policy

---

## 3. Correções arquiteturais prioritárias

## 3.1 Prioridade 1 — Agentes oficiais do Squad Cliente

Formalizar como oficiais:
- `Agente Coordenador do Squad Cliente`
- `Agente Comercial do Squad Cliente`
- `Agente Operacional do Squad Cliente`
- `Agente Administrativo/Financeiro do Squad Cliente`

### Resultado esperado
Para cada agente, definir:
- missão
- escopo
- responsabilidades
- fronteiras
- handoffs
- quando atua sozinho
- quando escala

### Observação crítica
O `Agente Comercial` deve ser fechado com definição rica, cobrindo pelo menos:
- relação da empresa com o mercado
- público
- oferta
- preço
- proposta
- negociação
- funil
- clientes ativos
- rentabilidade da carteira

---

## 3.2 Prioridade 2 — Precedência entre squads

Formalizar a regra de complementaridade entre:
- `Squad Cliente`
- `Squad Versus`
- `Squad de Engenharia`

### Resultado esperado
Explicitar:
- quando o `Squad Cliente` conduz sozinho
- quando o `Squad Cliente` escala para o `Squad Versus`
- quando o `Squad Versus` atua como orientador e não como executor direto
- quando o `Squad de Engenharia` entra por gatilho técnico, e não por conveniência funcional

### Regra-alvo
- `Squad Cliente` = operação assistida e contexto local
- `Squad Versus` = direção consultiva, governança, crítica sistêmica e controladoria
- `Squad de Engenharia` = evolução técnica, correção, observabilidade e sustentação estrutural

---

## 3.3 Prioridade 3 — Equalização oficial de Sapiens

Formalizar `Sapiens` como:
- **marca-mãe**
- **front door de experiência**

E não como agente isolado de uma única família.

### Resultado esperado
Canonizar:
- `Sapiens Cliente`
- `Sapiens Consultor`
- `Sapiens Engenharia`

Separando sempre:
- nome visível de experiência
- família canônica do squad
- profile técnico
- harness inicial

---

## 3.4 Prioridade 4 — Autonomia e coprodução humano + agente

Criar matriz formal por agente definindo:
- o que apenas lê
- o que analisa
- o que sugere
- o que prepara
- o que executa
- o que exige confirmação
- o que exige `human gate`
- o que é proibido

### Resultado esperado
Reduzir ambiguidade operacional e impedir:
- excesso de autonomia implícita
- mutação sensível fora da surface correta
- confusão entre sugestão, preparação e execução

---

## 3.5 Prioridade 5 — Auditoria canônica read-only

Consolidar `auditor_versus` e demais papéis de auditoria como:
- `read-only` por princípio
- sem mutação operacional
- com telemetria, evidência e trilha reforçadas

### Resultado esperado
Ter clareza em:
- manifesto do agente
- playbook do agente
- harness do agente
- policy/rbac/surface

---

## 4. Ajustes necessários no build atual

## 4.1 Runtime e harnesses

O build atual está correto em tratar:
- `Squad` como família
- `Agente` como papel
- `Harness` como invólucro operacional

### Ajuste necessário
Fechar a documentação oficial que falta para sustentar isso de forma completa.

---

## 4.2 Squad Cliente

### Ajustes
- fortalecer a definição do `Agente Comercial`
- formalizar limites do `Agente Adm/Financeiro`
- decidir se `estrategico_cliente` e `pessoas_capacidade_cliente` entram agora como oficiais ou ficam em fase 2

---

## 4.3 Squad Versus

### Ajustes
- formalizar o `Coordenador do Squad Versus`
- consolidar `auditor_versus` como `read-only`
- explicitar o papel consultivo diante do `Squad Cliente`

---

## 4.4 Squad de Engenharia

### Ajustes
- formalizar melhor o `Coordenador do Squad de Engenharia`
- fechar gatilhos oficiais de escalonamento técnico
- consolidar a fronteira entre atuação funcional e atuação técnica

---

## 5. Artefatos canônicos que precisam nascer ou ser consolidados

## 5.1 SPECs
- `estrutura_oficial_dos_squads_v1`
- `arquitetura_oficial_squad_cliente_v1`
- `agentes_oficiais_squad_cliente_v1`
- `harnesses_oficiais_squad_cliente_v1`
- equivalentes para `Squad Versus`
- equivalentes para `Squad de Engenharia`

## 5.2 Manifestos
- um manifesto por squad
- um manifesto por agente crítico

## 5.3 Playbooks
- coordenador de cada squad
- comercial, operacional e adm/financeiro do cliente
- auditor, strategist e operations do versus

## 5.4 Runbooks
- instalação
- ativação
- startup
- troubleshooting
- smoke por squad/harness

## 5.5 Harnesses
- um documento canônico por harness publicado

---

## 6. Sequência recomendada de execução

### Etapa A
Formalizar:
- agentes oficiais do `Squad Cliente`
- precedência entre squads
- equalização oficial de `Sapiens`

### Etapa B
Formalizar:
- autonomia
- coprodução humano + agente
- auditoria `read-only`
- amadurecimento do `Modo Conselho` como protocolo especial do Agente Líder antes de congelar em SPEC

### Etapa C
Consolidar:
- manifestos
- playbooks
- runbooks
- harnesses oficiais

### Etapa D
Revisar:
- policy
- contracts
- permission matrix
- catálogo de instalação e snippets

---

## 7. Critérios de aceite

Este plano será considerado atendido quando:
- os três squads tiverem fronteiras explícitas
- o `Squad Cliente` tiver agentes oficiais fechados
- o `Agente Comercial` estiver formalizado com escopo rico
- a precedência entre `Cliente`, `Versus` e `Engenharia` estiver canônica
- `Sapiens` estiver equalizado como front door oficial
- autonomia e coprodução estiverem formalizadas
- auditoria `read-only` estiver coerente entre docs, policy e harness

---

## 8. Fontes de referência

- `C:\GestaoVersus\app32\app32\docs\specifications\estruturacao_versus_gestao_corporativa_paper_v1.md`
- `C:\GestaoVersus\app32\app32\docs\specifications\mapa_formal_versus_gestao_corporativa_v1.md`
- `C:\GestaoVersus\app32\app32\docs\specifications\arquitetura_operacional_squad_cliente_v1.md`
- `C:\GestaoVersus\app32\app32\docs\specifications\arquitetura_operacional_squad_versus_v1.md`
- `C:\GestaoVersus\app32\app32\docs\specifications\mcp_perfis_tools_liberacoes_por_squad_v1.md`
