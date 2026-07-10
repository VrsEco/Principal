# SPEC v1 — Experiência de Conexão APP32, CLI/IA e Canais via MCP/API

**Classe documental:** SPEC  
**Status:** Decisão oficial v1  
**Data:** 2026-07-10  
**Origem:** `app32/docs/papers/paper_comunicacao_app32_cli_ia_mcp_api_estagio_zero_v0.md`  
**Escopo:** APP32, MCP, API, CLI/IA do cliente, consultor, cliente, Squad Cliente, Squad Versus, Squad Engenharia, canais e conectores externos

---

## 1. Decisão

A experiência de comunicação entre APP32 e CLI/IA deve ser organizada como uma **jornada única de conexão e reconexão**, preservando as telas existentes, mas com responsabilidades explícitas.

A decisão oficial é:

> **Antes de ampliar capacidades agentic, o APP32 deve garantir conexão simples, segura, rastreável e reconstituível entre usuário, empresa, runtime de IA, surface MCP, token/credencial e canal utilizado.**

A camada de inteligência só deve ser considerada operacional quando a camada de comunicação estiver saudável.

---

## 2. Objetivo

Reduzir instabilidade, retrabalho e confusão operacional para consultor e cliente.

A SPEC define:

1. jornada canônica do consultor e do cliente;
2. responsabilidades de `/profile`, `/api-mcp`, `/channels` e console técnico;
3. contrato mínimo do `Connection Profile`;
4. sinais mínimos de saúde e diagnóstico;
5. regras para Bearer Token MVP e OAuth futuro;
6. governança de squads e MCP;
7. critérios de aceite para estabilização.

---

## 3. Princípios

### 3.1. Comunicação primeiro, operação depois

O primeiro alvo não é criar mais automações.

O alvo é garantir que o usuário consiga responder rapidamente:

1. estou conectado?
2. em qual empresa estou conectado?
3. com qual runtime/CLI?
4. com qual squad/perfil?
5. com qual surface MCP?
6. meu token/credencial está válido?
7. como reconecto se falhar?

### 3.2. MCP First quando houver estado operacional

Quando houver contexto real da empresa, leitura de evidências, análise assistida, maturidade, projetos, processos, indicadores ou registros consultivos, o caminho preferencial é MCP.

API REST permanece para telas, integrações específicas, serviços internos e fallback técnico.

### 3.3. Multi-tenancy obrigatório

Toda operação com dado empresarial precisa preservar:

- `company_id`;
- usuário/ator;
- perfil/squad;
- surface;
- permissão efetiva;
- trilha de uso.

Tools de descoberta podem operar sem `company_id` prévio quando sua função for justamente listar ou selecionar empresas acessíveis ao usuário.

### 3.4. Custo e capacidade de IA pertencem ao cliente

Quando a IA externa do cliente for utilizada, tokens, plano, capacidade e custo pertencem ao tenant/cliente.

O APP32 fornece contexto governado, instruções, tools, registro e rastreabilidade.

---

## 4. Atores e responsabilidades

| Ator | Responsabilidade |
|---|---|
| Consultor | Conduzir a jornada, orientar cliente, validar método e acionar suporte quando houver falha. |
| Cliente | Autorizar IA/conector, prover capacidade/token quando aplicável e validar realidade operacional. |
| APP32 | Prover contexto, credenciais, snippets, diagnóstico, logs, revogação e registro auditável. |
| CLI/IA do cliente | Consumir MCP/API autorizada, executar análise, pesquisa e síntese dentro do perfil permitido. |
| Squad Cliente | Validar aderência à rotina real da empresa. |
| Squad Versus | Validar método, protocolo, maturidade e próximos passos. |
| Squad Engenharia | Garantir estabilidade, segurança, observabilidade, API/MCP e correções técnicas. |

---

## 5. Responsabilidade das telas existentes

### 5.1. `/profile` — Instalar/Conectar IA pessoal

É a entrada principal do usuário para conexão MCP pessoal.

