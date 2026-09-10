# Runbook — Keycloak local com PostgreSQL, sem Docker

**Classe documental:** Runbook
**Status:** preparação local; não autoriza deploy nem OAuth público
**Escopo:** homologação isolada do IdP para APP32/MCP

## Objetivo

Validar Keycloak localmente antes da homologação remota, sem acoplar seu
runtime, banco ou segredos ao APP32. O APP32 continua dono de `company_id`,
grants, RBAC, capabilities e gates humanos.

## Limites obrigatórios

- Usar PostgreSQL dedicado `keycloak_local_hml`; nunca o banco do APP32.
- Não usar `dev-file`, H2, SQLite ou dados de produção.
- Manter `APP32_MCP_HTTP_ENABLE_OAUTH` desligado fora da coorte local. Para
  smoke R05 autorizado, habilitar temporariamente **somente** a surface de
  teste junto de `APP32_MCP_OIDC_ENABLED_SURFACES` e
  `APP32_MCP_USE_PRINCIPAL_GRANTS=1`; ausência de qualquer uma dessas flags
  não pode ativar OAuth parcialmente.
- Não registrar senha de banco, admin bootstrap, client secret, token ou chave
  privada no Git, terminal compartilhado ou logs.
- Keycloak local expõe somente HTTPS em `localhost:8443`; a interface de
  management fica em loopback. Não publicar portas na rede.
- Não usar HTTP como atalho: o verifier APP32 exige issuer e JWKS HTTPS.

## Artefatos versionados

- `deploy/keycloak/keycloak-local.env.template`
- `deploy/keycloak/keycloak.service.template` (referência futura Linux)

Runtime e segredos locais ficam fora do repositório, por exemplo:

```text
C:\GestaoVersus\services\keycloak\
C:\GestaoVersus\secrets\keycloak-local.env
```

## Pré-requisitos locais

1. PostgreSQL disponível localmente e uma distribuição Keycloak compatível com
   a versão Java exigida pela release escolhida.
2. Distribuição descompactada em diretório externo ao Git.
3. Criar, com administrador PostgreSQL local, banco e role dedicados:

```sql
CREATE ROLE keycloak_local_hml LOGIN PASSWORD '<definir-fora-do-git>';
CREATE DATABASE keycloak_local_hml OWNER keycloak_local_hml;
```

4. Copiar `keycloak-local.env.template` para arquivo externo e preencher
   valores reais. Não usar placeholders como credenciais.

## Subida local controlada

1. Carregar as variáveis do arquivo externo apenas no processo local.
2. Confirmar `KC_DB=postgres` e URL apontando para `keycloak_local_hml`.
3. Gerar fora do Git um PKCS12 com SAN `localhost` e `127.0.0.1`; referenciá-lo
   no arquivo externo por `KC_HTTPS_KEY_STORE_FILE` e
   `KCRAW_HTTPS_KEY_STORE_PASSWORD`. Manter também `KC_HTTP_HOST=127.0.0.1`:
   mesmo com HTTP desabilitado, ele limita o listener HTTPS ao loopback.
4. No diretório da distribuição Keycloak, executar em PowerShell:

```powershell
& .\bin\kc.bat build --db=postgres
& .\bin\kc.bat start --optimized
```

5. Verificar console/issuer em `https://localhost:8443` e health no management
   loopback, usando a cadeia local de confiança; nunca usar `--insecure` no
   ensaio do verifier. Se `8443` já estiver ocupada, escolher outra porta livre
   local e alterar conjuntamente `KC_HTTPS_PORT`, `KC_HOSTNAME`, issuer, JWKS
   e audience/profile do APP32.
6. Importar o template versionado de realm. A credencial do client SERVICE de
   smoke é gerada pelo Keycloak e fica somente no arquivo externo; não importar
   usuários ou roles empresariais do APP32.

## Validação antes do wiring APP32

1. Obter do realm somente metadados públicos: issuer, audience, JWKS URL,
   algorithms e client IDs aprovados.
2. Preencher `APP32_MCP_OIDC_*` apenas no ambiente local isolado. Quando o
   certificado local for autoassinado, fornecer `APP32_MCP_OIDC_CA_BUNDLE` com
   seu certificado público; o verifier mantém validação TLS normal e não aceita
   bypass de certificado.
3. Executar os testes do verifier e confirmar rejeição para issuer, audience,
   client, scope, assinatura e `kid` inválidos.
4. No clone descartável do APP32 já reconciliado, provisionar um principal e
   grant temporários com `issuer/sub` exatos; nunca usar usuário, empresa ou
   credencial de produção.
5. Subir o MCP HTTP em loopback e validar 401/403, `WWW-Authenticate`,
   protected-resource metadata, scope da surface e negativa cross-tenant.
   Desligar o processo e remover/reverter os dados de smoke após a evidência.
6. Para o gate de concorrência R05, usar duas identidades técnicas distintas,
   grants de empresas diferentes e requests simultâneos; registrar somente o
   resultado allow/deny e a confirmação de limpeza. O segundo client e sua
   inclusão temporária na allowlist existem apenas durante o processo local.
7. Para USER PKCE sob Keycloak 26, o scope `mcp-resource` deve conter
   `oidc-sub-mapper` com `access.token.claim=true` e
   `lightweight.claim=true`. O APP32 exige `sub` no access token para vínculo
   exato; não substituir isso por e-mail, username ou claim de sessão.

## Promoção posterior

Produção exige serviço próprio, PostgreSQL próprio, hostname HTTPS fixo,
proxy configurado, backup/restore testado e segredo externo. A unidade
`keycloak.service.template` é referência; não executar sem revisão de
infraestrutura e autorização explícita.
