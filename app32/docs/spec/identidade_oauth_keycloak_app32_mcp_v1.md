# SPEC — Identidade OAuth/OIDC e implantação Keycloak APP32/MCP

**Classe:** SPEC
**Data:** 2026-09-07
**Status:** arquitetura-alvo definida; IdP de produção preparado, sem OAuth APP32 ativo
**Card:** AA.J.21.239 — Auditoria e SPEC OAuth Keycloak APP32 MCP
**Liderança:** @ARQUITETO; governança gestao_versus_core
**Origem:** [histórico aprovado](https://chatgpt.com/share/6a9f1148-baec-83e9-9ad4-0fce7f197e17?ogimg=plain).

## 1. Limites e conclusão

Auditoria estática do checkout `codex/process-artifacts-runtime`, HEAD `e3acd8d642c88efc2595632f8a0cc749ee2c6933`. Não representa inspeção da branch principal remota nem certificação da produção. “Principal” foi interpretado como o contrato `PrincipalContext`, efetivamente encontrado no código. Alterações preexistentes do usuário foram preservadas.

O desenho é viável por evolução, não por substituição integral: já existem registry de surfaces, contexto por request, autorização tenant-aware e transporte Streamable HTTP. Faltam vínculo OIDC persistente, autenticação JWT efetiva e representação independente de pessoas, serviços e agentes. Ativar a flag OAuth existente não implementa esses componentes.

Esta SPEC complementa, sem duplicar a jornada, `C:/GestaoVersus/app32/app32/docs/spec/experiencia_conexao_app32_cli_ia_mcp_api_v1.md` e a base histórica `C:/GestaoVersus/app32/app32/docs/specifications/arquitetura_identidade_surfaces_squads_v1.md`. Em caso de conflito sobre identidade OAuth, prevalece esta evolução; regras atuais de runtime permanecem até o corte aprovado.

## 2. Auditoria AS-IS, evidências e riscos

Todos os arquivos nesta tabela ficam sob `C:/GestaoVersus/app32/app32/`.

| Evidência | Constatação | Consequência / prioridade |
|---|---|---|
| `src/intelligence/security/tenant_rbac.py:210`, `PrincipalContext` | Possui user, company, employee, role, channel, permissions e metadata; não possui subject/issuer/tipo de identidade explícitos. | Evoluir contrato sem criar usuário humano fictício para SERVICE/AGENT. P1. |
| `src/core/mcp_http_auth.py:87,409,678` | Identidade HTTP e verifier usam registry estático/token persistido; provider OAuth levanta `NotImplementedError`. | Implementar resource server/verifier para IdP externo, não servidor OAuth próprio. P1. |
| `src/core/mcp_http_auth.py:352-406` | Resolver DB-backed lê `fallback_role` de header/query e o aplica sem `_allow_context_override()`. | Entrada não confiável chega ao contexto autenticado. Remover override de privilégio; testar cadeia completa. P1, exploração ponta a ponta não demonstrada. |
| `src/core/mcp_runtime.py:146-172` | Identidade é reconsultada por user e company; role resolvido tem precedência sobre fallback. | Pode mitigar o risco anterior em alguns caminhos; não justifica manter o dado contaminado. Identidade técnica ainda depende do modelo humano. |
| `src/core/mcp_runtime.py:213`, `wrap_mcp_callable` | Política é aplicada quando capability é encontrada; flags de confirmação vêm do payload. | Auditar cobertura de todas as tools e comprovação de aprovação. Alvo: deny-by-default e aprovação persistida, não booleano autodeclarado. P1. |
| `services/user_mcp_token_service.py:2123` | Consulta token por hash, verifica usuário ativo e resolve empresas; atualiza uso/empresa e faz commit na autenticação. | Preservar isolamento; extrair autorização/seleção da gestão de token. JWT local não elimina consultas APP32 nem custo de auditoria. |
| `models/user_mcp_token.py` | Token pessoal carrega `last_company_id` e `last_harness_key`. | Estado compartilhado pelo token pode interferir entre conexões; futura seleção deve pertencer à conexão autenticada, não ao token global. |
| `src/core/mcp_http_server.py:118-150` | Já usa registry canônico, Streamable HTTP e configuração stateless; atribui `_token_verifier` privado do SDK. | Manter transporte e registry; reduzir acoplamento à API privada com versão testada. Não reconstruir MCP do zero. |
| `app.py:1202,1234` | Blueprint registrado vem de `api/routes/auth.py`. Também existe `api/auth.py`. | Alterar rota efetiva; não confundir arquivo paralelo com entrada ativa. |
| `requirements.txt:67-68` | Intervalos `mcp>=1.29.0,<2.0.0` e `fastmcp>=3.4.5,<4.0.0`. | Registrar versões efetivamente homologadas e compatibilidade antes do rollout. |
| `docker-compose.yml`, `deploy/systemd/app32-mcp-http.service`, `deploy/nginx/app32-mcp-http.conf` | Há composição Docker e artefatos de operação systemd/proxy. | Topologia real, permissões de hospedagem e capacidade para Keycloak devem ser verificadas; não presumir Docker em produção. |

## 3. Decisão-alvo

- Keycloak self-hosted como autoridade de autenticação, em serviço independente, PostgreSQL separado logicamente e credenciais próprias. Mesmo host é opção, não requisito; dimensionamento depende de medição.
- APP32 continua autoridade de memberships, tenants, roles, capabilities e aprovação humana. Keycloak não é CRM nem fonte exclusiva de permissão de negócio.
- USER usa Authorization Code + PKCE S256; SERVICE usa Client Credentials; AGENT possui identidade técnica própria. Cliente de IA operando sob login humano continua USER com contexto de atuação: nome do runtime não transforma pessoa em AGENT.
- `subject_type` (USER/SERVICE/AGENT) é diferente de `actor_type` (ex.: client_agent), `runtime_profile`, squad e harness. Manter esses eixos separados, sem concessão automática de privilégios.
- OAuth também pode transportar access tokens pelo header `Authorization: Bearer`. A migração é de **token proprietário para OAuth**, não a eliminação do esquema Bearer.
- APP32 → terceiros usa emissor/audience/credencial do terceiro, armazenados com proteção e escopo por tenant. Nunca encaminhar access token recebido pelo MCP a outra API como passthrough.

## 4. Contrato Principal e persistência propostos

Evoluir `PrincipalContext` de forma aditiva: `principal_id`, `subject_type`, `issuer`, `subject`, `client_id`, `auth_method`, `token_scopes` e identificador de correlação. Preservar `user_id` opcional apenas para pessoas vinculadas; role/permissões são resolvidos no APP32 para o tenant ativo. Não guardar token cru em metadata, logs ou auditoria.

Proposta de modelos novos (nomes sujeitos à revisão de migration):

| Modelo | Responsabilidade e restrições |
|---|---|
| IdentityPrincipal | ID interno e tipo; vínculo opcional ao User; status. Catálogo global de identidade, sem dados empresariais. |
| ExternalIdentity | Vínculo único `(issuer, subject)` → principal. Não vincular contas automaticamente por igualdade de e-mail. Provisionamento/vinculação exige fluxo autenticado ou convite aprovado. |
| PrincipalCompanyGrant | `(principal_id, company_id)`; role, limites de capabilities/surfaces, status e validade. FK e unicidade composta; toda consulta empresarial escopada por company_id. |
| ConnectionContext | Identificador opaco de conexão, proprietário principal/client, empresa selecionada e harness autorizado; seleção expira e é revalidada. Nenhum estado mutável compartilhado por access token. |

Identidade global é exceção explícita e limitada ao cadastro/vínculo; não libera leitura empresarial sem grant. SERVICE/AGENT têm responsável humano, finalidade, revogação e permissões próprias. Não herdam automaticamente acesso de quem os criou.

Autorização efetiva = grants APP32 ∩ limites do cliente ∩ scopes do token ∩ política da surface ∩ capability ∩ tenant ∩ gate humano aplicável. Role admin não contorna audience, tenant, surface, scopes ou revogação.

Domínios canônicos existentes devem ser preservados: `routine`, `processes`, `finance`, etc. Normalizar aliases antes de avaliar política; não introduzir `processos:read` como segundo catálogo paralelo. Mapping OAuth-scope → capability deve ser explícito e testado.

## 5. Fluxo e controles obrigatórios

1. Validar access JWT com biblioteca mantida: algoritmo permitido, assinatura, `iss`, `aud`, `exp`, `nbf` quando presente, subject e client. Rejeitar ID token como credencial da API; nenhuma escolha de issuer/JWKS por URL arbitrária recebida no token.
2. Cache de JWKS limitado, refresh controlado em `kid` desconhecido, proteção contra tempestade de refresh e timeout. Falha fecha acesso; não aceitar chave desconhecida quando IdP estiver indisponível. Token conhecido e válido pode continuar conforme política documentada de cache.
3. Resolver vínculo externo, status local e grants do tenant. Header/query pode solicitar empresa, nunca concedê-la; bloquear pedido fora dos vínculos. Sem empresa, permitir somente descoberta/seleção estritamente própria; exigir company_id para dados empresariais.
4. Injetar Principal por request; preservar reset de ContextVar e contexto do SDK. HTTP não herda identidade de env de stdio. Validar requests concorrentes de usuários/empresas diferentes.
5. Autorizar cada `tools/call`, inclusive ferramenta ausente do catálogo de capabilities: negar por padrão. `tools/list` é conveniência, não controle de segurança.
6. Aprovação de alto impacto referencia registro no servidor, vinculado a principal, empresa, ação, payload e validade; não confiar em `confirmed_mutation=true`.
7. Web: callback valida state, nonce OIDC, PKCE e redirect URI exato; sessão segura HttpOnly/Secure, proteção CSRF e logout. Access/refresh não aparecem em URL, snippet ou log.
8. Revogação: JWT local não garante revogação imediata no IdP. Definir TTL curto e SLA; bloqueio de principal/grant local deve prevalecer. Para urgência usar denylist/versionamento local com invalidação limitada e verificável. Rotação de refresh e revogação de sessão precisam de teste.

## 6. MCP e interoperabilidade

O alvo de referência desta auditoria é a revisão MCP **2025-11-25**, não uma promessa de compatibilidade automática com qualquer versão futura. Publicar Protected Resource Metadata e discovery do authorization server, com challenge 401 utilizável. Fixar URI canônica do recurso por endpoint e validar audience correspondente, incluindo proxy e prefixos `/mcp/<surface>`.

Homologar `resource`, PKCE, redirect URIs e mecanismo de registro por cliente. Pré-registro é alternativa; não presumir que habilitar DCR ou instalar Keycloak torna Claude/Codex compatíveis. Client ID Metadata Documents e DCR dependem de suporte e política do servidor escolhido. Não anunciar recurso não implementado. Client Credentials para API não comprova suporte automático de cada cliente MCP.

Preservar stdio e registry único. `user` não publica financeiro sensível; `analytics` não modifica dados; `admin` mantém gates; `ops` não vira atalho privilegiado. Integração real de Claude/Codex é gate separado, posterior à prova protocolar em homologação.

## 7. Plano por arquivos/componentes

Base absoluta de todos os caminhos abaixo: `C:/GestaoVersus/app32/app32/`. Arquivos marcados NOVO são propostas, não existem por efeito desta SPEC.

| Ação | Caminhos | Entrega / responsável |
|---|---|---|
| PREPARADO | `deploy/keycloak/keycloak-local.env.template`, `deploy/keycloak/keycloak.service.template`, `docs/runbooks/runbook_keycloak_local_postgres_sem_docker_v1.md` | Homologação local sem Docker, PostgreSQL separado, TLS loopback, segredos externos e referência futura systemd; não ativa OAuth no APP32 nem autoriza deploy. @ARQUITETO/@DBA. |
| FUTURO | `deploy/keycloak/compose.yml` | Container em modo produção, versão/digest homologados, DB separado, secrets externos, health, TLS/proxy, backup/restore, se Docker for adotado. @ARQUITETO/@DBA. |
| NOVO | `deploy/keycloak/realm-template.json` | Contrato declarativo de realm/scopes/client público local, sem segredos; independe de Docker e é pré-requisito para ensaio JWT/JWKS. @BACKEND_API/@ARQUITETO. |
| ALTERAR | `deploy/nginx/app32-mcp-http.conf`, `deploy/systemd/app32-mcp-http.service`, `requirements.txt` | Discovery acessível pelo proxy, variáveis não secretas e versões testadas; validar topologia antes de mudar deploy. @BACKEND_API. |
| NOVO | `models/identity_principal.py`, `models/external_identity.py`, `models/principal_company_grant.py`, `models/connection_context.py`, migration aditiva em `migrations/versions/` | Constraints, índices e vínculo seguro; backfill idempotente e reversível sem modificar passwords existentes. @DBA. |
| ALTERAR | `models/__init__.py`, `models/user.py` | Registrar relações e compatibilidade com User; não criar pessoas fictícias. @DBA. |
| NOVO | `services/identity_service.py`, `services/principal_authorization_service.py`, `services/connection_context_service.py` | Provisionamento, grants, resolução tenant-safe e seleção por conexão. @BACKEND_SERVICE. |
| NOVO | `src/intelligence/security/oauth_token_verifier.py` | Verificação JWT/JWKS compartilhada sem acoplamento à rota; contrato de falha fechado. @BACKEND_API. |
| ALTERAR | `src/intelligence/security/tenant_rbac.py`, `runtime_identity.py`, `tool_policy.py`, `src/core/mcp_runtime.py` | Principal aditivo, grants técnicos, interseção de autorização, auditabilidade e negar capability desconhecida. @BACKEND_SERVICE. |
| ALTERAR | `src/core/mcp_http_auth.py`, `src/core/mcp_http_server.py` | Adaptar verifier/contexto e discovery; remover trust em override; manter tokens antigos sob política explícita de compatibilidade. @BACKEND_API. |
| MANTER / INTEGRAR | `src/core/mcp_surface_registry.py`, `src/intelligence/tooling/capabilities.py` | Reusar catálogos e políticas; nenhuma lista OAuth paralela. @AI_ENGINEER. |
| NOVO / ALTERAR | `services/oidc_login_service.py` (novo), `api/routes/auth.py`, `app.py` | Login/callback/logout finos e sessão Flask; não modificar `api/auth.py` apenas por semelhança de nome. @BACKEND_API. |
| EXTRAIR / DEPRECIAR GRADUALMENTE | `services/user_mcp_token_service.py`, `models/user_mcp_token.py` | Extrair config/onboarding e resolução de empresa para services próprios; manter hash/revogação/legado durante transição. @BACKEND_SERVICE. |
| ALTERAR | `scripts/installers/install-codex-laboratorio.ps1`, `install-claude-laboratorio.ps1`, `install-sapiens-claude-desktop-windows.ps1`, `scripts/install_claude_mcp_app32_prod.ps1` | Distinguir OAuth remoto de compatibilidade stdio/token; preservar harnesses e instalação, sem embutir segredo OAuth. @AI_ENGINEER. |
| ALTERAR após rastrear templates efetivos | templates utilizados por `api/routes/auth.py` e jornada Conexões | Mostrar método, principal, tenant, permissões e reconexão; não duplicar gestão de credenciais no frontend. @FRONTEND. |
| AMPLIAR | `tests/test_core_mcp_http_auth.py`, `test_core_mcp_http_server.py`, `test_core_mcp_http_reconnect.py`, `test_core_mcp_runtime_http_context.py`, `test_user_mcp_token_service.py`, `test_auth_profile_mcp_token_routes.py` | Regressão e compatibilidade legada. @QA_AUTOMATION. |
| NOVO | `tests/test_oauth_token_verifier.py`, `test_identity_service.py`, `test_oidc_login_routes.py`, `test_oauth_mcp_tenant_isolation.py` | JWT, grants, callback, isolamento concorrente e lifecycle de credencial. @QA_AUTOMATION. |

## 8. Sequência de implantação e gates

**Revisão em 2026-09-09:** a sequência executável vigente está na seção 14. As fases abaixo são referências de rollout, não autorização para integrar OAuth antes do hardening. A seção 14 prevalece em caso de conflito.

Cada entrega futura terá um card próprio com checklist; os passos abaixo não são autorização de deploy nesta auditoria.

| Fase | Dependência | Critério para avançar |
|---|---|---|
| 0 — fechar contrato e hardening | esta SPEC | Teste negativo do override, cobertura de capabilities/gates, decidir issuer, recurso, vínculo e estratégia de registro. |
| 1 — Keycloak em homologação | topologia validada | Restore de DB comprovado, TLS/discovery, configuração sem segredo no Git e rollback documentado. |
| 2 — identidade e OAuth APP32 | fase 1 | Migration aditiva, piloto USER, callback/state/PKCE/nonce, grant tenant-safe e login legado preservado. |
| 3 — OAuth MCP | fase 2 | JWT, metadata, 401/403, isolamento concorrente, quatro surfaces e stdio aprovados. |
| 4 — Claude/Codex | fase 3 | Login e reconexão reais em versões registradas; token expirado, revogado e audience errada rejeitados. |
| 5 — SERVICE/AGENT | base de modelos desde fase 2 | Client Credentials individual, revogação independente, owner e grants; sem user_id artificial. |
| 6 — migrar usuários | piloto e métricas | Coortes por tenant, orientação de reconexão, cobertura de clientes e janela de compatibilidade explícita. |
| 7 — retirar legado | uso legado zerado no período aprovado | Revogar credenciais e desligar emissão antes da remoção de código; retenção de auditoria e rollback seguros. |

Flags propostas: método OAuth habilitado por ambiente/coorte e aceitação legada com allowlist e data de corte. Credencial OAuth inválida não deve cair silenciosamente no verificador legado. Manter namespaces e seleção explícitos; não inferir identidade confiável só pelo formato do token.

## 9. Testes de aceite, operação e rollback

- JWT: assinatura adulterada, algoritmo indevido, issuer/audience incorretos, expiração, nbf, kid novo/desconhecido, JWKS indisponível e rotação. Nenhum token/segredo nos logs.
- Tenant: dois usuários, duas empresas e duas conexões simultâneas do mesmo usuário; mudança de grant durante token válido; empresa forjada em payload/header/query; sem vazamento em ContextVar ou env.
- Privilégio: role em header não eleva acesso; AGENT não herda role do criador; surface e scope restritivos prevalecem; ferramenta desconhecida negada; gate falso não autoriza.
- Web: state/nonce errados, code reutilizado, redirect indevido, PKCE inválido, conta sem vínculo, e-mail coincidente e logout/CSRF.
- Compatibilidade: stdio, tokens antigos permitidos, coorte OAuth, healthz, reconnect, seleção de tenant/harness e instalação em clientes reais.
- Medir p50/p95, falhas de login, 401/403/503, refresh/JWKS, consultas/commits por chamada, decisões negadas e uso legado, sem alta cardinalidade ou exposição de identidade em métricas públicas. Limites numéricos de aceite exigem baseline de homologação, ainda não medido.

Rollback: desativar OAuth apenas para coorte afetada; preservar migrations aditivas e vínculos. Retornar a versão de aplicação homologada com compatibilidade legada restrita; nunca reativar tokens revogados ou override inseguro. Falha no IdP não pode liberar acesso. Migration destrutiva somente após janela de retenção; não executar downgrade do banco Keycloak com binário incompatível. Ensaiar restore com backup próprio em ambiente isolado antes de produção.

## 10. Documentação dependente e pendências

Antes de cada rollout, atualizar na ordem: Paper de comunicação → esta SPEC e SPEC de Conexões → Manifestos afetados pela identidade técnica → Playbooks de autorização/onboarding → Runbook de produção → Harnesses. Nesta entrega somente decisão/plano foi registrada: não reescrever instruções operacionais como se OAuth já existisse.

Pendências de decisão: domínio e issuer definitivo (incluindo realm); topologia real e recursos; SLA de revogação/TTL; registro suportado por cada cliente; aprovação de vínculo/backfill; isolamento e expiração de ConnectionContext; versões fixadas e matriz de compatibilidade. São gates de implementação, não permissões para escolhas silenciosas em produção.

## 11. Evidências de validação desta auditoria

- Inspeção estática de Principal, auth HTTP, runtime, serviço/modelo de token, rota efetiva, deploy e documentos preexistentes.
- Suite executada: `C:/GestaoVersus/app32/.venv/Scripts/python.exe -m pytest app32/tests/test_core_mcp_http_auth.py -q`, com PYTHONPATH apontando para `C:/GestaoVersus/app32/app32` e bootstrap de DB/runtime desligado: **18 testes passaram**. Aviso de depreciação do TestClient/httpx e aviso de dependência de charset no ambiente.
- Isso valida a regressão atual dessa suite, **não OAuth implementado, exploração dos riscos nem integração de produção**. Sem deploy, alteração de schema ou autenticação. Apenas card operacional e documentação.

## 12. Hardening executado nesta entrega

Em 2026-09-07, `src/core/mcp_http_auth.py` foi corrigido para que o caminho de token pessoal persistido não aceite `fallback_role` por header ou query string, inclusive quando `APP32_MCP_HTTP_ALLOW_CONTEXT_OVERRIDE=1`. O papel agora é exclusivamente aquele resolvido pelo serviço de token e pelos vínculos persistidos no APP32.

O teste negativo `test_db_backed_token_never_accepts_role_from_request` cobre simultaneamente query e header com papéis administrativos forjados. A empresa solicitada permanece submetida à validação de `UserMcpTokenService`; este ajuste não altera o contrato de seleção de empresa, o fluxo de token legado ou qualquer rota web.

Validação após o ajuste: `test_core_mcp_http_auth.py`, `test_core_mcp_runtime_http_context.py`, `test_core_mcp_http_server.py` e `test_mcp_profile_scope_matrix.py`: **36 testes passaram**. `git diff --check` não reportou erros.

Esta é uma correção de fronteira de confiança do legado. Não implementa OAuth, Keycloak, principal técnico, aprovação persistida ou o mapeamento de capabilities descritos nesta SPEC.

O contrato em memória de `PrincipalContext` também foi evoluído de modo aditivo com `principal_id`, `subject_type`, `issuer`, `subject`, `client_id`, `auth_method`, `token_scopes` e `correlation_id`. Ele aceita somente `USER`, `SERVICE` e `AGENT`, sem inferência baseada em squad/runtime. A auditoria registra identificadores técnicos e scopes, mas não o `subject` bruto. Não há migration, tabela, vínculo OIDC ou mudança de autorização concedida por esse contrato: estas são as próximas entregas.

Em 2026-09-09, a base persistente foi criada de forma aditiva: `IdentityPrincipal`, `ExternalIdentity` e `PrincipalCompanyGrant`, com migration `20260909_1000`. `ExternalIdentity` exige unicidade global de `(issuer, subject)`; grants exigem unicidade de `(principal_id, company_id)`, vínculo obrigatório com `company_id`, lifecycle e índices por tenant/status. A migration não cria dados, não faz backfill, não altera tabelas existentes e não foi executada. Capabilities continuam no catálogo/policy canônicos, não na tabela de grants.

`PrincipalAuthorizationService` resolve primeiro o vínculo global previamente provisionado `issuer/sub → principal` e, separadamente, o grant ativo da empresa explicitamente solicitada. A resolução global nunca autoriza dados empresariais sozinha; ela nega campos ausentes, vínculo desconhecido, principal ausente/inativo e não cria vínculo por e-mail. A decisão empresarial nega ausência de empresa, grant inexistente/cross-tenant, principal ou grant inativos e vigência futura/expirada. Não emite token, não faz commit e ainda não valida JWT: essa integração exige issuer/audience/JWKS definidos, migration aplicada e uma entrega específica de compatibilidade.

O runtime MCP agora possui o gate experimental `APP32_MCP_USE_PRINCIPAL_GRANTS`, desligado por padrão. Quando ligado **e** um `principal_id` chega pelo contexto HTTP autenticado/configuração server-side, o runtime exige o grant correspondente ao `company_id` antes de executar a policy. `principal_id` recebido no payload da tool, header ou query é ignorado. O gate não cria principal para tokens legados nem altera stdio; sua ativação exige migration aplicada, provisionamento prévio e homologação por coorte.

Como preparação isolada para a fase JWT, `src/intelligence/security/oauth_token_verifier.py` agora valida localmente access tokens OIDC contra `issuer`, `audience` e JWKS previamente configurados, com HTTPS, allowlist assimétrica de algoritmos, `kid`, assinatura, `exp`, `iss`, `aud` e `sub` obrigatórios. O módulo rejeita token que não declare `typ=Bearer`, não escolhe JWKS por claim do token, não mantém o JWT bruto no resultado e não concede acesso a tenant. Ele permanece fora do transporte MCP até existir configuração aprovada de issuer/audience/JWKS e wiring por coorte; `PyJWT` foi declarado como dependência explícita.

## 13. Referências primárias consultadas

- [MCP Authorization 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization): resource server, discovery, registro e vínculo do token ao recurso.
- [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers): endpoints e integração com aplicações.
- [Keycloak em container](https://www.keycloak.org/server/containers): implantação de serviço independente.

Consulta em 2026-09-07. Compatibilidade e dimensionamento continuam sujeitos à homologação da versão escolhida.

## 14. Backlog revisado e ordem obrigatória de execução

Classe documental: SPEC. Revisão de execução em 2026-09-09, solicitada após auditoria do código.

### Estado e governança

- Atividades abaixo definidas localmente; cadastro e reconciliação remotos pendentes. A tentativa de listar o projeto vigente falhou no carregamento da chave privada SSH, antes de consultar ou criar cards.
- Os identificadores OAUTH-R01 a OAUTH-R08 são referências locais, não códigos de cards do APP32.
- Resolver o projeto pelo marcador `ENGINEERING_OPERATIONAL_CURRENT=1` e empresa `company_id=9`; não fixar o project_id nem deduzir o projeto vigente de códigos históricos.
- Antes de cadastrar, consultar inclusive cards concluídos e reconciliar `AA.J.21.239`, `AA.J.21.261` e `AA.J.21.262`, além de títulos sobre gate de grants e resolução externa. Esses códigos provêm do histórico desta tarefa e não foram reconfirmados nesta revisão. Preservar notas/evidências e reutilizar entregas equivalentes; não sobrescrever checklists históricos ou concluir cards por testes antigos.
- Um card por entrega, com os checklists abaixo nas notas. Dependências são gates de execução, não apenas ordem visual. Registrar os códigos reais aqui após cadastro e confirmação por leitura.
- Responsáveis abaixo são papéis técnicos, não atribuições de usuários do sistema. Não inventar responsável nominal, prazo ou autorização de produção.
- Baseline: 95 testes passaram na revisão, mas isso não certifica OAuth, PostgreSQL, isolamento concorrente nem produção. A reprodução isolada mostrou permissões legadas preservadas após aplicação de grant restritivo.
- Esta atualização organiza o trabalho: nenhuma correção de código, migration, deploy ou ativação de OAuth é autorizada implicitamente pelo cadastro.

### OAUTH-R01 — [Hardening da fronteira de autorização MCP]

Prioridade: P1, bloqueadora. Líder: @BACKEND_SERVICE, revisão @ARQUITETO e @QA_AUTOMATION. Dependência: nenhuma técnica; reconciliar card antes da implementação.

- [x] Transformar a reprodução `grant cliente + permissões finance.write do legado` em teste de regressão e impedir a herança de permissões incompatíveis com o principal/grant.
- [x] Impedir fallback de identidade HTTP para variáveis de usuário/empresa do stdio; preservar o stdio em caminho explicitamente separado.
- [x] Negar execução de ferramenta sem capability cadastrada; inventariar e regularizar o catálogo canônico em vez de criar exceção genérica.
- [ ] Substituir booleanos de aprovação enviados pelo cliente por verificação de aprovação persistida, vinculada a principal, company_id, ação, payload e validade; impedir reutilização indevida.
- [ ] Testar tenants distintos, conflito entre payload/contexto, permissão herdada, capability ausente e aprovação forjada/expirada.

Aceite: tentativas negativas não chamam o callback da ferramenta; fluxo autorizado continua funcional; nenhuma ampliação de acesso por compatibilidade.

Evidência parcial em 2026-09-09: quando `APP32_MCP_USE_PRINCIPAL_GRANTS=1` e existe `principal_id` confiável, o runtime deixa de herdar `user_id`, `employee_id` e permissões do contexto/env legado. Para principal humano, `user_id` e `employee_id` são reidratados somente a partir do principal persistido; para SERVICE/AGENT permanecem nulos. O grant continua fonte exclusiva de company_id e papel-base, e a policy recebe permissões vazias até R02 formalizar a interseção com scopes/capabilities. A flag continua desligada por padrão e não habilita OAuth. Testes de regressão cobrem principal humano e técnico; os itens restantes de R01 seguem pendentes.

Evidência parcial adicional em 2026-09-09: o wrapper MCP agora nega antes do callback toda ferramenta sem capability canônica, removendo a inferência permissiva por nome financeiro. Auditoria local do catálogo carregado encontrou 70 ferramentas LangChain e nenhuma sem capability (319 capabilities registradas); esse inventário não substitui smoke de todas as surfaces remotas. Teste de regressão garante que callback de ferramenta não cadastrada não é chamado.

Evidência parcial adicional em 2026-09-09: `confirmed_mutation`, `human_gate_confirmed` e `approval_confirmed` recebidos no payload MCP não confirmam mutação. O wrapper envia confirmação falsa para a policy até que exista consumo atômico de aprovação persistida vinculada ao principal, empresa, tool, digest do payload e validade. Isso é fail-closed e pode bloquear mutations que antes dependiam desses booleanos; não há fallback de compatibilidade. O fluxo de agentes possui registros `AgentAction`, mas ainda não atende sozinho esse contrato para MCP porque a verificação/consumo e a expiração precisam ser consolidados na próxima entrega.

Evidência parcial adicional em 2026-09-09: `ToolApprovalService` foi criada como fronteira independente para localizar e consumir uma única aprovação `AgentAction` no formato MCP. Ela exige `principal_id`, `company_id`, nome de tool, digest JSON canônico, status aprovado, origem `mcp_tool_approval`, chave de ação e expiração válida; a consulta padrão usa bloqueio de linha e o consumo muda o registro para executado. O wrapper MCP faz primeira avaliação sem confirmação e consulta/consome essa aprovação somente quando a negativa é de human gate; depois reavalia toda a policy. Booleano recebido do cliente continua sem autoridade. A service ainda não cria solicitações de aprovação: UX/workflow de criação, aprovação humana e testes PostgreSQL concorrentes seguem pendentes. Testes unitários cobrem vínculo exato, expiração, divergência de principal/tool/origem e payload não canônico.

Evidência parcial adicional em 2026-09-09: o runtime reconhece contexto HTTP autenticado pelo transporte e não consulta `APP32_MCP_USER_ID`, `ACTIVE_USER_ID`, `APP32_MCP_FALLBACK_ROLE`, channel, surface ou client do processo quando esse contexto existe. Contexto HTTP sem usuário não herda usuário/role do stdio; o stdio sem contexto HTTP preserva seu caminho explícito por ambiente. Teste de regressão cobre o isolamento contra todas essas variáveis.

### OAUTH-R02 — [Contrato único de identidade autenticada e política efetiva]

Prioridade: P1, bloqueadora. Líder: @ARQUITETO com @BACKEND_API e @BACKEND_SERVICE. Depende de R01.

- [ ] Transportar principal_id, subject_type, user_id opcional, issuer, subject, client_id, auth_method, scopes e correlação até policy/auditoria sem reconstrução contraditória por metadata ou payload.
- [ ] Derivar vínculo humano do principal persistido; negar incompatibilidade entre usuário e principal. SERVICE/AGENT não herdam usuário/funcionário do processo.
- [ ] Formalizar e testar a interseção grant, limites do cliente, scopes, surface, capability, tenant e aprovação. Reutilizar o catálogo canônico; scopes não criam permissões novas.
- [ ] Definir modos explícitos de autenticação legada/OAuth: ausência de principal ou falha OAuth deve negar o caminho OAuth, nunca retornar ao legado. Documentar a flag experimental atual como insuficiente para enforcement OAuth.
- [ ] Cobrir propagação íntegra e reset de contexto, compatibilidade por keywords/posicionais e ausência de tokens/subject bruto na auditoria.

Aceite: identidade única e rastreável de entrada a execução; scope restrito limita inclusive admin; ausência de escopo obrigatório não ganha acesso por role.

Evidência parcial em 2026-09-09: `MCPExecutionContext` passou a expor `principal_id` como campo próprio e o wrapper o envia diretamente à policy e ao binding de aprovação. O valor continua originado exclusivamente do contexto HTTP autenticado/configuração server-side; payload da tool não o define.

Evidência parcial adicional em 2026-09-09: o contexto HTTP e `MCPExecutionContext` agora transportam `subject_type`, issuer, subject, client_id, auth_method, token_scopes e correlation_id como campos técnicos; o wrapper os envia diretamente à policy. O subject não é incluído na metadata do contexto nem na auditoria genérica do catálogo. Essa propagação não valida JWT, não autoriza scopes e não aceita esses campos por header/query/payload; o futuro verifier permanece sua única fonte OAuth.

Evidência parcial adicional em 2026-09-09: a policy passou a aplicar o contrato OAuth explícito `mcp:access ∩ mcp:<surface>` para identidades com issuer OIDC e método diferente de `internal_bearer`. `mcp:access` não concede nenhuma surface sozinho; `mcp:analytics` não permite `admin`, inclusive para role administrativa. O mapeamento é deliberadamente separado de `ToolScope`/capabilities, que continuam sendo avaliados pelo catálogo canônico. Tokens internos de transição permanecem no caminho legado até R05 ligar o verifier e impedir fallback em requisição OAuth.

### OAUTH-R03 — [Lifecycle de principals e grants validado em PostgreSQL]

Prioridade: P1. Líder: @DBA com @BACKEND_SERVICE. Depende de R02.

- [ ] Unificar a avaliação de status, starts_at, expires_at e revoked_at entre model e service, incluindo limites temporais e convenção UTC.
- [ ] Definir responsável humano, finalidade e lifecycle de SERVICE/AGENT; definir os invariantes de user_id por subject_type e os efeitos de exclusão/desativação de usuário.
- [ ] Preservar comparação exata de issuer/subject, sem strip/casefold que possa fundir identidades; rejeitar entradas inválidas sem auto-link por e-mail.
- [ ] Revisar migração aditiva contra heads atuais, FKs, índices e unicidades; executar upgrade/downgrade somente em PostgreSQL descartável autorizado, nunca SQLite ou produção.
- [ ] Testar concorrência de vínculo/grant, revogação, reativação, identidade órfã e provisionamento idempotente; documentar aprovação do futuro backfill.

Aceite: evidência real de migration e constraints em PostgreSQL; nenhum principal revogado/órfão obtém acesso; datas avaliadas de forma uniforme.

Evidência parcial em 2026-09-09: verifier, contexto RBAC e resolução de vínculo agora preservam `issuer`/`subject` literalmente após apenas rejeitar valores ausentes ou só de espaços; não aplicam trim/casefold antes da consulta de `ExternalIdentity`. Testes cobrem subject com espaços e confirmam que a busca persistida recebe o identificador exato. A migration aditiva também passou a exigir no banco `user_id` somente para USER e, para SERVICE/AGENT, `responsible_user_id` e `purpose` obrigatórios; identidades técnicas não usam humano sintético. O lifecycle de grant foi centralizado em `PrincipalCompanyGrant.inactive_reason_at(now)` e é reutilizado pela service para status, revogação, início e expiração. Ainda faltam execução em PostgreSQL e testes de concorrência desta atividade.

### OAUTH-R04 — [Contrato Keycloak e verifier JWT robusto]

Prioridade: P1. Líder: @BACKEND_API com @ARQUITETO. Depende de R03.

- [ ] Aprovar issuer/realm, audience/resource, JWKS, algoritmos, perfil de access token, client_id, TTL/SLA de revogação e registro de clientes; URLs de exemplo em testes não são configuração aprovada.
- [ ] Ajustar dependência explícita para PyJWT[crypto] e validar instalação limpa na versão Python alvo; revisar validação estrita das URLs e claims, preservando identificadores exatos.
- [ ] Implementar cache JWKS limitado, sincronização/limite de refresh para kid desconhecido e timeout; definir comportamento de chave conhecida, rotação e indisponibilidade sem fail-open.
- [ ] Tornar a distinção access token/ID token explícita no perfil Keycloak aprovado, sem assumir typ=Bearer como regra universal.
- [ ] Testar assinatura adulterada, algoritmo/kid inválido, claims ausentes, issuer/audience errados, exp/nbf, rotação, falha JWKS e rajadas concorrentes, sem chamadas reais ao IdP nos testes unitários.

Aceite: verifier isolado aprovado, sem integração pública; falhas seguras e comportamento de cache demonstrados, não apenas inferidos da biblioteca.

Evidência parcial em 2026-09-09: a dependência passou a declarar `PyJWT[crypto]` explicitamente. O verifier não presume mais `typ=Bearer`: o perfil do resource server pode exigir um `expected_token_type` explícito, enquanto perfis Keycloak que usem outro valor não são rejeitados por uma convenção implícita. O perfil também pode restringir `client_id` por allowlist explícita e exige o baseline `mcp:access`, sem conceder surface/capability por esse scope. `OAuthTokenVerifierSettings.from_mapping()` exige issuer, audience, JWKS **e ao menos um client_id aprovado**, rejeita espaços/formatos ambíguos e não consulta discovery ou o token. O adaptador `from_prefixed_environ()` só lê a família `APP32_MCP_OIDC_*`, cuja referência comentada está em `.env.example`; ele não ativa OAuth. Assinatura, algoritmo, `kid`, issuer, audience e temporalidade (`exp`/`nbf`) continuam fail-closed. A resolução JWKS agora é serializada por verifier e mantém backoff limitado por `kid` indisponível, evitando rajadas concorrentes de refresh; os testes cobrem repetição, concorrência e rotação para novo `kid`, sem chamada real ao IdP. A configuração aprovada do realm e ensaio contra seu JWKS real ainda são pendências de R04.

Evidência local adicional em 2026-09-10: Keycloak 26.7.3 com JDK 21 e PostgreSQL dedicado foi validado fora do repositório, em TLS loopback. O realm declarativo `app32-local` importa scopes `mcp:access ∩ mcp:<surface>`, audiência estável `app32-mcp-resource`, cliente USER com PKCE S256 e cliente SERVICE de smoke sem segredo versionado. Um access token SERVICE emitido pelo realm foi validado pelo verifier real contra JWKS HTTPS, com CA local explícita, issuer, audiência, `azp` e `mcp:access` corretos. O suporte opcional a `APP32_MCP_OIDC_CA_BUNDLE` preserva `CERT_REQUIRED`; não existe modo inseguro. Essa prova não liga OAuth no transporte MCP, não cria vínculo de identidade APP32 e não autoriza produção.

**Gate de sequência em 2026-09-10:** a base PostgreSQL local do APP32 está em `20260614_1200`, enquanto a migration aditiva de principals depende de `20260907_1900`. É proibido aplicar apenas a migration OAuth, criar as três tabelas manualmente ou ligar R05 nessa base divergente. O próximo passo obrigatório é reconciliar a cadeia Alembic local até o head aprovado, com backup e evidência, e só então aplicar a migration aditiva/provisionar vínculos `issuer/sub` e grants por `company_id`.

O harness read-only `scripts/qa/audit_alembic_reconciliation.py` foi criado para registrar colisões físicas sem executar `stamp` ou DDL. Além do fingerprint, ele classifica cada `upgrade` pendente que exige evidência por schema idempotente/não idempotente, mutation de dados ou SQL bruto. Após corrigir o classificador para extrair somente `upgrade` e reconhecer operações Alembic de coluna/índice, 30 das 34 revisions exigem essa evidência (10 idempotentes, 14 não idempotentes, 8 com mutation de dados e 20 com SQL bruto; as classes podem coexistir). A cópia isolada revelou que as três tabelas da primeira revision, `20260630_1845`, já existem embora o ledger esteja em `20260614_1200`; o fingerprint de tabelas, colunas, índices e constraints nomeadas é `complete_candidate`, sem autorizar ledger porque FKs/defaults/dados ainda exigem prova. Em `20260701_1015` e `20260701_1030`, os fingerprints também são `complete_candidate`. Já `20260701_1045` é parcial: as colunas existem, mas os dois índices não; há FK equivalente com nome automático, diferente do nome procurado pela migration, portanto reexecutá-la criaria redundância. A tabela está vazia na cópia, mas isso não autoriza DDL ou ledger. Em `20260702_1800`, a validação semântica da constraint confirmou `conversion_requested`; é `complete_candidate`, mas sem autorização de ledger. A `20260718_1200` está fisicamente ausente (coluna e índice), compatível com o ledger anterior, e não deve ser aplicada isoladamente. Também revelou que `audit_reports` e `audit_follow_ups`, da revision `20260730_1600`, existem; essa migration igualmente pode ocultar drift. Seu fingerprint de tabelas, colunas, índices e constraints nomeadas está completo, mas é somente `complete_candidate` e não autoriza `stamp`: ainda faltam FKs/defaults/dados e as revisions anteriores. Em seguida, `knowledge_sources`, `knowledge_chunks` e `knowledge_index_runs` já existem e o upgrade encontra `DuplicateTable` em `20260730_1700`. O fingerprint confirmou ainda que `knowledge_chunks` não possui `ix_knowledge_chunks_content_fts`, esperado por essa revision, nem índice FTS equivalente. Há dados a preservar nessa cópia: 181 sources, 2.297 chunks e 716 index runs. A materialização é parcial e o harness retorna `reconciliation_required=true` com `stamp_allowed=false`. A cadeia possui 34 revisions pendentes até o head único `20260909_1000`; deve ser reconciliada em sequência desde `20260630_1845`. O resultado é evidência de drift, não autorização para pular revisions, criar o índice manualmente, recriar tabelas com dados ou ligar R05.

Evidência adicional em 2026-09-10: a `20260719_0900` possui `audit_points`, `audit_executions` e `audit_execution_items` completos no fingerprint de colunas, índices e constraints. É apenas `complete_candidate`; não altera o gate de reconciliação nem autoriza `stamp`.

Evidência adicional em 2026-09-10: a `20260719_1030` possui tabelas de auditoria fisicamente existentes, mas `audit_evidence_links` não tem `ck_audit_evidence_links_parent`. A tabela está vazia e a ausência permanece drift parcial; não criar a constraint nem alterar o ledger isoladamente.

Evidência adicional em 2026-09-10: a `20260720_0900` está fisicamente ausente por completo — colunas, defaults, constraint e índice de elegibilidade. A tabela de análises está vazia nesta cópia, portanto seu `UPDATE` não produziu efeito; a revision continua pendente e não deve ser aplicada isoladamente.

Evidência adicional em 2026-09-10: o seed da `20260721_0900` está ausente por completo (`mission-official-v1.0`), embora a empresa AA exista. São esperados dois registros, global e tenant; a ausência é compatível com a revision pendente e não autoriza seed ou ledger isolados.

Evidência adicional em 2026-09-10: os seeds `vision-official-v1.0` e `values-official-v1.0` da `20260721_2130` estão ambos ausentes por completo, com zero dos dois registros esperados para cada versão. A ausência é compatível com a cadeia pendente e não autoriza seed ou ledger isolados.

Evidência adicional em 2026-09-10: o backfill da `20260723_1000` está ausente: há um projeto elegível sem portfólio, sem portfólio marcado pelo backfill e sem vínculo correspondente. Não executar o `INSERT`/`UPDATE` fora da cadeia Alembic.

Evidência adicional em 2026-09-10: os seeds de Posicionamento (`20260727_1800`) e Organograma (`20260727_2100`) estão ausentes por completo, com zero dos dois registros esperados para cada protocolo. A ausência é compatível com a cadeia pendente e não autoriza seed ou ledger isolados.

Evidência adicional em 2026-09-10: `knowledge_source_grants`, da `20260730_1800`, está completa no fingerprint de colunas, índices e constraint. É somente `complete_candidate`, sem autorização de `stamp`; o drift parcial da revision anterior continua bloqueando a cadeia.

Evidência adicional em 2026-09-10: a `20260801_0900` está parcial. Faltam os nomes históricos de índice e `ix_knowledge_training_pattern`; as unicidades UUID existem sob nomes diferentes, mas reexecutar a migration criaria índices redundantes. As tabelas afetadas estão vazias, mas não criar índices nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: a estrutura da `20260801_1500` está completa no fingerprint, mas o backfill de POPs é parcial: há 4 definições geradas com vínculo e 17 rotinas elegíveis sem definição. Isso torna `data_reconciliation_required=true`; não executar o backfill ou alterar ledger isoladamente.

Evidência adicional em 2026-09-10: `process_execution_assignments`, da `20260801_1530`, está completa no fingerprint de colunas, índices e constraints. É somente `complete_candidate` e não altera os gates de reconciliação.

Evidência adicional em 2026-09-10: na triagem detalhada da `20260802_2100`, as quatro tabelas de Árvore Estratégica existem, porém falta a FK nomeada `fk_strategic_trees_root_node` de `strategic_trees.root_node_id` para `strategic_tree_nodes.id` com `ON DELETE SET NULL`; a tabela possui somente as FKs de empresa e usuários. Assim, o schema é `partial_or_absent`, `stamp_allowed=false`. A capability `knowledge.strategic_tree` também não existe em `ai_capabilities`; não criar FK/capability nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: o marcador de rollout da `20260802_2100` confirmou capability e configuração habilitada ausentes para a empresa 9 (`absent_or_pending`). Não há rollout parcial a reparar nem autorização para ativação isolada.

Evidência adicional em 2026-09-10: na `20260813_1200`, `project_tasks` existe, mas falta `ix_project_tasks_board_page` sobre (`project_id`, `is_deleted`, `stage`, `id`). A revision está fisicamente pendente; não criar esse índice nem avançar o ledger fora da cadeia Alembic reconciliada.

Evidência adicional em 2026-09-10: na `20260821_1200`, as quatro tabelas do catálogo corporativo estão presentes, mas falta `ck_process_resource_links_criticality`. O seed tenant-safe das cinco dimensões é parcial: 20 das 65 dimensões esperadas não existem, cobrindo as empresas 3, 4, 5 e 13. A revision permanece divergente em schema e dados; não reparar constraint/seed nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: na `20260826_1800`, `indicator_goals` existe, mas faltam `name`, `goal_kind`, `goal_scope`, `composition_mode`, cinco constraints de regra e os dois índices de período. As duas normalizações de datas não têm linhas pendentes nesta cópia, mas o schema está `partial_or_absent`; não aplicar somente o schema nem alterar o ledger.

Evidência adicional em 2026-09-10: o schema da `20260826_2000` está completo, mas seu backfill não: há duas metas elegíveis com `routine_id` válido e zero registros em `indicator_goal_routines`. É divergência de dados; não executar o `INSERT` isoladamente nem alterar o ledger.

Evidência adicional em 2026-09-10: na `20260901_1900`, as quatro estruturas de execução de rotinas existem, mas faltam `routines.execution_mode`, sua constraint, seis constraints auxiliares e dois índices (código de gatilho e responsável único). A revision está `partial_or_absent`; não aplicar fragmentos nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: na `20260903_1200`, `process_activity_artifact_interactions` está completo, porém as tabelas anteriores de definição e execução não têm `execution_scope`/`scope_key`, suas constraints nem índices. A revision está parcial; não completar fragmentos nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: a `20260903_1300` está fisicamente ausente — sem `user_presence_sessions`, seus índices ou constraint. Isso é compatível com o ledger pendente; não criar a tabela isoladamente.

Evidência adicional em 2026-09-10: em `20260904_1400`, falta `roles.qualification_requirements`. Não adicionar a coluna nem alterar ledger fora da sequência reconciliada.

Evidência adicional em 2026-09-10: em `20260904_1500`, faltam as unicidades tenant-safe de `roles` e `employees`, e `employee_role_occupancies` está ausente. Não criar tabela/constraints nem alterar ledger isoladamente.

Evidência adicional em 2026-09-10: a `20260904_1800` está fisicamente ausente — sem `employee_qualification_evidences`, índice ou constraints. É compatível com o ledger pendente; não criar a tabela isoladamente.

Evidência adicional em 2026-09-10: a `20260907_1900` está fisicamente ausente — sem `usage_telemetry_hourly`, índices ou constraints. É compatível com o ledger pendente; não criar telemetria isoladamente.

Evidência adicional em 2026-09-10: a `20260909_1000`, head aditivo de identidade OAuth, está fisicamente ausente — sem `identity_principals`, `external_identities` ou `principal_company_grants`. A persistência OAuth não foi materializada; não aplicar somente essa migration enquanto a cadeia anterior estiver divergente.

Evidência adicional em 2026-09-10: a auditoria final cobriu as 34 revisions pendentes entre o ledger `20260614_1200` e o head `20260909_1000`, sem mutação. `schema_reconciliation_required`, `data_reconciliation_required` e `reconciliation_required` continuam verdadeiros; somente `seed_reconciliation_required` é falso. Isso não autoriza `stamp`, DDL, seed/backfill isolado ou a ativação de R05.

Evidência adicional em 2026-09-10: R04 avançou em clone descartável até `20260730_1600`, com o ledger confirmado nesse ponto. A execução controlada seguinte falhou em `20260730_1700` por `DuplicateTable` de `knowledge_sources`; a transação preservou o ledger em `20260730_1600`. O próximo trabalho é tornar essa revision reconciliável e idempotente no clone, não pular o ledger nem ativar R05.

Evidência adicional em 2026-09-10: a `20260730_1700` foi corrigida para validar o contrato físico pré-existente e usar criação idempotente exclusivamente para seus próprios objetos. No clone R04, a migration concluiu, materializou o índice FTS ausente e avançou o ledger a `20260730_1700`; o fingerprint ficou `complete_candidate`. A validação ocorreu apenas no clone descartável.

Evidência adicional em 2026-09-10: a `20260730_1800` também foi corrigida após `DuplicateTable` em `knowledge_source_grants`. A validação fail-closed e o DDL idempotente permitiram aplicá-la somente no clone R04; o fingerprint ficou `complete_candidate` e o ledger avançou a `20260730_1800`.

Evidência final do clone R04 em 2026-09-10: a cadeia Alembic foi executada integralmente apenas na cópia descartável `app32_oauth_r04_20260910`, que atingiu o head `20260909_1000` sem revisions pendentes. A auditoria final retornou `reconciliation_required=false`, `schema_gate=false`, `data_gate=false` e `seed_gate=false`. O smoke transacional de `IdentityPrincipal`, `ExternalIdentity` e `PrincipalCompanyGrant` foi revertido ao fim da transação. Essa evidência não altera a base principal/local, não provisiona vínculo OAuth persistente e não autoriza deploy.

### OAUTH-R05 — [Integração OAuth no transporte HTTP MCP]

Prioridade: P1. Líder: @BACKEND_API com @AI_ENGINEER. Depende de R01 a R04 concluídas.

- [ ] Ligar verifier, resolução externa, contrato de identidade e grant por tenant sob configuração explícita; suportar identidade técnica sem usuário humano fictício.
- [ ] Publicar discovery de recurso protegido apontando para o IdP externo, challenge WWW-Authenticate e contratos 401/403; não implementar authorization server proprietário no placeholder APP32.
- [ ] Preservar registry canônico de surfaces e separar validação HTTP da reavaliação por tools/call; falha de OAuth não tenta token legado como fallback.
- [ ] Definir seleção de empresa/conexão com validade e isolamento por principal/client; sem empresa, somente operações explicitamente autorizadas de descoberta própria.
- [ ] Exercitar cadeia HTTP real até callback com duas identidades/empresas e requisições concorrentes; negar contextos forjados e verificar reset após exceção, cancelamento e reconexão.

Aceite: testes HTTP ponta a ponta de allow/deny, surfaces e isolamento passam; OAuth continua desativado publicamente.

Evidência inicial de R06 em 2026-09-10: a matriz de homologação separa o SDK MCP Python local (candidato técnico imediato para `streamable-http` com SERVICE) dos clientes de uso final. O realm-template já contrata `app32-mcp-local` como client público com Authorization Code + PKCE S256 e `app32-mcp-service-smoke` como client confidencial de SERVICE; ambos exigem vínculo `issuer/sub` e `PrincipalCompanyGrant` no APP32. Claude Desktop permanece no caminho legado local `stdio`/proxy com bearer e não é evidência OAuth; Claude.ai exige HTTPS público e redirect registrado, portanto não pode ser homologado no loopback. A execução operacional, critérios negativos e limite de escopo estão no Harness R06; não houve ativação de OAuth, provisionamento persistente ou deploy.

Evidência adicional de R06 em 2026-09-10: o SDK MCP Python iniciou sessão `streamable-http` real contra a surface `ops` em loopback, negociou o protocolo e executou `tools/list` autenticado com access token SERVICE do Keycloak TLS/JWKS. O principal e grant foram criados somente no clone R04 e removidos no encerramento. A descoberta sem empresa selecionada agora trata a ausência de `company_id` como ausência de contexto para filtragem — não como autorização: `tools/list` pode exibir o catálogo publicado, enquanto `tools/call` continua exigindo grant para empresa explícita. A correção possui teste de regressão. USER PKCE, revogação, expiração, falhas do IdP, reconexão e clientes finais continuam pendentes.

Correção e evidência USER de R06 em 2026-09-10: a investigação mostrou que o perfil local emitia lightweight access tokens sem `sub`; o ajuste canônico adiciona ao client scope `mcp-resource` o mapper `oidc-sub-mapper` com presença explícita no access token e no lightweight token. O fluxo Authorization Code + PKCE S256 foi repetido com usuário efêmero, completou login, redirect, troca, validação de assinatura/issuer/audience/`sub` e inicialização de sessão MCP `streamable-http` na surface `user` com `company_id=9`. Principal USER, vínculo e grant existiram somente no clone R04; o usuário Keycloak, mapper temporário, registros e listeners foram removidos. Não flexibilizar o verifier; expiração, revogação, falha do IdP, reconexão e clientes finais continuam pendentes.

Conclusão local de R06 em 2026-09-10: a suíte focada de 104 testes validou expiração, issuer/audience, escopo baseline/surface, grant inativo/expirado, indisponibilidade de JWKS, ausência de fallback OAuth e reconexão somente de leitura. SERVICE Client Credentials e USER Authorization Code + PKCE foram exercitados por cliente SDK MCP real em `streamable-http`, com isolamento por `company_id`, clone descartável e limpeza confirmada. Esta é uma decisão de conclusão **local**: Claude.ai/Codex como clientes externos e qualquer listener HTTPS público continuam fora de escopo; R07 requer autorização explícita de produção, coorte, backup/restore e smoke pós-deploy.

Evidência parcial em 2026-09-10: o transporte HTTP MCP recebeu um adaptador OIDC por coorte explícita. A surface só entra no contrato OAuth quando coexistem `APP32_MCP_HTTP_ENABLE_OAUTH=1`, `APP32_MCP_OIDC_ENABLED_SURFACES` contendo a surface e `APP32_MCP_USE_PRINCIPAL_GRANTS=1`; as flags continuam desligadas por padrão. Na coorte, o JWT é verificado contra a configuração OIDC server-side, resolvido somente por vínculo exato `issuer/sub → principal` e chega ao runtime sem `company_id`. A empresa solicitada é então autorizada exclusivamente pelo grant persistido; SERVICE/AGENT não recebem usuário humano sintético. JWT inválido, vínculo ausente, escopo de surface insuficiente ou indisponibilidade da resolução retornam falha fechada e nunca tentam token interno/DB-backed como fallback. Surfaces fora da coorte preservam o contrato legado e não anunciam o issuer externo de outra coorte.

O resource metadata da surface OAuth aponta para o issuer Keycloak externo e as negativas OAuth retornam `WWW-Authenticate` com `resource_metadata`; `mcp:access` é o baseline e `mcp:<surface>` é exigido antes do callback. A suíte local cobre 401 sem fallback, 403 por scope, metadata, preservação do legado fora da coorte, propagação do principal técnico e isolamento de `company_id=9` contra `company_id=10` por grant. Não houve listener público, deploy, segredo, alteração de produção ou ativação de flag. A homologação com clientes reais permanece em R06.

Evidência adicional em 2026-09-10: o smoke R05 ocorreu por HTTP em loopback, com access token SERVICE emitido pelo Keycloak local sobre TLS e validado contra o JWKS real com a CA explícita. A surface `ops` foi usada porque é a scope default do client SERVICE do realm (`mcp:access ∩ mcp:ops`). Um principal técnico, vínculo `issuer/sub` e grant da empresa 9 foram criados apenas no clone R04; a chamada com `company_id=9` alcançou o callback e a mesma identidade com `company_id=10` recebeu negativa de tenant. A correção também alinhou a variável documentada `APP32_MCP_OIDC_CA_BUNDLE` ao carregador do verifier, sem reduzir a validação TLS.

Evidência final de R05 em 2026-09-10: duas identidades SERVICE distintas, uma do client local existente e outra de client Keycloak efêmero, foram verificadas contra o mesmo JWKS real e vinculadas a grants de empresas distintas no clone R04. Quatro requests HTTP concorrentes atravessaram o middleware OAuth da surface `ops` e o callback do runtime: os dois pares principal/empresa corretos foram permitidos e os dois cruzados foram negados. A allowlist do segundo client existiu somente no processo do smoke; ao final, os dois vínculos temporários, o client efêmero e o listener loopback foram removidos, e o Keycloak local foi parado. Isso valida o transporte HTTP/contexto MCP local, não substitui a homologação de conector/cliente real de R06.

Evidência de infraestrutura R07 em 2026-09-10: o website isolado `id.gestaoversus.com.br` foi provisionado no Configr como aplicação Docker, com Keycloak `26.7.3` em perfil `prod`, PostgreSQL `16.10-alpine` dedicado, volume próprio, segredos fora do repositório e listener restrito a `127.0.0.1:8080` atrás do proxy TLS. A imagem foi otimizada no build e inicia com `start --optimized`. O realm vazio `app32` foi criado sem importar usuários ou clientes do APP32; o discovery externo retornou o issuer exato `https://id.gestaoversus.com.br/realms/app32` e o health interno confirmou banco, cluster e inicialização em estado `UP`. Um dump PostgreSQL inicial foi gerado e validado com `pg_restore -l`; restore completo, clients OAuth APP32, migrations, flags e coorte continuam bloqueados pelos gates de R07.

### OAUTH-R06 — [Homologação OAuth com Keycloak e clientes reais]

Prioridade: P1. Líder: @QA_AUTOMATION com @BACKEND_API e @AI_ENGINEER. Depende de R05; requer ambiente isolado autorizado.

- [ ] Provisionar piloto aprovado em homologação com configuração/segredos externos ao Git, principals e grants explícitos, sem importar usuários de produção automaticamente.
- [ ] Validar USER com PKCE e SERVICE/AGENT com credenciais próprias nos clientes suportados; registrar versões e mecanismos reais de registro de cliente.
- [ ] Validar tokens expirados, scopes insuficientes, revogação local, rotação, IdP indisponível, reconexão e isolamento entre tenants em tráfego real.
- [ ] Medir latência e falhas, estabelecer limites de aceite e ensaiar rollback seguro sem reativar credenciais revogadas.
- [ ] Confirmar stdio/legado, healthz, auth obrigatória e segregação das quatro surfaces.

Aceite: relatório reproduzível de homologação e rollback, com pendências explícitas; teste unitário não substitui este gate.

### OAUTH-R07 — [Rollout OAuth controlado por coorte]

Prioridade: P2, bloqueada até R06 e autorização explícita de produção. Líder: @QA_AUTOMATION com @ARQUITETO.

- [ ] Consolidar SPEC e documentação dependente na ordem Paper → SPEC → Manifesto → Playbook → Runbook → Harness, sem duplicar decisões.
- [ ] Aprovar coorte, vínculo/backfill, janela, backup/restore e plano de comunicação/reconexão; definir critérios objetivos de parada.
- [ ] Aplicar migrations/provisionamento e ativar somente a coorte autorizada com smoke pós-deploy e monitoramento sem segredos.
- [ ] Demonstrar segregação entre OAuth obrigatório e legado explicitamente permitido; registrar evidências antes de ampliar a coorte.

Aceite: piloto de produção aprovado e observado; problemas revertem a coorte com rollback seguro. A criação deste card não autoriza deploy.

### OAUTH-R08 — [Desativação controlada de tokens proprietários]

Prioridade: P2, bloqueada até R07 e janela de uso legado zerado aprovada. Líder: @ARQUITETO com @BACKEND_API.

- [ ] Inventariar clientes/usuários remanescentes e comprovar ausência de uso legado no período definido, preservando compatibilidade stdio que não faça parte da retirada.
- [ ] Desabilitar emissão e revogar credenciais proprietárias sob autorização explícita, com comunicação e suporte de reconexão.
- [ ] Remover caminhos temporários, flags ambíguas e placeholder OAuth obsoleto, preservando auditoria e retenção acordadas.
- [ ] Validar negativa definitiva de credenciais revogadas e atualização de instaladores, runbooks e harnesses.

Aceite: legado desativado sem regressão dos clientes suportados e sem mecanismo de rollback que ressuscite credenciais revogadas.

### Ordem e próxima ação

`Reconciliação/cadastro → R01 → R02 → R03 → R04 → R05 → R06 → aprovação de produção → R07 → janela aprovada sem legado → R08`.

Próxima entrega técnica: R01. Não iniciar R05 por haver verifier e 95 testes unitários verdes. Datas serão definidas após estimativa e disponibilidade; nenhum prazo foi inventado nesta revisão.
