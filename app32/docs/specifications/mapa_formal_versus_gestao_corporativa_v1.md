# Mapa Formal da Versus Gestão Corporativa

## Status
Versão formal v1 derivada do paper `C:/GestaoVersus/app32/app32/docs/specifications/estruturacao_versus_gestao_corporativa_paper_v1.md`.

## Natureza do documento
Este documento é a referência formal da arquitetura da Versus Gestão Corporativa.

Seu papel é:
- consolidar a visão oficial da Versus
- estabilizar conceitos, blocos e responsabilidades
- servir como base para priorização executiva, produto e engenharia
- orientar a passagem de amadurecimento para execução

---

## 1. Visão formal da Versus Gestão Corporativa
A Versus Gestão Corporativa é um sistema integrado de operação empresarial apoiado por quatro frentes estruturais:

1. `Forma de Trabalho`
2. `Ferramenta`
3. `Agentes`
4. `Orquestração`

Essas quatro frentes operam sobre princípios transversais:
- multi-tenancy obrigatório com `company_id`
- `MCP First` para atuação agentic e estado operacional
- runtime externo como padrão de reasoning dos squads
- governança, rastreabilidade e auditabilidade por desenho
- coprodução progressiva entre humanos e agentes

---

## 2. Estrutura oficial do mapa

### 2.1 Forma de Trabalho
Camada que define como a Versus trabalha, entrega, acompanha e evolui contas, projetos e operações.

### 2.2 Ferramenta
Camada que materializa a operação em `APP32 + MCP`, com domínio, dados, services, dashboards, capabilities e governança.

### 2.3 Agentes
Camada de workforce digital composta por `Squad Versus`, `Squad Cliente` e `Squad de Engenharia`.

### 2.4 Orquestração
Camada que coordena papéis humanos, squads, capabilities, workflows, aprovações e handoffs.

---

## 3. Princípios arquiteturais permanentes

### 3.1 APP32 como núcleo operacional
O `APP32` é a base comum de domínio, dados, trilhas, workflows determinísticos, dashboards, aprovações e objetos colaborativos.

### 3.2 MCP como contrato canônico
O `MCP` é a interface oficial entre os runtimes externos e o APP32.

Ele concentra:
- capability registry
- contracts
- surfaces
- RBAC / permission matrix
- human gate
- trilha de auditoria

### 3.3 Runtime externo como padrão
O reasoning principal dos agentes deve ocorrer em runtimes externos autorizados, como CLI, Claude, Antigravity e equivalentes.

### 3.4 Governança por desenho
Toda ação relevante deve preservar:
- identidade do ator
- papel do ator
- `company_id`
- capability utilizada
- surface utilizada
- evidência do resultado

### 3.5 Assistência como escada de autonomia
Utilização assistida e maturidade assistida são partes formais do operating model, não apenas recursos de interface.

---

## 4. Forma de Trabalho

### 4.1 Objetivo
Definir o operating model oficial da Versus, isto é, como a empresa vende, implanta, estabiliza, acompanha, governa e evolui o trabalho junto aos clientes.

### 4.2 Escopo
Inclui:
- estratégia
- marketing
- implantação
- estabilização
- operação recorrente
- projetos
- processos
- controladoria
- indicadores
- auditoria
- evolução da conta

### 4.3 Componentes principais
- fases do relacionamento
- ritos de gestão
- entregáveis por fase
- papéis internos da Versus
- papéis do cliente
- critérios de avanço
- indicadores de sucesso
- critérios de escalonamento

### 4.4 Responsabilidades
- dar coerência metodológica à Versus
- evitar drift entre consultoria, software, agentes e operação
- orientar o desenho da ferramenta e dos squads
- servir como referência para implantação e sustentação

### 4.5 Riscos principais
- método implícito demais
- dependência excessiva de pessoas-chave
- diferença entre discurso comercial e entrega real
- automação de ambiguidade

### 4.6 Dependências
- consenso executivo
- clareza de serviços e fases
- tradução do método para APP32, MCP e squads

### 4.7 Critérios de maturidade
A Forma de Trabalho é considerada madura quando houver:
- fases explícitas
- papéis claros
- ritos definidos
- entregáveis por etapa
- critérios de avanço e governança formalizados

---

## 5. Ferramenta

### 5.1 Objetivo
Materializar a operação da Versus e do cliente em uma plataforma governada, auditável e escalável.

