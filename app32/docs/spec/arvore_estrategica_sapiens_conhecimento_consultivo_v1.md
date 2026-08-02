# SPEC — Árvore Estratégica do Sapiens v1

**Classe documental:** SPEC
**Status:** Aprovada para homologação do P0 — implementação local concluída, sem deploy
**Data:** 2026-08-02
**Domínio canônico:** `knowledge`
**Capability:** `strategic_tree`
**Aplicação piloto:** Versus Gestão Corporativa (`company_id = 9`)
**Especialistas líderes:** `@ARQUITETO`, `@AI_ENGINEER`
**Apoios:** `@BACKEND_SERVICE`, `@BACKEND_API`, `@DBA`, `@FRONTEND`, `@QA_AUTOMATION`
**Paper de origem:** `docs/papers/paper_sistema_geracao_entrega_percepcao_recaptura_valor_v1.md`
**SPEC-base:** `docs/spec/arquitetura_oficial_camada_conhecimento_corporativo_app_versus_v1.md`

## 1. Objetivo

Definir o contrato funcional, arquitetural, de segurança, experiência e integração MCP da `Árvore Estratégica`, nova superfície conversacional do Sapiens para registrar, classificar, organizar, relacionar, analisar e amadurecer conhecimento organizacional.

A capability deve permitir que colaborador, cliente, consultor e Squads contribuam em linguagem natural, preservando:

- simplicidade na superfície;
- robustez no núcleo;
- isolamento por `company_id`;
- origem e conteúdo original;
- confidencialidade;
- histórico e versionamento;
- separação entre contribuição, hipótese, análise, validação e decisão;
- gates humanos antes de qualquer impacto canônico.

## 2. Decisões oficiais propostas

1. o nome funcional é **Árvore Estratégica**;
2. o conceito técnico é **Árvore Consultiva de Conhecimento**;
3. a capability é `strategic_tree` e pertence ao domínio `knowledge`;
4. Sapiens é a porta conversacional principal;
5. o escopo aparece ao lado de `Minha Empresa` e `APP Versus`;
6. a árvore organiza a navegação e o grafo preserva relações transversais;
7. conversa é a interface principal;
8. PostgreSQL é a fonte de verdade;
9. todo dado tenant-owned exige `company_id`;
10. conteúdo bruto é imutável, salvo correção formal ou política de retenção;
11. síntese e classificação não sobrescrevem a contribuição original;
12. colaborador pode registrar ideia sem conhecer a taxonomia;
13. o sistema pergunta somente quando houver ambiguidade ou risco relevante;
14. Squad Cliente e Squad Versus operam somente dentro de seus papéis e permissões;
15. MCP reutiliza as mesmas services da API;
16. MVP não promove conteúdo automaticamente para objetos canônicos;
17. anonimato verdadeiro não pode ser simulado por simples ocultação do nome;
18. os escopos atuais do Sapiens permanecem compatíveis;
19. lógica de negócio em rota Flask é proibida;
20. feature flag controla o rollout por empresa.

## 3. Relação com a Camada de Conhecimento

A SPEC-base define inicialmente uma camada de leitura, recuperação e resposta citada. A Árvore Estratégica é uma extensão colaborativa e mutável do mesmo domínio, com boundaries próprios.

| Capacidade | Responsabilidade |
|---|---|
| Camada de Conhecimento | recuperar fontes autorizadas e responder com evidência |
| Árvore Estratégica | receber contribuições, organizar discussão e amadurecer temas |
| Domínios canônicos | manter estratégia, processos, indicadores, projetos e demais verdades oficiais |

A árvore pode consumir evidências da Camada de Conhecimento e, futuramente, gerar propostas de promoção. Ela não substitui fontes canônicas nem workflows proprietários.

## 4. Escopos no Sapiens

O seletor passa a admitir:

| Identificador | Rótulo | Comportamento |
|---|---|---|
| `all` | Todos | consulta combinada nos escopos autorizados; não cria contribuição por inferência |
| `company` | Minha Empresa | busca e resposta sobre fontes tenant-owned |
| `product` | APP Versus | ajuda oficial do produto |
| `strategic_tree` | Árvore Estratégica | conversa, registro e maturação em árvores autorizadas |

Regras:

1. selecionar `strategic_tree` não altera silenciosamente a empresa ativa;
2. criação e escrita exigem contexto autenticado e `company_id` válido;
3. alternar escopo preserva rascunho local, mas não mistura histórico de forma implícita;
4. pergunta em outro escopo pode sugerir abrir ou relacionar um Tema Consultivo, sem registrar automaticamente;
5. o widget global e a página `/sapiens` devem apresentar nomenclatura consistente.

## 5. Contrato de experiência

### 5.1 Cinco movimentos

```text
Conte
→ Entenda
→ Discuta
→ Decida
→ Acompanhe
```

### 5.2 Interação conversacional

O fluxo esperado é:

```text
pergunta
→ resposta
→ interpretação
→ proposição
→ contraponto
→ aprofundamento
→ ajuste
→ confirmação
→ registro
→ próxima discussão
```

O usuário não precisa preencher formulário técnico para começar.

### 5.3 Componentes visíveis

- conversa;
- seletor de árvore;
- breadcrumb do ramo ativo;
- árvore lateral ou recolhível;
- resumo do Tema Consultivo;
- evidências e fontes sob demanda;
- ações contextuais;
- pendências e próxima ação;
- estados em linguagem simples.

### 5.4 Ações principais

- `Adicionar informação`;
- `Fazer entrevista`;
- `Pesquisar`;
- `Analisar tema`;
- `Conversar`;
- `Estacionar ramo`;
- `Retomar tema`;
- `Registrar validação`;
- `Registrar decisão`.

Ações ainda não implementadas devem permanecer ausentes, e não visíveis como promessa enganosa.

## 6. Árvore na interface e grafo no núcleo

### 6.1 Árvore

A árvore possui um pai visual por nó e organiza:

- tema raiz;
- tema principal;
- subtema;
- investigação;
- decisão;
- desdobramento;
- item estacionado.

### 6.2 Grafo

Relações adicionais permitem conectar um nó ou contribuição a:

- outro ramo;
- pessoa ou papel;
- processo ou macroprocesso;
- oferta;
- cliente;
- projeto ou atividade;
- indicador;
- reunião ou decisão;
- Business Review;
- fonte de conhecimento.

Relação probabilística nasce como `proposed` e não se torna verificada sem regra determinística ou validação autorizada.

## 7. Modelo conceitual

### 7.1 `strategic_trees`

- `id`;
- `company_id`;
- `title`;
- `purpose`;
- `status`;
- `visibility_scope`;
- `root_node_id`;
- `created_by_user_id`;
- `updated_by_user_id`;
- `created_at`;
- `updated_at`;
- `archived_at`.

### 7.2 `strategic_tree_nodes`

- `id`;
- `company_id`;
- `tree_id`;
- `parent_node_id`;
- `node_type`;
- `title`;
- `summary`;
- `visible_status`;
- `technical_status`;
- `sensitivity_level`;
- `visibility_scope`;
- `sort_order`;
- `owner_user_id`;
- `created_by_user_id`;
- `updated_by_user_id`;
- `created_at`;
- `updated_at`;
- `closed_at`;
- `archived_at`.

### 7.3 `strategic_tree_contributions`

- `id`;
- `company_id`;
- `tree_id`;
- `node_id`;
- `contribution_type`;
- `source_type`;
- `source_ref`;
- `attribution_mode`;
- `author_user_id`, anulável conforme modalidade;
- `participant_ref`, opaco e restrito quando pseudonimizado;
- `raw_content`;
- `sanitized_content`;
- `classification_json`;
- `confidence_state`;
- `sensitivity_level`;
- `visibility_scope`;
- `status`;
- `created_at`;
- `updated_at`;
- `deleted_at`, apenas por política autorizada.

### 7.4 `strategic_tree_relations`

- `id`;
- `company_id`;
- `tree_id`;
- `source_type`;
- `source_id`;
- `relation_type`;
- `target_type`;
- `target_ref`;
- `status`;
- `confidence_state`;
- `generated_by`;
- `validated_by_user_id`;
- `created_at`;
- `validated_at`.

### 7.5 `strategic_tree_analyses`

- `id`;
- `company_id`;
- `tree_id`;
- `node_id`;
- `analysis_type`;
- `squad`;
- `summary`;
- `facts_json`;
- `hypotheses_json`;
- `contradictions_json`;
- `gaps_json`;
- `options_json`;
- `risks_json`;
- `recommendations_json`;
- `protocol_snapshot_json`;
- `created_by_user_id`;
- `created_at`.

### 7.6 `strategic_tree_validations`

