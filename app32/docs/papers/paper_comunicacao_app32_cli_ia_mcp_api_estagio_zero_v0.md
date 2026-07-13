# Paper v0.0 — Comunicação APP32, CLI/IA, Squads e Canais via MCP/API**Status:** estágio zero / amadurecimento conceitual  **Classe documental:** Paper  **Escopo:** APP32, CLI/IA, MCP, API, consultor, cliente, Squad Cliente, Squad Versus, Squad Engenharia, canais de comunicação e integrações  **Diretriz:** primeiro estabilizar a comunicação; depois expandir a operação assistida.---## 1. Pergunta centralComo o APP32, o CLI/IA, o consultor, o cliente, o Squad Cliente, o Squad Versus e o Squad Engenharia devem se conectar via MCP/API de forma estável, segura, rastreável e simples, para que a operação consultiva possa acontecer sem atrito?---## 2. Tese inicialA prioridade da primeira etapa não é ampliar a inteligência, criar novos agentes ou expandir fluxos consultivos.A prioridade é fazer a comunicação rodar bem.A operação assistida já funciona de forma satisfatória quando a conexão está estabelecida. O gargalo atual está na estabilidade, clareza, segurança e facilidade de reconexão entre APP32, CLI/IA, usuários e squads.Portanto, a primeira frente deve concentrar-se em:- conexão;- autenticação;- empresa ativa;- surface correta;- token/credencial;- status de saúde;- teste de conexão;- rastreabilidade;- reconexão;- revogação de acesso.---## 3. Princípios### 3.1 MCP FirstQuando houver estado operacional do APP32, contexto real da empresa, evidências, protocolos, leitura de maturidade ou registro de análise assistida, o caminho preferencial deve ser MCP.A API REST permanece relevante para:- telas do APP32;- serviços internos;- integrações específicas;- fallback técnico;- configurações e operações administrativas quando MCP não for a melhor superfície.### 3.2 Multi-tenancy obrigatórioToda conexão deve preservar isolamento por empresa.São obrigatórios:- `company_id`;- usuário/ator;- surface;- perfil;- permissões;- logs de uso;- trilha auditável.Qualquer possibilidade de cruzamento indevido entre empresas deve ser tratada como falha crítica.### 3.3 Tokens e capacidade de IA pertencem ao clienteQuando a análise for feita em CLI/IA externa do cliente, o consumo de tokens, capacidade computacional e custo de IA pertencem ao tenant/cliente.O APP32 deve:- fornecer contexto tenant-safe;- expor tools governadas;- orientar protocolos;- registrar resultados;- permitir validação dos squads;- preservar decisão humana.---## 4. Atores| Ator | Papel na comunicação ||---|---|| APP32 | Provedor de contexto, autenticação, tools, registros, governança e trilha auditável. || CLI/IA | Consumidor MCP/API autorizado, executor de análise, pesquisa, síntese e retorno estruturado. || Consultor | Operador metodológico, validador da condução e responsável pela decisão consultiva. || Cliente | Dono do tenant, da realidade operacional, dos tokens/capacidade de IA e da validação de aderência. || Squad Cliente | Apoia a leitura operacional e valida se a análise faz sentido na rotina da empresa. || Squad Versus | Apoia método, estruturação, protocolos e coerência com a Metodologia Versus. || Squad Engenharia | Apoia estabilidade, dados, API, MCP, segurança, UX e riscos técnicos. |---## 5. Estado atual identificado no APP32O APP32 já possui bases relevantes para esta arquitetura. O ponto agora não é começar do zero, mas organizar e amadurecer o que já existe.### 5.1 Tela API / MCP**URL:** `/api-mcp`  **Template:** `app32/templates/integrations.html`  **Rota:** `app32/api/routes/integrations.py`Função atual:- catálogo de integrações API/MCP;- contratos de interoperabilidade;- backlog de integrações;- solicitação de nova integração;- classificação por canal técnico: `API`, `MCP` ou `API + MCP`.Leitura conceitual:- deve ser a superfície de contratos, interoperabilidade e evolução API/MCP;- não deve virar apenas uma tela técnica isolada;- deve dialogar com a operação consultiva, os squads e os runtimes externos.### 5.2 Tela Configurações de Canais**URL:** `/channels`  **Template:** `app32/templates/integrations_admin.html`  **Rota:** `app32/api/routes/integrations.py`Função atual:- configuração de IA;- e-mail SMTP/inbound;- WhatsApp;- Telegram;- Instagram;- providers;- credenciais;- webhooks;- testes operacionais;- serviços ativos e conexões.Leitura conceitual:- esta tela já representa a camada prática de canais externos;- deve continuar separando canal operacional de contrato MCP/API;- precisa conversar melhor com a visão de conexão estável e diagnóstico.### 5.3 Perfil / Instalar Squad**URL:** `/profile`  **Template:** `app32/templates/auth/profile.html`  **Rotas MCP:** `app32/api/routes/auth.py`Função atual:- escolha de runtime: Claude, Antigravity, Codex ou outro;- escolha de squad: Squad Cliente, Squad Versus ou Engenharia;- escolha de empresa padrão;- geração, renovação e revogação de token MCP;- resolução de surface;- resolução de perfil;- geração de comando/snippet de instalação.Leitura conceitual:- esta é a base mais próxima do futuro gerenciador de conexão MCP/CLI;- já resolve parte importante do problema;- precisa evoluir em diagnóstico, reconexão, clareza de status e orientação ao consultor/cliente.### 5.4 Console operacional API / MCP**URL legado/operacional:** `/configs/ai/mcp/console` com redirecionamentos relacionados para `/api-mcp`  **Template:** `app32/templates/modules/operations/ai_mcp_console.html`  **Rota:** `app32/api/routes/configs.py`Função atual:- visão operacional de API/MCP;- surfaces;- perfis;- permissões;- onboarding;- readiness;- release;- dashboard;- catálogo e governança MCP.Leitura conceitual:- é uma superfície mais técnica e operacional;- útil para Engenharia, governança e validação;- não deve ser confundida com a experiência simples do consultor/cliente para conectar e reconectar CLI/IA.---## 6. Problema centralA arquitetura já possui peças relevantes, mas a experiência de comunicação ainda está dispersa.Hoje existem telas para:- API/MCP;- canais;- perfil/token MCP;- console operacional MCP.O problema é que o usuário pode não saber claramente:- onde gerar a conexão;- onde testar;- onde ver se está online;- onde verificar empresa ativa;- onde validar surface;- onde resolver token expirado;- onde reconectar;- onde revogar;- onde diferenciar MCP, API, e-mail, WhatsApp e demais canais.---## 7. Hipótese de amadurecimentoNão devemos criar imediatamente uma nova tela isolada.A hipótese inicial é evoluir o conjunto existente para formar uma experiência coerente de conexão:1. `/profile` continua sendo o local do usuário para instalar/configurar runtime MCP pessoal.2. `/api-mcp` continua sendo o local de contratos, catálogo e integrações API/MCP.3. `/channels` continua sendo o local de canais externos como e-mail, WhatsApp, Telegram, Instagram e IA.4. O console operacional MCP permanece como superfície técnica para Engenharia/governança.O que precisa amadurecer é a costura entre essas telas, criando uma jornada clara:> configurar canal ou runtime → gerar credencial → testar conexão → confirmar empresa/surface → usar CLI/IA → registrar retorno → auditar uso.---## 8. Diretriz para a próxima SPECA próxima SPEC não deve começar por novas capabilities de IA.Deve começar por uma SPEC de estabilização da comunicação, possivelmente com o nome:**SPEC v1 — Experiência de Conexão APP32, CLI/IA e Canais via MCP/API**A SPEC deve decidir:- se haverá uma tela agregadora ou apenas links/jornada entre telas existentes;- qual tela será a entrada principal para consultor e cliente;- quais diagnósticos mínimos serão obrigatórios;- como testar MCP e canais;- como exibir empresa ativa, surface, perfil e último uso;- como tratar token expirado ou conexão quebrada;- como registrar auditoria mínima;- quais permissões cada ator possui;- como evitar duplicidade entre `/api-mcp`, `/channels`, `/profile` e console técnico.---## 9. Princípio operacional final deste estágioAntes de ampliar a operação assistida, a comunicação precisa ficar simples.O consultor e o cliente não devem precisar entender toda a arquitetura para operar.Eles precisam saber:1. estou conectado ou não;2. em qual empresa estou conectado;3. com qual perfil/squad estou operando;4. qual canal/runtime estou usando;5. se o MCP/API/canal está saudável;6. como reconectar;7. como pedir ajuda ou acionar Engenharia quando falhar.---## 10. Decisão provisóriaA decisão deste estágio zero é:> Reaproveitar as telas existentes de API/MCP, Configurações de Canais, Perfil/Instalar Squad e Console Operacional MCP como base da arquitetura de comunicação, evitando criar uma nova superfície antes de definir a jornada canônica de conexão e reconexão.---## 11. Próximo passoAvançar para a SPEC apenas após alinhar:1. qual é a jornada ideal do consultor;2. qual é a jornada ideal do cliente;3. qual é a jornada técnica da Engenharia;4. qual é a responsabilidade de cada tela existente;5. quais sinais mínimos de saúde/conexão precisam aparecer para reduzir instabilidade e retrabalho.---## 12. Benchmark de conexão MCP nos principais runtimes/CLIsEsta seção registra a pesquisa inicial sobre como os principais runtimes/CLIs configuram conexões MCP. A conclusão principal é que o protocolo MCP é comum, mas o formato de configuração varia por cliente.Portanto, o APP32 não deve tentar impor um único formato de instalação. Deve manter um servidor MCP canônico e gerar snippets/adaptadores por runtime.### 12.1 Codex CLI**Referência:** documentação oficial OpenAI Codex MCP.O Codex suporta MCP no CLI e na extensão IDE.Transportes suportados:- STDIO local;- Streamable HTTP remoto;- Bearer Token;- OAuth via `codex mcp login <server-name>`.Configuração principal:```text~/.codex/config.toml```Também pode haver configuração por projeto em:```text.codex/config.toml```Exemplo conceitual para APP32:```toml[mcp_servers.app32]url = "https://app.gestaoversus.com.br/mcp/user/"bearer_token_env_var = "APP32_MCP_TOKEN"```Recursos relevantes:- configuração por CLI ou por arquivo;- variável de ambiente para token;- HTTP headers;- timeout;- enable/disable;- allowlist/denylist de tools;- modo de aprovação por tool;- OAuth futuro.Leitura para APP32:- é um dos melhores alvos para o MVP;- permite token fora do arquivo;- é aderente ao uso por consultor, engenharia e Codex local;- deve receber snippet TOML próprio.### 12.2 Claude Code**Referência:** documentação oficial Claude Code MCP.O Claude Code recomenda HTTP remoto para servidores cloud.Exemplo conceitual:```bashclaude mcp add --transport http app32 https://app.gestaoversus.com.br/mcp/user/```Com Bearer Token:```bashclaude mcp add --transport http app32 https://app.gestaoversus.com.br/mcp/user/ \  --header "Authorization: Bearer SEU_TOKEN"```Transportes suportados:- HTTP remoto;- STDIO local;- SSE, mas depreciado quando HTTP estiver disponível;- WebSocket para cenários de push/eventos.Recursos relevantes:- scopes: local, project, user;- `.mcp.json`;- `~/.claude.json`;- `/mcp` para status e autenticação;- OAuth;- reconexão automática com backoff para HTTP/SSE;- indicação de servidor pendente/falho.Leitura para APP32:- é alvo muito forte para consultor e clientes avançados;- tem excelente UX de instalação via comando;- deve receber comando pronto gerado pelo APP32;- é aderente ao uso com surface explícita e Bearer Token no MVP.### 12.3 Claude Desktop**Referências:** documentação MCP/Claude Desktop e custom connectors remotos.O Claude Desktop possui dois caminhos distintos.#### Local MCPConfiguração via arquivo:```text%APPDATA%\Claude\claude_desktop_config.json```Exemplo conceitual com proxy local:```json{  "mcpServers": {    "app32": {      "command": "npx",      "args": ["-y", "mcp-remote", "https://app.gestaoversus.com.br/mcp/user/"]    }  }}```#### Remote MCP / Custom ConnectorPara conectores remotos, Claude conecta a partir da infraestrutura da Anthropic, não da máquina local.Requisitos:- URL pública HTTPS;- servidor alcançável pela internet;- OAuth como alvo recomendado;- configuração por Connectors.Leitura para APP32:- para MVP, Claude Desktop pode exigir proxy/configuração local ou pacote guiado;- para uso empresarial maduro, o alvo correto é Remote MCP com OAuth;- Bearer Token é útil no curto prazo, mas OAuth deve ser tratado como destino arquitetural.### 12.4 Gemini CLI / Antigravity**Referência:** documentação pública do Gemini CLI e MCP Server Integration.A documentação pública mais sólida encontrada para o ecossistema Google é o Gemini CLI. Para Antigravity, o tratamento deve ser compatível por proximidade de runtime/cliente MCP, mas validado novamente antes da SPEC final.Configuração principal:```text~/.gemini/settings.json```Formato conceitual:```json{  "mcpServers": {    "app32": {      "httpUrl": "https://app.gestaoversus.com.br/mcp/user/",      "headers": {        "Authorization": "Bearer SEU_TOKEN"      },      "timeout": 5000    }  }}```Transportes/recursos:- STDIO via `command`;- HTTP via `httpUrl`;- SSE via `url`;- headers;- timeout;- include/exclude tools;- trust;- comando `gemini mcp list`.Leitura para APP32:- deve receber snippet JSON próprio;- `trust: true` não deve ser padrão;- por segurança, manter confirmações ativas;- útil para clientes que adotarem ecossistema Google/Antigravity.### 12.5 VS Code / GitHub Copilot**Referências:** documentação oficial VS Code e GitHub Copilot MCP.Configuração por workspace:```text.vscode/mcp.json```Ou por perfil de usuário do VS Code.Exemplo conceitual:```json{  "servers": {    "app32": {      "type": "http",      "url": "https://app.gestaoversus.com.br/mcp/user/"    }  }}```Recursos relevantes:- instalação via galeria MCP;- configuração manual;- configuração por workspace ou usuário;- confirmação de confiança;- OAuth via ação de autenticação;- logs;- enable/disable;- políticas organizacionais;- sandbox para STDIO em macOS/Linux.Leitura para APP32:- importante para times técnicos;- não deve ser o primeiro alvo de UX para consultor;- deve ser suportado como opção avançada.---## 13. Síntese comparativa| Runtime | Formato principal | Melhor uso no APP32 ||---|---|---|| Codex CLI | `~/.codex/config.toml` | MVP técnico/consultor/engenharia || Claude Code | `claude mcp add` / `.mcp.json` | MVP consultivo e cliente avançado || Claude Desktop | `claude_desktop_config.json` / Connectors | Usuário final, com evolução para OAuth || Gemini / Antigravity | `~/.gemini/settings.json` | Clientes no ecossistema Google || VS Code / Copilot | `.vscode/mcp.json` | Times técnicos e engenharia |Conclusão:> Um servidor MCP APP32; múltiplos snippets de conexão por runtime.---## 14. Decisão arquitetural provisóriaO APP32 deve manter um contrato MCP único e canônico no servidor, com surfaces explícitas:```text/mcp/user//mcp/admin//mcp/analytics//mcp/ops/```A experiência do usuário deve gerar configurações específicas por runtime:- Codex TOML;- Claude Code command;- Claude Desktop JSON;- Gemini/Antigravity JSON;- VS Code/Copilot JSON;- instrução humana resumida;- teste de conexão;- diagnóstico de erro;- revogação/renovação de token.A autenticação deve seguir esta evolução:1. **MVP controlado:** Bearer Token por usuário/perfil/empresa, com expiração e revogação.2. **Evolução canônica:** OAuth para conectores remotos maduros, especialmente Claude Connectors e ambientes corporativos.---## 15. Implicação para a SPEC futuraA futura SPEC deve definir um `Connection Profile` canônico do APP32, independente do runtime externo.Campos mínimos sugeridos:- runtime alvo;- profile/squad;- surface;- `company_id` padrão;- URL MCP;- auth mode;- token status;- expiração;- último uso;- tools disponíveis;- snippet gerado;- teste de conexão;- logs/diagnóstico;- ação de revogar;- ação de renovar;- instrução de reconexão.Esta SPEC deve evitar duplicar contratos MCP por runtime. O que muda por runtime é apenas o envelope de configuração; o contrato operacional do APP32 deve permanecer único.
---

