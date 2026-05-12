# Motor de Testes Operacionais e Cenários Simulados — Empresa-Laboratório Versus v1

## Status
Documento de execução do card `AA.J.16.5`.

## Objetivo
Definir o motor de cenários do laboratório para simular, de forma controlada e reproduzível:
- vendas
- compras
- despesas
- produção/prestação de serviços
- caixa
- metas
- equipe/capacidade
- eventos operacionais e gerenciais

preservando a separação entre:
- **evento de negócio**
- **evento operacional**
- **task/processo de gestão**

---

## 1. Decisão principal
O motor do laboratório deve nascer em duas camadas:

### Camada A — Catálogo de cenários
Fonte estruturada dos eventos simulados.

### Camada B — Ingestão e reflexo no APP32
Responsável por transformar os cenários em:
- registros consumíveis via API/MCP
- reflexos em finanças, indicadores e contexto operacional
- gatilhos de gestão para os squads

---

## 2. Regra arquitetural central
**Task não é o evento primário do negócio.**

Ou seja:
- venda não nasce como task
- compra não nasce como task
- despesa não nasce como task
- fechamento não nasce como task

Esses fatos devem nascer como **evento de negócio**.

As tasks/processos entram depois, como:
- reação operacional
- ação corretiva
- acompanhamento
- governança
- plano de resposta

Essa separação é essencial para não misturar:
- operação do negócio
- gestão da execução
- modelagem do experimento

---

## 3. Modelo de dados conceitual do motor

## 3.1 Evento de negócio
Representa um fato econômico/operacional ocorrido ou simulado.

Exemplos:
- venda realizada
- proposta perdida
- compra de insumo
- despesa administrativa
- contrato fechado
- contrato cancelado
- atraso de fornecedor
- demissão
- admissão
- redução de produtividade

### Campos mínimos esperados
- `company_id`
- `scenario_id`
- `event_type`
- `event_date`
- `business_domain`
- `reference_code`
- `amount` quando aplicável
- `quantity` quando aplicável
- `metadata`
- `source = laboratorio`
- `simulation_cycle`

---

## 3.2 Evento operacional
Representa o efeito do evento de negócio na operação.

Exemplos:
- aumento de backlog
- ruptura de estoque
- atraso de entrega
- queda de capacidade
- aumento de retrabalho
- sobrecarga de equipe

### Campos mínimos esperados
- `company_id`
- `scenario_id`
- `trigger_event_id`
- `operational_effect_type`
- `severity`
- `started_at`
- `expected_duration`
- `metadata`

---

## 3.3 Task/processo de gestão
Representa a ação humana/agentic criada em resposta ao cenário.

Exemplos:
- reunião extraordinária
- renegociar fornecedor
- revisar meta comercial
- redistribuir carga
- abrir projeto de melhoria
- revisar preço
- revisar processo crítico

### Regra
Task de gestão deve nascer **depois** do evento e da análise, nunca como substituta do evento.

---

## 4. Forma recomendada de ingestão

## 4.1 Padrão recomendado para a primeira etapa
A primeira etapa deve usar um modelo híbrido:

### Fonte dos cenários
- **JSON estruturado** como fonte canônica inicial
- **planilha** como apoio operacional de edição/curadoria humana

### Entrada no APP32
- **API/MCP** como via oficial de ingestão

### Saída gerencial
- reflexo nos domínios existentes
- disponibilização do contexto para os squads
- geração posterior de tasks/processos/reuniões quando apropriado

---

## 4.2 Por que não começar só com task/processo
Porque isso geraria três problemas:
1. misturaria fato com resposta
2. degradaria análises causais
3. esconderia o que realmente aconteceu no negócio

---

## 4.3 Por que não começar só com ERP real
Porque neste momento o objetivo é validar:
- arquitetura
- MCP
- squads
- orquestração
- metodologia

Antes de depender de integração real completa.

---

## 5. Domínios de cenário da primeira etapa
O motor deve cobrir, no mínimo:

### 5.1 Comercial
- lead gerado
- proposta emitida
- venda fechada
- venda perdida
- desconto acima da média
- queda de demanda

### 5.2 Financeiro
- recebimento realizado
- recebimento atrasado
- inadimplência
- despesa extraordinária
- aumento de custo de fornecedor
- fechamento com lucro
- fechamento com prejuízo

### 5.3 Operacional
- pedido/ordem recebida
- aumento de backlog
- atraso de entrega
- ruptura de insumo
- retrabalho
- gargalo produtivo

### 5.4 Pessoas / Capacidade
- demissão
- vaga em aberto
- admissão
- novo colaborador com baixa destreza
- absenteísmo
- sobrecarga de equipe

### 5.5 Estratégico
- meta batida
- meta não batida
- meta abaixo da capacidade
- projeto de expansão
- revisão de prioridade

---

## 6. Forma de consumo pelos squads

## 6.1 Squad Cliente
Consome o motor para:
- enxergar fatos operacionais e comerciais
- registrar contexto local
- organizar resposta operacional
- preparar dados para interação com o Squad Versus

## 6.2 Squad Versus
Consome o motor para:
- analisar causas e efeitos
- revisar metas e planos
- provocar correções de processo, estratégia e estrutura
- gerar leitura crítica dos quatro pilares

## 6.3 Engenharia
Consome o motor para:
- observar gaps de capability
- identificar falhas de ingestão
- medir atritos entre evento, MCP, APP32 e squads

---

## 7. Estrutura mínima do catálogo de cenários
Cada cenário deve conter:
- `scenario_code`
- `scenario_name`
- `journey_type` (`A`, `B`, `C`)
- `cycle` (ex.: `mes_01`, `mes_02`)
- `event_type`
- `business_domain`
- `intended_effects`
- `expected_impacted_agents`
- `expected_impacted_kpis`
- `requires_human_review`
- `notes`

---

## 8. Gatilhos esperados no APP32
O motor deve servir para disparar, de forma posterior e governada:
- tarefas de gestão
- reuniões
- revisões de processo
- revisões de meta
- alertas de risco
- análises comparativas
- pedidos de integração/correção

---

## 9. Recomendação técnica para a primeira implementação
### Fase inicial do motor
- catálogo em JSON versionado
- ingestão por MCP/API controlada
- leitura via squads externos
- sem depender inicialmente de ERP real

### Evolução posterior
- conectores para ERP
- ingestão por planilha operacional
- geração automatizada de ciclos mensais
- trilha analítica dos cenários executados

---

## 10. Critérios de aceite do card AA.J.16.5
Este card é considerado atendido quando:
- a arquitetura do motor estiver definida
- a forma de ingestão estiver decidida
- a separação entre evento e task estiver explícita
- os domínios de cenário da primeira etapa estiverem fechados
- o projeto puder avançar para ativação dos runtimes e conectividade dos squads

---

## 11. Próximo passo
Com este fechamento, o próximo passo do projeto é o `AA.J.16.6`:
- ativar Claude, Antigravity e Codex com seus squads
- validar conectividade, startup, profiles e smoke MCP