### 5.2 Escopo
A Ferramenta é composta por:
- `APP32`
- `MCP`
- catálogo de capabilities
- surfaces e permissionamento
- trilhas e observabilidade
- objetos colaborativos

### 5.3 APP32
#### Papel
- domínio de negócio
- banco de dados
- services
- workflows determinísticos
- dashboards
- evidências
- aprovações
- multi-tenancy com `company_id`

#### Riscos
- acúmulo de features sem coerência
- domínios fortes com pouca integração
- superfícies legadas paralelas ao MCP

### 5.4 MCP
#### Papel
- interface canônica dos squads
- exposição formal de capabilities
- aplicação de surface, papel e tenant
- auditabilidade da atuação agentic

#### Riscos
- catálogo incompleto
- drift entre capability, policy e permissionamento
- mutações sensíveis fora da surface correta

### 5.5 Responsabilidades da Ferramenta
- sustentar a operação real
- permitir atuação segura dos squads
- registrar rastreabilidade ponta a ponta
- reduzir dependência de fluxos paralelos não governados

### 5.6 Dependências
- mapa de capabilities
- contratos estáveis por domínio
- governança de runtime e identidade
- priorização arquitetural contínua

### 5.7 Critérios de maturidade
A Ferramenta é considerada madura quando houver:
- capabilities canônicas suficientes
- uso consistente de MCP
- trilha confiável por ator e ação
- baixa dependência de rotas e acessos paralelos

---

## 6. Agentes

### 6.1 Objetivo
Constituir a workforce digital da Versus Gestão Corporativa com fronteiras, responsabilidades e mecanismos de cooperação claros.

### 6.2 Estrutura oficial
A camada de Agentes é composta por três conjuntos:
- `Squad Versus`
- `Squad Cliente`
- `Squad de Engenharia`

A implementação operacional desses conjuntos deve separar:
- **agente** como papel funcional
- **harness** como invólucro operacional governado

### 6.3 Squad Versus
#### Missão
Atuar como núcleo consultivo, metodológico e governante.

#### Exemplos de agentes
- `sapiens`
- `strategist_versus`
- `pmo_controller_versus`
- `business_architect_versus`
- `operations_versus`
- `followup_collector_versus`
- `performance_analyst_versus`
- `finance_versus`
- `auditor_versus`

#### Responsabilidades
- direção e crítica sistêmica
- estruturação de processos e governança
- controladoria e acompanhamento
- auditoria e coerência metodológica

### 6.4 Squad Cliente
#### Missão
Atuar como núcleo contextual e operacional do negócio do cliente.

#### Exemplos de agentes
- `commercial_cliente`
- `operational_cliente`
- `admfin_cliente`
- `strategic_cliente`
- `auditor_cliente`

#### Responsabilidades
- organizar a rotina local
- apoiar execução e cobrança diária
- traduzir contexto real da empresa
- preparar o terreno para interação com o Squad Versus

### 6.5 Squad de Engenharia
#### Missão
Viabilizar tecnicamente a arquitetura da Versus Gestão Corporativa.

#### Responsabilidades
- evoluir APP32, MCP e capabilities
- transformar diretrizes arquiteturais em entrega incremental
- sustentar qualidade, segurança e observabilidade
- proteger a coerência técnica da plataforma

### 6.6 Relação entre os squads
- o `Squad Versus` tem precedência metodológica e governante
- o `Squad Cliente` tem precedência contextual e operacional local
- o `Squad de Engenharia` tem precedência sobre implementação técnica e sustentação da plataforma

### 6.7 Dependências
- identidade distinta por ator
- runtime externo estável
- capabilities suficientes no MCP
- objetos colaborativos compartilhados no APP32

### 6.8 Critérios de maturidade
A camada de Agentes é considerada madura quando houver:
- papéis estáveis por squad
- fronteiras claras de autoridade
- boa coprodução humano + agente
- baixa ambiguidade entre método, operação e tecnologia

---

## 7. Orquestração

### 7.1 Objetivo
Coordenar como humanos, squads, capabilities e workflows interagem em cada contexto de trabalho.

### 7.2 Escopo
Inclui:
- roteamento
- priorização
- handoffs
- critérios de aprovação
- decisão de surface
- escalonamento
- resolução de conflitos entre contexto local e método

### 7.3 Responsabilidades
- decidir quando entra cada squad
- decidir quando o humano precisa assumir
- decidir quando a atividade é assistida, coproduzida ou executada
- preservar governança e rastreabilidade nas transições

