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

### Jornada de Estruturação Sapiens

A Jornada de Estruturação é uma camada de read model sobre a maturação N1, sem rebuild do dado transacional.

Hierarquia oficial v1:

- Jornada `sapiens_structuring`;
- Blocos ordenados com gate soft: `identity`, `process_architecture`, `modeling`;
- Sub-blocos paralelos com criticidade `essential`, `recommended` ou `optional`;
- Itens continuam sendo `strategy_maturation_items` quando estão em S1–S2.

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
- para os gates objetivos de estabilidade das fases `01` e `02`, o APP32 reaproveita `IndicatorData` + `IndicatorGoal`:
  - default de estabilidade = `3` ciclos consecutivos;
  - override por indicador em `indicators.source_config.required_stable_cycles` (compatível também com `stable_cycles`/`gate_cycles`);
  - um ciclo conta como válido quando a medição fica `on_target`, `exceeded` ou `alert`, conforme `performance_ranges`/polaridade do indicador;
  - quando ainda não existir classificação explícita de processo finalístico no domínio, a fase `01` opera em fallback controlado usando todos os indicadores de processo e expõe esse modo na UI.

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

---

## 13. Realinhamento com o Cockpit do Consultor

Status em 2026-07-01:

A capacidade **Strategic Alignment N1** permanece válida como motor técnico e consultivo de alinhamento, maturação e human gate.

Entretanto, sua superfície principal deixa de ser uma entrada independente de menu para o usuário comum.

### 13.1 Decisão oficial

O **Cockpit do Consultor** passa a ser a superfície oficial de condução da Camada Consultiva/Evolutiva.

A Maturação N1 deve ser entendida como:

- motor de revisão S1–S2;
- fila de hipóteses, drafts e pendências;
- mecanismo de human gate;
- apoio à maturidade das frentes Identidade, Processos, Planejamento Estratégico e Gerenciamento Estratégico.

### 13.2 Jornada de Estruturação

A Jornada de Estruturação continua sendo um read model relevante, mas subordinado ao cockpit.

Ela deve alimentar, principalmente:

- maturidade por frente;
- pendências essenciais;
- gates;
- próximos itens a revisar;
- evidências de avanço.

### 13.3 Maturação N1 como detalhe

A tela atual de Maturação N1 pode permanecer como superfície técnica ou administrativa durante a transição.

O destino recomendado é que suas ações sejam acessadas a partir do Cockpit do Consultor, especialmente pelo botão **Abrir frente** ou por indicadores de pendência.

A linguagem exposta ao usuário comum deve evitar termos técnicos como:

- S1/S2;
- payload;
- draft/pending como conceitos primários;
- nomes internos de block_type.

Esses conceitos podem permanecer na camada técnica, nos serviços, MCP tools, logs e documentação de engenharia.

### 13.4 Compatibilidade

As tools MCP e APIs existentes continuam válidas para agentes, engenharia e integrações.

A mudança é de **surface e experiência de produto**, não de invalidação do motor N1.

### 13.5 Surface da Maturação N1

A rota `/strategy/alignment-n1/maturation` pode existir como **fila auxiliar de evidências**.

Regras de produto:

- deve apontar o **Cockpit do Consultor** como superfície oficial de condução;
- não deve aparecer como item primário de menu quando sua função for apenas auxiliar;
- deve evitar promessa de criação automática de frente, projeto ou dado canônico sem gate humano;
- deve tratar itens confirmados como evidência auxiliar do read model N1;
- não deve competir com os quatro cards oficiais de Estruturação Empresarial do Cockpit.

### 13.6 Jornada Cliente — Identidade Organizacional

A superfície cliente da antiga Jornada de Estruturação deve expor a Identidade Organizacional conforme o Paper/SPEC canônico da Metodologia Versus:

- Missão;
- Visão;
- Valores;
- Posicionamento;
- Organograma.

Campos técnicos do N1, como proposta de valor, diferenciais, ICP/segmentos, propósito, objetivos/pilares, competências, políticas, stakeholders e SWOT, podem continuar existindo no motor técnico/read model, mas não devem aparecer como checklist principal da Identidade Organizacional para o cliente.

Proposta de valor, diferenciais e ICP/segmentos podem ser usados como evidência auxiliar para **Posicionamento**.

Objetivos/pilares pertencem à evolução de Planejamento/Gerenciamento Estratégico, não ao checklist principal de Identidade Organizacional do cliente.

### 13.7 Jornada Cliente — frentes canônicas de Estruturação Empresarial

A antiga Jornada de Estruturação deve usar as mesmas quatro frentes oficiais do Cockpit do Consultor:

1. Identidade Organizacional;
2. Processos;
3. Planejamento Estratégico;
4. Gerenciamento Estratégico.

Os blocos legados `Arquitetura de Processos` e `Modelagem` deixam de ser fases autônomas da Jornada e passam a ser evidências internas da frente **Processos**.

A frente **Processos** deve expor as subfases:

- Arquitetura;
- Modelagem;
- Implantação;
- Estabilização;
- Auditoria.

A frente **Planejamento Estratégico** deve expor:

- Estruturado;
- Conectado;
- Desdobrado;
- Vinculado à gestão.

A frente **Gerenciamento Estratégico** deve expor:

- Indicadores;
- Ciclos;
- Incentivos;
- Teia de Conexões.

### 13.8 Papel do N1 na maturação assistida

No contexto do Cockpit do Consultor, o N1 deve operar como um dos motores técnicos da maturação assistida.

Seu papel é apoiar agentes, Squad Versus e Squad de Engenharia em:

- detectar hipóteses de maturação ainda não confirmadas;
- organizar pendências S1–S2 sem expor jargão técnico ao usuário comum;
- fornecer evidências e lacunas para as quatro frentes do Cockpit;
- apoiar human gate antes de promover informação para dado canônico;
- alimentar recomendações contextuais de Identidade, Processos, Planejamento Estratégico e Gerenciamento Estratégico.

A camada agentic pode usar o N1 para análise e sugestão, mas a confirmação continua exigindo validação humana quando houver impacto metodológico ou operacional relevante.
