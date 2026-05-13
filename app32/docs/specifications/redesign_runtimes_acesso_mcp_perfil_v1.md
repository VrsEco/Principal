# Redesign da Tela de Perfil — Runtimes e Acesso MCP v1

## Objetivo
Evoluir a aba atual **`Token MCP remoto`** do perfil do usuário para refletir a arquitetura real da Versus:
- geração de token pessoal
- escolha de runtime
- escolha de squad
- instalação guiada
- configuração avançada opcional

O foco é sair de uma UX centrada em **JSON/prompt técnico genérico** para uma UX centrada em **instalação orientada por runtime e squad**.

---

## 1. Diagnóstico do estado atual
Tela atual observada em:
- `C:\GestaoVersus\app32\app32\templates\auth\profile.html`

Hoje a aba está centrada em:
- status do token
- gerar/renovar/revogar token
- empresa padrão
- nome do cliente
- geração de:
  - “Ativar Sapiens”
  - “Configuração técnica”
  - conteúdo pronto para copiar

### Problema
Essa experiência ainda comunica um modelo de:
- **conexão MCP genérica**

Mas a arquitetura atual já evoluiu para:
- **runtimes distintos**
- **squads distintos**
- **harnesses distintos**
- **instaladores distintos**

---

## 2. Decisão de UX
A aba deve deixar de ser pensada como:

## `Token MCP remoto`

e passar a ser pensada como:

## `Runtimes e Acesso MCP`

O token continua existindo, mas deixa de ser o centro exclusivo da experiência.

---

## 3. Estrutura proposta da nova tela

### Bloco A — Credencial MCP pessoal
Mantém a parte atual de:
- status do token
- último uso
- gerar token
- renovar token
- revogar token

### Papel do bloco
Esse bloco continua sendo a base de credencial do usuário.

### Reuso da tela atual
Reaproveitar:
- `#mcpTokenStatusText`
- `#mcpTokenLastUsageText`
- `#generateMcpTokenButton`
- `#renewMcpTokenButton`
- `#revokeMcpTokenButton`

---

### Bloco B — Escolha do runtime
Novo bloco com cards ou botões de seleção:
- **Codex**
- **Claude**
- **Antigravity**
- **Outro cliente MCP**

### Objetivo
Deixar claro **onde** o usuário quer instalar.

### Comportamento esperado
Ao selecionar o runtime, a interface:
- muda instruções
- muda instalador
- muda profile/surface padrão sugeridos

---

### Bloco C — Escolha do squad/perfil
Novo bloco com seleção de papel operacional:
- **Squad Cliente**
- **Squad Versus**
- **Squad de Engenharia**

### Regras
As opções exibidas podem depender do papel do usuário.

### Exemplo
- cliente: foco em `Squad Cliente`
- consultor: foco em `Squad Versus`
- técnico/admin: foco em `Squad de Engenharia`

---

### Bloco D — Contexto da instalação
Bloco para consolidar:
- empresa padrão
- nome do cliente local/opcional
- runtime escolhido
- squad escolhido
- profile resultante
- surface resultante

### Reuso parcial da tela atual
Reaproveitar:
- `#mcpCompanyId`
- `#mcpClientName`

### Campos novos sugeridos
- `runtime_selected`
- `squad_selected`
- `resolved_profile`
- `resolved_surface`

Esses dois últimos podem ser somente leitura.

---

### Bloco E — Instalação guiada
Novo centro da experiência.

### Ação principal
- **Copiar comando de instalação**

### Ações secundárias
- **Ver instruções**
- **Ver configuração técnica**
- **Ver harness**
- **Executar smoke guiado**

### Objetivo
Tornar o APP32 o emissor de contexto para instalação, sem obrigar o usuário a entender JSON manual logo de início.

---

### Bloco F — Configuração avançada
Esse bloco substitui a centralidade atual do JSON.

### Conteúdo
- JSON técnico
- URL MCP
- profile
- surface
- `company_id`
- troubleshooting

### Regra
Esse bloco existe, mas fica como **modo avançado**, não como centro da tela.

---

## 4. Fluxo ideal de uso

### Passo 1
Usuário entra na aba **Runtimes e Acesso MCP**

### Passo 2
Gera ou renova seu token pessoal

### Passo 3
Escolhe o runtime:
- Codex
- Claude
- Antigravity

### Passo 4
Escolhe o squad:
- Cliente
- Versus
- Engenharia