Deve concentrar:

- escolha do runtime: Codex, Claude, Antigravity/Gemini, VS Code/Copilot ou outro;
- escolha do squad/perfil;
- escolha da empresa padrão;
- geração, renovação e revogação de token Bearer MVP;
- geração de snippet específico por runtime;
- teste de conexão;
- status do token;
- instrução curta de reconexão.

### 5.2. `/api-mcp` — Contratos e catálogo API/MCP

É a superfície de interoperabilidade.

Deve concentrar:

- catálogo de contratos API/MCP;
- surfaces disponíveis;
- capabilities/tools publicadas;
- backlog de integrações;
- solicitações de nova integração;
- documentação técnica de consumo.

Não deve ser a tela principal de reconexão do usuário final.

### 5.3. `/channels` — Canais operacionais externos

É a superfície de configuração de canais.

Deve concentrar:

- e-mail;
- WhatsApp;
- Telegram;
- Instagram;
- provedores de IA/canal;
- webhooks;
- testes de envio/recebimento;
- status operacional dos canais.

Não deve substituir o perfil MCP pessoal.

### 5.4. Console técnico MCP/API

É a superfície de Engenharia/governança.

Deve concentrar:

- readiness;
- release checklist;
- auditoria técnica;
- catálogo de profiles/surfaces;
- observabilidade;
- diagnóstico avançado;
- congelamento de tools;
- troubleshooting de produção.

Não deve ser a experiência principal do consultor/cliente.

---

## 6. Connection Profile canônico

O APP32 deve tratar cada conexão CLI/IA como um `Connection Profile` lógico.

Campos mínimos:

| Campo | Regra |
|---|---|
| `connection_id` | Identificador interno da conexão. |
| `user_id` | Usuário autenticado dono da conexão. |
| `company_id` | Empresa padrão, quando aplicável. |
| `runtime` | Codex, Claude, Gemini/Antigravity, VS Code/Copilot, custom. |
| `squad` | Squad Cliente, Squad Versus ou Engenharia. |
| `surface` | `user`, `admin`, `analytics` ou `ops`. |
| `auth_mode` | Bearer Token MVP ou OAuth. |
| `token_status` | ativo, expirado, revogado, pendente ou erro. |
| `last_seen_at` | Última chamada MCP/API reconhecida. |
| `last_health_status` | ok, instável, falhou ou não testado. |
| `snippet_version` | Versão do snippet gerado para o runtime. |
| `allowed_tools_summary` | Resumo de tools/capabilities permitidas. |
| `diagnostic_message` | Erro orientado à ação quando houver falha. |

---

## 7. Jornada canônica de conexão

### 7.1. Consultor

1. Acessa `/profile`.
2. Escolhe empresa, runtime e Squad Versus ou Engenharia.
3. Gera ou renova token/conexão.
4. Copia snippet específico do runtime.
5. Instala no CLI/IA.
6. Executa teste de conexão.
7. Confirma empresa ativa e surface.
8. Usa MCP no Cockpit/Jornada.
9. Registra ou valida resultado no APP32.

### 7.2. Cliente

1. Acessa `/profile` com orientação do consultor.
2. Escolhe empresa e Squad Cliente.
3. Gera conexão do runtime escolhido.
4. Instala no CLI/IA do cliente.
5. Executa teste assistido.
6. Usa IA do cliente com tokens/capacidade próprios.
7. Retorna análise, validação ou evidência ao APP32.

### 7.3. Engenharia

1. Acessa console técnico.
2. Verifica health MCP/API.
3. Valida surfaces, profiles e catálogo.
4. Executa smoke de produção.
5. Corrige token, health, restart, routing ou policy.
6. Registra incidente/correção quando aplicável.

---

## 8. Diagnóstico mínimo obrigatório

Toda conexão MCP pessoal deve exibir ou permitir verificar:

- URL MCP efetiva;
- runtime selecionado;
- empresa padrão;
- surface;
- squad/perfil;
- token ativo/expirado/revogado;
- último uso;
- health público `/mcp/healthz`;
- teste autenticado básico;
- erro humano orientado à ação.

