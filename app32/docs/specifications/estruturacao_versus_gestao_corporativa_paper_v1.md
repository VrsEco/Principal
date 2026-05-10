# Estruturação Versus Gestão Corporativa

## Status
Paper v3 para amadurecimento executivo, arquitetural e operacional antes da execução.

## Natureza do documento
Este paper tem função de:

- consolidar a visão de estruturação da Versus
- alinhar método, plataforma, agentes e governança
- definir limites entre análise, amadurecimento e execução
- servir como documento-base para discussão, refinamento e futura abertura de frentes executivas no AA.J.1

---

## Resumo executivo
A Versus deve ser estruturada como um sistema operacional de gestão composto por quatro frentes integradas:

1. Forma de Trabalho
2. Ferramenta
3. Agentes
4. Orquestração

A diretriz central é:

- o APP32 deve ser a plataforma oficial de domínio, dados, services, governança e auditabilidade
- o MCP deve ser a interface canônica entre o APP32 e os agentes
- o processamento cognitivo principal do Squad de Work deve acontecer em runtimes externos, como CLI, Claude, Antigravity e equivalentes autorizados
- a Versus deve amadurecer primeiro seu operating model antes de transformar a arquitetura em execução técnica ampla
- a arquitetura de agentes deve contemplar duas famílias complementares: agentes do Squad Versus e agentes do Squad Cliente

---


## Convenção de nomenclatura oficial

Para fins deste projeto, adotam-se os seguintes nomes institucionais:

- `Squad Versus` — conjunto de agentes da Versus voltado a método, estrutura, governança, controladoria, auditoria e visão consultiva
- `Squad Cliente` — conjunto de agentes da empresa cliente voltado a contexto local, rotina, operação interna e execução assistida
- `Squad de Engenharia` — conjunto técnico já existente, responsável por evolução estrutural, correções, sustentação técnica e implementação

Esses nomes devem prevalecer no paper, na arquitetura e na comunicação executiva do projeto.

---

## 1. Tese central
A Versus não deve ser tratada como soma de:

- consultoria
- software
- IA
- automações isoladas

Ela deve ser tratada como um sistema integrado de operação e evolução empresarial.

O valor estratégico da Versus nasce da coerência entre:

- método de trabalho
- plataforma operacional
- workforce digital
- governança de execução

Se uma dessas camadas evoluir em direção diferente das demais, a empresa cresce com drift estrutural.

---

## 2. Objetivo deste projeto
Estruturar a Versus Gestão Corporativa para que ela opere com consistência em quatro frentes:

### 2.1 Forma de Trabalho da Versus
Definir como a Versus:

- vende
- implanta
- estabiliza
- mantém
- mede evolução
- opera marketing e crescimento
- conduz controladoria, processos, projetos, estratégia, indicadores e auditoria

### 2.2 Ferramenta
Definir como o APP32 e seu MCP sustentam a operação real da Versus com segurança, governança e escalabilidade.

### 2.3 Agentes
Definir a arquitetura do Squad de Work e do Squad de Gestão como workforce digital especializado, com papéis, limites e responsabilidades claros.

### 2.4 Orquestração
Definir a camada que coordena pessoas, agentes, capabilities e workflows com critérios de decisão, surface, permissão, auditoria e escalonamento.

---

## 3. Estrutura macro da Versus
A arquitetura alvo da Versus deve ser lida nesta hierarquia:

### 3.1 Forma de Trabalho
Camada-mãe.

Define:

- operating model
- fases de atendimento
- entregáveis
- ritos
- papéis
- critérios de avanço
- indicadores de sucesso

### 3.2 Ferramenta
Camada de materialização operacional.

Subdividida em:

#### 3.2.1 APP32
Responsável por:

- domínio de negócio
- banco de dados
- services
- workflows determinísticos
- dashboards
- trilhas e evidências
- multi-tenancy com `company_id`

#### 3.2.2 MCP
Responsável por:

- capability registry
- contratos operacionais
- tools canônicas
- surfaces (`user`, `admin`, `analytics`, `ops`)
- RBAC / permission matrix
- human gate
- auditoria de execução
- interface segura para agentes externos

### 3.3 Agentes
Camada de workforce digital.

Os agentes devem ser tratados como papéis operacionais digitais, e não como personagens genéricos.

### 3.4 Orquestração
Camada de coordenação do sistema.

Define:

- roteamento
- composição de agentes
- handoffs
- prioridades
- escalonamento
- critérios de aprovação
- surface correta de execução

