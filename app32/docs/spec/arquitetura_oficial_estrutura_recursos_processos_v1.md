# Arquitetura Oficial — Estrutura/Recursos de Processos Multi-Tenant

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a arquitetura oficial da camada **Estrutura/Recursos** no APP32 para:

- registrar o catálogo geral de recursos da empresa na Arquitetura de Processos;
- classificar recursos por tipos fixos para relatórios e indicadores;
- separar cadastro do recurso do uso/alocação em processos;
- suportar análise de custo, capacidade e gargalo;
- preservar isolamento multi-tenant por `company_id`;
- preparar integração futura com BPMN, POP, rotinas, indicadores e análise BPMS.

## 2. Decisão oficial

A camada **Estrutura/Recursos** passa a ser um artefato oficial da modelagem de processos.

Ela deve existir conceitualmente **entre**:

- `SIPOC`, que enquadra o processo em nível executivo;
- `Fluxo/BPMN`, que detalha a sequência e colaboração operacional.

Ordem oficial de leitura/modelagem no detalhe do processo:

1. SIPOC
2. Estrutura/Recursos
3. Fluxo/BPMN
4. POP
5. Rotinas
6. Indicadores

Regra:

- a camada Estrutura/Recursos **não substitui** cadastro de colaboradores, equipes, sistemas, ativos ou financeiro;
- ela registra **quais recursos são necessários e como são usados por um processo**;
- relatórios e indicadores devem consumir tipos fixos, não texto livre.

## 3. Tipos oficiais de recursos

Os tipos de recurso são fixos:

1. `people` — Pessoas
2. `inputs` — Insumos
3. `facilities` — Imóveis / Instalações
4. `digital_it` — TI / Digital
5. `equipment_tools` — Equipamentos / Ferramentas
6. `other` — Outros

Regra:

- `tipo` deve ser enum controlado pelo produto;
- `subtipo` é obrigatório para detalhamento analítico;
- quando `tipo = other`, o `subtipo` e as `observacoes` devem explicar claramente a natureza do recurso.

## 4. Modelo oficial de dados

A modelagem oficial deve separar:

- **Cadastro do recurso**: o que o recurso é, quanto custa e qual capacidade total está disponível;
- **Uso no processo**: quanto desse recurso compartilhado está alocado em cada processo, atividade/POP ou elemento BPMN.

### 4.1 Cadastro do recurso

Tabela oficial proposta:

- `resource_catalog`

Campos mínimos:

- `id`
- `company_id`
- `type`
- `subtype`
- `item_name`
- `unit_value`
- `quantity`
- `acquisition_total_amount`
- `installation_total_amount`
- `monthly_recurring_amount`
- `operational_capacity_value`
- `operational_capacity_unit` (`hour`, `day`, `month`)
- `estimated_useful_life`
- `notes`
- `is_active`
- `created_at`
- `updated_at`

Mapeamento funcional:

- `tipo` -> `type`
- `subtipo` -> `subtype`
- `nome do item` -> `item_name`
- `valor unitário` -> `unit_value`
- `quantidade` -> `quantity`
- `gasto total de aquisição` -> `acquisition_total_amount`
- `gasto total de instalação` -> `installation_total_amount`
- `gasto mensal recorrente` -> `monthly_recurring_amount`
- `capacidade operacional (hora / dia / mês)` -> `operational_capacity_value` + `operational_capacity_unit`
- `vida útil estimada` -> `estimated_useful_life`
- `observações` -> `notes`

### 4.2 Uso no processo

Tabela oficial proposta:

- `process_resource_links`

Campos mínimos:

- `id`
- `company_id`
- `process_id`
- `process_routine_id` nullable
- `bpmn_element_id` nullable
- `resource_id`
- `used_quantity`
- `usage_percentage`
- `used_quantity_per_execution`
- `estimated_monthly_instances`
- `monthly_used_quantity`
- `allocated_monthly_cost`
- `estimated_cost_per_execution`
- `capacity_bottleneck_notes`
- `is_active`
- `created_at`
- `updated_at`

Mapeamento funcional:

- `processo` -> `process_id`
- `atividade/POP opcional` -> `process_routine_id`
- `elemento BPMN opcional` -> `bpmn_element_id`
- `quanto usado por instância` -> `used_quantity_per_execution`
- `instâncias estimadas por mês` -> `estimated_monthly_instances`
- `quanto usado total no mês` -> `monthly_used_quantity`/`used_quantity` calculado
- `% usado no processo` -> `usage_percentage` calculado
- `custo mensal alocado ao processo` -> `allocated_monthly_cost`
- `custo estimado por execução` -> `estimated_cost_per_execution`
- `notas de capacidade/gargalo` -> `capacity_bottleneck_notes`

