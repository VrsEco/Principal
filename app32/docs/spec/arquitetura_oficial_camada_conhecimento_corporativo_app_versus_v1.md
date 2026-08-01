# SPEC — Camada de Conhecimento Corporativo do APP Versus v1

**Classe documental:** SPEC
**Status:** canônico
**Data:** 2026-07-30
**Domínio canônico:** `knowledge`
**Natureza inicial:** leitura, tenant-safe e MCP First
**Especialistas líderes:** `@ARQUITETO`, `@AI_ENGINEER`
**Apoios:** `@BACKEND_SERVICE`, `@BACKEND_API`, `@DBA`, `@FRONTEND`, `@QA_AUTOMATION`
**Paper de origem:** `docs/papers/paper_camada_conhecimento_corporativo_extensivel_v1.md`

## 1. Objetivo oficial

Definir o contrato funcional, arquitetural, de segurança e de evolução da Camada de Conhecimento Corporativo do APP Versus.

A capability deve transformar dados estruturados, documentos, decisões e evidências autorizadas em respostas:

- objetivas;
- rastreáveis;
- temporalmente corretas;
- sensíveis à autoridade da fonte;
- extensíveis;
- simples para o usuário;
- isoladas por empresa e permissão.

## 2. Decisão oficial

Ficam congeladas as seguintes decisões:

1. o domínio canônico é `knowledge`;
2. Sapiens é a porta conversacional principal;
3. a busca global do APP Versus reutiliza o mesmo domínio;
4. PostgreSQL é a fonte da projeção, filtragem, full-text search e relações;
5. `pgvector` é o alvo para similaridade semântica no mesmo perímetro PostgreSQL;
6. nenhuma busca vetorial substitui SQL determinístico;
7. toda fonte tenant-owned resolve `company_id` antes da recuperação;
8. ACL é aplicada antes de qualquer conteúdo chegar ao modelo;
9. falha de ACL ou freshness não tolerada resulta em `fail closed`;
10. toda afirmação material possui citação;
11. conflito e insuficiência de evidência são exibidos;
12. fonte operacional original permanece soberana;
13. o índice é uma projeção descartável e reconstruível;
14. novas fontes entram por adaptador registrado;
15. `product_help` é uma fonte global separada dos dados da empresa;
16. o MVP é somente leitura;
17. mutações permanecem nos domínios proprietários e workflows oficiais;
18. a interface comum não expõe termos técnicos de retrieval;
19. robustez pertence ao núcleo; simplicidade pertence à superfície;
20. não será criado um novo agente exclusivo no MVP.

## 3. Nome do produto e identificadores técnicos

O nome funcional e de marca é **APP Versus**.

Identificadores existentes de repositório, package, diretório, ambiente ou integração que utilizem `app32` permanecem inalterados até plano formal de migração técnica. A troca de marca não autoriza renomeação massiva de paths, imports, bancos, variáveis ou infraestrutura.

## 4. Escopo funcional

### 4.1 Incluído

- pergunta em linguagem natural;
- busca por palavras-chave;
- consultas determinísticas;
- busca textual e semântica;
- relações entre objetos;
- respostas citadas;
- fonte, versão, status e vigência;
- detecção de conflito;
- abstenção por falta de evidência;
- refinamento opcional;
- histórico individual de consultas;
- feedback;
- registro de lacuna;
- cockpit de curadoria;
- manual interativo do APP Versus;
- navegação assistida;
- tours guiados;
- telemetria e avaliação.

### 4.2 Fora do MVP

- mutação autônoma de fonte;
- aprovação automática;
- alteração automática de POP, decisão, projeto ou estratégia;
- indexação indiscriminada de e-mails e arquivos pessoais;
- conectores sem preservação de ACL;
- GraphRAG completo;
- Elasticsearch;
- agente autônomo de pesquisa;
- resposta factual sem citação;
- execução financeira ou contratual;
- renomeação técnica global de `app32`.

## 5. Contrato de experiência

### 5.1 Porta única

O usuário começa por uma única caixa que aceita pergunta ou termos.

Não é obrigatório escolher:

- modo;
- fonte;
- agente;
- tabela;
- tipo de busca;
- tecnologia.

### 5.2 Comportamentos internos

O sistema seleciona automaticamente:

- `find`: localizar objeto conhecido;
- `answer`: responder objetivamente;
- `investigate`: cruzar fontes, relações e períodos.

O comportamento selecionado pode ser informado de forma simples, como `Busca rápida` ou `Investigação aprofundada`.

### 5.3 Divulgação progressiva