---

## 4. Premissa arquitetural dos agentes

### 4.1 Princípio oficial
O Squad de Work deve usar os tokens/capacidade de processamento de runtimes externos, como:

- CLI
- Claude
- Antigravity
- equivalentes autorizados

E não depender, como arquitetura principal, do runtime interno de IA da Versus.

### 4.2 Consequência prática
O APP32 não deve ser o cérebro principal dos agentes.

O APP32 deve ser:

- fonte da verdade
- camada de domínio
- camada de services
- camada MCP
- camada de governança
- camada de auditoria

O runtime externo deve ser:

- cérebro
- reasoning engine
- orquestrador cognitivo
- consumidor das capabilities MCP do APP32

### 4.3 Regra de transição
Devemos caminhar de:

- `agent runtime in-app`

para:

- `agent runtime external + MCP-first`

O runtime interno atual pode continuar como:

- fallback
- homologação
- laboratório
- contingência

Mas não como desenho principal da arquitetura futura.

---

## 5. Arquitetura-base dos agentes

### 5.1 Agentes-alvo do Squad Versus
Arquitetura-base sugerida:

- `sapiens`
- `strategist_versus`
- `pmo_controller_versus`
- `business_architect_versus`
- `operations_versus`
- `followup_collector_versus`
- `performance_analyst_versus`
- `finance_versus`
- `auditor_versus`
- `feedback_coach_versus` (fase posterior)

### 5.2 Regras estruturais

#### Regra 1
Agentes de produção devem consumir capabilities canônicas do APP32 via MCP.

#### Regra 2
Agentes não devem operar o domínio por caminhos paralelos ao MCP quando houver capability oficial.

#### Regra 3
Agentes de leitura analítica e agentes de mutação operacional devem ter fronteiras explícitas.

#### Regra 4
Agentes de auditoria devem ser desenhados como `read-only` por princípio.

#### Regra 5
Agentes não devem ser inventados por estética de prompt; devem nascer de papéis reais do operating model da Versus.

---

## 6. Dualidade de agentes: Squad Versus + Squad Cliente

### 6.1 Princípio
A arquitetura futura não deve possuir apenas agentes da Versus.

Ela deve contemplar duas famílias complementares:

#### Família A — Squad Versus
Foco em:

- método
- consultoria
- estrutura
- governança
- controladoria
- auditoria
- visão externa e sistêmica

#### Família B — Squad Cliente
Foco em:

- contexto local
- operação interna
- prioridades do negócio
- linguagem da empresa
- conexão com os pares humanos do cliente
- execução assistida

### 6.2 Objetivo da dualidade
Essa dualidade permite que:

- a inteligência não fique apenas “de fora para dentro”
- o cliente tenha agentes aderentes à sua realidade operacional
- a Versus mantenha seu papel de arquitetura, orientação, crítica e governança
- a operação seja enriquecida pela interação entre método Versus e contexto local do cliente

### 6.3 Regra central
Agente da Versus e agente do cliente não devem ser clones concorrentes.

Eles devem ter papéis complementares.

---

## 7. Famílias de agentes e seus papéis

### 7.1 Agentes do Squad Versus
Entram como:

- estruturadores
- provocadores
- revisores
- orientadores
- controladores
- auditores
- guardiões do método

### 7.2 Agentes do Squad Cliente
Entram como:

- intérpretes do negócio local
- operadores contextuais
- organizadores da rotina
- ponte com os humanos da empresa
- preparadores da execução
- sintetizadores do contexto interno

### 7.3 Regra de valor
A Versus passa a operar não apenas com “agentes da Versus”, mas com uma malha híbrida de inteligência entre consultoria e cliente.

---

## 8. Pares por domínio

### 8.1 Comercial
- `commercial_cliente`
- `strategist_versus` ou futura derivação de crescimento

### 8.2 Operacional
- `operational_cliente`
- `operations_versus`
- `business_architect_versus`

### 8.3 Administrativo / Financeiro
- `admfin_cliente`
- `finance_versus`
- `auditor_versus`

### 8.4 Estratégico
- `strategic_cliente`
- `strategist_versus`
- `pmo_controller_versus`

### 8.5 Auditoria
- `auditor_cliente`
- `auditor_versus`

### 8.6 Observação importante
O par por domínio não significa simetria de autoridade. Significa complementaridade funcional.

---

## 9. Regras de precedência

### 9.1 Agente do cliente tem precedência em:

- contexto local
- rotina diária
- linguagem interna do negócio
- prioridade operacional imediata

### 9.2 Agente da Versus tem precedência em:

- método
- governança
- estrutura
- controladoria
- crítica sistêmica
- auditoria
- coerência arquitetural

### 9.3 Humano do cliente tem precedência em:

- decisão de negócio local
- validação operacional
- aceitação prática

### 9.4 Consultor da Versus tem precedência em:

- condução metodológica
- arbitragem estrutural
- evolução da conta
- escalonamento consultivo
- direção da implantação e amadurecimento

---

## 10. Coprodução humano + agente

### 10.1 Princípio
A arquitetura da Versus deve reconhecer a coprodução humano + agente como parte do operating model, e não como exceção.

### 10.2 Forma de trabalho híbrida
Devem existir atividades executadas em conjunto por:

- humano do cliente + agente do cliente
- consultor da Versus + agente da Versus
- humano do cliente + agente do cliente + agente da Versus
- consultor da Versus + agente da Versus + agente do cliente

### 10.3 Benefício esperado
Essa coprodução tende a elevar:

- qualidade
- velocidade
- contexto
- disciplina
- rastreabilidade
- consistência de execução

### 10.4 Regra estrutural
Sempre que possível, a atividade deve permitir evidência clara de:

- qual parte foi humana
- qual parte foi agentic
- qual capability foi usada
- quem validou
- qual foi o resultado final

---

## 11. Implicações para APP32, MCP e Orquestração

### 11.1 APP32
O APP32 deixa de ser apenas um sistema da Versus e passa a ser o espaço operacional onde convivem:

- método Versus
- operação do cliente
- humanos
- agentes
- trilhas de execução

### 11.2 MCP
O MCP precisa sustentar não apenas agentes da Versus, mas também agentes do cliente, com:

- surfaces corretas
- isolamento tenant-safe
- papéis distintos
- governança por capability
- trilha completa de auditoria

### 11.3 Orquestração
A orquestração passa a responder também:

- quando entra o agente do cliente
- quando entra o agente da Versus
- quando o humano precisa assumir
- quando a atividade é coproduzida
- como resolver divergência entre contexto local e método
- quem aprova, quem executa e quem audita

---

## 12. Estrutura dos Squads da Versus Gestão Corporativa

### 12.1 Visão geral
A arquitetura da Versus Gestão Corporativa passa a reconhecer três conjuntos formais de atuação:

- `Squad Versus`
- `Squad Cliente`
- `Squad de Engenharia`

Esses três squads não são equivalentes nem intercambiáveis. Eles compõem uma malha coordenada de método, operação, tecnologia e evolução contínua.

### 12.2 Squad Versus
#### Missão
Atuar como núcleo consultivo, metodológico e governante da arquitetura de gestão.

#### Responsabilidade principal
- formular direção e crítica sistêmica
- estruturar processos, controladoria, estratégia e governança
- orientar a execução do cliente com visão externa e disciplinada
- auditar aderência, risco e consistência

#### Exemplos de agentes
- `sapiens`
- `strategist_versus`
- `pmo_controller_versus`
- `business_architect_versus`
- `operations_versus`
- `performance_analyst_versus`
- `finance_versus`
- `auditor_versus`

### 12.3 Squad Cliente
#### Missão
Atuar como núcleo contextual e operacional do negócio do cliente, conectado à realidade diária da empresa.

#### Responsabilidade principal
- organizar contexto local e rotina interna
- apoiar execução, cobrança e priorização diária
- traduzir linguagem, urgência e restrições reais da empresa
- servir de ponte entre o método da Versus e a prática do cliente

#### Exemplos de agentes
- `commercial_cliente`
- `operational_cliente`
- `admfin_cliente`
- `strategic_cliente`
- `auditor_cliente`

### 12.4 Squad de Engenharia
#### Missão
Projetar, implementar, sustentar e evoluir a infraestrutura técnica da Versus Gestão Corporativa.

#### Responsabilidade principal
- evoluir APP32, MCP, catálogo de capabilities e governança técnica
- implementar integrações, contratos, observabilidade e controles
- sustentar qualidade, segurança, performance e auditabilidade
- transformar diretrizes arquiteturais em entregas incrementais reais

#### Observação
O Squad de Engenharia não substitui o Squad Versus nem o Squad Cliente. Ele viabiliza tecnicamente a operação dos dois.

### 12.5 Fronteiras entre os squads
#### Squad Versus
Tem foco em método, governança, estrutura, crítica, desenho e auditoria.