- `id`;
- `company_id`;
- `tree_id`;
- `node_id`;
- `analysis_id`;
- `validator_role`;
- `status`;
- `notes`;
- `validated_by_user_id`;
- `created_at`;
- `updated_at`.

### 7.7 `strategic_tree_decisions`

- `id`;
- `company_id`;
- `tree_id`;
- `node_id`;
- `decision`;
- `rationale`;
- `assumptions_json`;
- `accepted_risks_json`;
- `rejected_options_json`;
- `next_actions_json`;
- `decided_by_user_id`;
- `decided_at`;
- `status`.

### 7.8 `strategic_tree_audit_events`

Registra criação, classificação, movimentação, relacionamento, visualização sensível, validação, decisão, exportação, anonimização, retenção e exclusão.

## 8. Constraints e multi-tenancy

1. toda tabela tenant-owned possui `company_id NOT NULL`;
2. árvore, nó, contribuição, análise, validação e decisão devem possuir a mesma empresa;
3. `parent_node_id` pertence à mesma árvore e empresa;
4. relação tenant-owned não cruza empresas;
5. target externo exige adapter e validação de tenant;
6. repository e service recebem `company_id` explicitamente;
7. ID isolado não autoriza acesso;
8. exclusão de árvore não apaga fonte canônica relacionada;
9. conteúdo confidencial não entra em log de aplicação;
10. testes cross-tenant são gate de release.

## 9. Taxonomias iniciais

### 9.1 `node_type`

- `root`;
- `theme`;
- `subtheme`;
- `investigation`;
- `decision`;
- `unfolding`;
- `parked`.

### 9.2 `contribution_type`

- `human_statement`;
- `consultant_perception`;
- `operational_fact`;
- `documentary_evidence`;
- `ai_hypothesis`;
- `external_benchmark`;
- `question`;
- `proposal`;
- `contradiction`;
- `risk`;
- `recommendation`;
- `decision_input`.

### 9.3 Estados visíveis

- `collecting` — Coletando informações;
- `analyzing` — Analisando;
- `ready_to_discuss` — Pronto para discutir;
- `awaiting_decision` — Aguardando sua decisão;
- `in_execution` — Em execução;
- `completed` — Concluído;
- `parked` — Estacionado.

### 9.4 Estados técnicos

- `captured`;
- `classified`;
- `contextualized`;
- `evidenced`;
- `analyzed`;
- `validated`;
- `decided`;
- `linked_to_canonical`;
- `verified`;
- `rejected`;
- `superseded`;
- `archived`.

O orquestrador controla estados técnicos. O usuário não os administra manualmente.

## 10. Atribuição, confidencialidade e anonimato

### 10.1 Modos

- `identified`;
- `confidential`;
- `pseudonymized`;
- `anonymous`.

### 10.2 MVP

O MVP suporta:

- identificado;
- confidencial;
- pseudonimização somente quando o armazenamento separado e os controles estiverem implementados e testados.

`anonymous` permanece feature-flagged e indisponível até existir threat model, política de logs, retenção, mitigação de reidentificação e validação jurídica. A interface não pode prometer anonimato enquanto esses requisitos não forem satisfeitos.

### 10.3 Visibilidade

Valores iniciais:

- `author_only`;
- `branch_members`;
- `consultant`;
- `squad_client`;
- `squad_versus`;
- `company_authorized`.

Visibilidade não substitui grants. O backend calcula interseção entre papel, capability, vínculo com a árvore, sensibilidade e regra da contribuição.

## 11. Papéis

### 11.1 Colaborador ou cliente

- criar contribuição;
- corrigir ou complementar sua contribuição;
- confirmar classificação quando solicitado;
- visualizar conteúdo permitido;
- responder entrevista;
- validar síntese de sua fala quando aplicável.

### 11.2 Consultor

- criar e organizar árvores;
- acessar ramos autorizados;
- relacionar e estacionar temas;
- solicitar pesquisa ou entrevista;
- discutir análises;
- registrar decisão quando autorizado;
- iniciar desdobramento sem promover automaticamente o canônico.

### 11.3 Squad Cliente

- ler ramos autorizados;
- registrar análise da realidade operacional;
- propor classificação e relações;
- identificar convergências, divergências e gaps;
- validar exclusivamente como `squad_client`.

### 11.4 Squad Versus

