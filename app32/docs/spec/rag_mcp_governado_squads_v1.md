# SPEC — RAG MCP Governado para Squad Cliente e Squad Versus (v1)

**Status:** esqueleto arquitetural — não habilita ingestão, embeddings ou novas permissões em produção.  
**Owner:** Arquitetura / Backend Service / AI Engineer  
**Princípio:** MCP é a superfície operacional; RAG é recuperação de evidência autorizada, nunca uma fonte de autorização ou executor de regras.

## 1. Objetivo

Disponibilizar à IA, de forma rastreável e isolada por tenant:

1. conhecimento sobre o produto Gestão Versus;
2. conhecimento operacional da empresa, incluindo POPs publicados;
3. dados internos vivos por tools MCP tipadas; e
4. pesquisas externas controladas, com origem e data.

O resultado deve responder com evidências e nunca permitir que texto recuperado altere identidade, `company_id`, RBAC, escopo de tool ou política de mutação.

## 2. Fronteiras obrigatórias

| Camada | Responsabilidade | Não pode fazer |
| --- | --- | --- |
| OAuth / contexto MCP | Validar token, resolver `user_id`, `company_id`, papel e surface | Aceitar tenant ou papel informado pelo prompt/payload |
| Policy/RBAC | Autorizar ferramenta e fonte antes da recuperação | Delegar autorização ao modelo ou a metadados não validados |
| RAG | Recuperar e ordenar trechos já autorizados | Executar ações, decidir alçadas ou substituir consulta de dados vivos |
| Tools MCP / services | Consultar estado operacional e executar mutações validadas | Usar resposta do RAG como autorização |
| Orquestrador IA | Compor resposta citada e decidir se chama tool | Expor conteúdo sem evidência ou ignorar abstention |

## 3. Perfis de exposição

### 3.1 Squad Cliente

- Surface: `user` (e `analytics` somente quando o token possuir escopo explícito de leitura analítica).
- Recupera: `product`, e `company` cujo `company_id` seja o resolvido pelo token.
- Pode consultar POP, reunião e manual publicados para sua empresa conforme grants e RBAC.
- Não recupera conhecimento interno da Versus, documentos de outro tenant, credenciais, prompts internos, nem ferramentas administrativas/de deploy.

### 3.2 Squad Versus

- Surfaces: `admin`, `analytics`, `ops` e `finance`, conforme registry canônico e papel real do colaborador.
- Recupera conhecimento interno da Versus apenas quando a classificação e a permissão concederem acesso.
- Acesso a informações de clientes continua explicitamente delimitado por `company_id`, vínculo de atendimento e domínio; não existe busca global por conveniência.
- `analytics` permanece somente leitura; `finance` não é publicado em `user`; operações sensíveis requerem tool específica, confirmação e audit trail.

## 4. Coleções lógicas e metadados mínimos

| Coleção | Escopo | Exemplos | Regra de acesso |
| --- | --- | --- | --- |
| `system` | produto/global | manual, catálogo de módulos, guia MCP | leitura autenticada permitida pelo surface |
| `company` | tenant | POPs, fluxos publicados, atas, políticas | `company_id` do contexto + grant + RBAC |
| `versus_internal` | interno | playbooks, padrões de consultoria | RBAC Versus; nunca publicado ao cliente |
| `external` | controlado | fontes públicas, normas, pesquisas | conector permitido, classificação e citação obrigatórias |

Todo `source` e todo `chunk` devem portar, no mínimo: `knowledge_scope`, `company_id` (quando aplicável), `source_type`, `source_ref`, `canonical_uri`, `classification`, `authority_level`, `status`, `version`, `valid_from`, `valid_to`, `source_updated_at`, checksum e política de chunking. O índice vetorial replica esses metadados para que o filtro ocorra **antes** da similaridade.

## 5. Contratos MCP iniciais

Os tools não recebem `company_id`, papel ou surface como parâmetros. Estes valores são exclusivamente derivados por `resolve_mcp_execution_context`.

```text
answer_product_help(question, limit=3)
search_organizational_knowledge(question, limit=5)
answer_organizational_question(question, limit=5)
```

