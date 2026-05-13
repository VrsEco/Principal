# Sapiens MCP — MVP de Token por Usuário

**Data:** 2026-05-07  
**Status:** desenho funcional e técnico enxuto  
**Especialista líder:** @ARQUITETO  
**Apoios naturais:** @BACKEND_API, @BACKEND_SERVICE, @AI_ENGINEER, @QA_AUTOMATION

---

## 1. Objetivo

Permitir que o próprio usuário gere, renove e revogue seu acesso MCP remoto para clientes como Antigravity, usando:

- 1 token MCP por usuário;
- validade de 30 dias;
- notificação de expiração em D-3 e D0;
- configuração pronta para copiar.

---

## 2. UX recomendada

Local:

- `Meu Perfil > Segurança > Acesso MCP`

Blocos da tela:

1. **Status atual**
   - token ativo/inativo
   - expira em
   - último uso
   - último cliente

2. **Ações**
   - gerar token
   - renovar token
   - revogar token
   - copiar configuração

3. **Instruções para clientes**
   - URL do MCP
   - tipo de autenticação
   - bloco pronto para copiar

---

## 3. Modelo de dados mínimo

Tabela sugerida:

`user_mcp_tokens`

Campos:

- `id`
- `user_id`
- `token_hash`
- `token_prefix`
- `status` (`active`, `revoked`, `expired`)
- `created_at`
- `expires_at`
- `last_used_at`
- `revoked_at`
- `last_client_name`
- `last_surface`
- `last_company_id`
- `created_by_user_id`

Observações:

- guardar apenas hash;
- `token_prefix` serve para exibição mascarada;
- `expires_at` sempre = `created_at + 30 dias` no MVP.

---

## 4. Regras de negócio

### Geração

- invalida token ativo anterior do usuário, se a política for “um token por usuário”;
- gera novo segredo aleatório;
- grava hash;
- devolve token apenas uma vez.

### Renovação

- pode gerar novo token e revogar o anterior;
- renova mais 30 dias a partir da data da renovação;
- reaproveita o mesmo fluxo de exibição/cópia.

### Revogação

- marca `revoked_at`;
- status passa para `revoked`;
- o token deixa de autenticar imediatamente.

### Expiração

- se `expires_at < now`, o token não autentica;
- status lógico passa a `expired`.

---

## 5. Notificações obrigatórias

Disparos:

- **D-3**
- **D0**

Canais:

- e-mail
- WhatsApp

Template mínimo:

- assunto/título: `Seu token MCP expira em breve`
- corpo:
  - data de vencimento
  - impacto no cliente remoto
  - link para renovação no perfil

---

## 6. Endpoint/Service sugeridos

### Services

- `generate_user_mcp_token(user_id)`
- `renew_user_mcp_token(user_id)`
- `revoke_user_mcp_token(user_id)`
- `get_user_mcp_token_status(user_id)`
- `build_user_mcp_client_config(user_id)`

### Endpoints

- `POST /api/profile/mcp-token/generate`
- `POST /api/profile/mcp-token/renew`
- `POST /api/profile/mcp-token/revoke`
- `GET /api/profile/mcp-token/status`
- `GET /api/profile/mcp-token/client-config`

---

## 7. Configuração pronta para cópia

Formato humano:

```text
Nome: Sapiens User
URL: https://app.gestaoversus.com.br/mcp/user
Autenticação: Bearer Token
Token: <TOKEN_GERADO>
```

Formato estruturado:

```json
{
  "name": "Sapiens User",
  "url": "https://app.gestaoversus.com.br/mcp/user",
  "auth_type": "bearer",
  "token": "<TOKEN_GERADO>"
}
```

---

## 8. Critérios de aceite

1. o usuário gera o token no perfil;
2. o token expira em 30 dias;
3. o sistema envia aviso em D-3 e D0 por e-mail e WhatsApp;
4. o token pode ser revogado sem troca de senha;
5. o token respeita as permissões reais do usuário;
6. o sistema entrega bloco pronto para copiar no cliente remoto.
