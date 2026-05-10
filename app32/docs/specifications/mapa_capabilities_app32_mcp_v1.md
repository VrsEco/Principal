# Mapa de Capabilities APP32/MCP — Versus Gestão Corporativa

## Status
Versão inicial v1 produzida no contexto do card `AA.J.15.1`.

## Objetivo
Inventariar as capabilities atuais do APP32/MCP, classificar a prontidão para uso por squads externos e apontar gaps críticos para o MVP operacional assistido.

---

## 1. Visão geral executiva
Hoje o APP32 possui três camadas relevantes de capabilities:

1. **Catálogo canônico baseado em tools legadas**
   - exposto pelo `ToolCapabilityRegistry`
   - usado para compor os manifestos por surface
2. **Registradores MCP adicionais**
   - ampliam o MCP com superfícies novas e especializadas
   - ainda não estão integralmente refletidos no manifesto canônico por surface
3. **Runtime interno legado**
   - ainda concentra parte da operação agentic histórica
   - convive com o desenho alvo de runtime externo + MCP First

### Leitura principal
O APP32 já possui base relevante para squads externos, porém **a capacidade real disponível via MCP é maior do que a capacidade descoberta/governada pelo manifesto canônico atual**.

Esse drift é o principal achado do Passo 1.

---

## 2. Inventário canônico atual por surface
Manifesto extraído do catálogo oficial por surface.

### 2.1 Surface `user`
- **26 tools**
- domínios:
  - governance: 1
  - identity_self_service: 2
  - meetings: 5
  - operations: 2
  - processes: 5
  - projects: 5
  - routine: 4
  - strategy: 2

### 2.2 Surface `admin`
- **33 tools**
- domínios:
  - finance: 1
  - governance: 2
  - identity_admin: 2
  - identity_self_service: 2
  - meetings: 5
  - operations: 2
  - processes: 5
  - projects: 8
  - routine: 4
  - strategy: 2

### 2.3 Surface `analytics`
- **8 tools**
- domínios:
  - analytics: 1
  - finance: 1
  - projects: 2
  - strategy: 2
  - workload: 2

### 2.4 Surface `ops`
- **4 tools**
- domínios:
  - operations: 3
  - workload: 1

---

## 3. Catálogo compartilhado atual
O catálogo compartilhado hoje expõe:

- **40 LangChain tools legadas** como base do `ToolCapabilityRegistry`
- **19 registradores MCP adicionais** acoplados ao servidor MCP

Registradores adicionais identificados:
- `register_analysis_catalog_tools`
- `register_crud_contract_tools`
- `register_domain_example_tools`
- `register_domain_playbook_tools`
- `register_external_ai_onboarding_tools`
- `register_feature_catalog_tools`
- `register_external_llm_factory_tools`
- `register_implantation_persona_profile_tools`
- `register_incentive_tools`
- `register_integration_request_tools`
- `register_operational_readiness_tools`
- `register_permission_matrix_tools`
- `register_profile_contract_tools`
- `register_release_checklist_tools`
- `register_sapiens_factory_tools`
- `register_surface_playbook_tools`
- `register_tool_freeze_tools`
- `register_usage_dashboard_tools`
- `register_work_journey_tools`

---

## 4. Capabilities MCP adicionais com maior peso

### 4.1 Financeiro
Arquivo principal:
- `C:/GestaoVersus/app32/app32/src/core/mcp_financial_tools.py`

Volume identificado:
- **75 tools MCP** financeiras declaradas no registrador

Cobertura aparente:
- catálogo-base financeiro
- habilitações de domínio financeiro
- ingestão financeira
- schedules e fechamentos
- orçamento
- classificação
- reconciliação
- dashboards e relatórios
- operações diversas do workspace financeiro

### 4.2 Work Journey
Arquivo principal:
- `C:/GestaoVersus/app32/app32/src/core/mcp_work_journey_tools.py`

Volume identificado:
- **25 tools MCP** de jornada operacional

Cobertura aparente:
- quadro operacional da jornada
- blocos
- regras recorrentes
- tarefas avulsas
- transferências
- ausências
- agenda materializada
- locks/unlocks
- movimentação de agenda
- bindings com rotina/processo

### 4.3 Catálogos/documentação operacional MCP
Arquivos relevantes:
- `mcp_feature_catalog_tools.py`
- `mcp_analysis_catalog_tools.py`
- `mcp_domain_playbook_tools.py`
- `mcp_surface_playbook_tools.py`
- `mcp_external_ai_onboarding_tools.py`
- `mcp_external_llm_factory_tools.py`

Cobertura aparente:
- descoberta de contexto
- catálogo de features
- onboarding para IA externa
- playbooks por domínio/surface
- suporte à Sapiens Factory e surfaces externas