Extensões propostas, ainda sem publicação:

```text
search_external_evidence(question, source_policy, limit=5)     # leitura, citações obrigatórias
get_knowledge_source(source_ref)                               # somente se autorizado
request_knowledge_ingestion(source_ref, classification, ...)   # mutação, workflow/aprovação
```

As respostas possuem `query_id`, plano de busca, evidências/citações, versão e avisos. Sem evidência autorizada, retornam abstention; não inventam uma resposta.

## 6. Modelo de recuperação híbrida

1. Contexto OAuth/MCP resolve identidade, company e surface.
2. Policy constrói filtros imutáveis de tenant, classificação, vigência, grants e fontes permitidas.
3. Recuperação lexical PostgreSQL (FTS) e vetorial PostgreSQL/`pgvector` ocorre somente dentro do conjunto autorizado.
4. Re-ranking privilegia fonte oficial, vigente, específica e mais recente.
5. O orquestrador combina evidências com dados vivos vindos de tools MCP, mantendo cada origem separada.
6. A resposta apresenta citações e registra a interação para auditoria/feedback.

O atual repositório `knowledge_sources`/`knowledge_chunks` e o `KnowledgeQueryService` constituem a fundação relacional. A evolução para `pgvector` substituirá o armazenamento vetorial legado somente mediante migração, backfill, teste de paridade e plano de rollback; SQLite e Chroma não são arquitetura alvo.

## 7. Ingestão e segurança de conteúdo

- Somente fontes cadastradas por adapter são ingeríveis.
- POP entra apenas quando publicado, versionado e vigente; rascunhos ficam fora da recuperação padrão.
- Sanitizar HTML/arquivos, detectar segredos e PII indevida, calcular checksum e preservar a origem.
- Conteúdo é **dados não confiáveis**: instruções nele contidas não podem alterar prompt do sistema, políticas, chamadas de tools ou configuração.
- Mudança, exclusão, expiração e reindexação são auditadas em `knowledge_index_runs` e devem preservar a reversibilidade da versão anterior.

## 8. Dados internos e pesquisa externa

Dados internos de ERP, financeiro, projetos ou pessoas são consultados por tools MCP de domínio com schema/RBAC; não são copiados integralmente para embeddings. Pesquisa externa passa por conector allowlisted, registra URL, título, data de coleta, licença/classificação e trechos citados. Resultado externo não é promovido a POP ou verdade operacional sem aprovação humana.

## 9. Critérios de aceite da primeira entrega

1. Uma busca no Squad Cliente não recupera chunk, título nem metadado de outra empresa.
2. Uma busca sem empresa ativa para escopo corporativo falha de modo seguro.
3. `system` e POP vigente retornam `canonical_uri`, versão e trecho de origem.
4. A tool não aceita `company_id` no schema público e o log contém `query_id`, identidade, surface, escopo e fontes retornadas.
5. Texto com tentativa de prompt injection é tratado como conteúdo, sem alterar ferramentas permitidas.
6. Testes PostgreSQL comprovam filtro anterior à busca vetorial e paridade básica com FTS.

## 10. Entregas incrementais

1. Consolidar contratos, classificação e fontes `system`/`company` já existentes.
2. Introduzir `pgvector` e recuperação híbrida sob feature flag, com migração e backfill auditável.
3. Publicar o catálogo por surface para Squad Cliente e Squad Versus, com testes de RBAC/tenant.
4. Adicionar conector externo governado e workflow de curadoria, sem misturar suas evidências aos dados internos.

## 11. Fora de escopo desta SPEC inicial

- autonomia para mutar dados a partir de conteúdo recuperado;
- acesso cross-tenant;
- ingestão automática de qualquer upload ou URL;
- substituição das regras determinísticas de serviços por prompt ou RAG.

## 12. Baseline verificado — continuidade do que já existe

Esta SPEC não inicia uma base RAG do zero. Ela consolida e direciona a evolução da
Camada de Conhecimento Corporativo já definida em
`docs/spec/arquitetura_oficial_camada_conhecimento_corporativo_app_versus_v1.md`.
O estado abaixo foi verificado no código em 2026-09-24; o documento canônico de
conhecimento mantém o detalhamento histórico e funcional.

