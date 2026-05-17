# Arquitetura do Instruction Registry do Squad Cliente v1

Status: oficial  
Escopo: contrato canônico do registry instrucional remoto do `Sapiens Cliente`

## 1. Objetivo

Definir oficialmente como o `Squad Cliente` deve carregar instruções remotas no bootstrap da sessão, com:

- bundle mínimo
- versionamento
- cache
- camadas composicionais
- segurança multi-tenant

## 2. Decisão oficial

O `Sapiens Cliente` passa a poder consumir um **instruction registry remoto** via MCP.

### 2.1 Tool de discovery
- `describe_app32_instruction_registry_tool`

### 2.2 Tool resolvedora
- `resolve_app32_instruction_bundle_tool`

## 3. Bundle mínimo oficial

O bundle mínimo oficial deve conter:

- `runtime_profile`
- `experience_label`
- `surface`
- `agent_key`
- `harness_key`
- `channel`
- `bundle_version`
- `company_id` quando disponível
- `summary`
- `introduction_message`
- `cache_ttl_seconds`
- `startup_sequence`
- `mandatory_rules`
- `handoff_rules`
- `forbidden_actions`
- `layer_matrix`
- `doc_refs`

### 3.1 O que o bundle não deve conter

- SPEC inteira
- Paper inteiro
- Runbook inteiro
- exemplos longos
- casuística inchada

## 4. Matriz oficial de camadas

| Precedência | Layer | Papel | Pode ter override remoto |
|---|---|---|---|
| 1 | global | governança transversal | não |
| 2 | runtime | regras do squad/profile/surface | sim |
| 3 | agent | especialização do agente/harness | sim |
| 4 | tenant_override | ajuste mínimo por cliente/canal | sim, com auditoria |

## 5. Modelo JSON de referência

```json
{
  "runtime_profile": "squad_cliente",
  "experience_label": "Sapiens Cliente",
  "surface": "user",
  "agent_key": "SC-COORD",
  "harness_key": "harness_coordenador_cliente_v1",
  "channel": "stable",
  "bundle_version": "2026-05-17.1",
  "company_id": 31,
  "summary": "Bundle mínimo do Squad Cliente com bootstrap remoto, versionado e cacheável.",
  "startup_sequence": [
    "resolve_app32_instruction_bundle_tool",
    "describe_app32_squad_runtime_tool",
    "list_user_app32_capabilities",
    "describe_app32_profile_contracts_tool",
    "describe_app32_surface_playbooks_tool"
  ]
}
```

## 6. Modelo YAML de referência

```yaml
runtime_profile: squad_cliente
experience_label: Sapiens Cliente
surface: user
agent_key: SC-COORD
harness_key: harness_coordenador_cliente_v1
channel: stable
bundle_version: 2026-05-17.1
company_id: 31
startup_sequence:
  - resolve_app32_instruction_bundle_tool
  - describe_app32_squad_runtime_tool
  - list_user_app32_capabilities
  - describe_app32_profile_contracts_tool
  - describe_app32_surface_playbooks_tool
```

## 7. Escalabilidade oficial

As instruções são oficialmente consideradas escaláveis quando:

- o bundle é curto
- a composição é por camadas
- docs completos ficam fora do bundle
- o override por tenant é pequeno
- a versão é explícita
- existe cache por `runtime + agent + harness + tenant + channel + version`

## 8. Ordem oficial de bootstrap

1. `resolve_app32_instruction_bundle_tool`
2. `describe_app32_squad_runtime_tool`
3. `list_user_app32_capabilities`
4. `describe_app32_profile_contracts_tool`
5. `describe_app32_surface_playbooks_tool`
6. `describe_app32_domain_playbooks_tool`

## 8.1 Regra adicional para `Sapiens On`

Quando o usuário acionar a entrada genérica `Sapiens On`, `/sapiens-on`, `Sapiens On` ou `sapiens on`, o sistema deve:

1. descobrir os squads disponíveis para aquele usuário
2. ativar diretamente se houver apenas um
3. perguntar ao usuário, quando houver múltiplos squads, exatamente:
   - `Escolha entre: Cliente, Versus ou Engenharia.`
4. após a escolha, confirmar a ativação com primeira linha curta:
   - `Sapiens Cliente Ativado`
   - `Sapiens Consultor Ativado`
   - `Sapiens Engenharia Ativado`
5. se o runtime suportar título de sessão, usar:
   - `Sapiens Cliente On`
   - `Sapiens Consultor On`
   - `Sapiens Engenharia On`

## 9. Guardrails

- `company_id` permanece obrigatório quando houver contexto tenant
- bundle não substitui contracts nem capabilities
- `tenant_override` não pode romper camada global
- surface `user` não pode ganhar poder de `admin`, `analytics` ou `ops`

## 10. Operação visual oficial no APP32

O console `API / MCP` passa a expor uma área canônica chamada `Instruction Registry`, com quatro blocos oficiais:

1. **Resumo executivo**
   - entries
   - ativas
   - overrides tenant
   - canais
   - runtimes
2. **Leitura AS-IS → TO-BE**
   - explicita o salto de bootstrap local para bundle remoto governado
3. **Administração remota**
   - cadastro mínimo de entry
   - edição explícita de entry existente
   - filtros por runtime/canal/status/rollout
   - promoção visual entre canais
   - mudança rápida de status
   - recarga do estado
   - invalidação controlada de cache
4. **Observabilidade curta**
   - entries publicadas
   - auditoria recente
   - mudanças recentes com diff resumido

Além disso, a promoção entre canais deixa de ser apenas convenção de UI e passa a ter ação semântica dedicada no backend.

Essa tela existe para evitar operação artesanal via banco ou prompt e para tornar o rollout remoto auditável.

## 11. Artefatos dependentes

- Manifesto
- Playbook
- Runbook
- Harness

Todos publicados nesta mesma iniciativa documental.
