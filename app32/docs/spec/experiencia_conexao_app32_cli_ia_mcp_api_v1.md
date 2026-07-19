# SPEC v1 — Experiência de Conexão APP32, CLI/IA e Canais via MCP/API

**Classe documental:** SPEC  
**Status:** Decisão oficial v1  
**Data:** 2026-07-10  
**Origem:** `app32/docs/papers/paper_comunicacao_app32_cli_ia_mcp_api_estagio_zero_v0.md`  
**Escopo:** APP32, MCP, API, CLI/IA do cliente, consultor, cliente, Squad Cliente, Squad Versus, Squad Engenharia, canais e conectores externos

---

## 1. Decisão

A experiência de comunicação entre APP32 e CLI/IA deve ser organizada em uma **tela única de Conexões**, preservando as funcionalidades existentes, mas reduzindo a dispersão operacional.

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

### 5.1. `/channels` — Conexões unificadas

É a entrada principal do usuário para conexões operacionais.

Deve concentrar em um só lugar:

- e-mail;
- WhatsApp;
- Telegram;
- Instagram;
- provedores de IA;
- CLI/IA via MCP;
- testes de conexão;
- health e diagnóstico básico.

### 5.2. `/profile` — Modo detalhado de instalação MCP

Deixa de ser a entrada principal da conexão MCP e passa a funcionar como modo detalhado, fallback seguro e autoatendimento avançado do usuário.

Deve concentrar:

- escolha do runtime: Codex, Claude, Antigravity/Gemini, VS Code/Copilot ou outro;
- escolha do squad/perfil;
- escolha da empresa padrão;
- geração, renovação e revogação de token Bearer MVP;
- geração de snippet específico por runtime;
- teste de conexão;
- status do token;
- instrução curta de reconexão.

### 5.3. `/api-mcp` — Contratos e catálogo API/MCP

É a superfície de interoperabilidade.

Deve concentrar:

- catálogo de contratos API/MCP;
- surfaces disponíveis;
- capabilities/tools publicadas;
- backlog de integrações;
- solicitações de nova integração;
- documentação técnica de consumo.

Não deve ser a tela principal de reconexão do usuário final.

### 5.4. Tela única, sem duplicar lógica

A tela `/channels` deve chamar os endpoints já existentes de canais e de MCP, sem duplicar regra de negócio no frontend.

O objetivo é unir a experiência de operação, não criar uma segunda implementação de token/canal.

### 5.5. Console técnico MCP/API

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

1. Acessa `/channels`.
2. Escolhe empresa, runtime e Squad Versus ou Engenharia.
3. Gera ou renova token/conexão.
4. Copia snippet específico do runtime.
5. Instala no CLI/IA.
6. Executa teste de conexão.
7. Confirma empresa ativa e surface.
8. Usa MCP no Cockpit/Jornada.
9. Registra ou valida resultado no APP32.

### 7.2. Cliente

1. Acessa `/channels` com orientação do consultor.
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
2. Misturar regras internas de WhatsApp/e-mail com regras de token MCP; a tela pode ser única, mas os contratos continuam separados.
3. Exigir `company_id` em tool de descoberta de empresas do usuário.
4. Renovar token de um runtime e derrubar outro runtime sem aviso explícito.
5. Colocar segredo em documentação, print ou prompt.
6. Tratar `/healthz` web como prova de que MCP está saudável.
7. Permitir mutação crítica via MCP sem surface, permissão e gate humano.
8. Deixar consultor/cliente sem mensagem de reconexão orientada à ação.
9. Configurar clientes MCP novos em SSE quando `streamable-http` estiver disponível.
10. Deixar handshake SSE legado pendurado sem resposta explícita.

---

## 13. Critérios de aceite

A experiência estará aderente quando:

1. `/channels` for a entrada principal para canais, provedores e CLI/IA via MCP;
2. `/profile` permanecer disponível como modo detalhado/fallback;
3. `/api-mcp` estiver claro como catálogo/contrato, não reconexão final;
4. console técnico estiver claro como superfície de Engenharia;
5. cada conexão tiver runtime, squad, surface, empresa e status;
6. token Bearer for isolado por runtime/conector;
7. health MCP for separado do health web;
8. reconexão tiver instrução curta e testável;
9. Claude, Codex, Gemini/Antigravity e VS Code tiverem snippets próprios;
10. OAuth estiver desenhado como evolução sem bloquear o MVP;
11. `/mcp/healthz` declarar `streamable-http` como transporte canônico e `sse_supported=false`;
12. tentativa SSE legada sem sessão retornar erro objetivo, sem travar o cliente;
13. payloads de escopo MCP manterem `active_company_id` e `companies[].selected` consistentes;
14. runtime MCP possuir monitor automático e ação administrativa de reparo seguro.