#### Squad Cliente
Tem foco em contexto local, rotina, execução assistida e aderência à realidade operacional.

#### Squad de Engenharia
Tem foco em plataforma, capabilities, contratos, runtime, qualidade técnica e sustentação evolutiva.

#### Regra estrutural
Nenhum squad deve absorver integralmente a função do outro. O valor da arquitetura nasce da cooperação com fronteiras claras.

### 12.6 Relação entre humanos e squads
#### Consultor da Versus
Relaciona-se prioritariamente com o `Squad Versus`, mas também arbitra interações com o `Squad Cliente` quando há conflito metodológico, necessidade de escalonamento ou definição de rumo.

#### Humano do cliente
Relaciona-se prioritariamente com o `Squad Cliente`, validando, corrigindo e contextualizando a execução cotidiana.

#### Coprodução
Atividades críticas podem envolver combinação coordenada entre:
- humano do cliente
- agente do `Squad Cliente`
- consultor da Versus
- agente do `Squad Versus`

#### Engenharia
O `Squad de Engenharia` atua como camada de suporte e evolução, garantindo que a coprodução ocorra sobre uma plataforma coerente, auditável e segura.

### 12.7 Relação entre APP32, MCP e os squads
#### APP32
É a base operacional comum dos três squads: domínio, dados, serviços, trilhas, dashboards e governança.

#### MCP
É a interface canônica de acesso agentic ao APP32. Tanto o `Squad Versus` quanto o `Squad Cliente` devem consumir capabilities oficiais via MCP, respeitando surface, papel, tenant e trilha de auditoria.

#### Orquestração
A orquestração coordena quando cada squad entra, qual capability pode usar, quando há handoff para humano e como conflitos são resolvidos.

#### Runtime externo
O raciocínio principal dos agentes continua externo ao APP32. O `Squad de Engenharia` sustenta essa arquitetura; o `Squad Versus` a governa; o `Squad Cliente` a utiliza na prática operacional.

---

## 13. Modelo Operacional de Uso dos Squads

### 13.1 Princípio operacional
O `Squad Versus` e o `Squad Cliente` não devem ter seu raciocínio principal executado dentro do APP32.

O desenho-alvo é:

- `Squad Versus` rodando em runtime externo da Versus
- `Squad Cliente` rodando em runtime externo do cliente
- `APP32` como base comum de domínio, estado operacional, governança e auditoria
- `MCP` como interface canônica de integração entre os runtimes e o APP32

### 13.2 Papel do consultor da Versus
O consultor da Versus opera, supervisiona e evolui o uso do `Squad Versus`.

Na prática, isso significa:

- utilizar um runtime externo autorizado, como CLI, Claude, Antigravity ou equivalente
- acionar agentes do `Squad Versus` conforme o tipo de trabalho
- consumir capabilities oficiais do APP32 via MCP
- interpretar os resultados à luz da metodologia da Versus
- arbitrar conflitos entre contexto local e método

### 13.3 Papel do cliente
O cliente utiliza o `Squad Cliente` como camada de apoio à sua operação real.

Na prática, isso significa:

- operar agentes aderentes à sua rotina e ao seu negócio
- registrar, consultar e atualizar contexto operacional por capabilities do APP32
- interagir com pares humanos da empresa em atividades de rotina, cobrança, preparação e execução assistida
- levar contexto qualificado para posterior interação com o `Squad Versus`

### 13.4 Papel do APP32 e do MCP
O APP32 não é a casa principal do reasoning dos agentes.

O APP32 deve ser:

- fonte da verdade
- camada de domínio e serviços
- base de dados e evidências
- motor de workflows determinísticos
- repositório de trilhas, dashboards, aprovações e objetos colaborativos

O MCP deve ser:

- a interface oficial entre os runtimes externos e o APP32
- o ponto de aplicação de surface, papel, escopo e capacidade
- a camada de governança e auditabilidade da atuação agentic

### 13.5 Regra de integração
A integração correta não é, em regra, `CLI Versus ↔ CLI Cliente` diretamente.

A integração preferencial é:

- `Runtime Versus → MCP/APP32`
- `Runtime Cliente → MCP/APP32`

Quando um lado precisar interagir com o outro, isso deve ocorrer por meio de:

- estado compartilhado governado no APP32
- evidências registradas
- objetos colaborativos
- trilhas de execução
- aprovações e handoffs auditáveis