| Capability | Estado atual verificável | Continuidade nesta SPEC |
| --- | --- | --- |
| Projeção de conhecimento | `KnowledgeSource`, `KnowledgeChunk`, `KnowledgeSourceGrant`, `KnowledgeIndexRun`, `KnowledgeInteraction`, feedback e propostas de treinamento | preservar como núcleo relacional; evoluir sem duplicar uma segunda base de conhecimento |
| Isolamento e ACL | `company_id` em fontes/chunks, grants por empresa/usuário/colaborador e contexto MCP sem `company_id` no schema público | aplicar o mesmo gate a todo retrieval futuro, inclusive vetor e fontes externas |
| Recuperação atual | `KnowledgeQueryService` filtra status, vigência, exclusão e autorização antes do PostgreSQL full-text; entrega claims, citações e abstenção | acrescentar vetor e re-ranking ao plano híbrido, não substituir o fluxo existente |
| Fontes registradas | adapters de `product_help`, `system_documentation`, `process_publication` e `meeting` | ampliar por adapters versionados, uma fonte por onda e com contrato/testes |
| MCP/Sapiens | tools de produto e conhecimento organizacional estão no catálogo LangChain e no registry MCP | manter os mesmos contratos de leitura e publicar extensões somente pelo registry de surfaces |
| Operação e aprendizagem | sincronização por checksum, ledger de indexação, feedback, treinamento supervisionado e golden set | medir qualidade antes/depois e manter aprovação humana para qualquer ajuste de comportamento |

### 12.1 O que já está atendido

- `product_help` e `system_documentation` separam orientação do APP de
  conhecimento corporativo; o primeiro é global e o segundo indexa material
  técnico elegível.
- `process_publication` indexa somente a publicação mais recente com status
  `published`, preservando versão, URI, vigência e grants.
- `meeting` indexa somente reuniões elegíveis e falha fechada quando a concessão
  para participantes internos não puder ser resolvida.
- A recuperação atual já registra `query_id`, plano, fontes, citações, avisos e
  ações de navegação derivadas de metadados cadastrados.
- Há testes de contrato para migration, repository, adapters, atualização,
  scheduler, query, MCP, Sapiens, feedback e treinamento.

### 12.2 Lacunas reais a tratar sem reimplementar o núcleo

1. **Semântica:** não há `pgvector`, embeddings versionados ou re-ranking
   semântico produtivo. O componente Chroma legado em `src/intelligence/rag.py`
   é experimental e não deve ser integrado a novas superfícies.
2. **Cobertura de fontes:** processos publicados e reuniões já estão cobertos;
   instâncias de processo, projetos, atividades, estratégia, indicadores,
   anexos e conectores externos permanecem ondas futuras.
3. **QueryPlan:** o plano atual é seguro e auditável, mas inicia com `sql` e
   `full_text`. Ele precisa evoluir para estratégias tipadas `vector`,
   `relationship_graph` e `hybrid`, sempre validadas pelo backend.
4. **Temporalidade e governança:** parte dos campos conceituais canônicos —
   supersessão explícita, bitemporalidade completa, labels de segurança,
   quarentena, checksum de ACL e geração de índice — ainda requer modelagem e
   migração própria.
5. **Surfaces de squads:** as surfaces técnicas atuais são `user`, `admin`,
   `analytics`, `ops` e `finance`. `squad_cliente` e `squad_versus` são perfis
   de exposição/política sobre elas, não novos valores livres recebidos do
   cliente.

## 13. Plano de ajuste e evolução

### P0 — consolidar e proteger o existente

- Declarar `services/knowledge` e suas tabelas como única projeção RAG
  corporativa; impedir qualquer novo uso produtivo do Chroma legado.
- Criar uma auditoria de paridade entre catálogo, registry MCP, capabilities,
  RBAC, grants e adapters, falhando fechada em drift.
- Publicar o catálogo de conhecimento permitido por surface e perfil de squad,
  sem introduzir `company_id` em payload.
