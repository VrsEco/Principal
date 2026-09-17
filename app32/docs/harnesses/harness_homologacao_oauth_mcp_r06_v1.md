# Harness — Homologação OAuth MCP R06

> **Regressão obrigatória — 2026-09-17:** cobrir permissão APP32 concedida,
> teto opcional do grant, grant vazio, remoção de vínculo com token ainda
> válido e negativa cross-tenant. Escrita financeira só entra após contrato de
> `company_id` explícito, idempotência e aprovação humana consumível.
> **Incremento finance — 2026-09-17:** homologar a surface `finance` em fluxo
> completo: criação da aprovação persistida, aprovação pelo APP32, consumo único
> com payload idêntico e negativa cross-tenant antes de qualquer promoção.

Classe documental: Harness. Escopo: ambiente isolado local/homologação; nunca produção.

## Objetivo

Validar o contrato OAuth do resource server MCP após R05, sem ampliar coorte,
publicar listener, reutilizar identidade real ou registrar segredo/token.

## Matriz de clientes e decisão

| Cliente | Fluxo contratado | Situação R06 | Limite |
|---|---|---|---|
| SDK MCP Python local | `streamable-http` + Bearer OIDC SERVICE | candidato ao smoke técnico imediato | executa apenas loopback, Keycloak TLS e clone R04 |
| `app32-mcp-local` Keycloak | Authorization Code + PKCE S256, USER | pronto no realm-template; requer usuário efêmero e redirect loopback | não usar Direct Grant como evidência de PKCE |
| `app32-mcp-service-smoke` Keycloak | Client Credentials, SERVICE | pronto para smoke com client/grant efêmeros | não cria `user_id` sintético |
| Claude Desktop | `stdio`/proxy + bearer legado atual | fora da evidência OAuth R06 | não suporta concluir OAuth pelo proxy legado |
| Claude.ai | MCP remoto HTTPS + OAuth | bloqueado no loopback | requer URL pública, redirect e aprovação explícita de homologação |
| Codex desktop/CLI | Authorization Code + PKCE, DCR e MCP remoto HTTPS | confirmado em smoke autenticado read-only | exigir aprovação pontual; não registrar token nem selecionar aprovação permanente |

## Pré-condições fail-closed

1. Clone Alembic R04 no head e Keycloak local com TLS/CA explícita.
2. Flags apenas no processo do ensaio: `APP32_MCP_HTTP_ENABLE_OAUTH=1`,
   `APP32_MCP_OIDC_ENABLED_SURFACES=<surface>` e
   `APP32_MCP_USE_PRINCIPAL_GRANTS=1`.
3. Um principal e grant explícito por identidade; `company_id` solicitado e
   reavaliado no runtime. Token inválido nunca cai no registry legado.
4. Cada client/usuário/redirect criado para o ensaio é removido no `finally`.

## Sequência de evidências

1. SERVICE: inicializar sessão real pelo SDK MCP Python, listar tools e chamar
   somente operação de leitura autorizada na surface contratada.
2. USER: executar Authorization Code com PKCE S256 usando usuário efêmero;
   validar token, vínculo exato e grant da empresa solicitada.
3. Negativos: `exp`, `mcp:<surface>` ausente, vínculo/grant revogado,
   indisponibilidade controlada de JWKS/IdP e reconexão de leitura.
4. Isolamento: duas identidades e duas empresas em sessões concorrentes;
   somente os pares de grant corretos prosseguem.
5. Limpeza: confirmar zero vínculos, clients e usuários efêmeros; desligar
   listeners locais. Produção fica fora do ensaio.

## Critério de parada

Falha em assinatura, issuer, audience, scope, vínculo, grant, ContextVar,
limpeza ou negativa cross-tenant bloqueia R06. Nenhum resultado local autoriza
R07, deploy ou OAuth público; Claude.ai e Codex só entram após compatibilidade
e ambiente HTTPS de homologação aprovados.

## Evidência registrada

