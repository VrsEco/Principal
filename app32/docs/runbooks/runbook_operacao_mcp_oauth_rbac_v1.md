# Runbook — Operação e diagnóstico do MCP OAuth/RBAC

> **Diagnóstico obrigatório — 2026-09-17:** validar a projeção APP32 → MCP
> removendo em homologação um vínculo ou permissão e repetindo a chamada sem
> renovar o token. A negativa confirma que OAuth não mantém RBAC paralelo.

**Classe documental:** Runbook  
**Escopo:** `mcp-versus` remoto OAuth, produção controlada  
**Data:** 2026-09-16

## Fluxo normal

1. No APP32, confirmar usuário ativo, empresa correta, papel e
   `PrincipalCompanyGrant` ativo.
2. No cliente, conectar `mcp-versus` em
   `https://app.gestaoversus.com.br/mcp/pilot/user/` e concluir OAuth/PKCE.
3. Executar `tools/list`, uma leitura da empresa concedida e uma negativa
   cross-tenant. Não registrar token, cookie, código ou senha na evidência.
4. Para mutação, confirmar que a tool está na surface correta e que a policy
   servidor exige/aprova o gate aplicável antes da chamada.

## Diagnóstico por sintoma

| Sintoma | Verificação | Ação segura |
|---|---|---|
| `401 invalid_token` | issuer, expiração e reconexão OAuth | reautenticar; nunca inserir Bearer manual na conexão OAuth |
| `403`/scope | scopes `mcp:access` e `mcp:user`, client/redirect aprovados | corrigir o client no IdP; não ampliar escopo por tentativa |
| empresa negada | grant ativo e `company_id` pedido | corrigir/criar grant explícito após aprovação |
| tool não aparece | catálogo da surface `user` | não alterar role para contornar; encaminhar para a surface/fluxo correto |
| cliente mostra catálogo antigo | cache/sessão local | reiniciar o cliente e refazer login OAuth |

## Revogação e incidente

1. Suspender o `PrincipalCompanyGrant` para bloquear o tenant imediatamente.
2. Se houver suspeita de identidade, desativar o principal e revogar sessão no
   IdP conforme o incidente.
3. Preservar correlação, `client_id`, principal, empresa, surface e decisão de
   policy; nunca preservar token cru.
4. Revalidar 401 sem autenticação, 403 cross-tenant e o catálogo após a
   contenção.

## Limite de segurança

`mcp_permissions` é teto opcional e não mecanismo de elevação. `user` não
publica finance sensível ou mutações; esse acesso precisa de entrega/surface
própria com policy, auditoria e gate aprovados.

## Coorte analytics financeira

Antes de habilitar, validar o usuário, `financial.read`, o grant para cada
empresa e o escopo `mcp:analytics`. Após conectar, validar uma leitura
permitida, uma empresa sem grant e a ausência de tools mutáveis. O nome público
continua `mcp-versus`; `analytics` é uma surface interna e nunca uma marca de
conector para o usuário.

## Coorte financeira operacional

Usar a surface `https://app.gestaoversus.com.br/mcp/pilot/finance/` somente
para usuário APP32 já autorizado, com scope `mcp:finance` e `company_id`
explícito. O nome público do conector é `mcp-versus`; não criar aliases como
`mcp-versus-finance`. Para mutar: executar a chamada uma primeira vez, aprovar
a solicitação persistida exibida no APP32 e repetir **o mesmo payload**. Não
passar booleano de confirmação, não alterar o payload após a aprovação e não
repetir operação com outro `company_id`.