### 13.6 Modelos operacionais possíveis
#### Modelo A — Centralizado na Versus
Características:

- a Versus opera os agentes principais
- o cliente interage mais por interface e mediação humana
- menor autonomia do cliente
- menor complexidade inicial

#### Modelo B — Híbrido assistido
Características:

- a Versus opera plenamente o `Squad Versus`
- o cliente começa a operar partes do `Squad Cliente`
- há coprodução progressiva
- o APP32 se consolida como hub operacional comum
- equilíbrio entre governança e adoção realista

#### Modelo C — Distribuído pleno
Características:

- a Versus opera seu próprio runtime e seu próprio squad
- o cliente opera seu próprio runtime e seu próprio squad
- ambos consomem MCP/APP32 como núcleo comum
- maior autonomia, maior riqueza operacional e maior complexidade governante

### 13.7 Recomendação de adoção
A recomendação atual é:

- tratar o `Modelo C` como arquitetura-alvo
- iniciar a implantação pelo `Modelo B`
- usar o `Modelo A` apenas quando necessário por limitação de maturidade do cliente ou por fase inicial da conta

Essa recomendação reduz fricção sem sacrificar a arquitetura futura.

### 13.8 Pré-requisitos para o modelo distribuído
Antes da adoção plena do modelo distribuído, a Versus precisa amadurecer:

- identidade distinta para humano do cliente, agente do cliente, humano da Versus, agente da Versus e perfis de engenharia
- autenticação e autorização por papel, surface e empresa
- capabilities MCP canônicas suficientes para operação real
- trilha de auditoria por ator, runtime, capability e resultado
- objetos colaborativos no APP32 para análise, parecer, pendência, revisão, aprovação e handoff

### 13.9 Veredito operacional
O uso dos squads deve evoluir como malha distribuída e governada:

- runtime externo para reasoning
- APP32 como núcleo operacional comum
- MCP como contrato canônico de integração
- humanos e agentes atuando em coprodução progressiva

---

## 14. Modo de Utilização Assistida

### 14.1 Princípio
A arquitetura da Versus Gestão Corporativa deve reconhecer que parte relevante dos usuários não estará pronta, desde o primeiro momento, para explorar plenamente o potencial do `Squad Cliente`, do `Squad Versus` e do `APP32`.

Por isso, o uso dos squads deve começar, quando necessário, em modo de utilização assistida.

### 14.2 Objetivo
O objetivo do modo de utilização assistida é:

- apoiar o usuário na execução do trabalho
- ensinar o usuário a interagir melhor com os agentes
- ensinar o usuário a utilizar melhor o APP32
- ampliar progressivamente a autonomia operacional e decisória
- reduzir fricção de adoção sem comprometer governança

### 14.3 Tese operacional
O squad não deve apenas trabalhar para o usuário.

Ele deve também:

- ajudar o usuário a formular melhor demandas
- sugerir caminhos mais adequados
- revelar capacidades pouco conhecidas do APP32
- orientar o uso correto dos agentes
- transferir repertório operacional ao longo do tempo

### 14.4 Fases de maturidade do uso assistido
#### Fase 1 — Condução forte
Contexto típico:

- usuário iniciante
- conta em início de implantação
- baixa familiaridade com agentes
- baixa familiaridade com o APP32

Postura esperada do squad:

- orientar passo a passo
- explicar opções e limites
- estruturar pedidos mal formulados
- sugerir próximos movimentos
- reduzir ambiguidade operacional

#### Fase 2 — Coprodução orientada
Contexto típico:

- usuário com familiaridade parcial
- uso recorrente, mas ainda inconsistente
- boa intenção com necessidade de apoio frequente

Postura esperada do squad:

- complementar raciocínio
- organizar execução
- revisar solicitações
- alertar sobre riscos, omissões e dependências
- acelerar a operação sem tomar todo o protagonismo

#### Fase 3 — Autonomia assistida
Contexto típico:

- usuário maduro
- boa compreensão da operação
- boa capacidade de condução do trabalho com apoio pontual

Postura esperada do squad:

- atuar de forma mais enxuta
- ser mais contextual do que didático
- acelerar decisões e execução
- entrar por exceção, revisão, síntese e ganho de performance

### 14.5 Posturas operacionais do squad
#### Postura tutora
Usada quando há baixa maturidade do usuário ou alta complexidade do fluxo.

Função principal:

- explicar
- orientar
- educar
- traduzir o sistema
- conduzir a interação

#### Postura copiloto
Usada quando o usuário já participa ativamente, mas se beneficia de apoio cognitivo e estrutural.