## 16. Correções emergenciais consolidadas após incidente MCP Sapiens

Em 06/07/2026 foi observado incidente real no conector `sapiens-user`, com três sintomas distintos:

1. tokens Bearer antigos retornando `401 Unauthorized`;
2. MCP retornando `502 Bad Gateway` enquanto a aplicação web seguia saudável;
3. tools de descoberta falhando quando não havia `company_id` selecionado.

A análise separou os problemas em três categorias.

### 16.1 Token Bearer por conector/runtime

O desenho anterior tendia a operar como se houvesse apenas um token ativo por usuário. Isso é frágil porque a renovação de um runtime pode invalidar outro runtime já instalado.

Decisão de curto prazo:

> Tokens Bearer do MVP devem ser tratados por conector/runtime, não apenas por usuário.

Exemplos de conectores distintos:

- `claude:squad_cliente`;
- `codex:squad_cliente`;
- `antigravity:squad_cliente`;
- `claude:squad_versus`.

Regra:

- renovar o token do Claude Desktop não deve revogar o token do Codex;
- renovar o token do Codex não deve derrubar o Claude Desktop;
- revogação ampla por usuário deve existir, mas como ação explícita administrativa.

### 16.2 Descoberta de contexto sem company_id

Tools de descoberta pessoal não podem exigir tenant prévio, pois servem justamente para descobrir ou selecionar contexto.

