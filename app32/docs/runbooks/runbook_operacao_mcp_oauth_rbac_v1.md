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
   `https://app.gestaoversus.com.br/mcp/pilot/` e concluir OAuth/PKCE.
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

## Provisionamento automático de identidade

1. Crie ou ative o usuário apenas no APP32 e confirme o vínculo ativo com a
   empresa. O APP32 gera o evento `identity_provisioning_outbox` e tenta a
   sincronização imediatamente.
2. Para usuário novo, o Keycloak envia o convite de definição de senha. Nunca
   copie senha local, hash ou token para o Keycloak, card, log ou suporte.
3. Se a identidade estiver pendente/falha, execute o processador
   `scripts/process_identity_provisioning_outbox.py` ou aguarde a retentativa
   agendada. Consulte somente status, código e mensagem saneada do evento.
4. Antes de alterar o client técnico, valide `manage-users`, `query-users` e
   `view-users` no realm `app32`; não conceda `realm-admin` para resolver
   falha de convite. `manage-realm` é excepcional e temporário, apenas para
   configurar SMTP/tema do realm, devendo ser revogado ao término.
5. Smoke mínimo: usuário novo recebe identidade, conclui a senha, autentica
   por OAuth e acessa exclusivamente empresas com vínculo ativo. Em seguida,
   desative-o no APP32 e valide a negativa no próximo uso OAuth.


### Correção de discovery unificada — AA.J.21.332 (2026-09-18)

- No endpoint `/mcp/pilot/`, `list_user_app32_capabilities` mantém o nome por compatibilidade, mas descreve as ferramentas publicadas pelo conector unificado, incluindo o filtro `domain=finance`. Nos endpoints segmentados seu significado permanece restrito à respectiva surface.
- `tools/list` e manifesto compartilham a seleção de ferramentas privilegiadas por scope OAuth e permissão específica da capability. `financial.view` não equivale a `financial.create`.
- O catálogo indica discovery, não autorização definitiva: cada execução revalida empresa/grant/RBAC e mutações com human gate exigem aprovação persistida. Scopes do manifesto são metadados do catálogo, não os claims do token.
- Critério de regressão: igualdade entre tools expostas e manifesto (exceto a própria tool de capabilities), filtro financeiro com leitura versus criação, token sem scope, teto de grant e isolamento tenant.
- Não declarar paridade integral com todas as funções do APP32: a publicação remota continua limitada à coorte revisada. Homologação real da sessão cliente permanece obrigatória; testes simulados não a substituem.

## Recuperar conexão OAuth pelo Perfil

Use **Perfil → Instalar Squad → Recuperar conexão OAuth** quando o usuário
não receber convite, não conseguir autenticar no Keycloak ou quando o vínculo
APP32/Keycloak precisar de realinhamento.

1. O próprio usuário autenticado confirma a ação. Ela não aceita empresa,
   e-mail, perfil ou permissões informados pelo navegador.
2. O APP32 recria/atualiza a identidade no Keycloak, reconcilia somente grants
   de empresas com vínculo `Employee` ativo e suspende grants locais obsoletos.
3. O Keycloak envia o e-mail nativo de `UPDATE_PASSWORD`. O usuário conclui a
   senha pelo link e então remove/reconecta `mcp-versus` no seu cliente.
4. Validar `tools/list`, uma consulta permitida e uma negativa cross-tenant.
   A recuperação não deve criar capabilities nem ampliar roles.
5. Em caso de limite de solicitações ou falha, não repetir em lote nem criar
   senha manual: consultar a auditoria saneada e o log do provisionador.

O e-mail usa o tema `versus` do Keycloak. Ele preserva link, expiração e ação
nativa do IdP; APP32 não deve enviar link próprio de redefinição para essa
finalidade.

### Privilégio do client técnico

O client de provisionamento usa `manage-users`, `query-users` e `view-users`.
`manage-realm` é excepcional, temporário e administrativo apenas para alterar
SMTP/tema do realm; revogue-o ao terminar. `realm-admin` é proibido para este
fluxo.
