# Implantação dos Squads no CLI — Harnesses, Snippets e Playbook v1

## Status
Documento de execução do card `AA.J.16.2`.

## Objetivo
Definir como os squads serão implantados no CLI do consultor e do cliente durante o experimento da Empresa-Laboratório Versus, preservando:
- runtime externo como regra
- MCP First
- separação entre papel de negócio e harness operacional
- proteção do modelo de negócio da Versus

---

## 1. Decisão principal
A implantação no CLI será feita por composição de cinco artefatos:

1. **definição do papel do agente**
2. **harness operacional do agente**
3. **snippet MCP do profile correspondente**
4. **playbook curto de ativação**
5. **smoke de conexão e escopo**

Regra:
- o papel do agente descreve a função de negócio
- o harness descreve como o papel opera
- o snippet conecta o runtime ao APP32/MCP
- o playbook orienta a primeira sessão
- o smoke comprova que o runtime está apto a operar com segurança

---

## 2. O que vai no CLI do cliente
No CLI do cliente deve ficar apenas o necessário para a operação assistida.

### Conteúdo permitido
- harnesses do Squad Cliente
- prompts-base operacionais
- startup sequence
- regras de segurança e escopo
- snippets MCP do profile `squad_cliente`
- playbooks curtos de ativação
- checklists de smoke

### Conteúdo proibido
- metodologia consultiva completa da Versus
- heurísticas estratégicas proprietárias profundas
- protocolos avançados internos do Squad Versus
- lógica completa de governança consultiva da Versus

### Regra de desenho
O harness do cliente deve ser **thin**, operacional e orientado a consumo de capability.

---

## 3. O que vai no CLI do consultor Versus
No CLI do consultor pode ficar uma camada mais rica de orientação metodológica, desde que continue governada.

### Conteúdo permitido
- harnesses do Squad Versus
- prompts-base consultivos
- startup sequence privilegiada
- snippets MCP do profile `squad_versus`
- playbooks de discovery, revisão e direcionamento
- checklists de análise e escalonamento

### Regra de desenho
Mesmo no runtime Versus, a inteligência deve continuar ancorada em MCP, profiles, surfaces e trilha auditável.

---

## 4. Pacote mínimo por harness
Cada harness do experimento deve ter um pacote mínimo composto por:

### 4.1 Manifesto do harness
Campos mínimos:
- nome do harness
- papel de negócio associado
- squad
- runtime preferencial
- surface MCP
- domínios prioritários
- objetivo operacional

### 4.2 Prompt-base
Deve conter:
- missão
- escopo
- limites
- política de escalonamento
- regra de menor privilégio
- formato esperado de saída

### 4.3 Startup sequence
Deve conter:
- ferramentas MCP obrigatórias da primeira sessão
- validação de contexto e `company_id`
- leitura do contrato de surface
- discovery das capabilities permitidas

### 4.4 Tools permitidas e proibidas
Deve explicitar:
- tools obrigatórias
- tools opcionais
- tools proibidas
- ações que exigem escalonamento

### 4.5 Smoke de ativação
Deve validar:
- conectividade MCP
- profile correto
- surface correta
- tenant correto
- acesso negado onde deveria ser negado

---

## 5. Pacote inicial do Squad Cliente
Para a primeira etapa, o pacote inicial do CLI do cliente deve prever os seguintes harnesses:

- `harness_coordenador_cliente_v1`
- `harness_comercial_cliente_v1`
- `harness_operacional_cliente_v1`
- `harness_admfin_cliente_v1`
- `harness_estrategico_cliente_v1`
- `harness_pessoas_capacidade_cliente_v1`

### Estratégia de ativação inicial
No primeiro ciclo, o cliente não deve iniciar com todos os harnesses visíveis ao mesmo tempo.

A experiência recomendada é:
1. `harness_coordenador_cliente_v1` como entrada principal
2. demais harnesses acionados por roteamento ou por instrução do coordenador

---

## 6. Pacote inicial do Squad Versus
Para a primeira etapa, o pacote inicial do CLI da Versus deve prever harnesses equivalentes aos papéis consultivos priorizados no experimento.

No mínimo:
- harness de coordenação consultiva
- harness de estratégia/revisão
- harness de operação/processos
- harness de controladoria/análise

A granularidade final do Squad Versus pode continuar amadurecendo, mas o cliente não depende disso para a ativação inicial do CLI.

---

## 7. Snippets MCP por profile
O experimento deve usar o mesmo MCP canônico do APP32, com perfis distintos.

### Cliente
- profile: `squad_cliente`
- surface: `user`
- startup mínimo:
  - `list_user_app32_capabilities`
  - `describe_app32_profile_contracts_tool`
  - `describe_app32_surface_playbooks_tool`

### Versus
- profile: `squad_versus`
- surface: `admin`
- startup mínimo:
  - `list_admin_app32_capabilities`
  - `describe_app32_profile_contracts_tool`
  - `describe_app32_surface_playbooks_tool`
  - `describe_app32_domain_playbooks_tool`

---

## 8. Playbook curto de ativação

### 8.1 Cliente
1. carregar harness principal do cliente
2. conectar ao snippet MCP `squad_cliente`
3. executar startup mínimo
4. confirmar `company_id` e surface
5. validar discovery das capabilities permitidas
6. iniciar a jornada pelo coordenador do cliente

### 8.2 Versus
1. carregar harness principal do consultor
2. conectar ao snippet MCP `squad_versus`
3. executar startup mínimo
4. confirmar tenant-alvo e surface
5. validar contracts e playbooks publicados
6. iniciar discovery consultivo antes de mutação

---

## 9. Smoke recomendado por runtime

### Claude / Squad Cliente
- conecta no MCP `user`
- resolve contexto da empresa correta
- lista capabilities permitidas
- falha corretamente em capability proibida

### Antigravity / Squad Versus
- conecta no MCP `admin`
- resolve tenant com `company_id` explícito quando necessário
- lê contracts e playbooks
- falha corretamente em ação não permitida ou mal contextualizada

### Codex / Engenharia
- valida trilhas, perfis, snippets e erros reproduzíveis
- não atua como squad de negócio

---

## 10. Critérios de aceite do card AA.J.16.2
Este card é considerado atendido quando:
- a forma de implantação no CLI estiver definida
- a separação entre papel e harness estiver explícita
- a composição do pacote de ativação estiver fechada
- a regra de proteção do modelo de negócio estiver registrada
- a estratégia de uso de snippets MCP estiver consolidada
- o experimento puder avançar para a estruturação do MCP por squad

---

## 11. Modelo de instalação seguro
O modelo preferencial de instalação deve ser:

- APP32 gera o token e o contexto
- o usuário executa um instalador do runtime
- o token é informado no momento da instalação, de forma segura
- o segredo não é embutido no pacote nem no repositório

Referência operacional:
- `C:\GestaoVersus\app32\app32\docs\specifications\instalacao_segura_harnesses_via_app32_v1.md`
- `C:\GestaoVersus\app32\app32\scripts\installers\install-codex-laboratorio.ps1`

---

## 12. Próximo passo
Com este documento, o próximo passo do projeto é o `AA.J.16.3`:
- estruturar o MCP, perfis, tools e liberações por squad
- validar se o catálogo atual já suporta os harnesses definidos
- identificar gaps de capability e de policy para o experimento
