# SPEC — Glossário oficial do mcp-versus

**Classe:** SPEC
**Data:** 2026-10-08
**Status:** proposta para aprovação humana; nenhuma renomeação em produção é feita por este documento
**Card:** a registrar (estabilização e experiência do MCP)
**Liderança:** @ARQUITETO; governança gestao_versus_core
**Complementa:** [Identidade OAuth/OIDC e implantação Keycloak APP32/MCP](identidade_oauth_keycloak_app32_mcp_v1.md) (decisão de 2026-09-16: `mcp-versus` é o nome público do conector) e [Experiência de conexão APP32 CLI/IA/MCP/API](experiencia_conexao_app32_cli_ia_mcp_api_v1.md).

## 1. Decisão

1. **`mcp-versus` é o único nome do conector MCP do APP32**, para usuários, clientes (Claude, Codex, Antigravity), código, logs, métricas e documentação. Não há outro MCP de comunicação.
2. O que for **superfície interna** (`user`, `admin`, `analytics`, `finance`, `ops`) é detalhe de implementação de autorização e **nunca** é apresentado como conector, servidor ou "MCP" separado.
3. **"Pilot/piloto" não é nome de produto.** Descreve apenas a coorte de rollout; deixa de nomear caminhos, clients, constantes e variáveis ao final da transição (seção 5).
4. **"Sapiens" nomeia o produto de IA e seus fluxos** (workflow, árvore estratégica, contexto). Não nomeia o conector, o servidor, o endpoint nem o comando de instalação.
5. O espelho de permissões continua regido pela SPEC de identidade: o usuário vê e executa o que o APP32 lhe concede (grant ∩ RBAC ∩ teto); o glossário não altera autorização.

## 2. Termos canônicos

| Termo | Definição oficial | Não usar como sinônimo de |
|---|---|---|
| **mcp-versus** | O conector remoto único (servidor MCP HTTP + OAuth) do APP32. | pilot, APP32 MCP, Sapiens MCP, app32-user/admin/analytics |
| **endpoint** | A URL pública do mcp-versus. Alvo canônico proposto: `/mcp` (seção 5). | surface, mount |
| **surface** | Partição interna de autorização (`user`, `admin`, `analytics`, `finance`, `ops`). | servidor, conector |
| **tool** | Operação MCP publicada com nome, domínio e permissão exigida. | capability (a capability descreve a tool) |
| **capability** | Metadado de uma tool: domínio, permissões, risco, gate humano, escopo. | tool |
| **domínio** | Agrupamento funcional da tool (ex.: `finance`, `processes`, `whatsapp_status`). Deve existir no catálogo, na matriz de permissões e nos playbooks. | surface |
| **principal** | Identidade OAuth (`issuer/sub`) vinculada a um usuário APP32. | usuário, token |
| **grant** | `PrincipalCompanyGrant`: autorização do principal para uma empresa; `mcp_permissions` é teto restritivo. | role, escopo OAuth |
| **escopo OAuth** | Rótulo no token (`mcp:access`, `mcp:user`, …). Identifica a surface contratada; não concede permissão de negócio. | permissão |
| **permissão** | Direito de negócio resolvido pelo APP32 por empresa em cada chamada. | escopo OAuth |
| **realm** | Realm Keycloak `app32` em `id.gestaoversus.com.br`. | tenant, empresa |
| **client pré-registrado** | Client OAuth público com PKCE cadastrado no realm, por runtime (`mcp-versus-claude`, `mcp-versus-codex`, `mcp-versus-antigravity`). Caminho preferencial. | client DCR |
| **client DCR** | Client criado por registro dinâmico. Contingência para runtimes que não aceitam pré-registro; não deve acumular. | client pré-registrado |
| **runtime** | Cliente de IA que consome o mcp-versus: Claude Code, Claude.ai/Desktop, Codex, Antigravity. | usuário |
| **Sapiens** | Produto de IA e seus fluxos de trabalho. | mcp-versus |

## 3. Mapeamento: nome antigo → nome canônico

Contagens por busca textual na `main` em 2026-10-08 (código em `app32/src`, `services`, `api`, `scripts`, `models`, `utils`, `config.py`; exclui docs e testes). São indicativas, pois "sapiens" mistura produto e conector.