### Passo 5
APP32 resolve automaticamente:
- profile
- surface
- empresa padrão
- comando de instalação

### Passo 6
Usuário copia o comando de instalação

### Passo 7
Executa o instalador no runtime escolhido

### Passo 8
Se necessário, consulta a configuração técnica avançada

---

## 5. Mapeamento de escolhas para profile/surface

### Claude + Squad Cliente
- profile: `squad_cliente`
- surface: `user`

### Antigravity + Squad Versus
- profile: `squad_versus`
- surface: `admin`

### Codex + Engenharia
- profile: `engineering`
- surface: `ops`

---

## 6. Wireframe textual proposto

## Aba: `Runtimes e Acesso MCP`

### Seção 1 — Credencial MCP
- card de status
- card de último uso
- botões:
  - gerar
  - renovar
  - revogar

### Seção 2 — Instalar em um runtime
- card Codex
- card Claude
- card Antigravity
- card Outro

### Seção 3 — Ativar um squad
- card Squad Cliente
- card Squad Versus
- card Engenharia

### Seção 4 — Contexto da instalação
- empresa padrão
- nome do cliente local
- profile resolvido
- surface resolvida

### Seção 5 — Instalação guiada
- botão principal:
  - **Copiar comando de instalação**
- botão secundário:
  - **Ver instruções**
- botão secundário:
  - **Ver configuração técnica**

### Seção 6 — Avançado
- JSON
- URL MCP
- troubleshooting

---

## 7. Mapeamento técnico para a página atual

### Arquivo principal
- `C:\GestaoVersus\app32\app32\templates\auth\profile.html`

### JS de apoio existente
Hoje a lógica da aba de perfil está embutida no próprio template.

### Recomendação
Extrair a lógica MCP do perfil para um JS dedicado, por exemplo:
- `C:\GestaoVersus\app32\app32\static\js\profile_mcp_runtime_installer.js`

### CSS dedicado sugerido
- `C:\GestaoVersus\app32\app32\static\css\profile_mcp_runtime_installer.css`

---

## 8. Elementos que podem ser reaproveitados

### Reaproveitar quase sem mudança
- status do token
- último uso
- gerar/renovar/revogar token
- empresa padrão
- nome do cliente

### Reaproveitar com mudança semântica
- `#buildMcpActivationButton`
  - deixar de ser “Ativar Sapiens”
  - passar a ser “Copiar comando de instalação”

- `#buildMcpTechnicalButton`
  - manter como “Configuração técnica”
  - mas movido para bloco avançado

- `#copyMcpConfigButton`
  - pode continuar existindo como ação auxiliar

- `#mcpConfigOutput`
  - virar área dinâmica para:
    - comando de instalação
    - instruções
    - JSON avançado

---

## 9. Mudanças específicas de conteúdo

### Texto do cabeçalho do card
Hoje:
- `Acesso MCP remoto`

Proposto:
- `Instalação de runtimes MCP`

### Descrição
Hoje:
- “Gere o token mensal para conectar Claude, Antigravity ou outro cliente remoto ao Sapiens.”

Proposto:
- “Gere seu token pessoal, escolha o runtime e o squad, e copie a instalação guiada para Codex, Claude, Antigravity ou outro cliente MCP.”

---

## 10. Hierarquia de experiência

### Modo padrão
- instalação guiada
- centrada em runtime + squad
- baixa carga técnica

### Modo avançado
- JSON
- conteúdo técnico
- troubleshooting
- details MCP

---

## 11. Recomendação de implementação em fases

### Fase 1 — Redesign de UX sem mexer no backend estrutural
- renomear aba
- introduzir seletor de runtime
- introduzir seletor de squad
- trocar CTA principal para comando de instalação
- preservar JSON em área avançada

### Fase 2 — APP32 gerar instaladores por runtime
- conectar runtime + squad -> payload de instalação
- exibir comando pronto
- exibir profile/surface resolvidos

### Fase 3 — Validação guiada
- smoke guiado
- troubleshooting contextual
- eventual status de “instalado/validado”

---

## 12. Veredito
O layout atual ainda é funcional, mas comunica uma arquitetura anterior.

O redesenho recomendado deve:
- manter a credencial MCP
- reduzir o protagonismo do JSON
- elevar runtime + squad ao centro da experiência
- tornar o APP32 o ponto de ativação guiada dos harnesses

Esse é o caminho mais aderente à arquitetura atual da Versus.