Em 2026-09-10, o smoke SERVICE usou o SDK MCP Python contra a surface `ops`
real em `streamable-http`: inicialização, negociação de protocolo e `tools/list`
autenticado passaram com access token emitido pelo Keycloak local TLS e JWKS
validado por CA explícita. O principal, vínculo externo e grant existiram apenas
no clone R04; a limpeza confirmou zero vínculos do smoke e nenhum listener MCP.
O Keycloak local também foi encerrado. A descoberta sem `company_id` somente
expõe o catálogo publicado; chamada de tool empresarial permanece bloqueada até
grant de empresa explícita. Não é evidência de USER PKCE nem de cliente final.

O primeiro ensaio USER PKCE em 2026-09-10 revelou access token lightweight sem
`sub`, que foi rejeitado corretamente pelo verifier. A correção canônica inclui
o mapper `oidc-sub-mapper` no scope `mcp-resource`, com `access.token.claim` e
`lightweight.claim` ativos. Repetido o ensaio com mapper temporário equivalente,
o USER efêmero concluiu Authorization Code + PKCE S256, validação OIDC e sessão
MCP `streamable-http` em `user` com empresa explícita. Usuário, mapper, vínculo,
grant e listeners foram removidos ao término. Aceitar token sem sujeito continua
proibido.

A validação final local executou 104 testes focados em 11,35 s. A cobertura
inclui expiração, `iss`/`aud`, scopes, grants inativos/expirados, JWKS
indisponível, ausência de fallback OAuth e política de reconexão de leitura.
Com os smokes USER e SERVICE, a R06 local está concluída. A promoção R07 não é
automatizável: exige autorização de produção e ambiente HTTPS público aprovado.

## Incremento local de auditoria P0 — 16/09/2026