### 7.4 Riscos principais
- roteamento excessivamente técnico e pouco operacional
- ambiguidades entre decisão humana e agentic
- conflitos sem regra de precedência
- perda de contexto nos handoffs

### 7.5 Dependências
- critérios por tipo de trabalho
- identidades e papéis bem definidos
- objetos colaborativos e trilhas no APP32
- regras de precedência estabilizadas

### 7.6 Critérios de maturidade
A Orquestração é considerada madura quando houver:
- roteamento previsível
- baixo conflito de autoridade
- boa transição entre humanos e squads
- escalonamento claro
- trilha completa de handoffs e decisões

---

## 8. Camadas transversais

### 8.1 Modo de Utilização Assistida
A utilização assistida é parte do operating model e organiza a transição entre condução forte, coprodução orientada e autonomia assistida.

### 8.2 Modelo de Maturidade Assistida
A maturidade assistida mede evolução de qualidade de uso, autonomia e responsabilidade, para evitar paternalismo e premiar progresso real.

### 8.3 Coprodução humano + agente
A atividade híbrida deve ser tratada como modo normal de trabalho em cenários relevantes, sempre com rastreabilidade de quem fez o quê.

### 8.4 Objetos colaborativos
O APP32 deve amadurecer objetos como:
- análise
- parecer
- pendência
- revisão
- aprovação
- handoff
- evidência

---

## 9. Modelo operacional dos squads

### 9.1 Arquitetura-alvo
- `Squad Versus` em runtime externo da Versus
- `Squad Cliente` em runtime externo do cliente
- `APP32` como núcleo operacional comum
- `MCP` como contrato canônico de integração

### 9.2 Estratégia de adoção
- `Modelo C` distribuído pleno como alvo
- `Modelo B` híbrido assistido como implantação recomendada
- `Modelo A` centralizado na Versus apenas como fase inicial ou exceção

### 9.3 Regra de integração
A integração preferencial é:
- `Runtime Versus → MCP/APP32`
- `Runtime Cliente → MCP/APP32`

Não se deve depender de acoplamento direto entre CLIs como desenho principal.

### 9.4 Regra de implantação de harness
- o **harness do Squad Versus** roda prioritariamente no runtime externo da Versus
- o **harness do Squad Cliente** roda prioritariamente no runtime externo do cliente
- o APP32 publica contratos, snippets, profiles e governança, mas não deve ser o runtime principal desses harnesses

### 9.5 Regra de proteção do modelo de negócio
O harness distribuído ao cliente deve ser **thin** e operacional.

Ele pode conter:
- instrução operacional
- startup
- regras de segurança
- formato de interação
- escalonamento

Ele não deve conter, de forma aberta e completa:
- o núcleo proprietário da metodologia Versus
- heurísticas consultivas profundas
- protocolos estratégicos avançados de revisão e governança

---

## 10. Governança executiva do mapa

### 10.1 Uso do documento
Este mapa deve ser usado para:
- orientar decisões executivas
- validar coerência de novas iniciativas
- revisar aderência entre produto, engenharia e operação
- abrir frentes futuras no AA.J.1 com menor ambiguidade

### 10.2 Relação com o paper
O paper permanece como documento de amadurecimento conceitual.

O mapa formal passa a ser:
- a síntese estabilizada
- a referência estrutural
- a base para desdobramentos complementares

### 10.3 Relação com execução
Toda execução futura deve demonstrar aderência explícita a este mapa, principalmente em:
- `company_id`
- MCP First
- runtime externo
- rastreabilidade
- separação entre squads
- progressão de autonomia assistida

---

## 11. Próximos desdobramentos recomendados
1. criar mapa de capabilities por domínio do APP32/MCP
2. criar arquitetura operacional detalhada do `Squad Versus`
3. criar arquitetura operacional detalhada do `Squad Cliente`
4. definir objetos colaborativos formais do APP32
5. definir política de identidade, papel e runtime por ator
6. derivar roadmap executivo e técnico a partir deste mapa

---

## 12. Veredito final
A Versus Gestão Corporativa deve ser tratada como uma arquitetura integrada de método, plataforma, workforce digital e coordenação.

O valor da Versus não nasce apenas da consultoria, do APP32 ou dos agentes isoladamente.

Ele nasce da coerência entre:
- Forma de Trabalho
- Ferramenta
- Agentes
- Orquestração

Este mapa formal existe para preservar essa coerência como referência permanente.
