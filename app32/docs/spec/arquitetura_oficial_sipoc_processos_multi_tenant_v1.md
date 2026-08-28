# Arquitetura Oficial — SIPOC de Processos Multi-Tenant

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a arquitetura oficial do artefato SIPOC no APP32 para:

- enquadrar processos em visão executiva de alto nível;
- delimitar início, fim, fornecedores, entradas, saídas e clientes;
- conectar modelagem macro com BPMN, POP, rotinas, indicadores e análise BPMS;
- manter versionamento, publicação controlada e isolamento por tenant;
- permitir adoção opcional por cliente, conforme necessidade e maturidade operacional.

## 2. Decisão oficial

O SIPOC passa a ser um **artefato oficial e opcional de modelagem de processo** no APP32.

Ele deve existir **entre**:

- a visão estrutural do processo (`ProcessArea` -> `MacroProcess` -> `Process`);
- e a visão detalhada/operacional (`ProcessBpmnDiagram`, `ProcessRoutine`, POP e rotinas).

O SIPOC **não substitui** BPMN, POP, rotinas ou indicadores.

Independentemente da persistência do artefato, seus cinco pontos formam a lente metodológica obrigatória para criar ou revisar o fluxo. A obrigatoriedade é de análise, não de cadastro: o APP32 continua aceitando processos sem snapshot SIPOC publicado.

Quando adotado pelo cliente, o SIPOC passa a ser a **camada de enquadramento do processo**, usada para:

- definição de escopo;
- alinhamento de stakeholders;
- validação de handoffs;
- ligação entre processo e medição;
- preparação do AS-IS da análise BPMS;
- apoio à leitura regulatória e de compliance quando o processo estiver sujeito a obrigações legais, normativas ou setoriais.

Além do SIPOC de Processo, o APP32 pode suportar **SIPOC de Macroprocesso** quando houver necessidade de leitura executiva da cadeia ponta a ponta.

## 3. Princípios oficiais

1. **company_id é obrigatório em toda leitura e escrita**
2. **SIPOC é um snapshot versionado por processo**
3. **apenas uma versão published por processo**
4. **edição ocorre somente em draft**
5. **o SIPOC representa o AS-IS oficial até nova publicação**
6. **o nível correto do SIPOC é macro, não operacional**
7. **o SIPOC precede detalhamento em BPMN/POP**
8. **toda integração do SIPOC com o app deve preservar rastreabilidade**
9. **não existe obrigatoriedade global de SIPOC por tenant, macroprocesso ou processo**
10. **requisitos regulatórios são camada de apoio do SIPOC, não nova coluna da matriz principal**
11. **o fluxo é construído progressivamente do gatilho ao objetivo e validado regressivamente do objetivo ao gatilho**
12. **SIPOC é contrato transversal do processo, não relação 1:1 com atividades BPMN**
13. **objetivo e saída são conceitos distintos: a saída é a entrega; o objetivo é o resultado pretendido**

## 4. Encaixe oficial no domínio de processos

### 4.1 Artefatos já existentes

O domínio atual já possui:

- `ProcessArea`
- `MacroProcess`
- `Process`
- `ProcessBpmnDiagram`
- `ProcessRoutine`
- `ProcessBpmsAnalysis`
- indicadores vinculados ao processo

### 4.2 Posição oficial do SIPOC

Ordem oficial de leitura/modelagem:

1. mapa de processos
2. SIPOC
3. BPMN
4. POP
5. rotinas
6. indicadores
7. análise BPMS

Decisão oficial:

- o SIPOC deve vir **antes** do fluxo/BPMN;
- a lógica oficial é **enquadrar primeiro, detalhar depois**;
- portanto o fluxo representa a próxima camada após a definição executiva do SIPOC.

Observação:

- esta ordem descreve o encaixe conceitual do SIPOC **quando ele existir**;
- a ausência de SIPOC não bloqueia BPMN, POP, rotinas, indicadores ou análise BPMS.
- mesmo sem artefato persistido, a modelagem deve verificar `Supplier`, `Input`, `Process`, `Output` e `Customer` como contrato de coerência.

### 4.2.1 Regra de construção e validação bidirecional

Na criação ou revisão do BPMN, executar os dois percursos:

1. **progressivo:** gatilho → fornecedores → entradas → transformação/atividades → saídas → clientes/recebedores → objetivo;
2. **regressivo:** objetivo → saídas necessárias → transformações suficientes → entradas requeridas → fornecedores adequados → gatilho coerente.

O bloco `Process` do SIPOC permanece macro e pode corresponder a várias atividades BPMN. Gateways e exceções podem produzir mais de uma saída válida. Todo caminho encerrado precisa entregar um resultado intencional a um recebedor identificado; itens fora do corte atual podem, por exemplo, ser classificados para um ciclo futuro, sem criar loop artificial na mesma instância.

Posicionamento oficial por nível:

- **SIPOC de Macroprocesso**: fica na tela `https://app.gestaoversus.com.br/process-map`, após `Macroprocessos`;
- **SIPOC de Processo**: fica no detalhe do processo, antes de `Fluxo/BPMN`.

### 4.3 Papel semântico

- **Mapa de Processos**: portfólio e hierarquia
- **SIPOC de Macroprocesso**: enquadramento executivo da cadeia
- **SIPOC de Processo**: enquadramento executivo do processo
- **BPMN**: fluxo formal
- **POP**: passo a passo operacional
- **Rotinas**: cadência e agenda
- **Indicadores**: medição
- **BPMS Analysis**: aderência, gaps e priorização
- **Apoio regulatório**: obrigações legais, normativas e setoriais aplicáveis ao processo

## 5. Modelo oficial de dados

O SIPOC **não deve** nascer como campo solto em `Process`.

O modelo oficial é um artefato próprio, versionado e multi-tenant.

### 5.1 Tabela principal

Tabela oficial proposta:
- `process_sipoc_snapshots`

Campos mínimos:
- `id`
- `company_id`
- `process_id`
- `version`
- `status` (`draft`, `published`, `archived`)
- `title`
- `objective`
- `start_boundary`
- `end_boundary`
- `trigger_event`
- `customer_requirements`
- `constraints_notes`
- `measures_notes`
- `risks_notes`
- `notes`
- `created_by_user_id`
- `updated_by_user_id`
- `published_at`
- `created_at`
- `updated_at`

### 5.2 Tabela de itens

Tabela oficial proposta:
- `process_sipoc_items`

Campos mínimos:
- `id`
- `company_id`
- `sipoc_snapshot_id`
- `lane` (`supplier`, `input`, `process`, `output`, `customer`)
- `title`
- `description`
- `order_index`
- `source_type` (`manual`, `bpmn`, `indicator`, `bpms`)
- `source_ref`
- `is_critical`
- `created_at`
- `updated_at`

### 5.3 Restrições oficiais

- unicidade de `version` por `process_id`
- no máximo 1 snapshot `published` por `process_id`
- `company_id` do snapshot deve ser igual ao `company_id` do `Process`
- `company_id` do item deve ser igual ao `company_id` do snapshot
- `lane` deve ser validado por enum controlado

### 5.4 Camada regulatória de apoio

O modelo oficial do SIPOC deve suportar uma camada complementar de compliance/regulatório.

Tabela oficial proposta:
- `process_sipoc_regulatory_items`

Campos mínimos:
- `id`
- `company_id`
- `sipoc_snapshot_id`
- `sipoc_item_id` (nullable, quando a regra afetar uma macroetapa específica)
- `regulatory_domain`
- `regulatory_code`
- `regulatory_name`
- `regulator_entity`
- `requirement_summary`
- `affected_scope_type` (`process`, `lane_item`)
- `control_requirements`
- `risk_level` (`low`, `medium`, `high`, `critical`)
- `evidence_requirements`
- `notes`
- `created_at`
- `updated_at`

Regras:

- a camada regulatória não altera as 5 colunas do SIPOC;
- um item regulatório pode se aplicar ao processo inteiro ou a uma macroetapa específica;
- `company_id` deve respeitar o tenant do snapshot;
- `sipoc_item_id` só pode apontar para item do mesmo snapshot.

## 6. Regras oficiais de modelagem

### 6.0 Regra de adoção

O SIPOC é **opcional**.

Sua criação depende de decisão do cliente, do tenant ou do responsável de modelagem, conforme:

- complexidade do processo;
- necessidade de alinhamento executivo;
- necessidade de clarificação de escopo;
- necessidade de explicitar handoffs, fornecedores, entradas, saídas e clientes;
- necessidade de preparação para BPMS, BPMN ou melhoria contínua.

