# SPEC — Contrato Técnico da Análise Assistida Consultiva via MCP

**Classe documental:** SPEC  
**Status:** Contrato técnico v1 implementado localmente, pendente deploy  
**Data:** 2026-07-01  
**Origem:** `app32/docs/spec/camada_analise_assistida_mcp_tenant_owned_v1.md`  
**Escopo:** Persistência, APIs, MCP tools e UI das frentes consultivas do Cockpit do Consultor

---

## 1. Decisão

A persistência da análise assistida deve registrar o que volta da IA/CLI conectada ao MCP, sem transformar o APP32 em executor direto da IA.

O fluxo oficial é:

1. IA/CLI do cliente consulta o APP32 via MCP.
2. IA/CLI devolve diagnóstico/recomendação ao usuário.
3. Usuário registra a análise recebida no APP32.
4. Squads validam.
5. Consultor registra decisão.
6. Somente depois a recomendação pode virar projeto, atividade, maturação, revisão de processo ou Business Review.

---

## 2. Entidades conceituais

### 2.1. AssistedAnalysis

Registro da análise recebida da IA/CLI.

Campos mínimos:

- `id`
- `company_id`
- `front_key`
- `ai_origin`
- `responsible`
- `created_by_user_id`
- `updated_by_user_id`
- `diagnosis`
- `benchmarks`
- `risks`
- `recommendations`
- `status`
- `source_payload_json`
- `protocol_id`
- `protocol_version`
- `protocol_source`
- `protocol_title`
- `protocol_snapshot_json`
- `created_at`
- `updated_at`

Status sugeridos:

- `received`
- `under_review`
- `validated`
- `rejected`
- `converted`
- `archived`

### 2.2. AssistedAnalysisValidation

Registro de validação por squad.

Campos mínimos:

- `id`
- `company_id`
- `analysis_id`
- `squad` (`client`, `versus`, `engineering`)
- `status` (`pending`, `validated`, `needs_adjustment`, `rejected`)
- `notes`
- `validated_by_user_id`
- `created_at`
- `updated_at`

### 2.3. AssistedAnalysisDecision

Gate humano do consultor.

Campos mínimos:

- `id`
- `company_id`
- `analysis_id`
- `decision` (`accept`, `adjust`, `reject`, `hold`)
- `conversion_target` (`none`, `project`, `process`, `indicator`, `routine`, `business_review`, `urgent_need`, `structural_learning`)
- `decision_reason`
- `next_action`
- `governance_notes`
- `decided_by_user_id`
- `created_at`
- `updated_at`

---

## 3. MCP tools — leitura

### 3.1. `consultive_get_front_context`

Entrada:

```json
{
  "company_id": 123,
  "front_key": "processes"
}
```

Saída mínima:

```json
{
  "company_id": 123,
  "front_key": "processes",
  "front_title": "Processos",
  "maturity": { "score": 47, "status": "partial" },
  "subphases": [],
  "summary": "..."
}
```

### 3.2. `consultive_get_front_evidence`

Entrada: `company_id`, `front_key`.

Saída: evidências internas com origem, data e objeto canônico relacionado.

### 3.3. `consultive_get_front_gaps`

Entrada: `company_id`, `front_key`.

Saída: gaps metodológicos e técnicos já conhecidos.

### 3.4. `consultive_get_methodology_guidance`

Entrada: `front_key`, `subphase_key` opcional.

Saída: orientação da Metodologia Versus para frente/subfase.

---

## 4. MCP tools — registro

### 4.1. `consultive_register_assisted_analysis`

Entrada mínima:

```json
{
  "company_id": 123,
  "front_key": "processes",
  "payload": {
    "ai_origin": "Claude Desktop",
    "responsible": "Consultor Versus",
    "diagnosis": "...",
    "benchmarks": "...",
    "risks": "...",
    "recommendations": "...",
    "analysis_status": "received",
    "source_payload": {}
  }
}
```

Regras:

- exige `company_id`;
- exige usuário autenticado/autorizado;
- não cria ação operacional;
- status inicial: `received`.
- registra o protocolo ativo usado na análise;
- quando o protocolo for fallback, `protocol_id` fica nulo, mas `protocol_snapshot_json`, `protocol_version`, `protocol_source` e `protocol_title` permanecem preenchidos.

### 4.1.1. `consultive_list_assisted_analyses`

Entrada mínima:

```json
{
  "company_id": 123,
  "front_key": "processes",
  "status": "received",
  "limit": 20
}
```

Saída:

- análises assistidas do tenant;
- protocolo/versionamento usado no momento da análise;
- validações de Squad Cliente, Squad Versus e Squad Engenharia;
- última decisão humana do consultor, quando existir.

### 4.2. `consultive_register_squad_validation`

Entrada mínima:

```json
{
  "company_id": 123,
  "analysis_id": 456,
  "squad": "versus",
  "status": "validated",
  "notes": "..."
}
```

Regras:

- validação deve respeitar escopo do squad;
- Squad Cliente não aprova método sozinho;
- Squad Versus não deve ignorar restrição operacional validada pelo cliente.

### 4.3. `consultive_register_consultant_decision`

Entrada mínima:

```json
{
  "company_id": 123,
  "analysis_id": 456,
  "payload": {
    "consultant_decision": "adjust",
    "conversion_target": "project",
    "decision_reason": "...",
    "next_action": "...",
    "governance_notes": "..."
  }
}
```

Regras:

- decisão final exige consultor ou responsável autorizado;
- não converte automaticamente sem tool específica;
- deve gerar trilha auditável.

---

## 5. MCP tool — conversão em ação

### 5.1. `consultive_create_recommended_action`

Entrada mínima:

```json
{
  "company_id": 123,
  "analysis_id": 456,
  "decision_id": 789,
  "target_type": "project_task",
  "payload": {}
}
```

Regras:

- só pode rodar após decisão aprovada;
- deve respeitar permissões do objeto alvo;
- deve criar vínculo entre análise, decisão e objeto gerado;
- mutações críticas devem ter human gate.

---

## 6. Superfície APP32

### 6.1. Modal “Registrar análise recebida”

Função:

- receber o resultado trazido pela IA/CLI;
- registrar síntese, fontes, riscos, recomendações e validações iniciais;
- não executar ação operacional.

### 6.2. Modal “Registrar decisão do consultor”

Função:

- registrar aprovação, ajuste, nova análise ou rejeição;
- indicar destino possível da recomendação;
- preparar conversão posterior em ação.

---

## 7. Critérios de aceite técnico

1. Toda operação tem `company_id` obrigatório.
2. Registro de análise não cria objeto operacional automaticamente.
3. Validação por squad é separada da decisão do consultor.
4. Conversão em ação é tool própria e posterior.
5. UI deixa claro que APP32 não dispara IA.
6. MCP limita contexto por surface/permissão.
7. Dados externos são fontes consultivas, não verdade operacional.
8. Decisão final é humana.

---

## 8. Fora de escopo desta versão

- escolha de provedor de IA;
- cobrança ou medição de tokens;
- OAuth externo para provedores de IA;
- automação de conversão sem gate humano;
- deploy/ativação em produção.

---

## 9. Artefatos implementados localmente

- Modelos: `consultive_assisted_analyses`, `consultive_assisted_analysis_validations`, `consultive_assisted_analysis_decisions`.
- Migration: `20260701_1015_create_consultive_assisted_analysis.py`.
- Service: `ConsultiveAssistedAnalysisService`.
- API APP32:
  - `GET/POST /api/consultive/cockpit/fronts/<front_key>/assisted-analyses`;
  - `POST /api/consultive/cockpit/assisted-analyses/<analysis_id>/validations`;
  - `POST /api/consultive/cockpit/assisted-analyses/<analysis_id>/decision`.
- MCP:
  - `consultive_get_front_context`;
  - `consultive_get_front_evidence`;
  - `consultive_get_front_gaps`;
  - `consultive_get_methodology_guidance`;
  - `consultive_register_assisted_analysis`;
  - `consultive_register_squad_validation`;
  - `consultive_register_consultant_decision`;
  - `consultive_create_recommended_action`.