Regressão focada: `test_tool_approval_service`, `test_intelligence_audit_persistence_plan`, `test_ai_audit_persistence` e `test_mcp_policy_audit`: 27 passed. Executar com `PYTHONPATH` apontando para `app32` e `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

Cobertura nova: tenant/usuário/status/tipo da aprovação, arrays e logs redigidos, persistência obrigatória de mutações, best-effort de leitura e callback negado quando a trilha está indisponível. A suíte ampla de contexto não concluiu no ambiente por import do app; não é evidência de aprovação da regressão completa.

Este incremento não substitui os smokes USER/SERVICE. Antes de fechar P0, repetir OAuth autenticado, grant revogado/cross-tenant, concorrência e replay com PostgreSQL real, persistência de eventos e rollout controlado.

Validação adicional: 13 testes de contexto HTTP sem wrapper aprovados. Os 4 testes de wrapper também passaram com módulos `app` e `tool_catalog` isolados por stubs, conforme fronteiras já mockadas pelos testes; isso não valida bootstrap Flask nem catálogo real. Total: 44 cenários aprovados nas execuções focalizadas e isoladas.

Incremento schema v2: 30 testes focados aprovados, adicionando `test_ai_audit_schema_v2.py`. Cobertura: migration/contrato de índices e colunas, preservação de legado/downgrade, campos OAuth/policy e INSERT sem DDL em transação independente. São testes contratuais com stubs, não execução Alembic em PostgreSQL. Não há listener local em `127.0.0.1:5432` nem executáveis PostgreSQL/Docker encontrados no PATH desta sessão; homologação de banco permanece pendente.

## Evidência PostgreSQL real P0 — 16/09/2026

Provisionado laboratório portátil com [binários da EDB](https://www.enterprisedb.com/download-postgresql-binaries), PostgreSQL 16.15. Nenhum serviço instalado e nenhum dado/tenant de produção acessado. O hash do arquivo baixado foi registrado no diretório ignorado; isso é integridade local, não checksum publicado pelo fornecedor.

`test_audit_p0_postgresql_integration.py`: 9 passed em 3,54 s. Regressão focalizada: 30 passed em 3,34 s. O primeiro ensaio teve falha sem logs visíveis e o segundo reteve pipes no `pg_ctl`; ambos os clusters foram encerrados. O runner foi corrigido para logs em arquivos e a execução final retornou `suite_exit_code=0`, `listener_stopped=true`, `synthetic_only`, `production_access=false`.

Cobertura real: 11 testes em PostgreSQL 16.15, incluindo revision em schemas novo/legado, idempotência, colunas/índices, preservação/downgrade, redação, concorrência/replay, tenant/usuário/payload/expiração, busca da chave exata com 21 aprovações não relacionadas e transação própria da trilha. O replay de implantação carregou o APP32 e executou `flask db upgrade` dos heads `20260913_1500` e `20260916_1000` para o head único `20260917_1000` em banco sintético.

O smoke OAuth usa chave RSA efêmera e access JWT realmente assinado; valida assinatura, issuer, audience, client, scopes, vínculo `issuer/sub`, grant tenant-safe, cross-tenant, revogação do principal e persistência da decisão na trilha. Não usa token de produção nem rede externa.

Foi acrescentado o gate de rollout `check_oauth_mcp_rollout_readiness.py`. Cinco cenários contratuais validam piloto isolado, prevenção de corte acidental da surface `user`, HTTPS obrigatório, coorte explícita e alerta de Dynamic Client Registration. Na estação atual, o preflight real retornou `ready=false` e exit code `2`, sem revelar valores, porque grants/rota piloto e configuração externa do IdP não estão injetados. Este é o comportamento esperado antes da homologação autorizada.

O gate agora cobre sete cenários e aceita `--live` para discovery/JWKS/RFC 9728 sem token. Um teste adicional iniciou servidor JWKS HTTPS somente em loopback, com certificado/CA efêmeros, e comprovou fetch real pelo verifier e negativa de audience incompatível. A regressão focalizada acumulada passou em 60 cenários.

Em 17/09/2026, o preflight live read-only contra os endpoints públicos produtivos retornou `ready=true`, com discovery, JWKS e protected-resource metadata coerentes. A rota `/mcp/pilot/user/` sem bearer respondeu `401 invalid_token` e `WWW-Authenticate` com o metadata canônico. Nenhum token ou dado empresarial foi enviado. Naquele estágio, permaneciam pendentes o smoke autenticado e o rollout do código deste incremento.

O smoke seguinte confirmou o cliente real: `codex mcp login` concluiu Authorization Code com PKCE e Dynamic Client Registration sem expor credenciais. Em sessão read-only, e após aprovação humana apenas para a chamada corrente, `list_user_app32_capabilities` retornou 4 capabilities distribuídas em 3 domínios, com scope `mcp_user`. Não houve shell, leitura de arquivos, mutação nem aprovação permanente. A prova fecha a compatibilidade Codex CLI ↔ OAuth/MCP público, mas não a versão P0, ainda não promovida.

Diagnóstico adicional: a cadeia histórica desde banco vazio falha antes deste incremento, em `20260205_2000`, por FK de `portfolios` para `companies` sem baseline Alembic correspondente. Essa dívida deve ser saneada em entrega própria; o P0 não deve reescrever revision histórica. O IdP/JWKS HTTPS externo e o cliente Codex CLI já foram comprovados; ainda falta rollout controlado do código/migration P0 e validação pós-deploy, portanto o P0 permanece aberto.




No preflight final de 17/09/2026, a integração com `origin/main` revelou colisão do identificador inicialmente proposto `20260916_1000` com a migration de permissões MCP já publicada. O release foi corrigido sem reescrever histórico: a trilha de auditoria tornou-se a merge revision `20260917_1000`, dependente dos heads `20260913_1500` e `20260916_1000`. Novo laboratório: 11 testes PostgreSQL aprovados, `flask db upgrade` alcançou head único `20260917_1000` e o listener foi encerrado.

## Critério pendente — endpoint canônico `mcp-versus`

Antes de substituir as coortes de URL por um único endpoint público, o harness
deve comprovar: (1) `tools/list` só publica tools permitidas ao principal;
(2) cada chamada aplica a surface e o scope próprios da tool, e não uma
surface implícita do conector; (3) `company_id` sem grant continua negado;
(4) finance não é publicado ao perfil sem permissão APP32; (5) uma mutação
financeira cria aprovação persistida e só aceita replay idêntico. A troca de
nome local, isoladamente, não satisfaz esses critérios.