Logo:

- nem todo `MacroProcess` precisa ter SIPOC;
- nem todo `Process` precisa ter SIPOC;
- a plataforma deve suportar SIPOC sem impor obrigatoriedade estrutural.

Quando o processo possuir sensibilidade regulatória, o cliente pode optar por registrar:

- leis;
- normas;
- portarias;
- resoluções;
- instruções normativas;
- exigências de agências reguladoras;
- obrigações de evidência, retenção e controle.

### 6.1 Limite de detalhamento

No **SIPOC de Processo**, o bloco `process` deve conter:

- mínimo de 3 atividades de alto nível;
- máximo recomendado de 7 atividades de alto nível;
- nomes orientados a transformação de entrada em saída.

No **SIPOC de Macroprocesso**, o bloco `process` deve conter:

- processos filhos ou grandes etapas da cadeia;
- sem descer para atividades operacionais;
- linguagem executiva e interfuncional.

### 6.2 Publicação mínima

Um SIPOC só pode ser publicado se houver:

- `start_boundary` preenchido;
- `end_boundary` preenchido;
- ao menos 1 item em `supplier`;
- ao menos 1 item em `input`;
- entre 3 e 7 itens em `process`;
- ao menos 1 item em `output`;
- ao menos 1 item em `customer`.

### 6.3 Regra de atualização

Mudança relevante em:

- escopo do processo;
- fornecedores críticos;
- entradas críticas;
- saídas críticas;
- clientes principais;
- limites de início/fim;

deve gerar nova revisão em `draft` e nova publicação controlada.

Esta regra só se aplica aos processos ou macroprocessos que efetivamente adotarem SIPOC.

## 7. UI oficial

### 7.1 Tela principal do processo

Arquivo-alvo:
- `C:\GestaoVersus\app32\app32\templates\modules\processes\process_details_v2.html`

Nova aba oficial:
- `SIPOC`

Ordem oficial das abas:

- `SIPOC`
- `Fluxo`
- `POP`
- `Rotinas`
- `Indicadores`

Regra:

- a navegação do detalhe do processo deve refletir a ordem metodológica oficial;
- o usuário deve ver primeiro o enquadramento executivo do processo;
- depois, o fluxo detalhado em BPMN.

Regra de UX:

- a aba SIPOC pode ser exibida mesmo sem conteúdo, como feature disponível;
- a existência de processo sem SIPOC **não caracteriza pendência obrigatória**;
- o produto não deve comunicar ausência de SIPOC como erro estrutural.

### 7.2 Blocos da aba SIPOC

Blocos mínimos:

1. cabeçalho do SIPOC
   - título
   - status
   - objetivo
   - início
   - fim
   - evento disparador

2. grade SIPOC
   - fornecedores
   - entradas
   - processo
   - saídas
   - clientes

3. complementos
   - requisitos do cliente
   - restrições
   - medidas/indicadores
   - riscos
   - requisitos regulatórios aplicáveis
   - observações

4. ações
   - salvar draft
   - publicar
   - arquivar
   - duplicar para nova versão
   - sugerir a partir do BPMN

5. apoio regulatório
   - domínio regulatório
   - norma/lei/regulamento
   - órgão regulador
   - obrigação principal
   - impacto no processo
   - etapa afetada
   - criticidade
   - evidência/controle exigido

### 7.3 UX oficial

- leitura rápida e executiva;
- edição em blocos repetíveis;
- ordenação simples por `order_index`;
- comparação clara entre draft e published;
- nenhuma experiência de edição deve exigir conhecimento técnico de BPMN.

Regra adicional:

- o bloco regulatório deve ser apresentado como apoio de compliance;
- ele não deve competir visualmente com a matriz principal SIPOC;
- a leitura do SIPOC deve continuar executiva mesmo quando houver múltiplas obrigações regulatórias.

## 8. API oficial

Responsável principal:
- `@BACKEND_API`

Boundary:
- rota fina;
- regra de negócio em service;
- validação de tenant obrigatória.

### 8.1 Endpoints mínimos

- `GET /api/processes/<process_id>/sipoc`
  - retorna versão publicada e, se permitido, draft atual

- `POST /api/processes/<process_id>/sipoc`
  - cria snapshot draft inicial

- `PUT /api/processes/<process_id>/sipoc/<sipoc_id>`
  - atualiza metadados do draft