- Executar os testes existentes em PostgreSQL de integração e registrar uma
  baseline do golden set antes de alterar ranking ou planejamento.

### P1 — recuperação híbrida PostgreSQL

- Adicionar extensão `pgvector`, coluna de embedding, modelo/versão, geração de
  índice e migration reversível, sob feature flag desligada.
- Fazer backfill por checksum, com fila/ledger e rollback que apenas descarte a
  projeção vetorial, nunca a fonte soberana.
- Filtrar `company_id`, grants, classificação, vigência e status na consulta
  PostgreSQL antes de calcular distância vetorial; combinar FTS + vetor por
  ranking explícito e citável.
- Comparar precisão, isolamento e latência com o golden set; só então habilitar
  uma empresa piloto autorizada.

### P2 — fontes e dados vivos

- Implementar adapters, nesta ordem: instâncias de processo, projetos e
  atividades, estratégia/indicadores, depois anexos curados.
- Para perguntas de estado atual, prazo, responsável, saldo ou contagem, o
  orquestrador chama a tool MCP do domínio; a resposta separa claramente dado
  vivo de evidência RAG.
- Adicionar relações determinísticas entre POP, decisão, processo, projeto e
  indicador antes de considerar GraphRAG. GraphRAG completo continua fora do
  escopo.

### P3 — pesquisa externa governada

- Incluir somente conectores allowlisted e adapters que preservem URL, data de
  coleta, identidade do conector, classificação, licença, checksum e política
  de expiração/exclusão.
- Manter resultados externos em escopo `external` separado, sem promoção
  automática a procedimento, política ou fato interno.
- Exigir citação e sinalização visual de origem externa em toda afirmação que a
  utilize.

## 14. Ajuste do modelo de escopo

O modelo atual usa `product` e `company`, o que é suficiente para o MVP vigente.
As coleções `versus_internal` e `external` desta SPEC são **extensões futuras**:
não devem ser simuladas como `product`, nem adicionadas sem migration, regras de
ACL, classificação e testes próprios. Até essa evolução, o Squad Versus utiliza
somente fontes e tools já autorizadas pelas surfaces canônicas; o Squad Cliente
continua limitado ao produto e à empresa ativa.

## 15. Gates para avançar de fase

1. Nenhum chunk, embedding, título ou metadado de outro tenant aparece em
   testes negativos, inclusive pela rota vetorial.
2. Nenhuma fonte externa ou interna Versus chega ao Squad Cliente por fallback,
   cache, citação ou mensagem de erro.
3. Cada resposta híbrida distingue fonte RAG, tool MCP e origem externa, com
   versão/data/URI quando aplicável.
4. A migração `pgvector`, o backfill e o rollback são ensaiados em PostgreSQL
   antes de piloto.
5. Feedback e golden set não modificam ranking, embeddings ou conteúdo sem
   curadoria/aprovação humana.

## 16. Evidência de entrega — P0/P1 (2026-09-24)

**Decisão oficial:** `services/knowledge` + tabelas `knowledge_*` são a única projeção RAG
corporativa. O Chroma legado (`src/intelligence/rag.py`) não é usado por nenhuma superfície
nova; o conjunto de importadores existentes está congelado por teste.

### 16.1 Entregue (ativo)

| Item | Onde | Verificação |
| --- | --- | --- |
| Universo autorizado único (`authorized_universe_conditions`): tenant, grants, status, vigência, exclusão e coerência fonte↔chunk (drift de `company_id`/escopo falha fechado) | `services/knowledge/query_service.py` | `tests/test_knowledge_rag_governance.py` |
| `QueryPlan` com `requested_strategy`, `fallback_reason` e `evidence_origin` (`rag`); `strategies` continua `["sql","full_text"]` | `query_service.py`, `retrieval_strategy.py` | `tests/test_knowledge_vector_skeleton.py` |
| `evidence_origin` em toda citação/hit (`rag` \| `live_mcp` \| `external`) | `retrieval_strategy.EvidenceOrigin` | idem |
| Paridade catálogo × registry × capabilities × surfaces (sem `finance`/`ops`; `analytics` só busca/resposta corporativa; sem `company_id`/papel/surface/squad em parâmetros) | — | `test_knowledge_surface_and_rbac_parity` |
| Guarda anti-Chroma/SQLite na camada de conhecimento e congelamento dos importadores legados | — | `test_projection_layer_*`, `test_legacy_chroma_importers_*` |
| Negativos: cross-tenant FTS, sem `company_id`, grants user/employee, fonte expirada/futura/removida/rascunho, drift, prompt injection inerte, escopo `versus_internal` recusado pelo schema | — | `test_knowledge_rag_governance.py` |