Função principal:

- complementar
- organizar
- alertar
- proteger contra erros
- ampliar capacidade do usuário

#### Postura executora assistida
Usada quando a demanda está clara, o contexto está maduro e a governança permite ação mais direta.

Função principal:

- executar com segurança
- registrar evidências
- confirmar decisões relevantes
- devolver rastreabilidade e resultado

### 14.6 Regra de evolução
O modo assistido não deve gerar dependência permanente.

Sua finalidade é:

- elevar maturidade
- transferir autonomia
- melhorar qualidade de interação
- tornar o uso do APP32 e dos squads cada vez mais natural

Em outras palavras, o objetivo do assistido é formar autonomia aumentada, e não aprisionar o usuário em tutela contínua.

### 14.7 Relação com o Sapiens e com a entrada da experiência
A camada de entrada, especialmente o `sapiens`, deve assumir papel relevante na utilização assistida.

Essa camada deve:

- receber o usuário com baixo atrito
- traduzir intenção em caminhos operacionais
- sugerir capacidades e fluxos úteis
- orientar a formulação do pedido
- ajudar na descoberta gradual do potencial do APP32 e dos squads

### 14.8 Relação com onboarding e adoção
O modo de utilização assistida deve ser tratado como parte formal do onboarding operacional da conta.

Ele deve apoiar:

- primeiros usos
- formação de hábito
- ganho de confiança
- descoberta de valor
- transição do uso guiado para o uso mais autônomo

### 14.9 Veredito
A utilização assistida não é detalhe de interface. Ela é parte do operating model.

Sem ela, a Versus corre o risco de ter uma arquitetura tecnicamente forte, porém com adoção fria, subuso do APP32 e frustração na experiência inicial com os squads.

---

## 15. Modelo de Maturidade Assistida

### 15.1 Princípio
A utilização assistida não deve evoluir para dependência permanente nem para uma relação paternalista entre usuário e squad.

Para evitar esse risco, a Versus deve estruturar um modelo formal de maturidade assistida, capaz de medir e desenvolver a qualidade de uso do `APP32`, do `Squad Cliente` e do `Squad Versus`.

### 15.2 Objetivo
O modelo de maturidade assistida deve servir para:

- transformar uso assistido em trajetória de crescimento
- aumentar autonomia com responsabilidade
- melhorar a qualidade de interação com o APP32 e com os squads
- orientar onboarding, adoção e evolução contínua
- reduzir dependência improdutiva dos agentes

### 15.3 Regra conceitual
O foco não deve ser “gamificação” no sentido superficial.

O foco deve ser um modelo de progressão profissional e operacional assistida, com elementos de motivação e reconhecimento, mas ancorado em:

- maturidade real
- autonomia crescente
- qualidade de uso
- aderência metodológica
- responsabilidade operacional

### 15.4 Público-alvo
O modelo deve considerar, no mínimo, dois grandes grupos:

#### Consultores da Versus
Avaliados quanto à maturidade no uso da metodologia, do `APP32`, do `Squad Versus` e da condução do cliente em ambiente híbrido humano + agente.

#### Usuários da empresa cliente
Avaliados quanto à maturidade no uso do `APP32`, do `Squad Cliente`, da rotina operacional assistida e da capacidade de conduzir trabalho com autonomia progressiva.

### 15.5 Dimensões de maturidade
#### Para usuários da empresa cliente
Dimensões sugeridas:

- uso do `APP32`
- uso do `Squad Cliente`
- qualidade de solicitação e formulação de demanda
- autonomia operacional
- disciplina de execução
- uso correto de governança, aprovação e rastreabilidade

#### Para consultores da Versus
Dimensões sugeridas:

- uso metodológico do `APP32`
- uso do `Squad Versus`
- qualidade de condução assistida
- capacidade de orquestração humano + agente
- capacidade de formar autonomia no cliente
- aderência arquitetural e governante

### 15.6 Níveis de maturidade sugeridos
#### Nível 1 — Assistido
- depende de condução forte
- precisa de explicação frequente
- possui baixa familiaridade com APP32 e squads

#### Nível 2 — Orientado
- já executa com apoio recorrente
- consegue seguir fluxos com ajuda
- começa a formular melhor suas demandas

#### Nível 3 — Copiloto
- trabalha bem com o squad
- já utiliza o APP32 com mais consistência
- recebe apoio mais estrutural do que tutorial