- `POST /api/processes/<process_id>/sipoc/<sipoc_id>/items`
  - cria item de lane

- `PUT /api/processes/<process_id>/sipoc/<sipoc_id>/items/<item_id>`
  - edita item

- `DELETE /api/processes/<process_id>/sipoc/<sipoc_id>/items/<item_id>`
  - remove item

- `POST /api/processes/<process_id>/sipoc/<sipoc_id>/regulatory-items`
  - cria item regulatório

- `PUT /api/processes/<process_id>/sipoc/<sipoc_id>/regulatory-items/<regulatory_item_id>`
  - edita item regulatório

- `DELETE /api/processes/<process_id>/sipoc/<sipoc_id>/regulatory-items/<regulatory_item_id>`
  - remove item regulatório

- `POST /api/processes/<process_id>/sipoc/<sipoc_id>/publish`
  - publica snapshot draft

- `POST /api/processes/<process_id>/sipoc/<sipoc_id>/archive`
  - arquiva snapshot

- `POST /api/processes/<process_id>/sipoc/suggest-from-bpmn`
  - gera rascunho assistido a partir do BPMN publicado

### 8.2 Contrato de resposta mínimo

O snapshot deve expor:

- metadados do SIPOC;
- lista de itens agrupados por lane;
- lista de itens regulatórios;
- resumo de completude;
- referência ao processo;
- versão;
- status;
- timestamps;
- usuário de criação/edição/publicação quando disponível.

## 9. Serviços oficiais

Responsável principal:
- `@BACKEND_SERVICE`

Serviços esperados:

### 9.1 `process_sipoc_service.py`

Responsabilidades:

- criar draft;
- atualizar snapshot;
- validar publicação;
- publicar;
- arquivar;
- montar payload consolidado;
- garantir integridade entre processo, snapshot e itens.

Também deve:

- validar vínculo de itens regulatórios com snapshot/item;
- consolidar itens regulatórios no payload de leitura;
- impedir vínculo cross-tenant ou cross-snapshot.

### 9.2 `process_sipoc_suggestion_service.py`

Responsabilidades:

- sugerir macroetapas a partir de BPMN;
- sugerir outputs/clients a partir de indicadores e BPMS;
- manter separação entre sugestão e decisão humana.

## 10. Integrações oficiais

### 10.1 BPMN

O SIPOC deve poder consumir:

- nome do processo;
- atividades principais;
- lanes;
- eventos de início/fim;
- fluxos críticos.

Uso oficial:
- sugerir o bloco `process`;
- sugerir limites;
- apontar divergência entre SIPOC e BPMN.

### 10.2 POP

O SIPOC deve servir como camada acima do POP.

Regra:
- macroetapa do SIPOC pode referenciar múltiplas atividades POP;
- POP não substitui macroetapa de SIPOC;
- não detalhar passo operacional dentro do bloco `process` do SIPOC.

### 10.3 Indicadores

O SIPOC deve se integrar a indicadores em dois níveis:

- `measures_notes` como visão executiva;
- referências a indicadores reais do processo quando existirem.

### 10.4 BPMS Analysis

O SIPOC publicado passa a ser insumo preferencial para:

- `as_is_summary`
- stakeholders
- dependências
- handoffs
- saídas críticas
- requisitos de medição
- contexto regulatório quando existir

Na ausência de SIPOC, a análise BPMS continua operando a partir de:

- descrição do processo;
- BPMN publicado, quando existir;
- POPs e rotinas;
- indicadores;
- entrevistas e levantamento operacional.

Quando houver camada regulatória no SIPOC, ela deve poder apoiar:

- identificação de controles obrigatórios;
- classificação de risco operacional/regulatório;
- avaliação de aderência do app às obrigações declaradas;
- priorização de gaps com impacto legal ou setorial.

### 10.5 Apoio regulatório e compliance

O SIPOC deve suportar, como camada complementar, o registro de referências como:

- legislação trabalhista;
- legislação fiscal;
- normas técnicas;
- resoluções;
- portarias;
- exigências de agências como ANM, ANP e equivalentes;
- obrigações documentais, de retenção, evidência e controle.

Exemplos de uso:

- “atividade sujeita à lei XYZ trabalhista”
- “atividade sujeita à norma HZY fiscal”
- “atividade sujeita à NPT da ANM”
- “atividade sujeita à regra XPTO da ANP”