---

## 5. Achado crítico do inventário
### 5.1 Drift entre manifesto canônico e superfície MCP real
O manifesto por surface hoje é derivado do `ToolCapabilityRegistry`, que está sendo montado a partir das **tools legadas LangChain**.

Ao mesmo tempo, o MCP recebe **registradores adicionais** com dezenas de tools novas.

### Consequência
Parte importante das capabilities MCP já existe tecnicamente, mas **não aparece com a mesma clareza no manifesto canônico por surface/domínio**.

Isso produz quatro riscos:
1. descoberta incompleta por agentes externos
2. governança parcial do que realmente está exposto
3. diferença entre capacidade implementada e capacidade oficialmente catalogada
4. dificuldade de planejar squads externos com base em inventário confiável

### Exemplos claros
- `finance`: o manifesto por surface mostra presença muito pequena do domínio, enquanto o registrador financeiro possui dezenas de tools
- `work_journey`: o registrador possui 25 tools, mas esse domínio não aparece como domínio canônico equivalente no manifesto atual por surface

---

## 6. Classificação de prontidão para squads externos

### 6.1 Pronto ou quase pronto
#### Processos
- boa presença no manifesto canônico
- aderente à proposta comercial
- forte candidato para uso pelo `Squad Versus`

#### Projetos
- boa presença no manifesto canônico
- útil para operação e acompanhamento
- forte candidato para uso inicial do `Squad Cliente` e `Squad Versus`

#### Reuniões
- presença estável no catálogo atual
- útil para operação assistida e ritos

#### Estratégia (base)
- presença menor, mas existente
- suficiente para leituras e início de suporte analítico

### 6.2 Parcialmente pronto
#### Rotina / Operações
- presença relevante no manifesto
- ainda precisa melhor costura com front door, objetos colaborativos e fluxo MVP

#### Financeiro
- implementação MCP forte
- governança/catalogação ainda discrepante
- pronto tecnicamente em partes, mas não pronto canonicamente para squads externos

#### Work Journey
- implementação MCP forte
- ainda fora do eixo principal do manifesto canônico
- precisa encaixe de domínio/surface e política de uso

### 6.3 Ainda não pronto
#### Objetos colaborativos
- conceito amadurecido
- ainda não materializado como domínio/capability oficial

#### Maturidade assistida
- conceito amadurecido
- ainda sem capacidade operacional mínima no sistema

#### Governança cruzada de mudança
- necessidade reconhecida
- ainda sem capacidade institucional explícita

---

## 7. Gaps críticos para o MVP
1. **unificar catálogo canônico e registradores MCP adicionais**
2. **normalizar domínio canônico de work_journey / rotina operacional**
3. **expor o financeiro com governança compatível com sua superfície real**
4. **mapear identidade, papel e surface por ator antes da abertura ampla para squads externos**
5. **modelar objetos colaborativos mínimos no APP32**

---

## 8. Leitura por impacto nos pilares

### Forma de Trabalho
O inventário confirma que já existe base relevante para operacional, processos, projetos e parte de estratégia/financeiro, coerente com a metodologia da Versus.

### Ferramenta
O APP32 está mais maduro tecnicamente do que o seu catálogo oficial expressa hoje.

### Agentes
Os squads já podem nascer apoiados em domínios como processos, projetos e parte de rotina, mas ainda não devem assumir uso amplo de financeiro e jornada sem saneamento do catálogo/governança.

### Orquestração
A orquestração depende diretamente da correção desse inventário para saber o que está realmente pronto para ser chamado por cada squad.

---

## 9. Recomendação operacional imediata
A sequência correta após este inventário é:

1. executar `AA.J.15.2` para identidade, autenticação, papéis e surfaces
2. executar `AA.J.15.3` para fechar front door, papel do Sapiens e canal inicial
3. executar `AA.J.15.4` para modelar objetos colaborativos mínimos
4. só então abrir `AA.J.15.5` para o MVP do domínio operacional assistido

### Recomendação de domínio para o primeiro MVP
Começar por:
- **processos + projetos + rotina operacional básica**

Evitar abrir de início:
- financeiro amplo
- jornada completa
- maturidade assistida plena

até que o catálogo canônico esteja saneado.

---

## 10. Veredito final do Passo 1
### Conclusão
O APP32 possui capacidade real relevante para squads externos, mas **a prontidão oficial ainda é desigual entre os domínios**.

### Achado mais importante
Existe **drift entre a superfície MCP efetivamente implementada e o catálogo canônico de capabilities**.

### Implicação
O MVP deve começar pelos domínios mais estáveis do manifesto atual, enquanto a Versus corrige a governança/catalogação dos domínios mais avançados e mais sensíveis.
