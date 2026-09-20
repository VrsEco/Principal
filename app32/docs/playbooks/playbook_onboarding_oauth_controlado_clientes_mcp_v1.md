# Playbook — Onboarding OAuth controlado para clientes MCP

> **Gate adicional — 2026-09-17:** antes de aprovar uma coorte, testar a
> revogação no APP32 com o mesmo token OAuth ainda válido. A remoção de vínculo
> ou permissão deve negar a próxima chamada MCP; `mcp_permissions` não pode
> restaurar esse acesso.

**Classe documental:** Playbook
**Status:** vigente para coortes controladas
**Data:** 2026-09-11
**Card:** AA.J.21.280
**Escopo:** clientes externos que consumam o MCP remoto APP32 com login humano OAuth/OIDC.

## Decisão

O acesso remoto não é aberto por URL, token compartilhado ou `company_id`
informado pelo cliente. Cada conexão é autorizada pela interseção de identidade
OAuth, client OAuth permitido, scopes, surface, `PrincipalCompanyGrant` e policy
da tool. O conector produtivo usa o endpoint canônico `/mcp/pilot/`, com
catálogo calculado por principal, permissões APP32, grant e scopes OAuth.

Para caso de uso financeiro, há coorte controlada em `/mcp/pilot/finance/`,
com scope `mcp:finance`, `company_id` explícito e aprovação humana persistida
antes de qualquer mutação. A coorte financeira não amplia o perfil APP32:
apenas projeta no MCP as permissões efetivas já existentes para o mesmo
usuário. Ela não recebe nome público próprio: o nome exibido ao usuário é
sempre `mcp-versus`.

Este playbook é para **USER + Authorization Code com PKCE S256**. SERVICE e
AGENT exigem entrega e playbook próprios; não reutilizam conta humana nem o
client público desta jornada.

## Pré-requisitos de entrada

1. O caso de uso cabe no catálogo revisado da surface `user`; não inclui
   `finance` sensível, mutação financeira, `admin`, `analytics` ou `ops`.
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

- URL MCP: `https://app.gestaoversus.com.br/mcp/pilot/`.
- Discovery do recurso: `/.well-known/oauth-protected-resource/mcp/pilot`.
- Issuer: `https://id.gestaoversus.com.br/realms/app32`.
- Audience: `app32-mcp-resource`.
- Scopes: `mcp:access`, `mcp:user`; adicionar `mcp:analytics` e/ou
  `mcp:finance` somente quando o caso de uso e o RBAC APP32 exigirem.
- Catálogo remoto `user`: `list_user_app32_capabilities`,
  `get_company_profile`, `list_meetings`, `list_projects` e
  `list_project_tasks_secure`.

Esses parâmetros não concedem acesso sozinhos. O `company_id` requerido pela
tool é revalidado contra o grant do principal a cada chamada.

As permissões APP32 do usuário são resolvidas no runtime. Quando existir,
`PrincipalCompanyGrant.mcp_permissions` atua somente como teto: lista vazia não
eleva nada; lista preenchida reduz por interseção. Esse mecanismo não promove
tools financeiras para `user` e não substitui o contrato de uma surface
privilegiada.

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

O nome exibido e usado pelo Codex é `mcp-versus`, configurável por
`APP32_MCP_OAUTH_CODEX_SERVER_NAME`. Ele identifica apenas a conexão local do
CLI; não substitui o client OAuth `app32-mcp-pilot` e não altera grants,
`company_id`, scopes ou permissões.

## Coorte ChatGPT do plugin público

A coorte ChatGPT segue o mesmo fluxo USER deste playbook, com diferenças
operacionais explícitas:

1. A Engenharia registra o MCP em modo de gestão do ChatGPT e obtém o redirect
   URI e o modo de registro exatos antes de configurar o client no Keycloak.
2. O client é de plataforma, nunca de empresa. A autorização de empresa ocorre
   somente por `PrincipalCompanyGrant` após o login humano.
3. A configuração inicial usa apenas `/mcp/pilot/user/`, `mcp:access` e
   `mcp:user`; nenhuma surface `admin`, `analytics`, `ops` ou domínio financeiro
   sensível entra no catálogo comercial inicial.
4. O cliente instala/conecta o plugin e faz OAuth com sua conta Gestão Versus.
   Sem vínculo/grant ativo, a resposta é neutra e não revela empresas, contratos
   ou dados de negócio.
5. O primeiro uso móvel e web é homologado em conta ChatGPT Go brasileira antes
   de qualquer promessa comercial de plano mínimo.

O marketplace pessoal só pode ser usado para dogfood e homologação. Ele não
substitui a distribuição pública nem autoriza convite de clientes externos.

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

## Complemento: coorte financeira analytics

Para consulta financeira aprovada, a coorte usa
`https://app.gestaoversus.com.br/mcp/pilot/analytics/`. Ela requer
`mcp:access`, `mcp:analytics`, grant explícito e `financial.read` no APP32. O
catálogo é somente leitura; não usar esta coorte para criar, editar, importar,
liquidar ou excluir dados financeiros. Não instruir usuários a criar aliases
como `mcp-versus-analytics`: `mcp-versus` é o nome público canônico.


### Correção de discovery unificada — AA.J.21.332 (2026-09-18)

- No endpoint `/mcp/pilot/`, `list_user_app32_capabilities` mantém o nome por compatibilidade, mas descreve as ferramentas publicadas pelo conector unificado, incluindo o filtro `domain=finance`. Nos endpoints segmentados seu significado permanece restrito à respectiva surface.
- `tools/list` e manifesto compartilham a seleção de ferramentas privilegiadas por scope OAuth e permissão específica da capability. `financial.view` não equivale a `financial.create`.
- O catálogo indica discovery, não autorização definitiva: cada execução revalida empresa/grant/RBAC e mutações com human gate exigem aprovação persistida. Scopes do manifesto são metadados do catálogo, não os claims do token.
- Critério de regressão: igualdade entre tools expostas e manifesto (exceto a própria tool de capabilities), filtro financeiro com leitura versus criação, token sem scope, teto de grant e isolamento tenant.
- Não declarar paridade integral com todas as funções do APP32: a publicação remota continua limitada à coorte revisada. Homologação real da sessão cliente permanece obrigatória; testes simulados não a substituem.
