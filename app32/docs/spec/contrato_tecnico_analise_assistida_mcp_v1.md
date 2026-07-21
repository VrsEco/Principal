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
- `conversion_requested`
- `converted`
- `archived`

Regra oficial: `conversion_requested` significa que o consultor aprovou/ajustou a recomendação e solicitou intenção de ação para um objeto operacional. `converted` só deve ser usado quando a criação/vinculação do objeto operacional tiver ocorrido por ferramenta específica e com rastreabilidade.

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

Validação humana do consultor.

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

## 5. MCP tool — ação operacional

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

- só pode rodar após decisão aprovada ou ajustada;
- deve respeitar permissões do objeto alvo;
- deve criar vínculo entre análise, decisão e objeto gerado;
- mutações críticas devem ter human gate.

Na versão segura inicial, esta tool pode registrar apenas a intenção de ação e manter a análise em `conversion_requested`. A efetiva criação do projeto, processo, Business Review ou outro objeto canônico deve ser realizada por tool operacional específica, preservando validação humana e vínculo auditável.

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
- preparar a ação operacional posterior sem executá-la automaticamente.

---

## 7. Critérios de aceite técnico

1. Toda operação tem `company_id` obrigatório.
2. Registro de análise não cria objeto operacional automaticamente.
3. Validação por squad é separada da decisão do consultor.
4. Ação operacional é tool própria e posterior.
5. UI deixa claro que APP32 não dispara IA.
6. MCP limita contexto por surface/permissão.
7. Dados externos são fontes consultivas, não verdade operacional.
8. Decisão final é humana.

---

## 8. Fora de escopo desta versão

- escolha de provedor de IA;
- cobrança ou medição de tokens;
- OAuth externo para provedores de IA;
- automação de ação operacional sem validação humana;
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

---

## 11. Motor de Condução da Maturidade Assistida

### 11.1 Tool oficial

`consultive_get_next_action(company_id, front_key, subphase_key=None)` é uma tool de leitura da surface `user`, domínio `consultive`, permissionada por `consultive.read` e obrigatoriamente tenant-safe.

Ela não executa mutação e retorna:

```json
{
  "company_id": 9,
  "front_key": "identity",
  "subphase_key": "mission",
  "protocol": {"version": "fallback-v1", "source": "fallback"},
  "journey_state": "collecting_evidence",
  "current_state": {
    "coverage": {
      "score": 100,
      "metric_type": "registration_coverage",
      "does_not_prove_methodological_maturity": true
    },
    "methodological_maturity": {
      "status": "in_development",
      "is_mature": false,
      "score": null,
      "score_policy": "not_derived_from_registration_coverage",
      "open_reasons": ["assisted_analysis_missing"]
    },
    "latest_analysis_id": null,
    "validations": {},
    "consultant_decision": null
  },
  "next_action": {
    "key": "develop_mission_diagnosis",
    "label": "Diagnosticar e amadurecer a Missão",
    "responsible": "Squad Cliente / gestor / CLI do cliente",
    "objective": "...",
    "required_inputs": [],
    "allowed_tools": [],
    "completion_criteria": [],
    "human_gate_required": true,
    "write_policy": {
      "write_tools": ["consultive_register_assisted_analysis"],
      "requires_explicit_human_confirmation": true,
      "canonical_write_allowed": false
    }
  },
  "orchestration": {
    "may_execute": [],
    "must_not_execute": [],
    "handoff_to": "Squad Cliente",
    "blocked": false
  }
}
```

### 11.2 Máquina de estados do piloto Missão

1. `collecting_evidence`: não há análise assistida aplicável; Squad Cliente/gestor/CLI coleta contexto, entrevista, pesquisa e produz diagnóstico. Após apresentar o conteúdo e receber confirmação humana explícita, o CLI pode usar `consultive_register_assisted_analysis` para registrar a transição.
2. `awaiting_client_validation`: a análise existe e aguarda confirmação do conteúdo humano pelo Squad Cliente.
3. `awaiting_versus_validation`: conteúdo confirmado aguarda validação metodológica do Squad Versus.
4. `awaiting_engineering_validation`: usado quando há gap técnico, de dados, MCP, read model ou rastreabilidade.
5. `awaiting_consultant_decision`: validações necessárias concluídas; consultor decide aceitar, ajustar, manter ou rejeitar.
6. `approved_for_execution`: decisão aceita; somente executor autorizado pode persistir o conteúdo aprovado.
7. `executed_verified`: escrita autorizada foi relida e verificada.
8. `blocked`: rejeição, ajuste, capability ausente ou evidência insuficiente impede avanço.

### 11.3 Regras de decisão