## 5. Regras de integridade

Regras obrigatórias:

- toda leitura e escrita deve escopar `company_id`;
- `resource_catalog.company_id` deve ser igual ao `company_id` do processo vinculado;
- `process_resource_links.company_id` deve ser igual ao `company_id` do processo e do recurso;
- `process_routine_id`, quando informado, deve pertencer ao mesmo processo ou ao mesmo tenant;
- `bpmn_element_id`, quando informado, deve apontar para elemento do BPMN do processo, sem exigir FK direta;
- recurso inativo não deve ser sugerido para novo vínculo, mas vínculos históricos podem permanecer para rastreabilidade;
- custos e quantidades devem aceitar `0`, mas não valores negativos;
- `usage_percentage` deve ficar entre `0` e `100`;
- o catálogo deve expor uso total e quantidade disponível para evitar dupla contagem de capacidade compartilhada.

## 6. Regras de custo e capacidade

O APP32 deve preservar três leituras econômicas:

- **CAPEX**: `acquisition_total_amount` + `installation_total_amount`;
- **OPEX**: `monthly_recurring_amount`;
- **Alocação por processo**: `allocated_monthly_cost` e `estimated_cost_per_execution`.

Regra:

- o cadastro registra custo total do recurso;
- o vínculo registra custo atribuído ao processo;
- o vínculo não deve alterar custo base do catálogo;
- relatórios devem distinguir custo cadastrado, custo recorrente e custo alocado.

## 7. UI oficial

Arquivos-alvo:

- `C:\GestaoVersus\app32\app32\templates\modules\processes\process_map_v2.html`
- `C:\GestaoVersus\app32\app32\templates\modules\processes\process_details_v2.html`

Seções oficiais:

- `Arquitetura de Processos > Recursos`: catálogo geral, posicionado após o SIPOC de Macroprocesso e antes de Processos;
- `Detalhe do Processo > Estrutura/Recursos`: utilização/alocação de múltiplos recursos já existentes no catálogo geral.

Ordem oficial das abas:

- `SIPOC`
- `Estrutura/Recursos`
- `Fluxo`
- `POP`
- `Rotinas`
- `Indicadores`

Blocos mínimos:

1. resumo econômico do processo;
2. recursos vinculados por tipo;
3. seleção obrigatória de recurso existente, com botão de atalho para cadastrar/alterar recursos no catálogo geral;
4. vínculo do recurso ao processo;
5. custo mensal alocado;
6. custo estimado por execução;
7. notas de capacidade/gargalo;
8. uso por instância, instâncias estimadas por mês, uso mensal calculado, percentual usado e saldo disponível do recurso compartilhado.

## 8. API oficial

Responsável principal:

- `@BACKEND_API`

Boundary:

- rota fina;
- validação de payload;
- autorização por tenant;
- regra de negócio em service.

Endpoints mínimos:

- `GET /api/resources`
- `POST /api/resources`
- `PUT /api/resources/<resource_id>`
- `DELETE /api/resources/<resource_id>`
- `GET /api/processes/<process_id>/resources`
- `POST /api/processes/<process_id>/resources`
- `PUT /api/processes/<process_id>/resources/<link_id>`
- `DELETE /api/processes/<process_id>/resources/<link_id>`

## 9. Serviços oficiais

Responsável principal:

- `@BACKEND_SERVICE`

Serviço esperado:

- `process_resource_service.py`

Responsabilidades:

- validar tipo/subtipo;
- criar e atualizar recurso;
- criar e atualizar vínculo com processo;
- calcular uso mensal por recurso a partir de uso por instância x instâncias/mês;
- calcular uso total e disponibilidade do recurso compartilhado;
- calcular resumo econômico;
- consolidar recursos por tipo;
- impedir vínculo cross-tenant;
- preservar histórico de vínculos inativos;
- preparar payload para relatórios e indicadores.

## 10. Relatórios e indicadores

A camada deve permitir relatórios como:

- custo mensal alocado por processo;
- CAPEX estimado por processo;
- OPEX por macroprocesso;
- custo por execução;
- recursos críticos por tipo;
- gargalos declarados por processo;
- processos dependentes de TI/Digital;
- processos dependentes de Pessoas;
- distribuição de recursos por área, macroprocesso e processo.

Indicadores futuros possíveis:

- custo mensal por processo;
- custo médio por execução;
- percentual de custo por tipo de recurso;
- quantidade de recursos críticos por processo;
- capacidade operacional declarada versus demanda estimada;
- percentual usado por recurso compartilhado;
- consumo mensal estimado por processo;
- saldo disponível por recurso/capacidade.