A primeira camada mostra:

1. resposta direta;
2. confiança operacional;
3. ressalva crítica;
4. ação principal.

Sob demanda:

- evidências;
- fontes;
- filtros;
- histórico;
- relações;
- comparação de versões;
- detalhes da recuperação.

### 5.4 Composição da resposta

Ordem canônica:

1. `answer`;
2. `trust_signals`;
3. `claims`;
4. `warnings`;
5. `related_objects`;
6. `actions`;
7. `feedback`.

### 5.5 Sinais de confiança

São sinais explicáveis:

- `official`;
- `published`;
- `verified`;
- `historical`;
- `unverified`;
- `superseded`;
- `conflicted`;
- `insufficient_evidence`.

É proibido apresentar apenas um percentual genérico de “confiança da IA”.

## 6. Sapiens e busca global

### 6.1 Front door

O botão do Sapiens abre painel lateral sem remover o usuário da página atual.

O painel oferece:

- `Minha empresa`;
- `Como usar o APP Versus`;
- `Todos`, quando combinação for útil e autorizada.

### 6.2 Contexto de tela

O frontend pode enviar:

- `route_key`;
- `module_key`;
- `object_type`;
- `object_ref`;
- versão do produto;
- idioma.

O backend resolve:

- usuário;
- empresa ativa;
- surface;
- perfil;
- capabilities;
- grants.

O contexto de tela:

- é visível;
- pode ser removido;
- é sugestão, não autorização;
- nunca substitui `company_id`;
- nunca limita fontes silenciosamente.

### 6.3 Continuidade de experiência

Painel Sapiens, busca global, página de histórico e canais externos devem usar o mesmo contrato de resposta.

## 7. Escopos de conhecimento

`knowledge_scope` é obrigatório:

| Valor | Conteúdo |
|---|---|
| `company` | conhecimento tenant-owned da empresa ativa |
| `product` | manual oficial e versionado do APP Versus |
| `combined` | composição controlada dos dois escopos |

Regras:

1. `company` exige `company_id`;
2. `product` não recebe `company_id` artificial;
3. `product` respeita audience, versão, surface, perfil e capabilities;
4. `combined` identifica a origem de cada claim;
5. customização de cliente pertence a `company`;
6. documentação global do produto não pode revelar dados de tenant.

## 8. Fontes oficiais

### 8.1 Onda 1

- processos;
- rotinas e POPs;
- publicações do Portal de Processos;
- reuniões e decisões;
- instâncias de processos;
- projetos;
- atividades de projetos;
- planejamento estratégico;
- gestão estratégica;
- indicadores necessários às relações;
- `product_help`.

### 8.2 Onda 2

- metas e medições;
- rotinas e jornada de trabalho;
- ocorrências;
- auditoria interna;
- revisões urgentes;
- contratos e cláusulas;
- recursos de processos;
- portfólios.

### 8.3 Onda 3

- anexos;
- PDFs;
- planilhas;
- OCR e transcrições;
- políticas e manuais;
- conectores externos autorizados.

### 8.4 Regra de elegibilidade

Uma fonte só entra quando possui:

- proprietário funcional;
- resolução de tenant ou escopo global explícito;
- status elegível;
- autoridade;
- vigência;
- URI canônica;
- grants;
- campos sensíveis declarados;
- atualização e exclusão;
- testes de contrato;
- smoke de autorização;
- observabilidade;
- feature flag.

## 9. Tipos de conhecimento

`knowledge_kind`:

- `procedure`;
- `decision`;
- `meeting_record`;
- `operational_fact`;
- `strategic_intent`;
- `measurement`;
- `evidence`;
- `policy`;
- `contractual`;
- `analysis`;
- `reference`;
- `product_help`;
- `draft`.

O tipo altera:

- precedência;
- apresentação;
- elegibilidade;
- chunking;
- necessidade de verificação;
- linguagem da resposta.

## 10. Autoridade, vigência e conflito

Ranking de autoridade considera:

1. permissão;
2. aprovação/publicação;
3. validade;
4. versão;
5. autoridade declarada;
6. supersessão;
7. data do evento;
8. aderência.

Precedência procedimental inicial:

1. política aprovada vigente;
2. POP publicado vigente;
3. decisão aprovada que altere o procedimento;
4. ata concluída;
5. análise;
6. rascunho;
7. fato operacional histórico.

Precedência não apaga conflito. POP vigente e decisão posterior não incorporada devem aparecer juntos, com pendência explícita.

## 11. Temporalidade

O modelo é bitemporal:

- `valid_from` e `valid_to`: validade no negócio;
- `system_from` e `system_to`: validade da projeção no sistema.

São suportadas:

- consulta vigente agora;
- consulta vigente em data;
- reconstrução histórica;
- supersessão;
- correção sem apagar passado.

## 12. Modelo conceitual

### 12.1 `knowledge_sources`

Campos mínimos:

- `id`;
- `company_id`, anulável somente para escopo global;
- `knowledge_scope`;
- `source_type`;
- `source_ref`;
- `knowledge_kind`;
- `title`;
- `canonical_uri`;
- `status`;
- `authority_level`;
- `version`;
- `valid_from`;
- `valid_to`;
- `system_from`;
- `system_to`;
- `supersedes_source_id`;
- `visibility_scope`;
- `trust_level`;
- `security_labels`;
- `quarantine_status`;
- `acl_checksum`;
- `acl_synced_at`;
- `acl_source_version`;
- `content_checksum`;
- `source_updated_at`;
- `indexed_at`;
- `deleted_at`;
- `index_generation`.

### 12.2 `knowledge_chunks`

- `id`;
- `company_id`, conforme fonte;
- `knowledge_source_id`;
- `section_key`;
- `content`;
- `content_tsvector`;
- `embedding`;
- `metadata_json`;
- `chunk_order`;
- `token_count`;
- `content_checksum`;
- `parent_chunk_id`;
- `source_span`;
- `adapter_version`;
- `parser_version`;
- `embedding_model`;
- `chunking_policy`;
- `transformation_activity_id`;
- `generated_by`;
- `derived_from`;
- `index_generation`.

### 12.3 Entidades auxiliares

- `knowledge_source_grants`;
- `knowledge_source_relations`;
- `knowledge_index_events`;
- `knowledge_index_cursors`;
- `knowledge_query_logs`;
- `knowledge_feedback`;
- `knowledge_gaps`;
- `knowledge_verifications`;
- `knowledge_saved_queries`.

### 12.4 Constraints

1. fonte `company` exige `company_id NOT NULL`;
2. fonte `product` exige `company_id IS NULL`;
3. `source_type + source_ref + company_id/scope` é único na geração ativa;
4. chunk herda scope e tenant da fonte;
5. relação tenant-owned só liga fontes da mesma empresa;
6. grant não pode ampliar permissão da origem;
7. exclusão lógica precisa sair da geração ativa.

## 13. Grafo relacional determinístico

Relações iniciais:

- decisão `altera` POP;
- POP `orienta` processo;
- instância `executa` processo;
- decisão `gera` atividade;
- atividade `entrega` projeto;
- projeto `contribui_para` objetivo;
- indicador `mede` objetivo;
- reunião `registra` decisão;
- evidência `comprova` execução;
- artigo de ajuda `orienta` route/módulo.

O grafo inicial deriva de FKs e vínculos oficiais. Extração probabilística de novas relações não entra no MVP.

## 14. `QueryPlan`

Toda pergunta gera plano validado pelo backend.

```json
{
  "query_kind": "answer",
  "knowledge_scope": "company",
  "company_id": 9,
  "source_types": ["process_publication", "meeting"],
  "strategies": ["sql", "full_text", "vector", "relationship_graph"],
  "entities": [],
  "time": {
    "mode": "current",
    "from": null,
    "to": null
  },
  "filters": {},
  "limits": {
    "candidate_limit": 50,
    "answer_source_limit": 8
  }
}
```

Regras:

- modelo pode propor;
- backend valida enum, tenant, ACL, limites e fontes;
- `company_id` vem do contexto autenticado;
- usuário não injeta surface ou capability;
- estratégia `sql` é obrigatória para superlativos, status, contagens e datas determinísticas;
- plano é registrado sem conteúdo sensível desnecessário.

## 15. Recuperação

Pipeline:

1. resolver principal e empresa ativa;
2. resolver `knowledge_scope`;
3. validar ACL e freshness;
4. classificar intenção;
5. materializar `QueryPlan`;
6. executar SQL determinístico;
7. buscar texto e vetores já escopados;
8. percorrer relações autorizadas;
9. fundir rankings por RRF;
10. reranquear conjunto limitado;
11. expandir filho para pai contextual;
12. aplicar autoridade, vigência e recência;
13. detectar conflito e lacuna;
14. construir claims;
15. associar citações;
16. validar resposta;
17. registrar telemetria.

## 16. Chunking

Política por fonte:

| Fonte | Filho | Pai contextual |
|---|---|---|
| POP | passo | rotina/publicação |
| reunião | decisão/discussão | reunião/ata |
| projeto | atividade | projeto |
| estratégia | key result/iniciativa | objetivo/plano |
| processo | elemento/rotina | processo |
| instância | evento/evidência | instância |
| `product_help` | passo/bloco | artigo/tour |

Alteração de política incrementa `chunking_policy` e exige nova geração ou reprocessamento controlado.

## 17. Contrato de adaptador

```python
class KnowledgeSourceAdapter:
    source_type: str

    def list_changed_refs(
        self,
        *,
        company_id: int | None,
        cursor: str | None,
    ) -> ChangePage:
        ...

    def load_source(
        self,
        *,
        company_id: int | None,
        source_ref: str,
        principal: Principal,
    ) -> SourceDocument:
        ...

    def resolve_grants(
        self,
        *,
        company_id: int | None,
        source_ref: str,
    ) -> list[SourceGrant]:
        ...

    def build_chunks(self, source: SourceDocument) -> list[SourceChunk]:
        ...

    def build_relations(self, source: SourceDocument) -> list[SourceRelation]:
        ...

    def validate_scope(
        self,
        *,
        company_id: int | None,
        source_ref: str,
    ) -> None:
        ...
```

O adaptador declara:

- domínio proprietário;
- scope;
- resolução de tenant;
- statuses;
- autoridade;
- vigência;
- eventos;
- campos sensíveis;
- grants;
- exclusão;
- chunking;
- versões;
- testes.

## 18. Registry

O `KnowledgeSourceRegistry` é o único ponto de registro.

```python
SOURCE_REGISTRY = {
    "product_help": ProductHelpKnowledgeAdapter,
    "process_publication": ProcessPublicationKnowledgeAdapter,
    "meeting": MeetingKnowledgeAdapter,
    "process_instance": ProcessInstanceKnowledgeAdapter,
    "project": ProjectKnowledgeAdapter,
    "project_task": ProjectTaskKnowledgeAdapter,
    "strategic_plan": StrategicPlanKnowledgeAdapter,
    "strategy_management": StrategyManagementKnowledgeAdapter,
}
```

Não são permitidos imports dispersos de adaptadores no pipeline.

## 19. Indexação

### 19.1 Event-driven

Eventos relevantes alimentam transactional outbox na mesma transação do domínio.

### 19.2 Reconciliação

Job incremental recupera eventos perdidos por cursor.

### 19.3 Backfill

Backfill:

- idempotente;
- paginado;
- retomável;
- por tenant;
- observável;
- limitado;
- seguro para reexecução.

### 19.4 Operação

- fila idempotente;
- retry por tenant/fonte;
- dead-letter queue;
- checkpoint;
- SLA de freshness;
- geração inactive;
- validação;
- ativação atômica;
- rollback.

## 20. Segurança

### 20.1 Ordem obrigatória

1. autenticação;
2. empresa ativa;
3. surface;
4. domínio;
5. capability;
6. grants;
7. status/visibilidade;
8. recuperação;
9. síntese.

### 20.2 Fail closed

Consulta é negada quando:

- ACL não existe;
- checksum diverge;
- snapshot venceu além do SLA;
- grant não pode ser resolvido;
- cadeia de tenant é ambígua;
- source scope é incompatível;
- avaliação de autorização falha.

### 20.3 Trust zones

- `official`;
- `internal`;
- `external_trusted`;
- `external_untrusted`;
- `quarantined`.

Conteúdo recuperado é dado, nunca instrução. Documento não pode alterar prompt, `QueryPlan`, permissões ou tools.

### 20.4 Multi-tenancy

- todo repository/query tenant-owned recebe `company_id`;
- ID isolado nunca autoriza;
- pai e filho validam a mesma empresa;
- relação cruza somente fontes do mesmo tenant;
- logs não vazam título, trecho ou existência de fonte negada;
- testes cross-tenant são gate de release.

## 21. MCP

Tools canônicas de leitura:

- `search_organizational_knowledge`;
- `answer_organizational_question`;
- `get_knowledge_source`;
- `list_knowledge_sources`;
- `report_knowledge_gap`;
- `answer_product_help`;
- `get_product_help_article`;
- `list_product_help_suggestions`.

Surfaces:

- `user`: leitura autorizada e ajuda;
- `analytics`: análise transversal tenant-safe;
- `admin`: rollout, fontes, grants, verificação e backfill;
- `ops`: diagnóstico de indexação sem bypass de conteúdo.

