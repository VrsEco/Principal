# Sapiens MCP — Conexão Codex e Claude com tokens externos

## Objetivo
Disponibilizar o **Sapiens** como camada MCP operacional para clientes externos como **Codex** e **Claude**, mantendo a inferência e o consumo de tokens no cliente LLM e usando o APP32 apenas para:

- contexto operacional;
- validação de identidade;
- segregação por `company_id`;
- autorização;
- auditoria;
- execução segura de operações de negócio.

## Decisão arquitetural
Modelo canônico:

`Codex / Claude -> Sapiens MCP -> Services APP32 -> PostgreSQL`

### O que isso significa
- **Codex / Claude** continuam responsáveis pela conversa, raciocínio e consumo de tokens.
- **Sapiens MCP** não executa inferência de negócio por conta própria.
- **APP32** continua dono dos contratos, das validações e da persistência.

## Baseline validado em 2026-05-07
O ambiente de produção já possui a fundação remota do MCP:

- health remoto ativo em `https://app.gestaoversus.com.br/mcp/healthz`;
- surfaces publicadas:
  - `https://app.gestaoversus.com.br/mcp/user`
  - `https://app.gestaoversus.com.br/mcp/admin`
  - `https://app.gestaoversus.com.br/mcp/analytics`
- runtime HTTP remoto em `app32/src/core/mcp_http_server.py`;
- autenticação MVP por bearer token em `app32/src/core/mcp_http_auth.py`;
- fallback/stdio remoto por SSH para Codex/Claude Code em:
  - `app32/scripts/start_mcp_prod_ssh.ps1`
  - `app32/scripts/install_claude_mcp_app32_prod.ps1`

## Gap que esta entrega fecha
Faltava uma capacidade operacional clara para repetir, via MCP, a experiência de alteração de **Perfil de Persona** do módulo:

- Planejamento de Implantação
- seção `model`
- aba `Mapa de Persona & Jornada`

Esta entrega cria o recorte mínimo para uso frequente:

- consultar o conteúdo atual;
- simular a alteração;
- aplicar a alteração com segurança.

## Escopo funcional desta entrega
### Domínio
`plans.implantation.model.persona_profile`

### Operações
1. `describe_app32_implantation_persona_profile_tool`
2. `preview_app32_implantation_persona_profile_update_tool`
3. `apply_app32_implantation_persona_profile_update_tool`

## Regras obrigatórias
- `company_id` sempre obrigatório de forma explícita ou resolvido do contexto MCP autenticado;
- `plan_id` deve pertencer à empresa;
- o plano precisa estar em modo `implantation`;
- o segmento precisa existir de forma única;
- a persona precisa existir de forma única dentro do segmento;
- a escrita deve reutilizar `PlanService.save_implantation_data`;
- sem SQL bruto de mutação;
- sem lógica paralela fora de `services/`.

## Regra adicional obrigatória — consumo de processo da Gestão de Rotina
Quando existir um processo formalizado em **Gestão de Rotina** para o domínio/ação solicitada, o MCP não deve operar apenas por interpretação livre do prompt ou por heurística de tela.

Ele deve, antes da execução operacional:

- localizar o processo canônico aplicável;
- consumir a definição do processo e suas etapas;
- entender o objetivo de cada etapa;
- respeitar os campos, evidências, critérios e transições exigidos na instância;
- usar esse processo como contrato operacional da execução.

### Implicações práticas
- se houver processo definido, ele vira a principal referência de execução do MCP;
- a tool MCP deve preferir o processo vivo da rotina antes de derivar comportamento por texto livre;
- o conteúdo esperado em cada etapa da instância deve ser guiado pelo processo publicado, e não por suposição da LLM;
- isso reduz ambiguidade, melhora aderência operacional e preserva governança.

### Regra de precedência
1. processo canônico da **Gestão de Rotina**;
2. contratos MCP/REST publicados;
3. services de negócio;
4. inferência da LLM apenas para interpretação, nunca para redefinir o fluxo oficial.

### Consequência para próximas tools
Toda capability nova do Sapiens MCP que execute fluxo operacional multi-etapa deve avaliar explicitamente:

- existe processo oficial para esta operação?
- existe instância/processo-modelo que define entradas e saídas por etapa?
- a tool precisa consultar esse processo antes de montar preview, validação ou apply?

Se a resposta for sim, a integração com o processo deve fazer parte do contrato da tool.

## Contrato operacional
### Preview
Entrada:
- `company_id`
- `plan_id`
- `segment_name`
- `persona_name`
- `profile_text`

Saída:
- dados resolvidos do plano;
- trecho atual (`before`);
- trecho proposto (`after`);
- indicador `has_changes`.

### Apply
Entrada:
- `company_id`
- `plan_id`
- `segment_name`
- `persona_name`
- `profile_text`
- `dry_run` opcional

Saída:
- plano/empresa resolvidos;
- valor anterior;
- valor novo;
- status da persistência.

## Segurança e governança
### Surface recomendada
- **user** para operação normal de negócio;
- **admin** apenas para diagnóstico e suporte;
- **analytics** não deve mutar dados.