- protocolo tenant-owned ativo prevalece sobre fallback global;
- a análise considerada deve pertencer ao mesmo `company_id`, `front_key` e subfase do protocolo quando identificável;
- validação `rejected` ou `needs_adjustment` interrompe o avanço e devolve ação de revisão;
- Engenharia é obrigatória somente quando houver gap técnico bloqueante (`high` ou `critical`);
- nenhuma validação pode ser registrada em nome de outro Squad;
- decisão e persistência canônica continuam human-gated;
- a tool nunca declara execução ou maturidade concluída sem releitura equivalente.
- `current_state.coverage` mede presença e preenchimento; não prova maturidade;
- `current_state.methodological_maturity.score` permanece `null`: não se deriva percentual metodológico da cobertura cadastral;
- toda tool de escrita publicada em `allowed_tools` deve aparecer também em `write_policy.write_tools` e exigir confirmação humana explícita;
- `consultive_register_assisted_analysis` registra diagnóstico rastreável, mas não altera a Missão canônica;
- validações usam `consultive_register_squad_validation`, decisão usa `consultive_register_consultant_decision` e persistência canônica somente ocorre no estado autorizado.

### 11.3.1 Catálogo efetivo e autorização por ator

- tools/list pode publicar uma operação human-gated quando o ator poderá executá-la após confirmação explícita; a execução sem human_gate_confirmed=true continua negada;
- no runtime_profile=squad_cliente, consultive_register_assisted_analysis é classificada como review, não como mutação canônica;
- no mesmo runtime, consultive_register_squad_validation permite somente squad=client;
- consultive_register_consultant_decision permanece classificada como decisão consultiva e não pode ser publicada nem executada pelo Squad Cliente;
- o user_id de auditoria é resolvido pelo contexto MCP autenticado; valor divergente informado pelo cliente deve ser rejeitado;
- todas as operações continuam exigindo company_id tenant-safe e releitura equivalente após a escrita.


### 11.4 Critérios de aceite do piloto

1. `company_id` inexistente ou fora do tenant é recusado pelo contrato MCP;
2. Identidade sem análise retorna a ação de diagnóstico da Missão;
3. análise recebida avança sequencialmente pelas validações aplicáveis;
4. rejeição ou pedido de ajuste devolve estado bloqueado e ação de revisão;
5. decisão aceita devolve execução autorizada, sem executar escrita;
6. protocolo, perguntas, camadas de investigação e critérios de conclusão aparecem no retorno;
7. `consultive_get_next_action` permanece somente leitura; quando houver transição registrável, ela publica a tool de escrita separada e sua `write_policy`, sem executar a mutação automaticamente.
8. cobertura de 100% com gaps ou gates pendentes retorna maturidade metodológica não madura;
9. cada estado registrável publica a tool necessária para avançar e sua política de confirmação humana.

## 12. Classificação e elegibilidade da análise

### 12.1 Campos canônicos

`consultive_assisted_analyses` passa a registrar:

- `analysis_type`: `methodological` ou `technical_test`;
- `journey_eligible`: booleano calculado exclusivamente pelo service;
- `eligibility_reasons_json`: razões objetivas que permitem ou impedem o avanço.

A tool MCP expõe `analysis_type`, `subphase_key`, `human_evidence`, `internal_evidence` e `benchmark_not_applicable_reason` como argumentos explícitos do schema. `diagnosis`, `benchmarks`, `risks`, `recommendations` e os demais dados descritivos permanecem em `payload`. Argumentos explícitos prevalecem sobre duplicatas existentes no `payload`.

O APP32 não aceita que o cliente force `journey_eligible`; o service calcula a elegibilidade a partir da classificação e das evidências estruturadas.

### 12.2 Critério mínimo de Missão

Uma análise `methodological` de `identity/mission` é elegível somente quando contém:

1. `subphase_key=mission`;
2. `diagnosis` preenchido;
3. `human_evidence` preenchido;
4. `internal_evidence` preenchido;
5. `risks` preenchido;
6. `recommendations` preenchido;
7. `benchmarks` preenchido ou `benchmark_not_applicable_reason` justificado.

Análise `technical_test` é sempre `journey_eligible=false`. Análise metodológica incompleta também é persistida como inelegível para preservar auditoria, mas não avança a máquina de estados.

### 12.3 Regras da máquina de estados

- `_latest_applicable_analysis` considera somente análise da mesma empresa, frente e subfase com `journey_eligible=true`;
- `latest_received_analysis_id` expõe o registro mais recente, mesmo inelegível, sem confundi-lo com a análise metodológica ativa;
- validação de Squad, decisão do consultor e conversão operacional recusam análise inelegível;
- ausência de análise elegível mantém `collecting_evidence` e publica as razões de inelegibilidade;
- reclassificações corretivas preservam o registro original e sua autoria.

### 12.4 Correção auditável do piloto

O registro `id=7`, `company_id=9`, foi criado exclusivamente para testar o write-path MCP. Deve permanecer no histórico como `technical_test`, `journey_eligible=false`, sem validações ou decisão. A Missão da Versus retorna a `collecting_evidence` até existir análise metodológica elegível.