Regra oficial:

- esses registros devem existir como apoio estruturado;
- não devem virar nova coluna do SIPOC;
- devem poder apontar para o processo inteiro ou para macroetapa específica.

## 11. Book do Processo

Arquivo-alvo:
- `C:\GestaoVersus\app32\app32\templates\reports\process_documentation_v2.html`

Decisão oficial:

O Book do Processo deve ganhar uma seção própria:
- `SIPOC do Processo`

Regra:

- a seção deve ser renderizada somente quando houver SIPOC publicado;
- se não houver SIPOC, o Book do Processo segue válido sem essa seção.

Conteúdo mínimo da seção:

- objetivo;
- início e fim;
- evento disparador;
- tabela SIPOC em 5 colunas;
- quadro de requisitos regulatórios aplicáveis, quando houver;
- requisitos do cliente;
- medidas;
- riscos principais.

## 12. Permissões e segurança

- leitura: `processes.view`
- edição draft: `processes.edit`
- publicação/arquivamento: `processes.edit` com escopo compatível do tenant

Guardrails:

- proibir acesso cross-tenant;
- proibir publicação em processo de outra empresa;
- registrar autoria e timestamps;
- preservar histórico por versão.

Guardrail adicional:

- itens regulatórios não substituem validação jurídica ou consultoria regulatória;
- o app registra enquadramento operacional declarado, não emite parecer legal automático.

## 13. Não objetivos desta fase

Ficam fora desta SPEC:

- editor visual tipo canvas/swimlane para SIPOC;
- publicação automática por IA;
- sincronização bidirecional automática BPMN <-> SIPOC;
- cálculo estatístico avançado de maturidade;
- substituição de BPMS Analysis pelo SIPOC.

## 14. Ordem oficial de implementação

### Fase 1

- modelo de dados;
- services;
- endpoints CRUD;
- renderização da aba SIPOC;
- leitura no detalhe do processo.

### Fase 2

- publicação versionada;
- seção SIPOC no Book do Processo;
- integração básica com indicadores;
- resumo de completude.

### Fase 3

- sugestão a partir do BPMN;
- reaproveitamento no BPMS Analysis;
- diff entre versões;
- alertas de divergência SIPOC x BPMN.

## 15. Responsabilidades oficiais

- `@ARQUITETO`
  - semântica do artefato;
  - boundaries;
  - governança;
  - versionamento.

- `@BACKEND_SERVICE`
  - regra de negócio;
  - validação de publicação;
  - integridade do domínio.

- `@BACKEND_API`
  - surface REST;
  - payloads;
  - autorização;
  - serialização.

- `@DBA`
  - modelagem;
  - constraints;
  - índices;
  - estratégia de migração.

- `@FRONTEND`
  - aba SIPOC;
  - repetidores;
  - experiência executiva;
  - print/report.

- `@BACKEND_SERVICE` e `@ARQUITETO`
  - semântica do apoio regulatório;
  - boundary entre modelagem operacional e compliance.

- `@QA_AUTOMATION`
  - smoke multi-tenant;
  - CRUD;
  - publicação;
  - regressão do Book do Processo.

## 16. Critérios oficiais de aceite

Um processo SIPOC estará oficialmente aderente quando:

- existir snapshot draft editável por tenant;
- existir publicação controlada;
- o detalhe do processo exibir a aba SIPOC;
- o Book do Processo renderizar a seção SIPOC;
- o snapshot publicado puder ser reutilizado na análise BPMS;
- os testes cobrirem segregação por `company_id`.

Quando a camada regulatória for utilizada, também deve ser aceito quando:

- for possível registrar obrigação regulatória por processo ou por macroetapa;
- o payload de leitura expuser os itens regulatórios corretamente;
- o Book do Processo renderizar o quadro regulatório quando houver conteúdo;
- a segregação por `company_id` também cobrir os itens regulatórios.

## 17. Decisão oficial de adoção por cliente

O APP32 **não deve** impor SIPOC como pré-requisito universal.

A decisão oficial é:

- SIPOC disponível como artefato nativo do produto;
- adoção opcional por tenant/cliente;
- uso orientado por necessidade real de modelagem e gestão;
- sem bloqueio operacional para clientes que não desejarem utilizar SIPOC.
