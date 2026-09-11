# Harness — validação de onboarding OAuth MCP por coorte

**Classe documental:** Harness
**Status:** operacional para coorte controlada
**Escopo:** validação repetível de uma conexão USER OAuth antes de liberar uso.

## Entradas mínimas

- identificador da coorte e client OAuth aprovados;
- usuário Keycloak vinculado a `IdentityPrincipal` ativo;
- um `PrincipalCompanyGrant` ativo para a empresa de teste;
- uma empresa distinta sem grant para o mesmo principal;
- runtime MCP com suporte a Authorization Code + PKCE S256.

## Sequência

1. Confirmar discovery do recurso e `401` sem Bearer no endpoint MCP.
2. Conectar o runtime na URL da coorte e concluir login OAuth; não registrar
   senha, token, code ou refresh token.
3. Executar `tools/list`; comparar o catálogo com a allowlist da coorte.
4. Executar uma única leitura autorizada com a empresa concedida e registrar
   somente sucesso/erro, sem reproduzir conteúdo empresarial.
5. Executar a mesma classe de leitura com empresa sem grant; exigir negação e
   confirmar ausência de dados de negócio.
6. Revogar o grant em ambiente de ensaio ou usar grant já revogado; exigir
   bloqueio fail-closed. Em produção, esse passo só ocorre mediante incidente
   ou janela aprovada.

## Saída e gates

| Evidência | Aceite |
|---|---|
| Sem token | `401` e metadata OAuth utilizável |
| Login PKCE | cliente autenticado sem segredo compartilhado |
| Catálogo | somente tools previstas para a surface/coorte |
| Empresa concedida | leitura autorizada |
| Empresa sem grant | negação sem vazamento |
| Revogação | bloqueio prevalece sobre token ainda válido |

Falha em qualquer linha bloqueia o onboarding. O resultado deve ser anexado ao
card da coorte, sem dados de negócio, tokens ou URLs de callback com parâmetros
sensíveis.