### 16.2 Entregue sob feature flag (desligada; nada executa vetor)

- `KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED` (padrão desligada) + `KNOWLEDGE_EMBEDDING_MODEL`,
  `KNOWLEDGE_EMBEDDING_VERSION`, `KNOWLEDGE_EMBEDDING_INDEX_GENERATION`. Sem os quatro, a
  configuração não fica pronta. `KnowledgeQueryService` só executa vetor/híbrido com flag + modelo/versão/geração **e** um
  `embedding_provider` injetado no construtor (nenhum é injetado em produção; nenhum provedor foi
  escolhido). Sem eles, `vector`/`hybrid` recuam para FTS com `fallback_reason`
  (`vector_retrieval_disabled` | `embedding_provider_missing`); `relationship_graph` recua com
  `relationship_graph_not_available`. Falha do provedor/SQL vetorial recua para FTS com o aviso
  `vector_retrieval_failed`, sem expor o erro. As tools públicas **não** expõem `strategy`.
- Migration `20260924_1400` (encadeada em `20260924_1300`): cria só
  `knowledge_chunk_embeddings` (`vector(1536)`, FK `ON DELETE CASCADE`, `company_id`/escopo com
  CHECK, checksum do chunk, modelo/versão/geração). Falha com mensagem clara se `pgvector` não
  existir; sem backfill; sem índice ANN (busca exata dentro do universo filtrado — HNSW só após
  medição no golden set). `downgrade` remove apenas a projeção e mantém a extensão.
  `knowledge_sources`/`knowledge_chunks` (company_id, grants, status, vigência, origem,
  checksum) permanecem intactas e soberanas; status/vigência/grants **não** são replicados na
  projeção para não gerar drift de ACL.
- `services/knowledge/vector_retrieval.py`: statement cosseno que aplica o mesmo universo
  autorizado + geração/modelo + checksum não obsoleto **antes** do `ORDER BY` por distância.
  O serviço o usa via `_vector_rows` (PostgreSQL) e une FTS+vetor em `_merge_hybrid` com `HybridRankingPolicy`; testado com fetcher injetado (SQLite), não contra pgvector real.
- `HybridRankingPolicy`: autorização/vigência/status são *gates*; pesos explícitos para
  autoridade, FTS, similaridade vetorial e recência (sem vetor, o peso é redistribuído).

### 16.3 Não verificado / pendente

1. Migration e rollback **não** foram executados contra PostgreSQL com pgvector (extensão
   ausente no PG 14 local). Verificado: caminho de falha clara e contratos estáticos; o teste
   `test_postgres_vector_isolation_and_rollback_roundtrip` exige
   `APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL` (cluster descartável, porta ≠ 5432, banco `*_test`).
2. Dimensão 1536 e provedor/modelo de embedding aguardam decisão (Vertex AI proibido).
3. `20260924_1400` depende da revision `20260924_1300` (deploy de agentes, ainda não
   commitada): as duas devem seguir juntas.
4. Testes com `pytest-flask` local falham na coleta (`_request_ctx_stack`); usar `-p no:flask`.

### 16.4 Próximo passo (piloto controlado)

Ensaiar upgrade/downgrade em PG com pgvector → job de backfill por checksum com ledger em
`knowledge_index_runs` (fila, sem chamada em massa) → ligar consulta vetorial + `HybridRankingPolicy`
ao serviço → golden set (precisão, isolamento, latência) → habilitar uma empresa piloto
autorizada por flag por tenant → só então avaliar HNSW.

### 16.5 Medição de consumo de embeddings (2026-09-24)

