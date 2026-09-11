# Playbook — Onboarding OAuth controlado para clientes MCP

**Classe documental:** Playbook
**Status:** vigente para coortes controladas
**Data:** 2026-09-11
**Card:** AA.J.21.280
**Escopo:** clientes externos que consumam o MCP remoto APP32 com login humano OAuth/OIDC.

## Decisão

O acesso remoto não é aberto por URL, token compartilhado ou `company_id`
informado pelo cliente. Cada conexão é autorizada pela interseção de identidade
OAuth, client OAuth permitido, scopes, surface, `PrincipalCompanyGrant` e policy
da tool. O piloto produtivo usa somente a surface `user` em
`/mcp/pilot/user`.

Este playbook é para **USER + Authorization Code com PKCE S256**. SERVICE e
AGENT exigem entrega e playbook próprios; não reutilizam conta humana nem o
client público desta jornada.

## Pré-requisitos de entrada

1. O caso de uso é leitura operacional e cabe na surface `user`; não inclui
   `finance` sensível, `admin`, `analytics` ou `ops`.
2. Há responsável de negócio, usuário humano identificável, empresa(s) alvo e
   runtime MCP compatível com OAuth remoto.
3. O cliente OAuth e seus redirect URIs foram revisados. Para CLI/desktop,
   PKCE é obrigatório; client ID não é segredo e senha/refresh token nunca são
   copiados para prompt, card ou documento.
4. A empresa foi validada no APP32; a liberação será feita por grant explícito,
   nunca por e-mail coincidente ou papel fornecido pelo cliente.

## Fluxo operacional

| Etapa | Responsável | Ação | Evidência obrigatória |
|---|---|---|---|
| 1. Intake | Consultor + cliente | Registrar runtime, finalidade, usuário, empresa, surface e tools necessárias. | Ticket aprovado e menor privilégio justificado. |
| 2. Identidade | Engenharia | Criar ou vincular `(issuer, subject)` a um `IdentityPrincipal` USER. | Principal ativo; sem token ou senha em registro. |
| 3. Tenant grant | Engenharia + responsável da empresa | Criar `PrincipalCompanyGrant` ativo, com role e validade mínimas para cada `company_id`. | Grant auditável por empresa. |
| 4. Client OAuth | Engenharia | Autorizar o client OAuth do runtime/coorte e seus redirects exatos; manter issuer, audience e scopes MCP. | Revisão do client e da coorte; nenhuma credencial exposta. |
| 5. Conexão | Cliente | Adicionar a URL MCP recebida e autenticar no Keycloak com sua própria conta. | Login interativo concluído; cliente lista o catálogo. |
| 6. Smoke | Cliente + Engenharia | Executar uma leitura permitida na empresa concedida e uma negativa fora do grant. | Sucesso positivo e negação cross-tenant registrados. |
| 7. Operação | Suporte + Engenharia | Monitorar 401/403, expiração e uso; revogar client, identidade ou grant diante de incidente. | Registro de conexão e procedimento de revogação disponível. |

## Parâmetros do piloto atual

- URL MCP: `https://app.gestaoversus.com.br/mcp/pilot/user/`.
- Discovery do recurso: `/.well-known/oauth-protected-resource/mcp/pilot/user`.
- Issuer: `https://id.gestaoversus.com.br/realms/app32`.
- Audience: `app32-mcp-resource`.
- Scopes mínimos: `mcp:access` e `mcp:user`.
- Catálogo piloto: `list_user_app32_capabilities`, `get_company_profile`,
  `list_meetings`, `list_projects` e `list_project_tasks_secure`.

Esses parâmetros não concedem acesso sozinhos. O `company_id` requerido pela
tool é revalidado contra o grant do principal a cada chamada.

## Conector Codex no APP32

O APP32 expõe, para usuário autenticado, a configuração pública do conector em
`GET /profile/mcp-oauth/codex/config`. A resposta não aceita `company_id`, não
cria grant e não contém senha, token ou segredo. Quando a coorte estiver
habilitada, ela entrega os comandos `codex mcp add`, `codex mcp login` e
`codex mcp list`; o login abre o navegador somente na conexão inicial,
expiração, revogação ou reconexão.

A tela `/profile` apresenta o cartão **Conectar Codex por OAuth**. Sua feature
flag é `APP32_MCP_OAUTH_CODEX_CONNECTOR_ENABLED`; o `client_id` é configurado
externamente por `APP32_MCP_OAUTH_CODEX_CLIENT_ID`. Ambos precisam ser
habilitados somente na publicação controlada da coorte.

## Regras de expansão

- Um client OAuth representa o **software/canal**, não a fronteira de tenant.
  A fronteira de dados é o principal e seus grants APP32.
- Uma nova coorte ou runtime só entra após client OAuth, redirects, matriz de
  compatibilidade e smoke próprio aprovados. Não reutilizar permissões de uma
  coorte como atalho.
- Conceder mais de uma empresa exige aprovação explícita por empresa e smoke de
  seleção/isolamento. Não inferir empresa padrão de token global.
- Revogar um grant deve bloquear o uso mesmo se houver access token ainda
  válido; revogação urgente também desativa identidade ou client conforme a
  causa.
- Credencial OAuth inválida falha fechada. Nunca fazer fallback para token
  legado em uma rota OAuth.

## Critérios de aceite

1. Sem Bearer, token com `iss`/`aud`/scope incorreto ou client não permitido:
   acesso negado.
2. Usuário autenticado lista somente o catálogo da coorte/surface permitida.
3. Leitura em `company_id` com grant ativo funciona; a mesma leitura em empresa
   sem grant é negada e não retorna dados de negócio.
4. Nenhum segredo, token ou dado sensível aparece no ticket, log ou artefato de
   onboarding.
5. O cliente consegue reconectar por OAuth sem intervenção de Engenharia; para
   revogação ou incidente, o suporte segue o runbook correspondente.

## Limites

- Este playbook não substitui o onboarding legado `stdio`/token descrito em
  `docs/governance/external_ai_mcp_onboarding_manual.md`; aquele caminho não
  deve ser anunciado como OAuth remoto.
- Este playbook não autoriza habilitar nova rota, client, redirect URI, grant
  produtivo ou deploy sem card, revisão e autorização operacional apropriados.