- ler ramos autorizados;
- registrar análise metodológica;
- confrontar Paper, SPEC, benchmark e realidade;
- sugerir alternativas e sequência de estruturação;
- validar exclusivamente como `squad_versus`.

### 11.5 Squad Engenharia

Participa somente quando houver gap de ferramenta, dados, integração, segurança, performance ou UX. Não valida conteúdo empresarial por padrão.

## 12. Fluxos funcionais

### 12.1 Colaborador registra uma ideia

1. seleciona `Árvore Estratégica`;
2. escolhe árvore ou inicia em `Caixa de entrada`;
3. escreve em linguagem natural;
4. sistema preserva o conteúdo bruto;
5. classificador propõe ramo, tipo e relações;
6. confirmação só é solicitada quando necessária;
7. contribuição aparece no ramo autorizado;
8. síntese do ramo é atualizada de forma derivada.

### 12.2 Conversa abre um novo ramo

1. orquestrador detecta mudança relevante de assunto;
2. propõe ou cria ramo temporário;
3. preserva breadcrumb e ponto de retorno;
4. discussão continua;
5. ao encerrar, registra síntese e pendências;
6. retorna ao foco anterior ou estaciona o ramo.

### 12.3 Squad analisa via MCP

1. runtime resolve ator, empresa, Squad e surface;
2. lista árvores e pendências autorizadas;
3. lê ramo sanitizado conforme grants;
4. consulta evidências adicionais;
5. registra análise separada da contribuição original;
6. registra validação somente de seu próprio Squad;
7. próxima ação é recalculada.

### 12.4 Consultor decide

1. abre Tema Consultivo;
2. revisa fatos, falas, hipóteses, evidências, opções e riscos;
3. solicita aprofundamento ou decide;
4. registra justificativa e riscos aceitos;
5. decisão permanece ligada ao ramo;
6. eventual promoção ocorre em workflow futuro específico.

## 13. API

Prefixo sugerido: `/api/knowledge/strategic-trees`.

### Leituras

- `GET /` — listar árvores autorizadas;
- `GET /<tree_id>` — obter resumo e raiz;
- `GET /<tree_id>/nodes/<node_id>` — obter ramo;
- `GET /<tree_id>/nodes/<node_id>/contributions`;
- `GET /<tree_id>/pending`;
- `GET /<tree_id>/breadcrumb/<node_id>`.

### Escritas

- `POST /` — criar árvore;
- `POST /<tree_id>/contributions` — registrar contribuição;
- `POST /<tree_id>/nodes` — criar ramo;
- `PATCH /<tree_id>/nodes/<node_id>` — atualizar título, ordem ou estado permitido;
- `POST /<tree_id>/nodes/<node_id>/move`;
- `POST /<tree_id>/relations`;
- `POST /<tree_id>/analyses`;
- `POST /<tree_id>/validations`;
- `POST /<tree_id>/decisions`.

Toda escrita exige CSRF quando aplicável, idempotency key, capability, auditoria e verificação de tenant.

## 14. MCP

### 14.1 Tools de leitura

- `strategic_tree_list`;
- `strategic_tree_get`;
- `strategic_tree_get_branch`;
- `strategic_tree_list_pending`;
- `strategic_tree_search_contributions`;
- `strategic_tree_get_next_action`.

### 14.2 Tools de escrita

- `strategic_tree_create`;
- `strategic_tree_add_contribution`;
- `strategic_tree_create_branch`;
- `strategic_tree_move_node`;
- `strategic_tree_relate_items`;
- `strategic_tree_register_analysis`;
- `strategic_tree_register_validation`;
- `strategic_tree_register_decision`.

### 14.3 Regras MCP

1. tools delegam às mesmas services da API;
2. runtime resolve `user_id`, `company_id`, surface e Squad por request;
3. `company_id` explícito é validado contra o contexto autenticado;
4. tools de escrita exigem confirmação humana quando o impacto for material;
5. validação de Squad é limitada ao próprio Squad;
6. contribuição confidencial retorna conteúdo sanitizado conforme papel;
7. nenhuma tool P0 promove objeto canônico;
8. resposta informa `operation`, `company_id`, IDs opacos, estado e próxima ação;
9. idempotência impede duplicação em retry;
10. logs não incluem conteúdo sensível.

## 15. Services e boundaries

### Services propostas

- `StrategicTreeService`;
- `StrategicTreeContributionService`;
- `StrategicTreeClassificationService`;
- `StrategicTreeAnalysisService`;
- `StrategicTreeDecisionService`;
- `StrategicTreeAccessPolicy`;
- `StrategicTreeOrchestrationService`.