`services/knowledge/embedding_usage.py` registra tokens por execução em
`knowledge_index_runs.metadata_json["embedding_usage"]` (modelo, versão, geração, requisições,
tokens, `estimated`), sem migration e sem guardar texto. O `company_id` é o da própria
execução (nulo = manual do produto, custo da plataforma). `summarize_embedding_usage()` agrega
por empresa; o custo em USD só é calculado se `KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD` (ou o
parâmetro) for informado. Sem relatório de privacidade/contrato de provedor nesta etapa
(decisão adiada). O job de backfill deve envolver o provedor em `MeteredEmbeddingProvider` e
chamar `record_embedding_usage`.

### 16.6 Eventos de consumo com data/hora (2026-09-24)

Migration `20260924_1500` (após `20260924_1400`) cria `knowledge_embedding_usage_events`: um
registro por chamada de embedding, com `occurred_at` (UTC), `company_id`, `user_id`, `kind`
(`index` \| `query`), `run_id`/`query_id` opcionais, modelo/versão/geração, `tokens` e
`estimated`. **Nunca guarda o texto** da pergunta ou do documento. Consultas híbridas gravam um
evento `query` por chamada (conexão própria; falha de medição não afeta a resposta); a
indexação grava um evento `index` ao registrar o uso da execução.
`query_usage_events(company_id, kind, since, until)` agrega por empresa/tipo/dia, com custo se o
preço estiver configurado. Ainda sem tela/tool MCP para consulta (somente serviço). Migration
não aplicada em nenhum banco real; coberta por testes em SQLite e contrato estático.

### 16.7 Adapter OpenAI e backfill manual (2026-09-24)

- `openai_embedding_provider.py`: `text-embedding-3-small` (1536 dim). Chave só via
  `OPENAI_API_KEY` no ambiente; SDK importado tardiamente; nada é chamado na construção. Devolve
  o uso real de tokens (estimativa marcada quando o provedor não informa).
- `embedding_backfill_service.py` + `scripts/knowledge_embedding_backfill.py`: **manual**, nunca
  agendado. Padrão é simulação (`dry_run`, sem chamada externa). Execução exige `--execute`,
  flag/modelo/versão/geração configurados e limite (`--max-chunks`, padrão 50, máx. 500).
  **Somente `product_help`** (escopo `product`, `company_id` nulo): qualquer outra fonte é
  recusada até a decisão de privacidade/contrato (adiada). Idempotente por checksum; substitui
  vetor obsoleto da mesma geração; registra execução em `knowledge_index_runs`
  (`trigger_kind=manual_embedding_backfill`) e evento de consumo com data/hora; falha grava
  `failed` sem detalhe do provedor.
- Não executado contra OpenAI nem contra pgvector reais; testado com provedor/escritor falsos.

### 16.8 Ensaio em PostgreSQL com pgvector real (2026-09-24)

Executado em contêiner descartável `pgvector/pgvector:pg16` (127.0.0.1:55432, banco
`knowledge_vector_test`) com `scripts/knowledge_vector_rehearsal.py`: upgrade `1400`+`1500`,
consulta vetorial com isolamento por tenant (empresa 1 só vê o seu; empresa 2 só o seu, com
vetores idênticos), descarte de vetor com checksum obsoleto e rollback que remove apenas a
projeção (fontes/chunks e extensão preservados) — todas as verificações `OK`. Isto substitui a
pendência 16.3(1) para PostgreSQL 16; **não** cobre o PostgreSQL 14 de produção (confirmar
disponibilidade da extensão no servidor) nem chamadas reais à OpenAI.

### 16.9 Backfill contra pgvector real, com provedor falso (2026-09-24)

No mesmo contêiner de teste: simulação (3 trechos pendentes, tokens estimados), execução limitada
(2 + 1 trechos), reexecução sem pendências (nenhuma chamada), 3 vetores gravados com 1536
dimensões, 2 execuções no ledger `manual_embedding_backfill` e 2 eventos de consumo datados (UTC)
com custo calculado a partir do preço informado. Provedor **falso**: nenhuma chamada à OpenAI foi feita.