### Autorização
O comportamento deve espelhar a web:
- admin global: permitido;
- cliente / administrador com acesso total à empresa: permitido;
- colaborador sem acesso total a planos: negado.

## Estratégia de conexão por cliente
### Codex / Claude Code
Preferência atual:
- **stdio por SSH** contra produção

Motivo:
- não expõe token HTTP no cliente local;
- reaproveita a infraestrutura já existente do repositório;
- facilita testes de operação com `user_id` e `company_id` explícitos.

### Claude.ai
Preferência alvo:
- **MCP remoto HTTPS**

Pré-requisitos:
- endpoint público já publicado;
- bearer token ou OAuth;
- documentação objetiva da URL, surface e contexto exigido.

## Configuração canônica
### Repositório local / Codex
Manter entradas `.mcp.json` apontando para os launchers de produção por SSH.

### Claude Code
Manter instalador PowerShell dedicado para registrar as surfaces remotas.

### Claude.ai
Usar:
- URL pública do surface;
- bearer token da integração;
- `company_id` e `user_id` vinculados ao token ou injetados por política controlada.

## Critérios de aceite
Esta frente só pode ser considerada pronta quando:

1. o paper estiver atualizado;
2. a tool de persona estiver implementada;
3. existirem testes automatizados cobrindo:
   - sucesso;
   - plano inexistente;
   - segmento inexistente;
   - persona inexistente;
   - negação por tenant/contexto;
4. o deploy publicar a alteração sem quebrar o MCP remoto;
5. o smoke remoto validar:
   - `healthz`;
   - negação sem auth;
   - chamada autenticada de discovery;
   - preview/aplicação da tool nova.

## Roadmap curto pós-entrega
1. adicionar `bulk_update_implantation_persona_profiles`;
2. adicionar operações irmãs para `alignment`, `execution` e `finance`;
3. formalizar token registry por integração;
4. evoluir bearer MVP para OAuth quando o alvo principal for Claude.ai.

---

## MVP recomendado para cliente remoto — token MCP por usuário

Para acelerar a adoção em clientes remotos como Antigravity e conectores HTTP compatíveis, o MVP recomendado passa a ser:

- **1 token MCP por usuário do sistema**;
- permissões herdadas do próprio usuário;
- empresas acessíveis resolvidas pelo mesmo vínculo já usado no login web;
- seleção da empresa em runtime quando necessário;
- revogação do token separada da senha;
- expiração automática mensal.

### Regras deste MVP

1. o token **não** carrega permissão autônoma de negócio;
2. o token apenas autentica o usuário no conector MCP;
3. autorização continua vindo de:
   - vínculo do usuário com empresas;
   - permissões RBAC reais;
   - `company_id` ativo/resolvido na operação;
4. se o acesso do usuário for removido nas configurações normais do sistema, o MCP deve perder acesso junto;
5. o token MCP pode ser revogado independentemente do login/senha.

### Local recomendado da feature

`Meu Perfil > Segurança > Acesso MCP`

ou

`Meu Perfil > Integrações MCP`

### Ações esperadas na tela

- gerar token MCP;
- renovar token MCP;
- revogar token MCP;
- copiar configuração pronta para cliente remoto;
- visualizar:
  - status;
  - data de expiração;
  - último uso;
  - canal/cliente informado.

### Política de validade

Para este MVP, a validade definida é:

- **30 dias corridos**

Comportamento:

- o token nasce com `expires_at = created_at + 30 dias`;
- ao expirar, o servidor MCP responde negando autenticação;
- o usuário precisa renovar o token no perfil para continuar usando o cliente remoto.

### Política de aviso de expiração

O sistema deve notificar o usuário:

- **3 dias antes do vencimento**
- **no próprio dia do vencimento**

Canais obrigatórios:

- e-mail
- WhatsApp

Conteúdo mínimo da mensagem:

- nome da integração/token MCP;
- data de expiração;
- impacto esperado (“o cliente remoto deixará de acessar o Sapiens MCP”);
- CTA direto para renovar no perfil.

### Guardrails de implementação

- salvar apenas **hash** do token, nunca o token em texto puro;
- exibir o token completo apenas no momento da geração/renovação;
- depois disso, mostrar apenas versão mascarada;
- registrar:
  - `created_at`
  - `expires_at`
  - `last_used_at`
  - `revoked_at`
  - `last_client_name`
  - `last_surface`
- manter auditoria de uso por:
  - `user_id`
  - `company_id`
  - surface
  - tool
  - timestamp

### Configuração pronta para o cliente remoto

O sistema deve entregar ao usuário um bloco pronto para copiar, por exemplo:

```text
Nome: Sapiens User
URL: https://app.gestaoversus.com.br/mcp/user
Autenticação: Bearer Token
Token: <TOKEN_GERADO>
```

Quando o cliente suportar formato estruturado, o sistema pode entregar também:

```json
{
  "name": "Sapiens User",
  "url": "https://app.gestaoversus.com.br/mcp/user",
  "auth_type": "bearer",
  "token": "<TOKEN_GERADO>"
}
```

### Evolução posterior

Este MVP atende bem Antigravity e clientes MCP remotos que aceitem Bearer token.

Para Claude.ai como destino principal, o alvo arquitetural continua sendo:

- **OAuth**