---

## 14. Decisão final

O APP32 não deve tratar MCP/API/canais como telas soltas.

A arquitetura oficial passa a ser uma **jornada de conexão governada**:

> `/channels` conecta canais externos, provedores e CLI/IA via MCP; `/profile` permanece como modo detalhado/fallback de instalação pessoal; `/api-mcp` publica contratos; o console técnico governa saúde e diagnóstico; o MCP preserva contexto, segurança e rastreabilidade.

Essa organização reduz instabilidade percebida, facilita reconexão e prepara a base para análise assistida, squads e OAuth.



---

## 15. MCP-03 — Diagnóstico e reconexão guiada

A tela única de Conexões deve conter um bloco de diagnóstico para CLI/IA via MCP.

### 15.1. Diagnóstico mínimo

O bloco deve exibir:

- status do token;
- empresa padrão;
- runtime selecionado;
- último uso;
- health público do MCP;
- estado consolidado: OK, atenção, falha ou aguardando;
- recomendação orientada à ação.

### 15.2. Recomendações padrão

- MCP público falhou: acionar Engenharia antes de alterar token.
- Token ausente/revogado: criar ou renovar token e atualizar runtime.
- Empresa não definida: selecionar empresa padrão.
- Sem último uso: copiar configuração e executar teste no CLI/IA.
- Tudo OK: conexão pronta para operação.

### 15.3. Regra de implementação

O diagnóstico deve reaproveitar os endpoints existentes de status/configuração/health e não deve criar lógica paralela de autenticação ou canais.

---

## 16. MCP-04 — Transporte canônico e consistência de empresa ativa

Após validação real em cliente externo, ficou confirmado que:

- `streamable-http` conecta, inicializa e autentica normalmente;
- SSE legado contra `/mcp/user/` pode ficar pendurado antes de `initialize()`;
- o problema não é auth, tenant ou RBAC;
- o payload de `session_company` precisa manter consistência entre `active_company_id` e `companies[].selected`.

### 16.1. Decisão oficial de transporte

O transporte canônico do MCP remoto APP32 é:

```text
streamable-http
```

SSE legado não deve ser recomendado em snippets novos.

Quando um cliente tentar handshake SSE inicial sem `Mcp-Session-Id`, o APP32 deve retornar erro explícito:

```text
sse_transport_not_supported
```

O objetivo é evitar conexão infinita em `connecting...` e orientar o usuário para `streamable-http`.

### 16.2. Consistência multiempresa

Em tools de sessão/empresa:

- `data.active_company_id` é a fonte canônica da empresa ativa;
- `data.companies[].selected` deve refletir exatamente a mesma empresa;
- quando não houver empresa ativa, nenhuma empresa deve vir como `selected=true`.

Esse contrato evita que clientes externos renderizem empresa incorreta quando usam a lista em vez do campo top-level.

---

## 17. MCP-05 — Resiliência operacional do runtime MCP

Após queda real do `/mcp/healthz` com a aplicação web saudável, a decisão oficial é tratar o runtime MCP HTTP como serviço operacional separado.

### 17.1. Decisão

O APP32 deve ter três mecanismos complementares:

1. **manager idempotente** para start/stop/restart/status/health;
2. **monitor automático leve** para detectar falhas consecutivas e reiniciar com segurança;
3. **ação administrativa no APP32** para reparar o runtime quando o consultor/engenharia identificar falha.

### 17.2. Contrato operacional

Scripts oficiais:

```text
scripts/manage_mcp_http.sh
scripts/monitor_mcp_http.sh
```

Runbook oficial:

```text
docs/runbooks/runbook_mcp_runtime_resiliencia_v1.md
```

Rotas administrativas:

```text
GET  /api/integrations/mcp-runtime/status
POST /api/integrations/mcp-runtime/repair
```

### 17.3. Regras de segurança

