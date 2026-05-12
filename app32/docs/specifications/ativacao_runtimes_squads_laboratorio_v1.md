# Ativação dos Runtimes dos Squads — Empresa-Laboratório Versus v1

## Status
Documento de execução do card `AA.J.16.6`.

## Objetivo
Registrar a ativação controlada dos runtimes externos do laboratório, validando:
- Claude -> `Squad Cliente`
- Antigravity -> `Squad Versus`
- Codex -> `Squad de Engenharia`
- APP32/MCP remoto em produção como núcleo online do experimento

---

## 1. Contexto do laboratório
Empresa-alvo do experimento em produção:
- `company_id`: `10`
- `client_code`: `M1`
- nome: `Empresa-Laboratorio Versus - Validacao Integrada dos 4 Pilares`

Regra do experimento:
- a base da empresa é preparada no APP32
- a partir daí, a operação distribuída deve acontecer por runtime externo + MCP

---

## 2. Distribuição oficial dos runtimes
- **Claude** -> `squad_cliente` -> surface `user`
- **Antigravity** -> `squad_versus` -> surface `admin`
- **Codex** -> runtime técnico do experimento -> surface `ops` como alvo preferencial

---

## 3. Ajustes necessários identificados durante a ativação
Durante o smoke inicial do MCP remoto, foram identificados três gaps concretos:

1. o MCP HTTP remoto não publicava a surface `/mcp/ops`
2. os startup tools publicados nos snippets dos profiles estavam desalinhados com a surface real
3. a documentação operacional dos squads ainda refletia a sequência antiga de startup

---

## 4. Correções aplicadas
### 4.1 MCP HTTP remoto
Arquivo ajustado:
- `C:\GestaoVersus\app32\app32\src\core\mcp_http_server.py`

Correções:
- inclusão da surface `ops` no servidor HTTP remoto
- inclusão de `/mcp/ops` no `healthz`
- inclusão de `/mcp/ops` no índice público de endpoints
- inclusão do app `ops` no lifespan da aplicação HTTP

### 4.2 Snippets e startup tools
Arquivo ajustado:
- `C:\GestaoVersus\app32\app32\services\mcp_connection_snippet_service.py`

Correções:
- `squad_versus` passou a iniciar por `list_admin_app32_capabilities`
- `squad_cliente` passou a iniciar por:
  - `list_user_app32_capabilities`
  - `describe_app32_profile_contracts_tool`
  - `describe_app32_surface_playbooks_tool`
- `sapiens_default` deixou de depender de `bootstrap_session_context` como startup obrigatório

### 4.3 Documentação operacional
Documentos alinhados ao contrato corrigido:
- `arquitetura_operacional_squad_cliente_v1.md`
- `arquitetura_operacional_squad_versus_v1.md`
- `fechamento_operacional_squads_empresa_laboratorio_v1.md`
- `implantacao_cli_harness_squads_v1.md`
- `mcp_perfis_tools_liberacoes_por_squad_v1.md`

---

## 5. Evidências de ativação
### 5.1 Arquivos locais de configuração
As credenciais e configurações runtime-específicas foram geradas fora do repositório, em diretório local controlado.

### 5.2 Usuário técnico do cliente criado para o laboratório
Foi criado um usuário operacional da empresa-laboratório para o runtime do `Squad Cliente`, com token MCP pessoal para surface `user`.

### 5.3 Smokes mínimos validados
O experimento deve validar no mínimo:
- `/mcp/healthz` online
- negação sem autenticação
- `Squad Cliente` acessando `user`
- `Squad Versus` acessando `admin`
- `Codex/Engenharia` acessando `ops`
- segregação de surfaces

---

## 6. Resultado esperado após deploy
Com as correções publicadas, o estado-alvo do laboratório passa a ser:
- `/mcp/user` ativo para `Squad Cliente`
- `/mcp/admin` ativo para `Squad Versus`
- `/mcp/ops` ativo para `Squad de Engenharia`
- startup tools coerentes com a surface real
- base pronta para avançar à ingestão de dados via API/MCP

---

## 7. Critérios de aceite do card AA.J.16.6
Este card é considerado atendido quando:
- os três runtimes do experimento possuem configuração definida
- o MCP remoto publica as surfaces necessárias ao experimento
- os startup tools publicados estão coerentes com o contrato ativo
- os smokes mínimos passam em produção controlada
- o projeto pode avançar para `AA.J.16.7`