Regra:

> `list_my_companies` e `bootstrap_session_context` devem operar com `user_id` autenticado, mesmo sem `company_id` selecionado.

O `company_id` permanece obrigatório para tools operacionais que leem ou alteram dados de uma empresa específica.

### 16.3 Health check e restart do MCP

A aplicação web saudável não garante MCP saudável.

Decisão:

> O MCP precisa de health check, smoke e restart independentes.

Critérios mínimos:

- `/mcp/healthz` deve ser monitorado separadamente;
- `502` em `/mcp/healthz` deve acionar restart do processo MCP;
- deploy só deve ser considerado saudável após smoke MCP;
- logs do processo MCP devem ser consultáveis para janela de falha.

### 16.4 OAuth continua sendo etapa estrutural posterior

OAuth 2.1 com PKCE segue como alvo canônico para conectores remotos maduros, mas não é a correção emergencial da instabilidade atual.

Sequência recomendada:

1. estabilizar Bearer Token por conector;
2. corrigir bootstrap sem tenant;
3. implantar health/restart do MCP;
4. evoluir para OAuth.

---

## 17. MCP-01 — Supervisor idempotente do runtime MCP HTTP

Após a estabilização inicial do Bearer Token por conector, ficou registrado um risco operacional remanescente: durante deploy/restart, o MCP podia tentar subir mais de um processo na porta `8101`, gerando erro `address already in use`.