#### Nível 4 — Autônomo
- conduz interações com qualidade
- usa os recursos com boa disciplina
- necessita pouco suporte didático

#### Nível 5 — Multiplicador
- opera com alta maturidade
- ajuda a formar outras pessoas
- pode funcionar como referência de uso qualificado

### 15.7 Efeito na experiência
A maturidade deve alterar a experiência real do usuário.

Exemplos:

- usuários iniciantes recebem mais explicação e mais condução
- usuários intermediários recebem mais apoio contextual e menos tutorial
- usuários avançados recebem mais velocidade, mais autonomia e menos atrito

Se a maturidade não modificar a experiência, ela tende a virar apenas adereço cosmético.

### 15.8 O que não deve ser medido como maturidade
O modelo não deve premiar sinais vazios como:

- volume bruto de mensagens
- quantidade de cliques
- frequência de uso sem qualidade
- dependência excessiva do assistido
- interação contínua sem ganho de autonomia

### 15.9 O que deve ser valorizado
O modelo deve valorizar sinais como:

- melhor formulação de pedidos
- uso mais correto dos fluxos e capacidades
- redução de retrabalho
- boa rastreabilidade
- melhor decisão assistida
- maior autonomia com responsabilidade
- capacidade de aprender com o uso

### 15.10 Cuidados de desenho
O modelo de maturidade assistida deve evitar:

- infantilização da experiência
- ranking público tóxico
- competição artificial entre pessoas
- premiação de volume em vez de qualidade
- captura política do sistema de maturidade

A comparação mais importante deve ser a evolução do próprio usuário ao longo do tempo, e não a exposição agressiva frente aos demais.

### 15.11 Relação com o modo de utilização assistida
O modelo de maturidade assistida complementa o modo de utilização assistida.

Na prática:

- o modo assistido define como o squad se comporta
- o modelo de maturidade define como o usuário evolui
- juntos, ambos evitam que a assistência se transforme em tutela permanente

### 15.12 Veredito
A criação de um modelo de maturidade assistida é uma resposta arquitetural forte ao risco de paternalismo.

Se bem desenhado, ele transforma a assistência em escada de evolução, e não em acomodação operacional.

---

## 16. Papel esperado de cada frente

## 16.1 Forma de Trabalho
É a camada que responde:

- como a Versus trabalha de verdade
- quais fases existem
- quem faz o quê
- o que é urgência, implantação, estabilização, manutenção e evolução
- como marketing, estratégia, operação e governança se conectam

### Veredito
É a frente prioritária. Sem ela, as demais camadas apenas automatizam ambiguidade.

## 16.2 Ferramenta
É a camada que materializa a operação da Versus.

### APP32
Deve representar a operação real.

### MCP
Deve ser a interface oficial de execução dos agentes.

### Veredito
A Ferramenta não pode evoluir só por acúmulo de features. Ela precisa evoluir como plataforma coerente da metodologia Versus.

## 16.3 Agentes
São a workforce digital da Versus e da empresa cliente.

### Veredito
Devem ser especializados, auditáveis, governados e coerentes com a capacidade real do APP32.

## 16.4 Orquestração
É a camada que transforma componentes em sistema.

### Veredito
Sem orquestração, haverá método sem execução, app sem coerência e agentes sem contexto.

---

## 17. Classificação arquitetural provisória

### 17.1 Principal
Itens que devem compor a arquitetura oficial-alvo:

- Forma de Trabalho explicitada
- APP32 como domínio e governança
- MCP como interface canônica dos agentes
- runtime externo como cérebro do Squad
- arquitetura dual de agentes: Squad Versus + Squad Cliente
- coprodução humano + agente como parte do operating model
- orquestração externa como camada principal de reasoning

### 17.2 Fallback
Itens que podem continuar, mas não como desenho principal:

- runtime interno do APP32 para agentes
- supervisor interno como contingência
- fluxos internos de homologação agentic

### 17.3 Legado
Itens que devem ser avaliados com cautela por possível desalinhamento futuro:

- acoplamento excessivo entre chat interno e runtime oficial
- agent runtime in-app como arquitetura dominante
- capabilities relevantes fora do catálogo canônico MCP

### 17.4 Alvo futuro
Itens que dependem de amadurecimento adicional:

- consolidação de controladoria/PMO como agente formal
- performance analyst plenamente apoiado por read models e analytics canônicos
- feedback coach com domínio próprio de people/performance mais maduro
- política formal de governança de tokens, runtime e auditoria por ambiente
- maturação da família completa de agentes do cliente por domínio