O MCP resolve contexto por request. Não aceita `company_id`, perfil ou surface do texto do usuário como fonte de verdade.

## 22. Boundaries

- **rota Flask:** autentica, valida schema, resolve contexto e serializa;
- **service:** planeja, recupera, autoriza e compõe;
- **repository/query:** executa leitura com scope e `company_id`;
- **adapter:** transforma a fonte proprietária;
- **frontend:** apresenta e coleta interação, sem decidir autorização;
- **MCP tool:** delega ao mesmo service;
- **workflow:** controla qualquer mutação posterior.

Lógica de negócio em rota é proibida.

## 23. Contrato de resposta

```json
{
  "query_id": "opaque-id",
  "mode": "answer",
  "knowledge_scope": "company",
  "answer": "Síntese objetiva.",
  "trust_signals": ["official", "published"],
  "claims": [
    {
      "text": "Afirmação material.",
      "citations": ["citation-1"]
    }
  ],
  "citations": [
    {
      "id": "citation-1",
      "source_type": "process_publication",
      "source_ref": "opaque-ref",
      "title": "Título autorizado",
      "source_span": "passo-3",
      "version": "4",
      "valid_from": "2026-07-18",
      "canonical_uri": "registered-route"
    }
  ],
  "warnings": [],
  "related_objects": [],
  "actions": []
}
```

Regras:

- URI é registrada, não inventada pelo modelo;
- citação negada não aparece;
- toda claim material possui uma ou mais citações;
- resposta sem evidência suficiente usa abstenção;
- ação só é exibida após capability check.

## 24. Manual interativo `product_help`

### 24.1 Campos

- `product_version`;
- `locale`;
- `route_key`;
- `module_key`;
- `page_context`;
- `audience`;
- `required_capabilities`;
- `help_kind`;
- `navigation_target`;
- `tour_definition_id`;
- `published_at`;
- `reviewed_by`;
- `verified_at`.

### 24.2 Tipos

- `concept`;
- `how_to`;
- `navigation`;
- `permission_explanation`;
- `troubleshooting`;
- `guided_tour`;
- `release_change`.

### 24.3 Navegação

`Levar-me até lá` resolve `route_key` registrado.

É proibido:

- navegar para URL arbitrária gerada;
- ignorar permission gate;
- revelar route inacessível;
- executar mutação.

### 24.4 Tour

Tour usa `data-help-id` estável e pode:

- destacar;
- explicar;
- aguardar ação;
- navegar;
- avançar;
- voltar;
- encerrar.

Tour não pode:

- enviar formulário automaticamente;
- executar ação destrutiva;
- contornar aprovação;
- seguir quando versão, route ou capability divergir.

### 24.5 Release gate

Mudança relevante de route, template, capability ou fluxo:

1. identifica artigos/tours impactados;
2. invalida orientação incompatível;
3. exige atualização;
4. exige QA;
5. exige revisão funcional;
6. publica vinculada à versão.

## 25. Cockpit de curadoria

Visões mínimas:

- unanswered;
- avaliação negativa;
- conflito;
- fonte vencida;
- fonte sem responsável;
- decisão sem desdobramento;
- duplicidade;
- fonte nunca usada;
- temas pesquisados;
- gaps por domínio;
- fila de revisão;
- cobertura.

O cockpit é separado da interface comum.

## 26. Feedback

Motivos:

- `incorrect`;
- `outdated`;
- `incomplete`;
- `wrong_source`;
- `not_answered`;
- `should_not_be_accessible`;
- `conflict_not_reported`.

Feedback negativo:

1. registra query, claims e fontes;
2. cria item de curadoria;
3. encaminha ao responsável;
4. permite corrigir fonte/regra;
5. reindexa;
6. reavalia pergunta.

Feedback nunca oficializa conteúdo automaticamente.

## 27. Jornadas de aceite

### 27.1 Venda para pessoa jurídica

- prioriza POP vigente;
- mostra passos;
- exibe selo oficial;
- cita decisão complementar;
- abre `processo (fluxo / POP)`;
- fato histórico não vira norma.

### 27.2 Última reunião

- resolve reunião concluída mais recente por SQL;
- informa a reunião considerada;
- lista decisões, responsáveis e prazos;
- distingue discussão de decisão;
- abre ata e objetos relacionados.

### 27.3 Manutenção elétrica

- investiga fontes múltiplas;
- separa definição, decisão, execução e lacuna;
- exibe linha do tempo;
- aponta conflito e responsável ausente;
- oferece registrar lacuna.

### 27.4 Ajuda do produto