Decisão:

> O runtime MCP HTTP deve ser gerenciado por script idempotente, com lock, PID, health local e health público.

Script canônico:

```text
app32/scripts/manage_mcp_http.sh
```

Comandos:

```bash
scripts/manage_mcp_http.sh status
scripts/manage_mcp_http.sh health
scripts/manage_mcp_http.sh restart
scripts/manage_mcp_http.sh stop
scripts/manage_mcp_http.sh start
```

Regras:

- o deploy deve chamar `manage_mcp_http.sh restart`;
- o script deve adquirir lock antes de start/stop/restart;
- o script deve encerrar listener existente na porta `8101` antes de subir novo processo;
- o script deve validar `/healthz` local antes de declarar sucesso;
- o script deve manter logs e PID em paths previsíveis;
- o health público `/mcp/healthz` continua sendo a validação externa mínima.

Esta decisão reduz a chance de restart duplicado e prepara a base para monitoramento automático e botão futuro de reparo de conexão.

---

## 18. MCP-02 — Contrato operacional de conexão CLI/IA ↔ APP32

Após estabilizar token por conector, bootstrap sem `company_id` e supervisor idempotente do MCP HTTP, a próxima decisão é transformar as telas existentes em uma jornada operacional coerente de conexão.

SPEC oficial criada:

```text
app32/docs/spec/experiencia_conexao_app32_cli_ia_mcp_api_v1.md
```

Decisão:

> O APP32 deve tratar a conexão CLI/IA como um `Connection Profile` governado, com runtime, usuário, empresa, squad/perfil, surface, modo de autenticação, status de token, último uso, health e snippet específico por runtime.

Responsabilidades oficiais:

- `/profile`: entrada principal para instalar/conectar CLI/IA pessoal;
- `/api-mcp`: contratos, catálogo e interoperabilidade API/MCP;
- `/channels`: canais externos como e-mail, WhatsApp, Telegram, Instagram e provedores;
- console técnico MCP/API: readiness, release, diagnóstico, observabilidade e Engenharia.

Essa decisão evita criar nova tela antes de organizar a experiência existente e prepara a base para a análise assistida MCP-first, tenant-owned e human-gated.

### 18.1. Ajuste de decisão — tela única de Conexões

Após alinhamento metodológico, a entrada principal não deve ficar dispersa entre Perfil, API/MCP e Canais.

Decisão complementar:

> A tela `/channels` passa a ser a tela única de Conexões, reunindo WhatsApp, e-mail, Telegram, Instagram, provedores de IA e CLI/IA via MCP. A tela `/profile` permanece como modo detalhado/fallback seguro de instalação pessoal MCP.

