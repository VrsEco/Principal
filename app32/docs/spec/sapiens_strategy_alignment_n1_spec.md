# SPEC — Sapiens Engenharia: Alinhamento Estratégico N1

Classe documental: **SPEC**
Status: **oficial — MVP técnico / ciclo conjunto com consultoria**
Data: **2026-05-31**
Piloto: **Save Water (`company_id = 1`)**

## 1. Decisão executiva

A plataforma passa a suportar a capacidade **Strategic Alignment N1** para cruzar:

- **Identidade Organizacional estruturada**;
- **Arquitetura de Processos**;
- **Rastreabilidade estratégica** entre processos, objetivos, pilares, proposta de valor, diferenciais, competências, políticas e indicadores.

Contrato canônico:

- `analysis_id`: `strategic_alignment_n1`
- `read_model`: `strategic.alignment_n1`
- Tool analítica canônica: `analyze_strategic_alignment_n1_tool`
- Alias de compatibilidade: `run_strategy_alignment_n1_analysis_tool`

## 2. Modelo de colaboração Claude × Engenharia

| Frente | Responsável | Decisão |
|---|---|---|
| Necessidade de negócio, benchmarks, perguntas ao cliente e validação consultiva | Cliente/Consultor via Claude | Claude pode seguir em paralelo. |
| Schema, segurança, multi-tenancy, MCP, performance, análise e QA | Squad Engenharia + CEO Consultoria | Engenharia decide viabilidade e implementação. |
| Pontos de trade-off | Ambos | Registrar em SPEC/backlog antes de expandir escopo. |

## 3. Parecer de viabilidade do MVP-N1

Viável com arquitetura **sidecar tenant-safe**, sem mutar imediatamente tabelas legadas críticas (`processes`, `indicators`, `okrs_*`) além de leitura/reuso.

### Por que sidecar no MVP

- evita migração disruptiva em entidades centrais já usadas por rotina, indicadores e OKRs;
- permite rastreabilidade C1–C5 por `company_id` com FKs compostas;
- preserva legados `companies.mvv_*` como fallback, mas cria identidade estruturada canônica;
- reduz risco de drift enquanto Claude valida o modelo consultivo real com cliente.

### O que fica para normalização v2

- `organization_values`, `strategic_pillars`, `organizational_policies`, `core_competencies` como tabelas normalizadas;
- `okrs_global.pillar_id` / `okrs_area.pillar_id`;
- `indicators.parent_indicator_id` e `indicators.strategic_objective_id`;
- CRUD MCP completo de indicadores, se a governança de indicadores confirmar o modelo.

## 4. Entidades oficiais do MVP

| Entidade | Tabela | Escopo tenant | Função |
|---|---|---|---|
| Identidade Organizacional | `organizational_identities` | `company_id` único | Guarda identidade estruturada A1–A14. |
| Perfil estratégico do processo | `process_strategy_profiles` | `company_id + process_id` | Complementa processo com B1–B10. |
| Vínculos de alinhamento | `process_strategic_alignment_links` | `company_id + process_id` | Ponte C1–C4 e parte de C2/C3. |
| Linha de visada de indicadores | `indicator_line_of_sight` | `company_id + indicadores` | Ponte C5. |
| Zona de maturação S1–S2 | `strategy_maturation_items` | `company_id` | Guarda hipóteses/drafts antes do human-gate S2→S3. |

## 5. Diagrama ER

```mermaid
erDiagram
    companies ||--o| organizational_identities : "company_id"
    companies ||--o{ strategy_maturation_items : "company_id"
    companies ||--o{ processes : "company_id"
    processes ||--o| process_strategy_profiles : "company_id + process_id"
    processes ||--o{ process_strategic_alignment_links : "company_id + process_id"
    indicators ||--o{ indicator_line_of_sight : "process_indicator_id"
    indicators ||--o{ indicator_line_of_sight : "corporate_indicator_id"

    organizational_identities {
        int id
        int company_id
        text mission
        text vision
        int vision_horizon_year
        text purpose
        jsonb values_json
        jsonb value_propositions_json
        jsonb pillars_json
        jsonb strategic_objectives_json
        jsonb policies_json
        jsonb swot_json
    }

    process_strategy_profiles {
        int id
        int company_id
        int process_id
        text objective
        string owner
        string customer_type
        string strategic_criticality
        string maturity_level
        jsonb indicators_json
        jsonb sipoc_json
        jsonb applicable_policies_json
    }

    process_strategic_alignment_links {
        int id
        int company_id
        int process_id
        string link_type
        string target_ref_type
        int target_ref_id
        string target_key
        numeric contribution_weight
    }

    indicator_line_of_sight {
        int id
        int company_id
        int process_indicator_id
        int corporate_indicator_id
        string relationship_type
        numeric contribution_weight
    }

    strategy_maturation_items {
        int id
        int company_id
        string block_type
        string status
        string source
        numeric confidence
        string state
        jsonb payload_json
        int confirmed_by_user_id
        datetime confirmed_at
    }
```