## 11. Integrações oficiais

### 11.1 SIPOC

O SIPOC enquadra fornecedores, entradas, saídas e clientes.

Estrutura/Recursos detalha o que sustenta a operação.

Regra:

- insumos do SIPOC podem sugerir recursos do tipo `inputs`;
- clientes/fornecedores do SIPOC não devem virar recurso automaticamente sem decisão humana.

### 11.2 BPMN

O vínculo pode apontar para `bpmn_element_id`.

Uso esperado:

- identificar recurso necessário em uma atividade;
- apoiar análise de gargalo;
- preparar execução assistida por sistemas, pessoas ou IA.

### 11.3 POP

O vínculo pode apontar para `process_routine_id`.

Uso esperado:

- indicar recurso necessário para uma atividade POP;
- calcular custo operacional aproximado da atividade;
- apoiar treinamento, execução e auditoria.

### 11.4 Indicadores

Indicadores devem consumir a camada de recursos para:

- custo;
- capacidade;
- dependência operacional;
- criticidade;
- gargalo.

### 11.5 BPMS Analysis

A análise BPMS deve usar Estrutura/Recursos para:

- identificar lacunas de capacidade;
- apontar dependência de sistemas;
- priorizar automação;
- estimar impacto econômico de melhoria;
- classificar gargalos estruturais.

## 12. Permissões e segurança

Permissões sugeridas:

- leitura: `processes.view`
- cadastro/edição de recurso: `processes.edit` ou permissão futura `resources.edit`
- vínculo em processo: `processes.edit`

Guardrails:

- proibir acesso cross-tenant;
- não confiar apenas em ids recebidos no payload;
- validar `company_id` do processo, recurso e vínculo;
- registrar timestamps;
- evitar exclusão física quando houver uso histórico relevante.

## 13. Não objetivos desta fase

Ficam fora desta SPEC:

- depreciação contábil completa;
- integração automática com financeiro;
- controle de estoque;
- manutenção preventiva;
- agenda de disponibilidade real;
- rateio automático avançado;
- valuation patrimonial completo;
- parecer de viabilidade econômica automatizado.

## 14. Ordem oficial de implementação

### Fase 1

- modelos `ResourceCatalog` e `ProcessResourceLink`;
- service de validação e consolidação;
- endpoints CRUD;
- catálogo geral de recursos na Arquitetura de Processos;
- aba Estrutura/Recursos no detalhe do processo;
- smoke multi-tenant.

### Fase 2

- resumo econômico no processo;
- seção no Book do Processo;
- filtros por tipo/subtipo;
- indicadores básicos de custo e capacidade.

### Fase 3

- integração com BPMS Analysis;
- sugestões a partir de SIPOC/BPMN/POP;
- relatórios consolidados por área e macroprocesso;
- alertas de gargalo e dependência crítica.

## 15. Responsabilidades oficiais

- `@ARQUITETO`
  - semântica do artefato;
  - ordem de modelagem;
  - boundaries com SIPOC, BPMN e POP.

- `@DBA`
  - modelagem;
  - constraints;
  - índices;
  - estratégia de migração.

- `@BACKEND_SERVICE`
  - regras de negócio;
  - validação multi-tenant;
  - cálculo de resumos.

- `@BACKEND_API`
  - contratos REST;
  - validação de entrada;
  - autorização.

- `@FRONTEND`
  - aba Estrutura/Recursos;
  - UX de cadastro/vínculo;
  - resumos visuais.

- `@QA_AUTOMATION`
  - CRUD;
  - regressão do detalhe do processo;
  - smoke multi-tenant;
  - validação de relatórios.

## 16. Critérios oficiais de aceite

A camada Estrutura/Recursos estará aderente quando:

- tipos fixos estiverem validados por enum;
- todo recurso possuir `company_id`;
- todo vínculo possuir `company_id`;
- recurso e processo de tenants diferentes forem bloqueados;
- for possível cadastrar/modificar recurso no catálogo geral;
- for possível vincular múltiplos recursos ao mesmo processo;
- a tela de processo exigir seleção de recurso já cadastrado e oferecer atalho para cadastro/alteração no catálogo;
- for possível vincular recurso opcionalmente à atividade/POP;
- for possível apontar `bpmn_element_id`;
- a tela do processo exibir recursos por tipo;
- o payload consolidado expuser custos, capacidade, uso total e disponibilidade;
- relatórios conseguirem agrupar por tipo/subtipo.