Essa mudança preserva o que já funciona e reduz atrito para consultor e cliente.

---

## 19. MCP-03 — Diagnóstico e reconexão guiada

Após centralizar canais e MCP na tela `/channels`, a próxima evolução é reduzir o atrito de suporte quando a conexão CLI/IA falhar.

Decisão:

> A tela de Conexões deve mostrar diagnóstico operacional da conexão MCP e orientar a ação correta para o consultor/cliente sem exigir conhecimento técnico da arquitetura.

Sinais mínimos:

- health público do MCP;
- token ativo, ausente, revogado ou expirado;
- empresa padrão selecionada;
- runtime selecionado;
- último uso registrado;
- recomendação objetiva;
- passo a passo de reconexão.

O objetivo é transformar falhas comuns em ações guiadas: testar health, renovar token, copiar configuração, atualizar runtime e confirmar último uso.

---

## 20. MCP-04 — Transporte canônico `streamable-http` e erro explícito para SSE legado

Após teste externo com Claude, foi identificado que a instabilidade observada não estava em auth, tenant, RBAC ou tool específica.

Achado:

- conexão por `streamable-http` inicializa e autentica normalmente;
- tentativa por SSE legado contra `/mcp/user/` pode ficar pendurada antes de `initialize()`;
- portanto, o problema está no handshake de transporte quando o cliente usa SSE em vez de `streamable-http`.

Decisão:

> O transporte canônico do MCP remoto APP32 é `streamable-http`. SSE legado não deve ser recomendado em snippets novos e deve receber erro explícito quando detectado em handshake inicial sem sessão.

Implicações:

- `/mcp/healthz` deve expor `transport=streamable-http` e `sse_supported=false`;
- clientes MCP devem ser configurados em HTTP/streamable-http sempre que suportado;
- tentativa SSE sem sessão não deve ficar em `connecting...` indefinidamente;
- a mensagem de erro deve orientar o usuário a trocar o transporte.

Achado secundário:

- em `session_company`, `active_company_id` estava correto, mas `companies[].selected` podia refletir a empresa padrão em vez da empresa ativa persistida.

Decisão:

> `companies[].selected` deve refletir exatamente `active_company_id`; quando não houver empresa ativa, nenhuma empresa deve vir marcada como selecionada.
