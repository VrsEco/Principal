# Harness — Homologação OAuth MCP R06

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
| Codex desktop/CLI | depende de suporte OAuth/redirect confirmado | não selecionado até registrar versão e mecanismo | não inferir compatibilidade pelo suporte MCP genérico |

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
