# Arquitetura Oficial — Dimensões e Recursos Habilitadores de Processos

**Status:** canônico
**Classe:** SPEC
**Versão conceitual:** 2.1
**Decisão aprovada em:** 21/08/2026

## 1. Tese oficial

> Dimensões Habilitadoras organizam os Recursos Habilitadores; os recursos viabilizam os processos; e os processos produzem entregas e geram valor para a empresa.

A camada passa a se chamar **Dimensões e Recursos Habilitadores**. O termo capacidade fica reservado à propriedade mensurável **Capacidade Operacional**, evitando colisão semântica.

Não será criada, nesta fase, uma entidade adicional de recurso ou inventário. Pessoas concretas, patrimônios, contratos e licenças individualizadas continuam pertencendo aos seus domínios de origem e poderão ser relacionados futuramente quando houver necessidade comprovada.

## 2. Definições

### 2.1 Dimensão Habilitadora

Agrupador configurável por `company_id`, usado para organizar recursos de natureza semelhante no catálogo corporativo. Dimensão não pertence a macroprocesso ou processo.

O APP32 deve oferecer como template inicial, sem enum global rígido:

1. Ativos e Estrutura Física;
2. Pessoas, Papéis e Competências;
3. Tecnologia, Dados e Sistemas;
4. Documentos e Conhecimento;
5. Materiais, Insumos e Serviços.

Cada tenant pode cadastrar, ordenar, renomear e inativar suas dimensões. **Interfaces entre processos não são dimensão habilitadora**; devem permanecer como relação ou contrato de interface.

### 2.2 Recurso Habilitador

Papel, equipe, competência, ativo, sistema, dado, documento, material ou serviço necessário à execução de um processo.

O nome deve ser curto, reconhecível e reutilizável, por exemplo: `Analista Fiscal`, `Time Fiscal`, `Sistema Fiscal Licenciado`, `Procedimento de Faturamento` ou `Equipamento de Movimentação`.

A condição específica exigida pelo processo não deve inflar o nome do recurso. Ela pertence ao vínculo Processo–Recurso.

### 2.3 Instância concreta

Pessoa nominal, patrimônio, contrato, licença ou item individualizado não é o recurso habilitador canônico. Exemplos:

- recurso `Analista Fiscal`; pessoa concreta `Maria Souza`;
- recurso `Sistema Fiscal Licenciado`; instância `contrato/licença do fornecedor`;
- recurso `Equipamento de Movimentação`; instância `patrimônio 0045`.

## 3. Modelo lógico

```text
CapabilityDimension
  └─ organiza → EnablingResource
                    └─ utilizado por → ProcessEnablingResourceLink
                                            ├─ Process
                                            ├─ ProcessRoutine (opcional)
                                            └─ elemento BPMN (opcional)
```

### 3.1 Dimensão

Tabela: `capability_dimensions`

Campos mínimos: `id`, `company_id`, `name`, `description`, `order_index`, `is_active`, `created_at` e `updated_at`.

### 3.2 Recurso Habilitador

O armazenamento `resource_catalog` é preservado para migração sem perda, mas seu contrato canônico passa a ser **recurso habilitador**.

Campos canônicos:

- `id`, `company_id`, `dimension_id`;
- `name` — compatível transitoriamente com `item_name`;
- `subtype` opcional;
- `operational_capacity_value`, `operational_capacity_unit`, `operational_capacity_period` e `max_recommended_utilization_pct`;
- dados quantitativos e econômicos opcionais já existentes;
- `notes`, `is_active` e timestamps.

Campos quantitativos são opcionais porque se aplicam a alguns recursos, mas não a todos.

### 3.3 Vínculo Processo–Recurso

O armazenamento `process_resource_links` é preservado, com contrato canônico **ProcessEnablingResourceLink**.

### 3.4 Planejamento de execução

`ProcessExecutionPlan` registra quantidade e período (`day`, `week`, `month`, `quarter`, `year`) uma única vez por processo. A service normaliza o planejamento para o horizonte mensal e o aplica a todos os recursos vinculados.

Além dos vínculos atuais, o contrato deve suportar:

- `required_condition` — condição necessária no processo;
- `criticality` — `low`, `medium`, `high` ou `critical`;
- `gap_notes` — lacuna ou gargalo observado;
- quantidade/uso requerido e custos opcionais.

## 4. Regras de negócio

- Toda dimensão, recurso e vínculo deve possuir `company_id`.
- Dimensões e recursos formam catálogo corporativo independente de macroprocessos e processos.
- O processo pode alocar qualquer recurso ativo do seu tenant.
- Recurso inativo não pode receber novo vínculo, preservando-se o histórico.
- A dimensão do recurso é obrigatória.
- Demanda planejada = consumo por execução × execuções planejadas normalizadas no mês.
- Utilização planejada = demanda planejada agregada ÷ capacidade operacional mensal × 100.
- Utilização real usa as instâncias concluídas no mês e pode ultrapassar 100%, evidenciando sobrecarga.
- O limite recomendado fica entre 0% e 100%, mas não limita o percentual calculado.
- Processo de apoio não deve ser confundido com recurso: `Gerir Pessoas` é processo; `Time Fiscal` é recurso.

## 5. Compatibilidade e migração

- Os registros atuais de `resource_catalog` são preservados e recebem uma dimensão por mapeamento do tipo legado.
- APIs legadas `/api/resources` permanecem temporariamente como aliases de compatibilidade.
- APIs canônicas usam `/api/enabling-dimensions`, `/api/enabling-resources`, `/api/processes/<id>/execution-plan` e `/api/processes/<id>/enabling-resources`.
- Respostas de transição podem expor aliases `resource`, `enabling_resource` e `capability`, evitando quebra abrupta de consumidores.
- A remoção dos nomes e endpoints legados exige telemetria de uso e nova decisão de migração.

Mapeamento inicial sugerido:

| Tipo legado | Dimensão padrão |
|---|---|
| `people` | Pessoas, Papéis e Competências |
| `digital_it` | Tecnologia, Dados e Sistemas |
| `facilities`, `equipment_tools` | Ativos e Estrutura Física |
| `inputs` | Materiais, Insumos e Serviços |
| `other` | Documentos e Conhecimento, sujeito a validação humana |

## 6. UI oficial

Na Arquitetura de Processos:

- aba **Recursos Habilitadores** como catálogo corporativo da empresa;
- telas internas separadas para cadastro/ordenação de dimensões e cadastro dos recursos;
- manutenção dos atributos quantitativos e econômicos como opcionais.

No detalhe do processo:

- aba **Recursos Habilitadores** entre SIPOC e Fluxo;
- planejamento único da frequência de execução do processo;
- seleção de recurso existente no catálogo corporativo;
- registro da condição requerida, criticidade e gap;
- visualização agrupada por dimensão, com demanda mensal, utilização planejada, utilização real e saldo.

No macroprocesso, qualquer visão de recursos é somente uma consolidação derivada das alocações de seus processos filhos; o macroprocesso não é proprietário nem ponto de cadastro do recurso.

## 7. API, service e segurança

- Rotas permanecem finas e a regra fica em service.
- Payloads devem ser validados e normalizados no backend.
- Toda busca por ID também deve filtrar `company_id`.
- Relações cross-tenant devem ser rejeitadas mesmo quando os IDs existirem.
- Índices compostos devem priorizar `company_id` com dimensão, recurso e processo.

## 8. Critérios de aceite

A evolução estará aderente quando:

- dimensões forem CRUD tenant-safe no catálogo corporativo e não enum global;
- recursos forem vinculados obrigatoriamente a uma dimensão do mesmo tenant;
- registros legados forem preservados e classificados;
- processos puderem planejar frequência e declarar recursos, consumo por execução, condição requerida, criticidade e gap;
- UI apresentar recurso habilitador como conceito principal e capacidade operacional como sua propriedade;
- percentuais planejado e real evidenciarem inclusive sobrecarga acima de 100%;
- APIs legadas continuarem funcionais durante a transição;
- testes comprovarem segregação entre tenants e regressão dos cálculos existentes.