Mensagens desejadas:

- “Token expirado ou revogado — gere novo token e atualize seu runtime.”
- “MCP público fora do ar — acione Engenharia.”
- “Conectado, mas sem empresa ativa — selecione empresa padrão.”
- “Runtime configurado, mas sem chamada recente — execute teste no CLI.”
- “Permissão insuficiente — peça ajuste de perfil no APP32.”

---

## 9. Bearer Token MVP e OAuth

### 9.1. Bearer Token MVP

Permanece válido para MVP controlado.

Regras:

- token por usuário + runtime/conector + squad/perfil;
- renovar um runtime não deve derrubar outro;
- revogação ampla deve ser ação explícita;
- token deve ter status e último uso visíveis;
- segredo não deve aparecer em logs, prompts ou prints desnecessários.

### 9.2. OAuth futuro

OAuth é o destino canônico para conectores remotos maduros.

Prioridade:

1. Claude Remote MCP / Connectors;
2. ambientes corporativos com rotação automática;
3. clientes que exigem controle de consentimento e revogação formal.

Bearer Token e OAuth podem coexistir enquanto houver migração.

---

## 10. Snippets por runtime

O APP32 deve gerar snippets adaptados, mantendo um único servidor MCP canônico.

Runtimes mínimos:

- Codex CLI: TOML;
- Claude Code: comando `claude mcp add`;
- Claude Desktop: JSON/proxy ou conector remoto conforme estágio;
- Gemini/Antigravity: JSON;
- VS Code/Copilot: `.vscode/mcp.json`.

O que muda por runtime é o envelope de configuração, não o contrato do APP32.

---

## 11. Relação com a Análise Assistida

Esta SPEC é pré-requisito operacional da SPEC `camada_analise_assistida_mcp_tenant_owned_v1.md`.

Sem conexão saudável, a análise assistida deve entrar em estado:

> “Conexão MCP pendente ou instável — regularize a conexão antes de executar análise assistida.”

---

## 12. Anti-padrões proibidos

1. Criar nova tela de conexão sem antes organizar `/profile`, `/api-mcp`, `/channels` e console técnico.
2. Misturar configuração de WhatsApp/e-mail com token MCP pessoal.
3. Exigir `company_id` em tool de descoberta de empresas do usuário.
4. Renovar token de um runtime e derrubar outro runtime sem aviso explícito.
5. Colocar segredo em documentação, print ou prompt.
6. Tratar `/healthz` web como prova de que MCP está saudável.
7. Permitir mutação crítica via MCP sem surface, permissão e gate humano.
8. Deixar consultor/cliente sem mensagem de reconexão orientada à ação.

---

## 13. Critérios de aceite

A experiência estará aderente quando:

1. `/profile` for a entrada principal para instalar/conectar CLI/IA pessoal;
2. `/api-mcp` estiver claro como catálogo/contrato, não reconexão final;
3. `/channels` estiver claro como canais externos;
4. console técnico estiver claro como superfície de Engenharia;
5. cada conexão tiver runtime, squad, surface, empresa e status;
6. token Bearer for isolado por runtime/conector;
7. health MCP for separado do health web;
8. reconexão tiver instrução curta e testável;
9. Claude, Codex, Gemini/Antigravity e VS Code tiverem snippets próprios;
10. OAuth estiver desenhado como evolução sem bloquear o MVP.

---

## 14. Decisão final

O APP32 não deve tratar MCP/API/canais como telas soltas.

A arquitetura oficial passa a ser uma **jornada de conexão governada**:

> `/profile` conecta o usuário e seu CLI/IA; `/api-mcp` publica contratos; `/channels` configura canais externos; o console técnico governa saúde e diagnóstico; o MCP preserva contexto, segurança e rastreabilidade.

Essa organização reduz instabilidade percebida, facilita reconexão e prepara a base para análise assistida, squads e OAuth.