---

## 18. Critérios para sair do modo “amadurecimento” e entrar em “execução”
A execução técnica ampla só deve começar quando os seguintes critérios mínimos estiverem claros:

### C1 — Operating Model explícito
A Versus precisa ter definição suficientemente clara de:

- fases
- papéis
- entregáveis
- governança
- objetivos por frente

### C2 — Hierarquia arquitetural aprovada
Precisa estar consolidada a hierarquia:

- Forma de Trabalho
- Ferramenta
  - APP32
  - MCP
- Agentes
  - Versus
  - Cliente
- Orquestração

### C3 — Premissa de runtime aprovada
Precisa estar decidido formalmente que:

- o runtime principal dos agentes é externo
- o APP32 é domínio + MCP + governança
- o runtime interno é fallback/laboratório/contingência

### C4 — Mapa de capabilities priorizado
Precisa existir um mapa inicial de:

- capabilities já maduras
- capabilities faltantes
- capabilities legadas a revisar

### C5 — Fronteiras de execução definidas
Precisa estar claro:

- o que é análise
- o que é estruturação
- o que é execução
- o que exige human gate
- o que é `read-only`
- o que é mutação operacional
- o que é papel do Squad Cliente
- o que é papel do Squad Versus

---

## 19. Questões críticas ainda em aberto
Este paper ainda precisa amadurecer resposta para as questões abaixo:

1. Qual é o operating model oficial da Versus?
2. Como o marketing entra formalmente na arquitetura da Forma de Trabalho?
3. Quais capabilities do APP32 já estão maduras para agentes externos?
4. Quais domínios ainda dependem de superfície legada/interna?
5. Como separar produção, fallback, laboratório e contingência?
6. Como institucionalizar controladoria/PMO dentro da arquitetura?
7. Qual é a política formal de governança de tokens, surfaces e auditoria?
8. Como será a evolução incremental do Squad sem quebrar a governança?
9. Quais agentes do cliente entram primeiro por domínio?
10. Como será a política de precedência e arbitragem em conflitos entre agente do cliente e agente da Versus?

---

## 20. Hipóteses de trabalho

### H1
A Versus precisa ser tratada como sistema integrado de operação, e não como soma de consultoria + app + IA.

### H2
A camada de Forma de Trabalho deve preceder e orientar a evolução das demais frentes.

### H3
O MCP deve ser a interface oficial entre APP32 e workforce digital.

### H4
O Squad de Work principal deve ser external-runtime-first.

### H5
A arquitetura do Squad de Gestão deve refletir a oferta real da Versus: controladoria, processos, projetos, estratégia, indicadores, finanças e auditoria.

### H6
O APP32 deve deixar de ser visto como local principal de inferência e ser consolidado como plataforma operacional governada.

### H7
A dualidade de agentes Squad Versus + Squad Cliente aumenta aderência, autonomia e qualidade da execução quando as fronteiras são claras.

---

## 21. Roadmap de amadurecimento

### Etapa A — Consolidação conceitual
- revisar e refinar este paper
- alinhar nomenclaturas
- estabilizar premissas

### Etapa B — Mapa formal da Versus
- detalhar as 4 frentes
- definir relações e dependências
- classificar principal, fallback, legado e alvo futuro

### Etapa C — Mapa de capabilities
- inventariar capabilities do APP32/MCP
- classificar por maturidade e risco
- identificar gaps para agentes externos

### Etapa D — Arquitetura operacional dos agentes
- definir agentes oficiais do Squad Versus
- definir família inicial de agentes do Squad Cliente
- definir limites por agente
- definir policy de surfaces e human gates
- definir modelo de coprodução humano + agente

### Etapa E — Só então execução técnica
- abrir cards de execução
- priorizar frentes
- implementar incrementalmente

---

## 22. Decisão provisória
Até segunda ordem, este projeto deve permanecer em modo de:

- análise
- estruturação
- amadurecimento arquitetural
- consolidação executiva

E não em modo de execução técnica direta.

---

## 23. Resultado esperado deste paper
Ao final do amadurecimento, este documento deve permitir:

- explicar a arquitetura da Versus para liderança e engenharia
- orientar priorização de projetos no AA.J.1
- servir como base para mapa formal da Versus
- orientar a separação entre principal, fallback, legado e alvo futuro
- reduzir ambiguidade antes da abertura de execução
- orientar a construção da malha híbrida de inteligência entre Versus e empresa cliente