### Boundaries

- **rota Flask:** autentica, valida schema, resolve contexto e serializa;
- **service:** aplica regras, estados, autorização e transação;
- **repository:** consulta sempre por `company_id`;
- **MCP:** adapta contrato e delega à service;
- **frontend:** apresenta e coleta interação, sem autorizar;
- **orquestrador:** calcula foco, ramo, pendência e próxima ação;
- **classificador:** propõe, nunca oficializa decisão.

## 16. Compatibilidade com o Sapiens atual

1. adicionar `strategic_tree` aos escopos não altera a semântica de `all`, `company` ou `product`;
2. endpoint atual de busca não recebe mutações da árvore;
3. JavaScript roteia `strategic_tree` para contrato dedicado;
4. histórico de consulta permanece separado do histórico colaborativo;
5. storage local usa chave por `company_id` e escopo;
6. widget e página completa compartilham rótulos e estados;
7. falha da Árvore Estratégica não derruba busca e ajuda do produto;
8. feature flag desabilitada preserva a interface anterior.

## 17. Classificação assistida

Entrada mínima:

- conteúdo;
- árvore e ramo atual, quando houver;
- contexto de tela autorizado;
- papel do ator;
- fontes relacionadas permitidas.

Saída proposta:

```json
{
  "suggested_node_id": 42,
  "suggested_contribution_type": "human_statement",
  "suggested_relations": [],
  "ambiguity": false,
  "clarifying_question": null
}
```

Regras:

- conteúdo original é registrado antes ou junto da classificação em transação segura;
- baixa confiança não bloqueia contribuição, mas envia para caixa de entrada;
- classificador não define autoridade nem maturidade;
- mudança de ramo preserva histórico;
- reclassificação é auditada;
- classificação não amplia visibilidade.

## 18. Orquestração e próxima ação

O orquestrador considera:

- estado do ramo;
- volume e diversidade de contribuições;
- gaps;
- contradições;
- evidências;
- análises;
- validações;
- decisão;
- itens estacionados;
- permissões do ator.

Saídas possíveis:

- coletar informação;
- pedir esclarecimento;
- solicitar evidência;
- pesquisar;
- entrevistar;
- analisar;
- discutir;
- validar;
- decidir;
- acompanhar execução;
- concluir ou estacionar.

Próxima ação é recomendação governada, não execução automática.

## 19. Segurança, privacidade e auditoria

- autenticação e empresa ativa antes da consulta;
- ACL antes da recuperação ou síntese;
- fail closed em ambiguidade de tenant ou grant;
- criptografia em trânsito e repouso conforme infraestrutura oficial;
- conteúdo sensível fora de logs e telemetria;
- exportação auditada;
- retenção por tipo e finalidade;
- eliminação sem quebrar trilha decisória necessária;
- proteção contra prompt injection em documentos e contribuições;
- sanitização antes de enviar a modelo externo;
- contrato aprovado com provedores de IA;
- sem uso disciplinar disfarçado;
- sem promessa falsa de anonimato;
- auditoria de leitura sensível quando aplicável.

## 20. MVP

### P0 — Fundacional

- migrations e modelos;
- repositories tenant-safe;
- services e policy;
- feature flag;
- árvores, nós e contribuições textuais;
- classificação inicial;
- breadcrumb e árvore lateral;
- escopo no Sapiens;
- acesso do consultor;
- tools MCP de leitura e `add_contribution`;
- auditoria;
- testes multi-tenant e RBAC.

### P1 — Maturação

- análises de Squad;
- validações;
- decisão do consultor;
- próxima ação;
- síntese por ramo;
- relações com objetos canônicos;
- entrevistas textuais;
- confidencialidade avançada.

### P2 — Expansão

- pseudonimização robusta e anonimato validado;
- áudio, gravação e transcrição;
- anexos e OCR;
- pesquisa externa estruturada;
- WhatsApp e e-mail;
- visualização ampliada do grafo;
- workflows de promoção canônica;
- indicadores de valor e aprendizado.

## 21. Critérios de aceite do P0