- detecta scope `product`;
- considera route e objeto atual;
- verifica capabilities;
- apresenta passos da versão ativa;
- oferece navegação registrada;
- inicia tour por `data-help-id`;
- mantém confirmação no workflow oficial.

## 28. Avaliação

Golden set inclui:

- consultas determinísticas;
- sem resposta;
- conflito;
- vigente agora;
- histórico;
- vocabulário equivalente;
- relações;
- cross-tenant;
- sem grant;
- prompt injection;
- ACL revogada;
- ajuda com route alterada;
- tour incompatível;
- usuário sem capability.

Métricas:

- Recall@K;
- NDCG;
- groundedness;
- completude;
- precisão de citações;
- completude de citações;
- abstenção correta;
- conflito detectado;
- freshness;
- latência;
- custo;
- zero vazamento;
- sucesso sem reformulação;
- tempo até primeira resposta útil.

## 29. Critérios de UX

1. pergunta comum sem modo ou fonte;
2. primeira resposta útil na primeira viewport desktop;
3. fonte, status, vigência e ressalva legíveis;
4. filtros recolhidos;
5. fonte aberta em no máximo duas ações;
6. citação com preview;
7. investigação apresenta progresso e cancelamento;
8. ausência oferece lacuna;
9. nenhum termo técnico de retrieval;
10. acessibilidade por teclado e leitor;
11. responsividade desktop/mobile;
12. teste com perfis de diferentes níveis digitais.

## 30. Observabilidade

Métricas mínimas:

- fontes elegíveis/indexadas;
- atraso por adaptador;
- falhas e DLQ;
- consultas por modo/scope;
- sem resultado;
- conflito;
- feedback;
- citação aberta;
- RBAC negado;
- cross-tenant bloqueado;
- custo;
- adoção por perfil;
- gaps resolvidos;
- uso de navegação;
- tours iniciados/concluídos;
- orientação desatualizada.

Logs devem possuir correlação sem persistir conteúdo sensível desnecessário.

## 31. Rollout

### Fase 0 — fundação

- modelos;
- registry;
- ACL;
- QueryPlan;
- FTS;
- telemetria;
- harness;
- `product_help`.

### Fase 1 — piloto vertical

- uma empresa piloto;
- publicações de processo/POP;
- reuniões concluídas;
- painel Sapiens;
- feedback;
- cockpit básico.

### Fase 2 — operação

- instâncias;
- projetos;
- atividades;
- planejamento;
- estratégia;
- indicadores;
- Trilha Decisão–Execução.

### Fase 3 — expansão

- anexos;
- fontes da Onda 2;
- pesquisa aprofundada;
- alertas;
- conectores aprovados.

## 32. Migração do RAG legado

1. ChromaDB não recebe novas responsabilidades;
2. seeds estáticos não são tratados como fonte tenant;
3. implementação duplicada é inventariada;
4. nova camada roda por feature flag;
5. resultados são comparados no harness;
6. tráfego migra por empresa;
7. legado fica somente leitura durante transição;
8. remoção ocorre após cobertura e rollback comprovados.

## 33. Gates de implementação

Nenhum rollout ocorre sem:

- migração PostgreSQL revisada;
- teste de constraint;
- cross-tenant;
- ACL fail-closed;
- contrato de adaptadores;
- golden set;
- citações;
- abstenção;
- observabilidade;
- rollback;
- acessibilidade;
- aprovação funcional das jornadas.

## 34. Dependências operacionais

Antes da busca semântica em produção:

- confirmar disponibilidade e operação de `pgvector`;
- definir modelo de embedding aprovado;
- definir limites e custo por empresa;
- definir SLA de indexação;
- definir retenção de logs e projeções.

Se `pgvector` não estiver disponível na primeira entrega, o MVP inicia com SQL + full-text search + relações, sem criar storage vetorial paralelo não governado.

## 35. Sequência oficial de implementação

1. migrations e constraints;
2. repositories tenant-safe;
3. registry e adapter `product_help`;
4. adapter de publicação de processo;
5. adapter de reunião;
6. indexação e reconciliação;
7. QueryPlanner;
8. retrieval híbrido;
9. composição e citações;
10. MCP;
11. painel Sapiens;
12. busca global;
13. cockpit;
14. harness e rollout piloto.

## 36. Evidências esperadas

Para considerar a SPEC implementada:

- migrations aplicadas;
- testes unitários;
- testes de contrato de adapter;
- testes de service;
- testes MCP;
- testes cross-tenant;
- testes de prompt injection;
- testes de UX;
- smoke com perguntas de referência;
- dashboards;
- runbook;
- playbook de inclusão de fontes;
- harness operacional.