| Nome atual | Ocorrências | Canônico | Observação |
|---|---|---|---|
| `mcp-versus` / `mcp_versus` | 32 em 5 arquivos | `mcp-versus` | Já correto. |
| `/mcp/pilot` (URL do conector unificado) | — | `/mcp` | **Alias** durante a transição; mudar a URL altera o destinatário (`resource`/audience) dos tokens, então exige janela e reautenticação. |
| `/mcp/user`, `/mcp/admin`, `/mcp/analytics`, `/mcp/ops`, `/mcp/pilot/user`, `/mcp/pilot/analytics`, `/mcp/pilot/finance` | — | absorvidos por `/mcp` | Mounts por surface deixam de ser anunciados; remoção só após nenhum runtime depender deles. |
| `app32-mcp-pilot` (client Keycloak) | — | substituído pelos clients `mcp-versus-*` | Decisão de remoção é humana (configuração de segurança do Keycloak). |
| `APP32_MCP_*` (variáveis de ambiente) | 222 em 29 arquivos | `MCP_VERSUS_*` | O código passa a ler a nova e, na ausência, a antiga com aviso de descontinuação. `.env` de produção só muda por operação humana. |
| `PILOT_*_TOOL_NAMES`, `pilot` em identificadores | 49 em 11 arquivos | nomes por função (`UNIFIED_*`, `*_COHORT_*`) | Renomear só com testes de contrato verdes. |
| `sapiens-user`, `app32-user/admin/analytics` como nome de servidor/conector | poucos | `mcp-versus` | Instaladores e instruções ao usuário nunca exibem esses nomes. |
| "surface user/admin" dito ao usuário como "MCP user/admin" | — | "permissões do mcp-versus" | Surface permanece só como termo técnico. |
| `sapiens` (contexto, workflow, escopo de tool) | 1.010 em 128 arquivos | **sem renomeação em massa** | Manter onde significa produto/fluxo. Revisar caso a caso apenas os usos que nomeiam o conector. |

## 4. Regras

1. **Código novo, logs, métricas, mensagens de erro e documentação** usam apenas termos da seção 2. Mensagens ao usuário dizem "mcp-versus"; nunca "pilot", "surface" ou o nome do cliente Keycloak.
2. **Identificadores técnicos legados** (variáveis, constantes, caminhos) só mudam com alias de compatibilidade, teste verde e plano de reversão. Nunca por substituição global.
3. **Identidade e dados persistidos** (issuer, audience, `sub`, `client_id`, valores gravados no banco, chaves de cache) **não são renomeados** por este documento. Qualquer mudança neles é migração própria, com aprovação.
4. **Ferramentas novas** declaram nome, domínio e permissão no catálogo e pertencem ao mcp-versus; não nascem em conector separado.
5. **Instalação**: um único nome de servidor (`mcp-versus`) em todos os runtimes e em todos os comandos gerados.

## 5. Transição (escalonada, cada etapa com aprovação)

| Etapa | Entrega | Risco |
|---|---|---|
| T0 | Este glossário aprovado e linkado; Paper/Playbook/Runbook dependentes revisados | nenhum |
| T1 | Teste de contrato que falha ao surgir nome fora do glossário em mensagens ao usuário, instaladores e metadata | baixo |
| T2 | Leitura dupla de variáveis `MCP_VERSUS_*` / `APP32_MCP_*` com aviso | baixo |
| T3 | Alias `/mcp` → conector unificado, sem remover `/mcp/pilot` | médio (audience) — exige homologação com os runtimes |
| T4 | Migração dos runtimes para `/mcp` e para clients pré-registrados; limpeza dos clients DCR duplicados e do `app32-mcp-pilot` | médio — ação humana no Keycloak |
| T5 | Remoção dos aliases e mounts antigos | só depois de nenhum uso em 14 dias de eventos |

## 6. Critérios de aceite

- Nenhum texto exibido ao usuário contém `pilot`, `sapiens-user`, `app32-user|admin|analytics` ou "surface" como nome de conector.
- Um único nome de servidor nos comandos de instalação de Claude, Codex e Antigravity.
- Teste de contrato (T1) ativo no CI do MCP.
- Nenhuma renomeação alterou `issuer`, `audience`, `sub` ou dados persistidos sem migração aprovada.

## 7. Fora do escopo e pontos em aberto

- **Modelo de escopos** (`mcp:<surface>` vs escopo único): decisão adiada até haver dados de sessão e clientes (eventos do Keycloak).
- **URL canônica `/mcp`**: proposta; depende de homologar o `resource`/audience com cada runtime.
- **Remoção de clients e variáveis em produção**: operação humana; este documento apenas a especifica.
- **Uso real de nomes antigos fora do repositório** (`.env` do servidor, configurações locais dos usuários) não foi inventariado.

## 8. Documentos dependentes (ordem Paper → SPEC → Manifesto → Playbook → Runbook → Harness)

Revisar após aprovação: `paper_manual_unificado_utilizacao_ia_usuario_app32_mcp_v1.md`, `runbook_operacao_mcp_oauth_rbac_v1.md`, `playbook_whatsapp_status_mcp_v1.md` e os instaladores em `scripts/installers/`.