## 6. Segurança, tenancy e LGPD

- Todo acesso exige `company_id` explícito.
- FKs compostas protegem vínculo filho contra troca de tenant:
  - `process_strategy_profiles(company_id, process_id) → processes(company_id, id)`;
  - `process_strategic_alignment_links(company_id, process_id) → processes(company_id, id)`;
  - `indicator_line_of_sight(company_id, indicator_id) → indicators(company_id, id)`.
- Mutação estratégica tem `human_gate=True` nas capabilities.
- Drafts e inferências não confirmadas ficam isolados em `strategy_maturation_items`; readiness/análise só contam canônico `confirmed`.
- Surface analítica é somente leitura: `analytics`.
- Dados estratégicos são sensíveis de negócio: sem SQL livre, sem cross-tenant, sem exposição financeira sensível em surface `user`.

## 7. Performance e custo de query

Índices MVP:

- `organizational_identities(company_id)`;
- `process_strategy_profiles(company_id, process_id)`;
- `process_strategic_alignment_links(company_id, process_id)`;
- `process_strategic_alignment_links(company_id, link_type)`;
- `process_strategic_alignment_links(company_id, target_ref_type, target_ref_id, target_key)`;
- `indicator_line_of_sight(company_id, process_indicator_id)`;
- `indicator_line_of_sight(company_id, corporate_indicator_id)`.
- `strategy_maturation_items(company_id, status)`;
- `strategy_maturation_items(company_id, block_type)`;
- `strategy_maturation_items(company_id, target_ref_type, target_ref_id, target_key)`.

O read model N1 é adequado para piloto e empresas médias. Para empresas com milhares de processos/indicadores, evoluir para materialização/cache do `strategic.alignment_n1`.

## 8. Tools MCP oficiais

### Identidade

| Tool | Tipo | Entrada mínima | Observação |
|---|---|---|---|
| `get_organizational_identity_tool` | leitura | `company_id` | Canônica consultiva. |
| `upsert_organizational_identity_tool` | escrita | `company_id`, `payload`, `user_id?` | Atualiza identidade estruturada e sincroniza MVV legado quando aplicável. |
| `get_strategy_identity_tool` | leitura | `company_id` | Alias legado/engenharia. |
| `upsert_strategy_identity_tool` | escrita | `company_id`, `payload`, `user_id?` | Alias legado/engenharia. |

### Perfil estratégico do processo

| Tool | Tipo | Entrada mínima | Observação |
|---|---|---|---|
| `get_process_strategic_profile_tool` | leitura | `company_id`, `process_id` | Canônica consultiva. |
| `upsert_process_strategic_profile_tool` | escrita | `company_id`, `process_id`, `payload`, `user_id?` | Objetivo, dono, cliente, criticidade, maturidade, SIPOC e políticas. |
| `get_process_strategy_profile_tool` | leitura | `company_id`, `process_id` | Alias legado/engenharia. |
| `upsert_process_strategy_profile_tool` | escrita | `company_id`, `process_id`, `payload`, `user_id?` | Alias legado/engenharia. |

### Ponte C1–C4

| Tool | Tipo | Entrada mínima |
|---|---|---|
| `list_process_strategy_alignment_links_tool` | leitura | `company_id`, `process_id?` |
| `upsert_process_strategy_alignment_link_tool` | escrita | `company_id`, `payload`, `user_id?` |
| `delete_process_strategy_alignment_link_tool` | escrita | `company_id`, `link_id` |

`link_type` permitido:

- `strategic_objective`
- `strategic_pillar`
- `value_proposition`
- `differential`
- `essential_competence`
- `policy`

### Ponte C5

| Tool | Tipo | Entrada mínima |
|---|---|---|
| `list_indicator_line_of_sight_tool` | leitura | `company_id`, `process_id?` |
| `upsert_indicator_line_of_sight_tool` | escrita | `company_id`, `payload`, `user_id?` |
| `delete_indicator_line_of_sight_tool` | escrita | `company_id`, `link_id` |

### Readiness e análise