## 37. Resultado canônico

O APP Versus terá uma camada única de conhecimento:

- robusta no backend;
- simples no uso;
- contextual pelo Sapiens;
- extensível por adaptadores;
- governada por autoridade e temporalidade;
- segura por tenant, ACL e capability;
- citável por afirmação;
- capaz de conectar decisão, processo, execução e estratégia;
- capaz de ensinar interativamente como utilizar o próprio produto.

## 38. Estado de implementação da Fase 0

Implementado em 2026-07-30:

- modelos `KnowledgeSource`, `KnowledgeChunk` e `KnowledgeIndexRun`;
- migration PostgreSQL `20260730_1700`;
- constraints de scope global versus tenant-owned;
- índice full-text em português;
- contrato e registry de adapters;
- primeiro adapter `product_help`;
- catálogo versionado inicial;
- sincronização idempotente por checksum;
- deativação automática de fontes removidas;
- ledger auditável de execuções;
- job `knowledge_product_help_sync` no scheduler dedicado;
- exposição do job no registry consultivo de automações;
- testes de adapter, sincronização, scheduler e migration.

Ainda não implementado:

- adapters tenant-owned;
- painel Sapiens;
- cockpit de curadoria;
- embeddings/`pgvector`.

## 39. Estado de implementação da busca citada

Implementado em 2026-07-30 como primeiro corte da Fase 1:

- domínio `knowledge` incluído na taxonomia canônica de tools;
- `KnowledgeQueryPlan` validado pelo backend;
- recuperação SQL com PostgreSQL full-text search;
- fallback SQL portável para testes;
- filtro prévio de scope global e `company_id`;
- vigência, status e exclusão lógica aplicados antes da recuperação;
- composição determinística com claims, citações e URI registrada;
- abstenção quando não existe evidência autorizada;
- ação de navegação derivada somente de metadado cadastrado;
- tools `answer_product_help`, `search_organizational_knowledge` e
  `answer_organizational_question`;
- contexto de empresa resolvido pelo runtime MCP, sem parâmetro `company_id`
  exposto nas tools.

Limites deste corte:

- somente `product_help` possui adapter e atualização automática;
- fontes tenant-owned usadas pelo retrieval dependerão dos próximos adapters;
- grants por fonte e cockpit permanecem pendentes;
- painel Sapiens, feedback e busca global permanecem pendentes;
- não há embeddings, reranking semântico ou geração por LLM;
- a migration precisa ser aplicada antes de ativar o runtime.

## 40. Estado de implementação dos primeiros adapters tenant-owned

Implementado em 2026-07-30:

- adapter `process_publication`, limitado à publicação `published` mais recente
  de cada processo;
- adapter `meeting`, limitado aos estados concluídos `completed` e `done`;
- projeção de conteúdo textual de POPs, atas, discussões, pautas e atividades;
- exclusão explícita de snapshots visuais e binários do conteúdo indexável;
- modelo `KnowledgeSourceGrant` e migration PostgreSQL `20260730_1800`;
- grants de empresa, usuário e colaborador validados antes da recuperação;
- contexto `user_id` e `employee_id` vindo do runtime MCP;
- sincronização automática por empresa ativa no job
  `knowledge_tenant_sources_sync`;
- configuração `KNOWLEDGE_TENANT_SYNC_MINUTES`, padrão de 15 minutos;
- testes de adapters, ACL, isolamento, scheduler, MCP e migration.

Decisões de segurança:

- grant de escopo `process` ou `activity` não é ampliado para a empresa;
- fonte com apenas grants não suportados permanece irrecuperável;
- reunião sem participante interno ativo e identificável falha fechada;
- `company_id` continua derivado do contexto autenticado;
- conteúdo global `product_help` permanece separado das fontes corporativas.

Limites conhecidos:

- equivalência de acesso para perfis administrativos com visão integral de
  reuniões ainda precisa de uma política canônica projetável;
- grants contextuais por processo/atividade exigem contexto de objeto no runtime;
- instâncias de processos, projetos, atividades e estratégia permanecem nas
  próximas ondas;
- migrations ainda precisam ser aplicadas no ambiente antes da ativação.

## 41. Catálogo oficial do Manual Inteligente

Ficam oficializadas as seguintes regras de implementação:

1. `product_help` reúne artigos curados e ajuda de navegação compilada;
2. `system_documentation` indexa somente `docs/papers` e `docs/spec`;
3. SPEC possui autoridade `official`; Paper possui autoridade `contextual`;
4. cada entrada navegável do menu deve possuir exatamente uma ajuda alcançável;
5. o job `knowledge_product_help_sync` sincroniza todas as fontes globais;
6. o job falha quando a auditoria detectar lacuna ou duplicidade de navegação;
7. perguntas de orientação iniciadas por `como`, `onde` ou equivalentes não
   podem cair em confirmação de workflow operacional;
8. candidato operacional único abaixo do limiar mínimo resulta em `no_match`;
9. conteúdo global nunca recebe `company_id`; fontes corporativas mantêm grants;
10. geração automática oferece navegação, não inventa procedimento operacional.

O baseline de 2026-07-31 contém 94 documentos de manual para 93 rotas distintas
do menu, com 100% de cobertura aferida pelo compilador. A diferença decorre de
duas visões autorizadas na mesma rota com parâmetros distintos.

## 42. Política de resposta simples e superfícies equivalentes

Ficam oficializadas as seguintes regras de experiência:

1. pergunta funcional de usuário não mistura manual com Paper/SPEC técnico;
2. quando um manual oficial for a melhor evidência, a resposta principal usa um
   único artigo e mantém as demais fontes fora do texto principal;
3. listas, opções e caminhos de menu permanecem estruturados, sem achatamento em
   um parágrafo longo;
4. identificadores internos, nomes de tools, capabilities, contratos de API e
   detalhes de arquitetura só aparecem quando a pergunta for explicitamente
   técnica;
5. um artigo pode cadastrar mais de uma ação de navegação interna segura;
6. caminhos alternativos relevantes devem ser apresentados com indicação clara
   de quando utilizar cada um;
7. a tela `/sapiens` e o atalho global usam o mesmo endpoint tenant-safe, os
   mesmos escopos e a mesma política de fallback;
8. o atalho global é uma versão compacta da experiência de conhecimento, com
   acesso explícito à tela completa.


## 43. Camada de entendimento e treinamento supervisionado

Ficam oficializados os seguintes contratos para a próxima evolução do Sapiens:

1. toda resposta gerada por `/api/agents/knowledge/answer` deve possuir um
   `interaction_id` persistível ou correlacionável;
2. antes da recuperação, o backend deve produzir um entendimento mínimo da pergunta
   com `intent`, `domain`, `confidence`, `signals` e `clarification_required`;
3. pergunta funcional de uso do produto prioriza `product_help` sobre ferramentas
   operacionais, exceto quando o usuário pedir execução explícita;
4. baixa confiança exige esclarecimento curto e não fallback técnico automático;
5. o feedback do usuário usa escala simples: `correct`, `partial`, `wrong`;
6. `partial` e `wrong` podem receber motivo controlado e comentário livre;
7. feedback sempre grava `company_id`, `user_id`, pergunta, entendimento, fontes,
   resposta resumida, rating, motivo, comentário, versão do motor e timestamps;
8. dados de feedback são tenant-owned e nunca ampliam acesso a fontes;
9. feedback não altera ranking, aliases ou artigos automaticamente;
10. o Robô Treinador gera propostas auditáveis em fila de curadoria.

### 43.1 Motivos controlados de feedback

Motivos iniciais:

- `wrong_subject`: respondeu sobre outro assunto;
- `too_technical`: linguagem técnica demais;
- `missing_path`: faltou caminho no APP;
- `wrong_source`: fonte usada não era adequada;
- `incomplete`: resposta incompleta;
- `not_found`: deveria saber, mas não encontrou;
- `outdated`: orientação desatualizada.

### 43.2 Robô Treinador

O robô consolida janelas de feedback por `company_id` e por escopo global quando a
fonte for `product_help`. A saída mínima é uma proposta com:

- padrão de pergunta;
- intenção/domínio sugeridos;
- evidências de avaliações negativas;
- fontes que foram usadas;
- sugestão de alias, ranking, artigo ou pergunta de esclarecimento;
- status `pending_review`.

A aplicação automática fica proibida no MVP. O cockpit de curadoria decidirá se a
proposta vira ajuste oficial.

### 43.3 Critérios de aceite do MVP

- botões `Certo`, `Parcial`, `Errado` na tela `/sapiens` e no widget global;
- endpoint tenant-safe para registrar feedback;
- modelo e migration de feedback/treinamento;
- service sem lógica de negócio em rota;
- testes de isolamento por `company_id`;
- testes de contrato para motivos controlados;
- job/service do Robô Treinador consolidando propostas sem aplicá-las.