---

## 10. Protocolos Consultivos Evolutivos

As instruções que conduzem Squad Cliente, Squad Versus, Consultor e IA/CLI não devem ficar presas ao template ou ao código.

Decisão oficial:

- instruções consultivas são objetos versionados em `consultive_protocols`;
- cada protocolo pode ser global ou override por `company_id`;
- cada protocolo é resolvido por `front_key`, `subphase_key`, `audience` e `depth_level`;
- o APP32 expõe o protocolo ativo via API e MCP;
- a IA/CLI do cliente deve chamar `consultive_resolve_protocol` antes de conduzir perguntas, pesquisa profunda, benchmark ou simulação;
- o protocolo pode evoluir de pergunta básica para investigação profunda sem alteração de código.

Campos canônicos:

- `company_id` opcional para diferenciar protocolo global de protocolo tenant-owned;
- `front_key`;
- `subphase_key`;
- `audience`: `ai_cli`, `client_squad`, `versus_squad`, `consultant`;
- `depth_level`: `basic`, `internal_diagnosis`, `deep_research`, `simulation`;
- `status`: `draft`, `active`, `archived`;
- `protocol_version`;
- `title`;
- `objective`;
- `prompt_markdown`;
- `protocol_json`.

Exemplo: evolução da missão organizacional

- Versão básica: perguntar ao gestor o que a empresa faz, para quem e qual valor entrega.
- Versão diagnóstico interno: cruzar missão com MVV, processos, indicadores e projetos.
- Versão pesquisa profunda: pesquisar empresas similares, mercado consumidor e referências globais.
- Versão simulação: testar aderência entre missão proposta, processos, capacidade de entrega e percepção de mercado.

MCP tools:

- `consultive_resolve_protocol`: resolve o protocolo ativo para a IA/CLI;
- `consultive_upsert_protocol`: cria ou atualiza protocolo tenant-owned com gate de escrita.

Critério de aceite:

- o roteiro exibido no Cockpit deve usar o protocolo ativo sempre que disponível;
- o fallback em código é permitido somente como segurança operacional;
- evolução metodológica deve ocorrer preferencialmente por protocolo versionado, não por alteração de template.

### 10.2 Rastreabilidade Protocolo → Análise

Cada análise recebida deve guardar uma fotografia do protocolo usado no momento do trabalho.

Decisão oficial:

- `consultive_assisted_analyses.protocol_snapshot_json` guarda o protocolo resolvido pela IA/CLI ou pelo APP32;
- `protocol_id` aponta para `consultive_protocols.id` quando o protocolo está persistido;
- `protocol_version`, `protocol_source` e `protocol_title` ficam redundantes por legibilidade e auditoria;
- histórico antigo não deve ser reescrito quando o protocolo evoluir;
- o consultor precisa enxergar na UI qual roteiro orientou aquela análise antes de decidir.

Justificativa:

- protocolos são evolutivos;
- uma análise feita com `fallback-v1` não pode parecer equivalente a uma análise feita com protocolo tenant-owned mais maduro;
- o Squad Versus e o Squad Cliente precisam auditar a qualidade da condução depois.

### 10.1 Protocolos-base obrigatórios do Cockpit

Todas as partes do Cockpit devem ter protocolo-base resolvível mesmo antes de existir override persistido no banco.

Frentes e subfases cobertas:

- Identidade Organizacional: `mission`, `vision`, `values`, `positioning`, `org_chart`;
- Processos: `architecture`, `modeling`, `implantation`, `stabilization`, `audit`;
- Planejamento Estratégico: `structured`, `connected`, `deployed`, `linked_to_management`;
- Gerenciamento Estratégico: `indicators`, `cycles`, `incentives`, `connection_web`.

Regra oficial:

- toda subfase deve retornar um protocolo ativo via `consultive_resolve_protocol`;
- quando não houver protocolo tenant-owned/global persistido, o service deve retornar fallback canônico `fallback-v1`;
- o fallback é segurança operacional, não substitui a evolução versionada;
- o protocolo pode ser aprofundado por `depth_level` sem alteração de template.