1. usuário autorizado vê `Árvore Estratégica` no Sapiens;
2. feature flag desligada preserva a interface atual;
3. colaborador registra contribuição em linguagem natural sem preencher taxonomia;
4. contribuição original permanece íntegra;
5. classificação propõe ramo ou utiliza caixa de entrada;
6. consultor autorizado vê árvore, breadcrumb e resumo;
7. usuário não autorizado não descobre existência de árvore ou ramo;
8. tentativa cross-tenant falha sem vazamento;
9. MCP consegue listar árvore e registrar contribuição autorizada;
10. retry com mesma idempotency key não duplica contribuição;
11. nenhum fluxo P0 altera objeto canônico;
12. busca atual de Minha Empresa e APP Versus continua passando nos testes;
13. interface funciona em desktop e mobile;
14. logs não expõem conteúdo confidencial;
15. auditoria registra toda escrita e mudança de classificação.

## 22. Testes obrigatórios

### Unitários

- taxonomias;
- transições de estado;
- classificação;
- policy;
- idempotência;
- sanitização.

### Integração

- criação de árvore e ramo;
- contribuição via API;
- contribuição via MCP;
- classificação e reclassificação;
- relações;
- grants;
- feature flag;
- transações e rollback.

### Segurança

- cross-tenant;
- IDOR;
- CSRF;
- RBAC;
- validação de Squad próprio;
- conteúdo confidencial em logs;
- prompt injection;
- reidentificação nos modos suportados.

### UX

- contribuição em menos de três ações;
- navegação e retorno de ramo;
- primeira viewport útil;
- responsividade;
- teclado e leitor de tela;
- diferenciação clara entre fala, hipótese, análise e decisão.

### Regressão

- Sapiens `all`;
- Sapiens `company`;
- Sapiens `product`;
- widget global;
- página completa;
- Camada de Conhecimento e `product_help`.

## 23. Observabilidade

Métricas iniciais:

- árvores ativas por empresa;
- contribuições por ator, ramo e tipo;
- tempo até classificação;
- taxa de ambiguidade;
- perguntas de esclarecimento;
- ramos abertos, estacionados e concluídos;
- tempo até discussão e decisão;
- contribuições via APP32 e MCP;
- erros de permissão;
- tentativas cross-tenant;
- uso por Squad;
- feedback de utilidade;
- itens relacionados a objetos canônicos.

Telemetria não armazena conteúdo bruto.

## 24. Rollout

1. desenvolver com feature flag desligada;
2. validar migrations e segurança localmente;
3. habilitar somente para `company_id = 9`;
4. criar árvore piloto `Reestruturação da Versus`;
5. registrar o conhecimento já produzido na conversa piloto;
6. validar experiência com consultor;
7. testar MCP com Squad Cliente;
8. corrigir classificação, árvore e síntese;
9. habilitar análise do Squad Versus quando disponível;
10. somente depois avaliar expansão para outros tenants.

## 25. Fora do P0

- gravação e transcrição de áudio;
- anonimato não verificável;
- promoção automática para objeto canônico;
- execução financeira, contratual ou disciplinar;
- treinamento autônomo do modelo com conteúdo do cliente;
- acesso irrestrito do consultor a contribuições confidenciais;
- geração de decisão sem gate humano;
- GraphRAG completo;
- novo módulo isolado no sidebar.

## 26. Decisão final da SPEC

A Árvore Estratégica será uma nova capability colaborativa do domínio `knowledge`, acessada pelo Sapiens e integrada ao MCP.

Ela permitirá registrar ideias e conhecimento em linguagem natural, organizar a conversa em árvore, relacionar os temas em grafo e amadurecer contribuições por análise, validação e decisão.

O MVP prioriza texto, simplicidade, segurança, multi-tenancy, rastreabilidade e compatibilidade com o Sapiens atual. Nenhuma contribuição se torna verdade canônica ou altera a empresa sem workflow e autorização específicos.

## 27. Evidência de implementação do P0

Implementado localmente em 2026-08-02:

- modelos, migration e feature flag por empresa;
- repository e services com `company_id` obrigatório;
- classificação determinística inicial e Caixa de entrada;
- API web com empresa da sessão, CSRF, idempotência e auditoria;
- quarto escopo responsivo no Sapiens;
- tools MCP `strategic_tree_list`, `strategic_tree_get`, `strategic_tree_get_branch` e `strategic_tree_add_contribution`;
- human gate para escrita MCP;
- testes de serviço, cross-tenant, confidencialidade, API, CSRF, catálogo e MCP.

O rollout permanece restrito à empresa piloto `company_id = 9` e depende de migration e deploy controlados.