- Reparar runtime MCP não renova token.
- Reparar runtime MCP não altera empresa ativa.
- Reparar runtime MCP não executa tool MCP.
- Ação administrativa exige permissão de administração de integrações.
- O monitor só reinicia após falhas consecutivas para evitar falso positivo.

---

## 18. MCP-06 — Contrato de roteamento operacional universal

### 18.1 Entrada canônica

A tool `resolve_app32_operation_tool` recebe `request_text`, `company_id` efetivo e data de referência opcional. Ela deve devolver:

- `route_status`;
- `domain` e `intent` canônicos;
- `action`, `risk` e `human_gate_required`;
- `target_harness_key` e `harness_switch_required`;
- `preferred_tool`;
- argumentos normalizados, incluindo período;
- `execution_sequence`;
- política de fallback.

Estados de rota: `ready`, `needs_input`, `specialist_discovery` e `unsupported_fast_fallback`. Em `specialist_discovery`, o domínio e o harness já estão definidos; o CLI atualiza `tools/list` uma única vez e escolhe somente uma tool executável daquele domínio.

### 18.2 Harness de sessão

`describe_app32_session_harness_tool` e `select_app32_session_harness_tool` são operações de contexto da surface `user`.

A seleção:

- persiste por token pessoal;
- aceita somente harness oficial do `squad_cliente`;
- valida compatibilidade com o perfil-base;
- preserva `company_id`;
- não altera permissões do usuário;
- exige refresh do catálogo efetivo na chamada seguinte.

### 18.3 Catálogo e execução

- catálogo efetivo contém apenas tools executáveis para papel-base, surface, runtime, harness, RBAC e tenant atuais;
- item `planned` nunca aparece como alternativa operacional ativa;
- roteador não executa regra de negócio nem consulta banco de domínio;
- tool preferencial chama service existente, sempre tenant-safe;
- leitura autorizada não exige confirmação;
- mutações continuam governadas por policy/HITL.

### 18.4 Primeiro contrato financeiro

`get_financial_payables_due_summary` consulta contas a pagar em aberto por `company_id` e intervalo explícito de vencimento. O retorno mínimo contém período, quantidade de títulos, total em aberto, moeda e itens resumidos.

### 18.5 Critérios de aceite

1. pergunta financeira com “próxima semana” resolve período de segunda a domingo;
2. processo, projeto, estratégia, comercial, reunião e identidade possuem rota determinística inicial;
3. troca de harness ocorre sem renovar token ou reconectar MCP;
4. catálogo pós-troca publica somente tools autorizadas;
5. fallback desconhecido não inicia varredura de catálogos;
6. smoke remoto confirma isolamento por `company_id` e resposta objetiva.

---

## 19. Descoberta segura e recuperação de sessão

### 19.1 Contrato de roteamento

- `domain` é a taxonomia técnica canônica para policy, RBAC, catálogo e telemetria;
- `business_area` é a classificação de negócio apresentada ao CLI e pode diferir do domínio técnico;
- `capability_not_available` indica ausência confirmada de tool executável no catálogo efetivo;
- esse estado deve retornar `preferred_tool=null` e `execution_sequence=[]`.

### 19.2 `specialist_discovery`

O CLI pode atualizar `tools/list` uma única vez, restrito ao harness indicado. Só pode executar uma candidata que responda diretamente ao pedido, com correspondência semântica exata. Afinidade de nome ou domínio não é suficiente. Sem candidata exata, deve encerrar com `capability_not_available`.

### 19.3 Recuperação transitória

Para HTTP `502`, `503` ou `504`:

1. repetir somente leitura idempotente;
2. limitar a três tentativas, aguardando 1, 2 e 4 segundos;
3. reabrir a sessão `streamable-http`;
4. restaurar o `company_id` e o harness anteriormente ativos;
5. reutilizar o mesmo token enquanto ele permanecer válido;
6. nunca repetir mutações automaticamente.

O `/healthz` publica essa política em `transient_recovery`. Durante encerramento sem resposta, o middleware deve preferir `503` com `Retry-After` a um erro genérico.

### 19.4 Critérios adicionais de aceite

1. pedido comercial retorna `business_area=commercial` sem romper o `domain=strategy` canônico;
2. saldo bancário consolidado, enquanto sem tool direta, retorna `capability_not_available` sem execução aproximada;
3. discovery genérico não executa candidata sem correspondência exata;
4. restart transitório não gera repetição automática de escrita.