| Tool | Tipo | Entrada mínima | Contrato |
|---|---|---|---|
| `get_strategic_alignment_n1_readiness_tool` | análise/leitura | `company_id` | Canônica consultiva. |
| `analyze_strategic_alignment_n1_tool` | análise/leitura | `company_id` | Canônica consultiva. |
| `get_strategy_alignment_n1_readiness_tool` | análise/leitura | `company_id` | Alias de compatibilidade. |
| `run_strategy_alignment_n1_analysis_tool` | análise/leitura | `company_id` | Alias de compatibilidade. |

### Zona de maturação S1–S2

| Tool | Tipo | Entrada mínima | Observação |
|---|---|---|---|
| `list_strategy_maturation_backlog_tool` | leitura | `company_id`, filtros opcionais | Equivalente estratégico do pending queue financeiro. |
| `review_strategy_maturation_item_tool` | escrita/human-gate | `company_id`, `item_id`, `decision` | `decision`: `confirm`, `reject` ou `hold`. Confirm promove S2→S3. |

Exposição MCP:

- surface `user` para `list_strategy_maturation_backlog_tool`;
- surface `user` para `review_strategy_maturation_item_tool` com ação RBAC específica `review`, permissão declarativa `strategy.maturation.review`, `company_id` obrigatório e `human_gate=True`;
- perfil/harness cliente pode revisar maturação sem ganhar `update` estratégico genérico; `analytics` permanece leitura/análise e não executa review.

Metadados oficiais por item:

- `status`: `draft`, `pending`, `confirmed`, `rejected`;
- `source`: `consultor`, `cliente`, `ia_inferido`, `sistema`;
- `confidence`: 0–1;
- `state`: `as_is`, `to_be`, `target`, `aspirational`;
- `confirmed_by_user_id` / `confirmed_at`.

Regras:

- `upsert_*` com `status=draft|pending|rejected` persiste em `strategy_maturation_items` e **não** altera dado canônico.
- Em identidade organizacional, itens aninhados com `status=draft|pending|rejected` dentro de listas estruturadas (`values`, `strategic_objectives`, `policies` etc.) também são roteados individualmente para `strategy_maturation_items`; o sidecar canônico recebe somente itens `confirmed`/sem status e não limpa o array existente quando o payload traz apenas itens não confirmados.
- Ao confirmar um item individual de identidade com `identity_field`/`item_type` de campo array (`values`, `value_propositions`, `differentials`, `pillars`, `essential_competencies`, `segments_icp`, `policies`, `stakeholders`, etc.), o human-gate faz `append`/`replace` no array canônico correspondente por `target_key`, sem re-stage e sem contaminar outros campos.
- `upsert_*` sem status ou com `status=confirmed` grava no sidecar canônico.
- readiness/análise filtram itens estruturados por `status=confirmed`; itens sem status são tratados como legado confirmado.
- readiness expõe `maturation.by_status` e `maturation.by_block` com backlog aberto e maturidade por bloco.

### Jornada de Estruturação / Maturação Estratégica Sapiens

A Jornada de Estruturação é uma camada de read model sobre a maturação N1, sem rebuild do dado transacional.

Com a entrada da camada **Estrutura/Recursos**, do **Painel de Gestão Estratégica** e da tese da **Malha Analítica Estratégica via MCP/Sapiens**, a jornada deixa de medir apenas identidade e modelagem de processos. Ela passa a medir a maturidade da empresa para executar a estratégia com capacidade, custo, governança, evidências e análise econômica.

Hierarquia oficial v2:

- Jornada `sapiens_structuring`;
- Read model `sapiens.structuring_journey`;
- Versão `v2`;
- Blocos ordenados com gate soft:
  1. `identity`;
  2. `process_architecture`;
  3. `resources_capacity`;
  4. `modeling`;
  5. `strategic_management`;
- Sub-blocos paralelos com criticidade `essential`, `recommended` ou `optional`;
- Itens continuam sendo `strategy_maturation_items` quando estão em S1–S2.

Blocos oficiais:

| Ordem | Bloco | Objetivo | Essenciais |
|---:|---|---|---|
| 1 | `identity` | Estruturar o DNA estratégico da empresa. | Missão, visão, valores, proposta de valor e objetivos/pilares. |
| 2 | `process_architecture` | Organizar como a empresa funciona. | Áreas, macroprocessos, processos, dono e objetivo do processo. |
| 3 | `resources_capacity` | Evidenciar com quais recursos a empresa executa. | Catálogo de recursos e vínculo de recursos por processo. |
| 4 | `modeling` | Detalhar a rotina em movimento. | Fluxo e raias/executores. |
| 5 | `strategic_management` | Medir se a estratégia é executável e governável. | Rastreabilidade estratégica e linha de visada de indicadores. |

Tool MCP:

| Tool | Tipo | Entrada mínima | Observação |
|---|---|---|---|
| `get_structuring_journey_tool` | leitura/read model | `company_id` | Retorna Bloco→Sub-bloco com maturidade, gate, pendências e faltantes. |

Regras:

- gate é **SOFT**: cliente é guiado por fases; consultor navega livre;
- próximo bloco destrava quando todos os sub-blocos `essential` do bloco anterior estão prontos;
- sub-blocos `recommended` e `optional` contam maturidade, mas não bloqueiam gate;
- as duas UIs, cliente lúdico e consultor funcional, consomem o mesmo read model `sapiens.structuring_journey`;
- B3 Modelagem calcula rollup por processo e pode ser filtrado por `scope=process&process_id=<id>`.
- `resources_capacity` usa `resource_catalog` e `process_resource_links`, sempre com `company_id`;
- `strategic_management` usa vínculos C1–C5, indicadores, painel executivo e snapshots analíticos como evidência de gestão;
- benchmarking de capacidade permanece `optional` enquanto estiver no nível Paper; nenhuma recomendação externa pode virar decisão automática sem validação humana.

## 9. Saída mínima do read model

O payload retorna:

- `summary`;
- `completeness`;
- `risk_signals`;
- `gaps`;
- `crossings`;
- `recommended_actions`.

`completeness` deve retornar:

- `overall_pct`;
- `by_block.identity`;
- `by_block.process_profiles`;
- `by_block.traceability`;
- `by_block.indicators`;
- `gap_status_counts`.

Cada item em `gaps` deve carregar:

- `gap_type`;
- `gap_status`: `unmapped`, `confirmed_none` ou `misaligned`;
- `severity`;
- `reason`.

`risk_signals` deve conter sinais ponderados, por exemplo:

- `differential_low_maturity_process`;
- `high_criticality_process_without_objective`;
- `regulatory_exposure_without_policy_link`;
- `process_indicator_without_corporate_line_of_sight`.

`recommended_actions` deve ser lista de objetos priorizados, não frase única:

- `priority`;
- `gap_type`;
- `gap_status`;
- `severity`;
- `weight`;
- `action`;
- `target_label`;
- `target`.

Gaps mínimos:

- `objectives_without_process`;
- `processes_without_objective`;
- `processes_without_purpose`;
- `pillars_without_process`;
- `value_propositions_without_process`;
- `differentials_without_process`;
- `essential_competencies_without_process`;
- `policies_without_process`;
- `values_without_policy`;
- `process_indicators_without_corporate`.

## 10. Backlog técnico priorizado

| Prioridade | Item | Estimativa | Risco |
|---|---|---:|---|
| P0 | Aplicar migration e smoke MCP no ambiente alvo | P | Baixo |
| P0 | Publicar UI/API/MCP da zona de maturação S1–S2 | P | Baixo — padrão financeiro reaproveitado |
| P0 | Popular Save Water via tools canônicas | M | Médio — depende do cliente/consultor |
| P0 | Executar `analyze_strategic_alignment_n1_tool(company_id=1)` | P | Baixo |
| P1 | Enriquecer `list_process_hierarchy` com perfil estratégico opcional | M | Médio — impacto em contrato existente |
| P1 | CRUD MCP de indicadores/linhagem completa | G | Médio/alto — governança de indicadores |
| P1 | Normalizar identidade em tabelas próprias | G | Médio — migração de dados estruturados |
| P2 | Materializar/cache do read model | M | Baixo/médio — só necessário em escala |
| P2 | UI para mapa N1 | G | Médio — depende da validação do modelo consultivo |

## 11. Não recomendado no MVP

- Adicionar `processes.objective` agora: risco de acoplamento com telas/serviços legados; usar `process_strategy_profiles.objective`.
- Adicionar `indicators.parent_indicator_id` agora: pode conflitar com `indicator_tree` e com hierarquia corporativa existente; usar `indicator_line_of_sight`.
- Criar tabelas normalizadas para todos os itens de identidade antes da validação da Save Water: alto custo de retrabalho se o benchmark/cliente mudar a taxonomia.
- Publicar mutação estratégica na surface `analytics`: viola segregação de análise/leitura.

## 12. Próximo ciclo conjunto

Claude/consultoria pode seguir em paralelo com:

1. benchmark e perguntas de identidade Save Water;
2. preenchimento inicial de missão, visão, valores, pilares, objetivos, políticas e diferenciais;
3. sugestão de vínculos C1–C5.

Engenharia deve seguir com:

1. aplicar migration;
2. validar tools MCP no runtime real;
3. carregar dados piloto;
4. entregar o primeiro mapa `strategic_alignment_n1`.
