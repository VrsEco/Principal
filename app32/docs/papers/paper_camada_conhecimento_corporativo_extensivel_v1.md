# Paper — Camada de Conhecimento Corporativo Extensível do APP Versus v1

**Classe documental:** Paper
**Status:** Consolidado; decisões oficiais congeladas em SPEC
**Data:** 2026-07-29
**Última atualização:** 2026-07-30
**Especialistas líderes:** `@ARQUITETO`, `@AI_ENGINEER`
**Apoios necessários para evolução:** `@DBA`, `@BACKEND_SERVICE`, `@BACKEND_API`, `@QA_AUTOMATION`
**Domínio canônico proposto:** `knowledge`
**Natureza inicial:** consulta somente leitura, tenant-safe e MCP First
**SPEC derivada:** `docs/spec/arquitetura_oficial_camada_conhecimento_corporativo_app_versus_v1.md`

## 1. Pergunta central

Como transformar os dados estruturados, documentos, decisões e evidências já existentes no APP Versus em uma memória corporativa pesquisável, confiável, citável e extensível, sem misturar empresas, permissões, rascunhos, versões ou níveis diferentes de autoridade?

## 2. Tese

O APP Versus deve possuir uma **Camada de Conhecimento Corporativo** capaz de:

- receber uma pergunta em linguagem natural;
- identificar se a resposta exige consulta temporal, estruturada, textual, semântica ou híbrida;
- localizar as fontes autorizadas dentro da empresa ativa;
- distinguir fato operacional, procedimento publicado, decisão, planejamento, evidência e análise;
- responder com fontes, datas, versões e nível de confiança;
- evidenciar conflito ou ausência de informação, sem inventar resposta;
- aceitar novas fontes por contrato de adaptação, sem redesenhar o núcleo de busca.

Essa camada não deve ser apenas um chat com documentos nem uma base vetorial isolada. Ela deve funcionar como **memória operacional e estratégica auditável da empresa**.

O núcleo pode e deve ser tecnicamente robusto, mas essa complexidade não pode ser transferida ao usuário. A experiência deve começar com **uma pergunta em uma única porta de entrada**, enquanto planejamento de consulta, combinação de fontes, autoridade, ACL, temporalidade e ranking permanecem invisíveis por padrão.

## 3. Resultado esperado

Perguntas como estas devem ser atendidas:

- “Como faço uma venda para pessoa jurídica?”
- “O que foi decidido na última reunião?”
- “Existe algo definido sobre manutenção elétrica dos prédios?”
- “Quais instâncias deste processo apresentaram o mesmo problema?”
- “O que está atrasando o projeto de expansão?”
- “Quais atividades foram definidas para executar este objetivo estratégico?”
- “Há divergência entre o planejamento estratégico e os projetos em execução?”
- “Qual decisão alterou a forma de executar este POP?”

A resposta precisa trazer:

1. síntese objetiva;
2. fatos e trechos que sustentam a síntese;
3. fontes acessíveis ao usuário;
4. data, versão, status e vigência;
5. conflitos, lacunas ou ressalvas;
6. próximos passos, somente quando fizer sentido.

## 4. Princípios inegociáveis

1. `company_id` é obrigatório em toda consulta e indexação tenant-owned.
2. Autorização ocorre antes da exposição do conteúdo ao modelo de IA.
3. Fonte sem escopo tenant determinístico não entra no índice corporativo.
4. Rascunho, publicado, concluído, cancelado e arquivado não são equivalentes.
5. Busca semântica não substitui consulta SQL determinística.
6. Toda resposta factual deve possuir proveniência.
7. Ausência de evidência deve resultar em “não localizado”, não em inferência apresentada como fato.
8. Conflitos entre fontes devem ser exibidos, não ocultados pela síntese.
9. Conteúdo indexado é uma projeção; a fonte operacional original continua soberana.
10. A inclusão de nova fonte deve ocorrer por adaptador registrado e testado.
11. Leitura operacional deve ser disponibilizada via MCP com RBAC e telemetria.
12. Mutação de fonte, publicação ou decisão continua sujeita aos workflows e gates humanos do domínio original.
13. Falha ou desatualização não tolerada na avaliação de ACL deve negar a consulta (`fail closed`).
14. Conteúdo recuperado é dado potencialmente hostil, nunca instrução para o modelo ou para uma tool.
15. Toda afirmação material da resposta deve ser rastreável ao trecho exato que a sustenta.

## 5. O que já existe no APP Versus

### 5.1 Processos, POPs e publicações

O APP Versus já possui:

- áreas, macroprocessos e processos;
- rotinas e passos de POP;
- descrição e resultado esperado;
- BPMN versionado;
- SIPOC;
- análises BPMS;
- mídia vinculada aos passos;
- publicação do Portal de Processos com versão, status, escopo de visibilidade e grants.

A publicação do Portal de Processos é candidata natural a fonte canônica de procedimentos publicados.

### 5.2 Reuniões e atas

O módulo de reuniões já registra:

- pauta;
- participantes;
- discussões;
- decisões;
- responsáveis e prazos;
- atividades derivadas;
- ata consolidada;
- vínculo com projeto;
- status e datas da reunião.

### 5.3 Operação, projetos e estratégia

Também já existem fontes estruturadas para:

- instâncias e execuções de processos;
- projetos, atividades, responsáveis, dependências e horas;
- planos, direcionadores e dados de implantação;
- OKRs globais, OKRs de área e key results;
- identidade organizacional;
- perfis e vínculos de alinhamento estratégico;
- indicadores, metas e medições;
- revisões executivas, decisões urgentes e aprendizado estrutural.

### 5.4 RAG legado

Existem implementações experimentais com ChromaDB e embeddings OpenAI. Elas demonstram viabilidade técnica, mas não constituem a arquitetura alvo porque:

- não possuem segregação completa por `company_id`;
- existem em mais de um caminho de implementação;
- não controlam de forma suficiente versão, vigência, publicação e grants;
- não garantem citação e autoridade da fonte;
- misturam conhecimento estático com conhecimento tenant-owned.

O legado pode servir como referência de experimentação, não como fonte produtiva soberana.

### 5.5 Decisão conceitual sobre RAG

O Sapiens deve usar **RAG governado**, não RAG genérico.

Nesta arquitetura, RAG significa recuperar evidências autorizadas antes de sintetizar
uma resposta, mas sempre subordinado a:

- autenticação, empresa ativa e `company_id`;
- grants, capabilities, status, vigência e autoridade da fonte;
- SQL determinístico para dados operacionais, contagens, status, datas e relações;
- full-text search para termos exatos, códigos e nomes;
- busca vetorial/semântica apenas como estratégia complementar;
- citações por afirmação material;
- abstenção quando a evidência não for suficiente.

Portanto, RAG é recomendável para perguntas abertas de conhecimento corporativo e
manual do produto, mas não deve substituir MCP/SQL em consultas operacionais atuais.

Exemplos:

- “Existe algo definido sobre manutenção elétrica?” pode usar RAG governado híbrido;
- “O que foi decidido na última reunião?” começa por SQL temporal e depois sintetiza a ata;
- “Quais atividades tenho hoje?” deve usar MCP/SQL de rotina, não busca vetorial;
- “Como faço para lançar uma conta a pagar?” prioriza `product_help` curado.

GraphRAG completo permanece fora do MVP. A primeira evolução deve ser PostgreSQL
full-text search + relações determinísticas; `pgvector` entra quando houver extensão,
custo, isolamento, métrica e rollback validados.

## 6. Inventário inicial de fontes

O inventário abaixo não é uma lista fechada. Ele representa a primeira rodada de cobertura.

### 6.1 Onda 1 — núcleo do MVP

| Fonte | Conteúdo pesquisável | Regra de autoridade | Resolução tenant |
|---|---|---|---|
| Processos | nome, descrição, notas, responsável | processo ativo | `Process.company_id` |
| POPs | rotina, passos, descrições, resultados e narração | preferir publicação vigente | `ProcessRoutine.company_id` ou processo pai |
| Portal de Processos | snapshot publicado, versão e grants | fonte procedimental prioritária | `ProcessPortalPublication.company_id` |
| Reuniões | pauta, discussões, decisões, ata e atividades | reunião concluída; ressalvar ausência de aprovação formal | `Meeting.company_id` |
| Instâncias de Processos | contexto, status, notas, execução, erros e resultados | fato operacional, não norma | `ProcessInstance.company_id` |
| Projetos | objetivo, descrição, status, prazo, orçamento e notas | fato de execução do projeto | `Project.company_id` |
| Atividades de Projetos | o quê, como, quem, prazo, status, notas e logs | fato operacional; herda escopo do projeto | `ProjectTask -> Project.company_id` |
| Planejamento Estratégico | planos, direcionadores, seções, OKRs e key results | preferir plano ativo/aprovado quando houver status | `Plan/OKR.company_id` |
| Gestão Estratégica | identidade, alinhamentos, indicadores e revisões | respeitar confirmação e status da fonte | tabelas estratégicas com `company_id` |

### 6.2 Onda 2 — ampliação operacional e de governança

| Fonte | Exemplos de conhecimento |
|---|---|
| Indicadores, metas e medições | resultados, desvios, tendências, evidências e vínculo com estratégia |
| Rotinas e jornada de trabalho | cadência, agenda, recorrência e execução do trabalho |
| Ocorrências | falhas, desvios e registros vinculados a processo ou projeto |
| Auditoria interna | critérios, evidências esperadas, achados e planos de ação |
| Revisões urgentes | decisão, custo de agir, custo de não agir, risco aceito e aprendizado estrutural |
| Contratos e cláusulas | obrigações, vigência, eventos, documentos e condições, com permissão reforçada |
| Recursos de processos | pessoas, equipamentos, instalações, capacidade, custo e gargalos |
| Portfólios | agrupamento e contexto executivo dos projetos |

### 6.3 Onda 3 — fontes documentais e externas

- documentos anexados aos objetos do APP Versus;
- PDFs, planilhas, imagens com OCR e transcrições;
- políticas internas aprovadas;
- manuais e normas;
- documentos da governança oficial do APP Versus, em escopo diferente do tenant cliente;
- e-mail, calendário, Drive, SharePoint, Teams, Slack ou outros conectores autorizados;
- bases externas contratuais, regulatórias ou setoriais.

Cada integração externa deve preservar:

- origem;
- identidade do conector;
- empresa;
- ACL de origem;
- data de captura;
- checksum;
- política de atualização e exclusão.

### 6.4 Fontes que exigem correção ou regra especial

Objetos sem `company_id` direto só podem entrar após resolução segura pelo pai:

- `ProjectTask` resolve empresa por `Project`;
- `ProcessStep` resolve empresa por `ProcessRoutine`;
- logs de atividade precisam resolver projeto, processo ou outro agregado proprietário;
- notas pessoais sem empresa explícita não podem ser promovidas automaticamente a conhecimento corporativo;
- anexos devem herdar e validar o tenant do objeto proprietário.

Se a cadeia de propriedade for ambígua, o adaptador deve rejeitar a indexação.

## 7. Tipos de conhecimento

Cada fonte deve ser classificada em um `knowledge_kind`:

- `procedure`: procedimento ou POP;
- `decision`: deliberação ou decisão aprovada;
- `meeting_record`: registro histórico de reunião;
- `operational_fact`: fato de execução;
- `strategic_intent`: objetivo, plano, OKR ou direcionador;
- `measurement`: indicador, meta ou medição;
- `evidence`: anexo, log ou comprovação;
- `policy`: política ou regra formal;
- `contractual`: cláusula ou obrigação contratual;
- `analysis`: análise produzida pelo sistema ou consultoria;
- `reference`: manual, norma ou referência não normativa;
- `product_help`: orientação oficial, contextual e versionada de uso do APP Versus;
- `draft`: material ainda não oficial.

Essa classificação impede que uma ocorrência isolada seja apresentada como procedimento oficial ou que uma análise seja apresentada como decisão.

## 8. Hierarquia de autoridade

A prioridade não deve ser definida apenas pelo tipo de arquivo. Ela deve considerar:

1. permissão do usuário;
2. status de publicação/aprovação;
3. vigência;
4. versão;
5. autoridade declarada;
6. data do evento;
7. relação de supersessão;
8. aderência à pergunta.

Exemplo de precedência procedimental:

1. política vigente aprovada;
2. POP publicado vigente;
3. decisão aprovada que explicitamente altere o procedimento;
4. ata de reunião concluída;
5. rascunho ou análise;
6. registros operacionais históricos.

Essa precedência não elimina conflito. Se uma decisão posterior ainda não foi incorporada ao POP, a resposta deve apresentar os dois fatos e sinalizar a pendência de governança.

## 9. Tipos de consulta

### 9.1 Consulta determinística

Usada quando a pergunta exige:

- último, primeiro, atual ou vigente;
- contagem;
- status;
- prazo;
- responsável;
- período;
- lista de objetos.

Exemplo:

> “O que foi decidido na última reunião?”

O sistema deve localizar por SQL a última reunião concluída e autorizada. Somente depois deve interpretar suas decisões e ata.

### 9.2 Consulta semântica

Usada quando o usuário procura um assunto sem conhecer os termos exatos:

> “Existe algo sobre responsabilidade pela manutenção elétrica?”

A consulta deve localizar termos equivalentes em diferentes fontes, como elétrica, instalação predial, manutenção preventiva, facilities ou responsabilidade técnica.

### 9.3 Consulta híbrida

Combina:

- filtro SQL;
- full-text search;
- busca vetorial;
- metadados;
- relações entre objetos;
- reranking por autoridade e relevância.

Esse deve ser o padrão para perguntas investigativas ou transversais.

### 9.4 Planejador tipado de consulta

Antes da recuperação, a pergunta deve ser materializada em um `QueryPlan` auditável, com uma ou mais estratégias:

- `sql`: datas, status, responsáveis, contagens, vigência e relações determinísticas;
- `full_text`: termos exatos, nomes, códigos e expressões do domínio;
- `vector`: equivalência semântica e vocabulário não conhecido pelo usuário;
- `relationship_graph`: travessia entre decisões, POPs, processos, instâncias, projetos, atividades, objetivos e indicadores;
- `hybrid`: composição explícita das estratégias anteriores.

O plano deve registrar filtros, período, fontes elegíveis, estratégia, limites, permissões exigidas e motivo da escolha. O modelo pode ajudar a propor o plano, mas a validação de tenant, ACL, tipos e limites pertence ao backend.

## 10. Arquitetura conceitual

### 10.1 Fonte soberana

As tabelas e documentos originais continuam sendo a fonte de verdade.

### 10.2 Projeção de conhecimento

Uma projeção normalizada mantém conteúdo pesquisável e metadados de controle.

Entidades conceituais:

- `knowledge_sources`;
- `knowledge_chunks`;
- `knowledge_source_grants`;
- `knowledge_source_relations`;
- `knowledge_index_events`;
- `knowledge_query_logs`;
- `knowledge_feedback`.

### 10.3 Campos mínimos da fonte

- `id`;
- `company_id`;
- `source_type`;
- `source_ref`;
- `knowledge_kind`;
- `title`;
- `canonical_uri`;
- `status`;
- `authority_level`;
- `version`;
- `effective_at`;
- `expires_at`;
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
- `deleted_at`.

### 10.4 Campos mínimos do trecho

- `id`;
- `company_id`;
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

### 10.5 Temporalidade bitemporal

A projeção deve distinguir:

- **tempo de validade:** quando o fato, procedimento ou decisão era válido no negócio;
- **tempo de sistema:** quando o APP Versus capturou, alterou ou deixou de considerar aquele registro.

Essa distinção permite responder “o que estava vigente em determinada data?”, reconstruir respostas históricas e corrigir dados sem reescrever silenciosamente o passado.

### 10.6 Grafo de relações

O primeiro grafo deve ser determinístico e persistido no PostgreSQL a partir de FKs e vínculos já existentes. Exemplos:

- decisão `altera` POP;
- POP `orienta` processo;
- instância `executa` processo;
- atividade `entrega` projeto;
- projeto `contribui_para` objetivo;
- indicador `mede` objetivo.

GraphRAG completo, com extração automática de entidades e sínteses globais, deve ser avaliado depois. Ele agrega valor em perguntas panorâmicas sobre grandes coleções não estruturadas, mas aumenta custo, latência e complexidade de governança.

## 11. Contrato extensível de adaptadores

Toda nova fonte deve implementar um contrato equivalente a:

```python
class KnowledgeSourceAdapter:
    source_type: str

    def list_changed_refs(self, *, company_id: int, cursor: str | None) -> ChangePage:
        ...

    def load_source(self, *, company_id: int, source_ref: str, principal: Principal) -> SourceDocument:
        ...

    def resolve_grants(self, *, company_id: int, source_ref: str) -> list[SourceGrant]:
        ...

    def build_chunks(self, source: SourceDocument) -> list[SourceChunk]:
        ...

    def build_canonical_uri(self, source: SourceDocument) -> str:
        ...

    def validate_tenant(self, *, company_id: int, source_ref: str) -> None:
        ...
```

O adaptador também deve declarar:

- tipo de fonte;
- domínio proprietário;
- estratégia de resolução de `company_id`;
- status aceitos;
- regra de autoridade;
- eventos que disparam reindexação;
- campos sensíveis;
- regra de exclusão;
- permissões necessárias;
- testes de isolamento.

O contrato deve versionar adaptador, parser e política de chunking para que uma mudança de transformação possa ser reprocessada, comparada e auditada.

## 12. Registro de fontes

O núcleo deve possuir um `KnowledgeSourceRegistry`, e não imports dispersos.

Exemplo conceitual:

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

Adicionar uma nova fonte passa a exigir:

1. registrar o adaptador;
2. declarar capability e permissões;
3. criar testes de contrato;
4. executar backfill tenant-safe;
5. habilitar rollout;
6. monitorar indexação e consultas.

O pipeline central de recuperação e resposta não deve precisar ser reescrito.

## 13. Modos de atualização do índice

### 13.1 Event-driven

Preferencial para alterações operacionais:

- reunião concluída;
- POP publicado;
- projeto ou atividade atualizada;
- instância concluída ou com falha;
- plano aprovado;
- decisão confirmada.

### 13.2 Reconciliação incremental

Job periódico busca registros alterados desde o último cursor para recuperar eventos perdidos.

Eventos críticos devem preferir **transactional outbox**, evitando o dual write entre a transação do domínio e a fila de indexação.

### 13.3 Backfill

Usado na ativação de uma nova fonte ou empresa. Deve ser:

- idempotente;
- paginado;
- retomável;
- observável;
- limitado por empresa;
- seguro para reexecução.

### 13.4 Exclusão e arquivamento

Remoção, revogação de grant, arquivamento ou troca de tenant deve refletir no índice sem depender apenas de expiração de cache.

### 13.5 Gerações, repetição e recuperação

O pipeline deve possuir:

- fila idempotente de indexação;
- retry isolado por tenant e fonte;
- dead-letter queue;
- checkpoint retomável;
- SLA de freshness por tipo de fonte;
- geração `inactive` construída em paralelo;
- validação antes da troca;
- ativação atômica da nova geração;
- rollback para a geração anterior.

## 14. Recuperação e resposta

Pipeline recomendado:

1. resolver usuário, empresa ativa, surface e permissões;
2. verificar freshness e integridade do snapshot de ACL;
3. classificar intenção, entidades, período e tipos de fonte;
4. materializar e validar o `QueryPlan`;
5. executar consultas SQL e relacionais determinísticas;
6. recuperar candidatos textuais e semânticos já escopados;
7. fundir rankings, preferencialmente com Reciprocal Rank Fusion;
8. reranquear por relevância, autoridade, vigência e recência;
9. expandir o trecho selecionado para seu pai contextual (`Small2Big`);
10. detectar conflito, lacuna e insuficiência de evidência;
11. gerar afirmações somente a partir dos candidatos autorizados;
12. vincular cada afirmação material ao trecho que a suporta;
13. devolver citações e links acessíveis;
14. registrar telemetria sem gravar conteúdo sensível desnecessário.

## 15. Persistência e busca

A arquitetura alvo deve permanecer na stack oficial:

- Python;
- Flask;
- PostgreSQL;
- OpenAI/LangGraph quando aplicável;
- MCP para exposição operacional.

Recomendação técnica para amadurecimento:

- PostgreSQL full-text search para termos exatos e filtros;
- `pgvector` para similaridade semântica, após validação de extensão e operação;
- índice híbrido no mesmo perímetro de dados tenant-safe;
- fusão dos rankings textual e vetorial por RRF, seguida de reranking somente sobre um conjunto pequeno;
- ChromaDB legado mantido apenas até existir plano explícito de migração ou descarte.

O armazenamento vetorial não deve ser tratado como fonte de verdade.

### 15.1 Chunking por fonte e recuperação pai-filho

Não deve existir uma política universal de chunking. Exemplos:

- POP: rotina e passo, preservando ordem e resultado esperado;
- reunião: pauta, discussão, decisão e encaminhamento;
- projeto: resumo do projeto como pai e atividades como filhos;
- planejamento: objetivo como pai, key results e iniciativas como filhos;
- processo: visão do processo como pai, elementos BPMN/SIPOC/POP como filhos.

A busca pode ranquear o filho mais preciso, mas deve entregar ao modelo o pai necessário para interpretação. Essa estratégia reduz perda de contexto sem inflar todos os trechos.

## 16. Segurança e RBAC

### 16.1 Ordem obrigatória

O conteúdo não pode ser recuperado globalmente e filtrado apenas após chegar ao LLM.

Ordem segura:

1. `company_id`;
2. surface;
3. domínio;
4. permissões;
5. grants da fonte;
6. status/visibilidade;
7. busca e ranking;
8. síntese.

Se a ACL estiver ausente, inconsistente, expirada além do SLA ou falhar durante a avaliação, a consulta deve ser negada e registrada. Não é aceitável “tentar responder” com filtro parcial.

### 16.2 Fontes sensíveis

Contratos, finanças, pessoas, auditoria e estratégia podem exigir permissões adicionais por fonte e campo.

### 16.3 Escopos diferentes

Devem existir separações explícitas entre:

- conhecimento da empresa cliente;
- conhecimento global do produto APP Versus;
- conhecimento interno da Versus;
- conteúdo pessoal do usuário;
- referências externas.

Um mesmo índice físico só é aceitável se a segregação lógica e os testes de cross-tenant forem fortes e verificáveis.

As consultas devem declarar um `knowledge_scope`:

- `company`: conhecimento operacional e estratégico da empresa ativa;
- `product`: manual e orientação oficial de uso do APP Versus;
- `combined`: composição controlada, com identificação visual da origem.

Conteúdo `product` é global e versionado por release, mas continua sujeito a audience, perfil, surface e capabilities. Ele não pode herdar nem revelar dados de empresa.

### 16.4 Zonas de confiança e prompt injection

Toda fonte deve ser classificada em:

- `official`;
- `internal`;
- `external_trusted`;
- `external_untrusted`;
- `quarantined`.

Instruções encontradas em documentos, páginas, e-mails ou anexos não podem alterar o system prompt, o `QueryPlan`, as permissões nem acionar tools. Conteúdo externo suspeito deve ser sanitizado, sinalizado ou colocado em quarentena. Conectores externos só entram quando preservarem ACL, exclusão e identidade da origem.

## 17. MCP e Sapiens

O domínio proposto deve nascer como leitura:

- `search_organizational_knowledge`;
- `answer_organizational_question`;
- `get_knowledge_source`;
- `list_knowledge_sources`;
- `report_knowledge_gap`.

Regras:

- `user`: leitura das fontes autorizadas;
- `analytics`: análise transversal tenant-safe;
- `admin`: gestão de adaptadores, rollout, backfill e grants;
- `ops`: diagnóstico técnico de indexação, sem atalho para conteúdo;
- mutações de fontes continuam nos domínios proprietários;
- ausência de permissão não deve revelar nem a existência de fonte restrita.

Não há justificativa inicial para criar um novo agente. O Sapiens e os agentes existentes devem consumir a capability de conhecimento via MCP.

## 18. Experiência de uso

### 18.1 Princípio norteador: robustez invisível

A interface deve ser simples sem simplificar indevidamente a arquitetura:

- uma única caixa aceita pergunta ou palavras-chave;
- o sistema interpreta automaticamente a melhor estratégia;
- nenhuma expressão como RAG, embedding, busca vetorial, RRF ou `QueryPlan` aparece para o usuário comum;
- filtros avançados permanecem recolhidos até serem necessários;
- a resposta curta aparece primeiro;
- evidências, conflitos, histórico e detalhes técnicos são revelados progressivamente;
- o usuário sempre consegue voltar à fonte original;
- o sistema não exige que a pessoa saiba previamente onde a informação está armazenada.

O princípio de produto é:

> **simples para perguntar, rápido para compreender, seguro para confiar e profundo quando necessário.**

### 18.2 Uma porta de entrada, três comportamentos internos

O backend deve distinguir três comportamentos, sem obrigar o usuário a escolher um modo antes de perguntar:

1. `find`: localizar um objeto ou registro conhecido;
2. `answer`: responder objetivamente a partir de fontes autorizadas;
3. `investigate`: cruzar múltiplas fontes, relações e períodos.

A interface pode informar discretamente “Busca rápida” ou “Investigação aprofundada” e permitir troca manual, mas a escolha inicial deve ser automática. Complexidade adicional deve seguir **divulgação progressiva**, por meio de um botão como `Refinar pesquisa`.

### 18.3 Composição padrão da resposta

A resposta padrão deve separar:

#### Resposta

Síntese direta da pergunta.

#### Confiança operacional

Sinais legíveis, e não um percentual opaco:

- `Procedimento oficial`;
- `Publicado e vigente`;
- `Verificado por <responsável> em <data>`;
- `Decisão posterior ainda não incorporada`;
- `Informação histórica, não normativa`;
- `Evidência insuficiente`.

#### Evidências

Trechos e fatos usados.

#### Fontes

Objeto, data, versão, status e link.

As citações devem ser associadas às afirmações, e não apenas listadas ao final. Cada referência precisa carregar `source_ref`, trecho ou `source_span`, versão, validade e URI canônica.

#### Conflitos ou ressalvas

Conteúdo divergente, desatualizado, não aprovado ou insuficiente.

#### Confiança

Indicador baseado em cobertura e qualidade das fontes, nunca apenas na confiança subjetiva do modelo.

#### Ações seguras

Conforme o tipo de resposta:

- `Abrir fonte`;
- `Ver trecho`;
- `Ver histórico`;
- `Comparar versões`;
- `Ver decisões relacionadas`;
- `Abrir projeto ou atividade`;
- `Solicitar revisão`;
- `Registrar lacuna`.

Qualquer mutação continua subordinada ao workflow do domínio proprietário e aos gates humanos aplicáveis.

### 18.4 Cartões tipados

Resultados não devem ser exibidos como uma lista homogênea de documentos. O APP Versus deve apresentar cartões específicos para:

- procedimento/POP;
- processo;
- reunião;
- decisão;
- instância de processo;
- projeto;
- atividade;
- objetivo/OKR;
- indicador;
- pessoa, especialista ou responsável.

Cada cartão deve priorizar os atributos que ajudam a decisão: status, vigência, responsável, prazo, relação com a pergunta e ação principal.

### 18.5 Escopo visível, mas não obrigatório

O usuário deve poder refinar por:

- período;
- tipo de fonte;
- processo;
- projeto;
- área;
- planejamento ou objetivo;
- status;
- conteúdo oficial, interno ou externo.

O padrão deve ser “fontes autorizadas relevantes”. O sistema não deve exigir configuração prévia para uma pergunta comum, mas precisa mostrar claramente quando utilizou web, conteúdo externo ou fonte não verificada.

### 18.6 Uso contextual

A capability não deve viver apenas em uma página isolada. Ela deve poder aparecer:

- na busca global do APP Versus;
- no Sapiens via MCP;
- dentro de processo, reunião, projeto, planejamento e indicador;
- em canais autorizados, como WhatsApp ou integrações futuras.

No uso contextual, o objeto aberto deve entrar como escopo sugerido, nunca como limitação oculta.

## 19. Exemplos de comportamento

### 19.1 Venda para pessoa jurídica

1. procurar POP publicado vigente;
2. filtrar pelo tenant e grants;
3. retornar passos, responsável, resultado esperado e link;
4. citar eventual política ou decisão complementar;
5. não usar instância histórica como norma principal.

### 19.2 Última reunião

1. localizar a última reunião concluída por data real, com fallback temporal documentado;
2. extrair decisões, responsáveis, prazos e atividades;
3. informar qual reunião foi considerada;
4. não pedir ID se a expressão temporal resolver unicamente a fonte.

### 19.3 Manutenção elétrica

1. buscar semanticamente em POPs, processos, atas, decisões, projetos e instâncias;
2. organizar resultados por tipo e data;
3. distinguir regra, decisão e ocorrência;
4. mostrar conflito ou ausência de definição oficial.

### 19.4 Atraso estratégico

1. localizar objetivo/OKR;
2. seguir vínculos para projetos, atividades, processos e indicadores;
3. consultar atrasos e bloqueios;
4. apresentar fatos operacionais que sustentam a conclusão.

## 20. Telemetria e qualidade

Métricas mínimas:

- fontes habilitadas por empresa;
- objetos elegíveis e indexados;
- atraso de indexação;
- falhas por adaptador;
- consultas sem resultado;
- consultas com conflito;
- respostas abertas pelo usuário;
- feedback útil/não útil;
- fontes mais citadas;
- tentativas negadas por RBAC;
- testes de cross-tenant;
- custo de embeddings e inferência.

Pergunta sem resposta deve poder gerar um `knowledge_gap`, não uma alucinação.

### 20.1 Harness de avaliação

Antes de rollout, cada adaptador e cada mudança de retrieval deve ser validado por um conjunto dourado de perguntas reais, versionado por domínio e tenant de teste. O conjunto deve incluir:

- respostas determinísticas;
- perguntas sem resposta;
- fontes conflitantes;
- consultas “vigente agora” e “vigente em determinada data”;
- vocabulário equivalente;
- relações entre estratégia, projeto, atividade e indicador;
- tentativa de acesso cross-tenant;
- tentativa de acesso a fonte sem grant;
- conteúdo com prompt injection;
- ACL revogada ou desatualizada.

Métricas mínimas:

- Recall@K e NDCG do retrieval;
- groundedness;
- completude da resposta;
- precisão e completude das citações;
- abstenção correta;
- detecção de conflito;
- freshness;
- latência e custo;
- zero exposição cross-tenant ou não autorizada.

RAGAS, RAGChecker e avaliadores equivalentes podem apoiar a medição, mas não substituem testes determinísticos de ACL, temporalidade e isolamento.

## 21. Critérios de entrada de uma nova fonte

Uma fonte só pode ser habilitada quando:

1. possuir proprietário funcional;
2. resolver `company_id` sem ambiguidade;
3. declarar status elegíveis;
4. declarar autoridade e vigência;
5. possuir URI canônica;
6. resolver grants;
7. definir campos sensíveis;
8. suportar atualização e exclusão;
9. possuir testes de contrato;
10. possuir smoke cross-tenant;
11. possuir política de observabilidade;
12. possuir rollback ou desativação por feature flag.

## 22. Recorte recomendado do MVP

### Fontes

- publicações de processos e POPs;
- reuniões concluídas;
- instâncias de processos;
- projetos e atividades;
- planos, OKRs e key results;
- identidade e alinhamento estratégico;
- indicadores necessários para responder às relações estratégicas.

### Capacidades

- consulta somente leitura;
- busca determinística, textual e semântica;
- citações;
- ACL;
- detecção básica de conflito;
- feedback;
- registry de adaptadores;
- backfill incremental por empresa.

### Fora do MVP

- ingestão irrestrita de arquivos externos;
- indexação de e-mails pessoais;
- alteração automática da fonte;
- aprovação automática de decisão;
- agente autônomo específico;
- respostas sem proveniência;
- mutações financeiras ou contratuais.
- Elasticsearch ou outro motor adicional sem evidência de necessidade;
- GraphRAG completo;
- agentes autônomos de pesquisa;
- conectores externos que não preservem ACL;
- indexação indiscriminada de e-mails ou arquivos pessoais.

## 23. Sequência de evolução documental

Após amadurecimento e aceite deste Paper:

1. criar a SPEC oficial do domínio `knowledge`;
2. alinhar Manifesto de identidade e limites;
3. criar Playbook de inclusão de fontes;
4. criar Runbook de backfill, reindexação e incidente;
5. criar Harness de recuperação, resposta e avaliação;
6. só então implementar modelos, registry, services, tools e UI.

## 24. Questões que a SPEC deverá congelar

- `knowledge` será confirmado como domínio canônico?
- quais statuses tornam cada fonte elegível?
- como decisões de reunião passam a ser consideradas oficiais?
- qual precedência formal entre decisão e POP publicado?
- quais perfis podem consultar estratégia, contratos e auditoria?
- a extensão `pgvector` estará disponível no PostgreSQL de produção?
- qual política de retenção das projeções e logs?
- quais fontes serão habilitadas por padrão para cada empresa?
- como será feita a migração ou retirada do ChromaDB legado?
- qual schema oficial do `QueryPlan` e quais estratégias podem ser combinadas?
- qual SLA de freshness torna uma ACL inválida e provoca `fail closed`?
- qual modelo bitemporal será adotado?
- qual taxonomia oficial de zonas de confiança e quarentena?
- qual contrato de citação por afirmação?
- quais métricas e thresholds bloqueiam rollout?
- qual modelo inicial de relações determinísticas?

## 25. Decisão proposta

Avançar para uma SPEC de **Camada de Conhecimento Corporativo Extensível**, com:

- PostgreSQL como núcleo de persistência e filtragem;
- busca híbrida;
- MCP First;
- registry de adaptadores;
- inclusão inicial das nove famílias de fontes da Onda 1;
- governança explícita de autoridade, status, vigência, grants e conflitos;
- possibilidade de adicionar novas fontes sem alterar o núcleo.
- `QueryPlan` tipado e auditável;
- ACL `fail closed` com controle de freshness;
- temporalidade bitemporal;
- citações por afirmação;
- chunking por fonte e recuperação pai-filho;
- RRF e reranking;
- grafo relacional determinístico no PostgreSQL;
- zonas de confiança contra prompt injection;
- harness de avaliação como gate de rollout.

## 26. Comparação com práticas externas

A pesquisa em fontes técnicas primárias reforça que o desenho-base está correto — busca híbrida, fonte soberana, ACL antes do modelo, proveniência e adaptadores — e indica os incrementos incorporados neste Paper:

| Prática externa | Aplicação proposta no APP Versus |
|---|---|
| PostgreSQL full-text search e `pgvector` híbrido | manter busca, filtros tenant e vetores no perímetro PostgreSQL; usar RRF e reranking |
| Índices hierárquicos e `Small2Big` | chunking específico por fonte, recuperação filho-pai |
| GraphRAG local/global | começar por relações determinísticas; postergar grafo extraído e busca global |
| W3C PROV | registrar origem, derivação, transformação e versões do pipeline |
| ACL documental em motores corporativos | persistir snapshot verificável, sincronizar e falhar fechado |
| Transactional outbox | garantir entrega consistente de mudanças à indexação |
| OWASP para prompt injection e embeddings | tratar fonte como dado não confiável, aplicar trust zones e quarentena |
| RAGAS, RAGChecker e ALCE | medir retrieval, groundedness, completude e qualidade das citações |

## 27. Referências primárias da pesquisa

- PostgreSQL — [Full Text Search](https://www.postgresql.org/docs/current/textsearch-intro.html)
- pgvector — [Open-source vector similarity search for PostgreSQL](https://github.com/pgvector/pgvector)
- Microsoft — [Advanced retrieval-augmented generation](https://learn.microsoft.com/en-au/azure/developer/ai/advanced-retrieval-augmented-generation)
- Microsoft GraphRAG — [Query overview](https://microsoft.github.io/graphrag/query/overview/)
- W3C — [PROV Primer](https://www.w3.org/TR/prov-primer/) e [PROV-O](https://www.w3.org/TR/prov-o/)
- Microsoft Azure AI Search — [Document-level access control](https://learn.microsoft.com/en-us/azure/search/search-query-access-control-rbac-enforcement)
- Microsoft Graph — [External item](https://learn.microsoft.com/en-us/graph/api/resources/externalconnectors-externalitem) e [external groups](https://learn.microsoft.com/en-us/graph/connecting-external-content-external-groups)
- Debezium — [Outbox Event Router](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html)
- OWASP GenAI — [Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) e [Vector and Embedding Weaknesses](https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/)
- NIST — [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- Lewis et al. — [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401)
- Es et al. — [RAGAS](https://arxiv.org/abs/2309.15217)
- Ru et al. — [RAGChecker](https://arxiv.org/abs/2408.08067)
- Gao et al. — [ALCE: Enabling Large Language Models to Generate Text with Citations](https://arxiv.org/abs/2305.14627)

## 28. Pesquisa funcional e de usabilidade do mercado

A análise de produtos de busca e conhecimento corporativo mostra uma convergência funcional:

| Padrão observado | Produtos de referência | Aplicação proposta no APP Versus |
|---|---|---|
| uma busca sobre múltiplas fontes | Glean, Rovo, Microsoft 365 Copilot Search, Slack | uma porta de entrada para todas as fontes autorizadas do tenant |
| resposta direta seguida dos resultados | Guru, Rovo, Notion, Slack | síntese curta no topo e cartões de objetos abaixo |
| modos de busca, conversa e pesquisa | Guru, Notion, Rovo | `find`, `answer` e `investigate`, escolhidos automaticamente |
| seleção de fontes e contexto | Notion, Guru, Slack | refinamento opcional por fontes, período e objetos APP Versus |
| cartões de pessoas, equipes e definições | Rovo, Gemini Enterprise | cartões tipados de pessoas, POPs, decisões, projetos, objetivos e indicadores |
| bookmarks, siglas e respostas curadas | Rovo, Microsoft 365 Copilot Search | glossário e respostas oficiais administráveis |
| verificação por especialista | Guru, Slite, Notion | responsável, validade, verificação e fila de revisão |
| explicação e diagnóstico da resposta | Guru | painel `Como esta resposta foi construída?`, sem expor chain-of-thought |
| conhecimento dentro do fluxo de trabalho | Slack, Rovo, Glean | busca global, módulos APP Versus, Sapiens e canais autorizados |
| detecção de gaps e conteúdo desatualizado | Guru, Slite | cockpit de lacunas, conflitos, fontes vencidas e respostas mal avaliadas |
| pesquisa aprofundada e relatório | Notion, Guru, Gemini Enterprise, Rovo | investigação multifuente com plano, progresso e relatório citável |
| passagem de resposta para ação | Glean, Rovo, Slack | abrir objeto e iniciar workflow seguro, sem mutação autônoma |

O mercado valida a necessidade da camada proposta, mas a maioria das ofertas é centrada em documentos, mensagens e conectores. O diferencial do APP Versus deve ser trabalhar nativamente com **objetos de gestão estruturados e suas relações de execução**.

## 29. Diferencial funcional: Trilha Decisão–Execução

O APP Versus deve permitir navegar e consultar a cadeia:

```text
decisão/diretriz
    -> política ou POP
        -> processo
            -> instâncias e evidências
    -> projeto
        -> atividades
            -> objetivo estratégico
                -> indicador e resultado
```

Essa trilha deve responder perguntas como:

- a decisão já foi incorporada ao procedimento?
- quais atividades executam esta decisão?
- o procedimento vigente está sendo seguido nas instâncias?
- quais projetos contribuem para este objetivo?
- qual indicador comprova o resultado?
- quais decisões não possuem desdobramento operacional?
- quais problemas recorrentes ainda não geraram decisão ou projeto?

Esse é um diferencial mais valioso que competir apenas por quantidade de conectores.

## 30. Cockpit de curadoria do conhecimento

A simplicidade da interface do usuário depende de uma operação forte nos bastidores. Gestores e curadores devem possuir uma área separada para:

- perguntas sem resposta;
- respostas com avaliação negativa;
- conflitos entre fontes;
- conteúdo vencido ou próximo da revisão;
- fontes sem responsável;
- decisões ainda não incorporadas a procedimentos;
- documentos duplicados ou concorrentes;
- fontes nunca utilizadas;
- temas mais pesquisados;
- lacunas por área, processo, projeto ou objetivo;
- fila de revisão priorizada por impacto e uso;
- evolução da cobertura e da confiança.

O cockpit não deve ser exposto ao usuário comum nem sobrecarregar a experiência de consulta.

## 31. Feedback e ciclo de melhoria

O feedback simples `útil/não útil` deve ser complementado, quando negativo, por motivos opcionais:

- incorreto;
- desatualizado;
- incompleto;
- fonte inadequada;
- não respondeu à pergunta;
- não deveria estar acessível;
- conflito não sinalizado.

Uma resposta útil pode ser compartilhada. Uma resposta incorreta pode gerar:

1. registro no cockpit;
2. vínculo com fontes e afirmações envolvidas;
3. encaminhamento ao responsável;
4. revisão da fonte ou regra;
5. reindexação;
6. nova avaliação da pergunta original.

O feedback não pode promover automaticamente uma informação a conhecimento oficial.

## 32. Jornadas funcionais de referência

### 32.1 “Como faço uma venda para pessoa jurídica?”

Interface esperada:

1. o usuário digita a pergunta na caixa única;
2. o sistema responde em poucos passos, priorizando o POP vigente;
3. mostra selo `Procedimento oficial`;
4. exibe responsável, validade e data da última revisão;
5. oferece `Abrir POP`, `Ver passos completos` e `Solicitar revisão`;
6. apresenta decisão complementar somente como ressalva citada.

O usuário não escolhe tabelas, fontes nem tipo de busca.

### 32.2 “O que foi decidido na última reunião?”

Interface esperada:

1. o sistema identifica automaticamente a última reunião concluída e autorizada;
2. informa explicitamente qual reunião foi considerada;
3. apresenta cartões de decisão, responsável, prazo e atividade criada;
4. permite abrir ata, projeto relacionado e histórico;
5. sinaliza quando uma discussão não se converteu em decisão formal.

### 32.3 “Existe algo definido sobre manutenção elétrica?”

Interface esperada:

1. a interface informa `Investigando processos, POPs, reuniões, projetos e instâncias`;
2. entrega uma síntese organizada em `Definições oficiais`, `Decisões`, `Execuções` e `Lacunas`;
3. mostra uma linha do tempo dos registros relevantes;
4. evidencia contradições e falta de responsável;
5. oferece `Registrar lacuna` ou `Solicitar definição`, sem criar norma automaticamente.

## 33. Priorização funcional

### P0 — MVP utilizável

- caixa única de busca e pergunta;
- escolha automática entre `find`, `answer` e `investigate`;
- resposta objetiva com citações por afirmação;
- cartões tipados;
- sinais de autoridade, vigência e verificação;
- refinamento opcional por fonte e período;
- ações para abrir fonte, ver trecho e registrar lacuna;
- feedback com motivo;
- histórico individual de consultas;
- cockpit básico de perguntas sem resposta e avaliações negativas.

### P1 — diferenciação APP Versus

- Trilha Decisão–Execução;
- linha do tempo de decisões e mudanças;
- comparação de versões;
- detecção de contradições e pendências de governança;
- glossário de termos e siglas;
- cartões de especialistas e responsáveis;
- perguntas sugeridas conforme o módulo aberto;
- consultas salvas e compartilháveis;
- fila de verificação por responsável;
- mapa de cobertura do conhecimento.

### P2 — evolução

- alertas sobre temas, fontes ou decisões acompanhadas;
- resumo periódico personalizado;
- investigação aprofundada com plano revisável;
- sugestão de atualização documental com diff e aprovação humana;
- presença contextual em navegador e canais externos;
- geração de minuta de POP, decisão, projeto ou atividade a partir de resposta validada;
- recomendações proativas baseadas no contexto autorizado.

## 34. Requisitos de simplicidade e aceitação de UX

A SPEC deve congelar critérios verificáveis:

1. uma pergunta comum pode ser feita sem selecionar fonte ou modo;
2. a primeira resposta útil deve caber na primeira viewport em desktop;
3. fonte, status, vigência e ressalvas devem ser compreensíveis sem abrir detalhes;
4. filtros avançados ficam recolhidos por padrão;
5. a fonte original pode ser aberta em no máximo duas ações;
6. toda citação oferece preview do trecho;
7. investigação longa apresenta progresso compreensível e pode ser cancelada;
8. ausência de resposta é comunicada com clareza e oferece registro de lacuna;
9. nenhum termo técnico de retrieval aparece na interface comum;
10. teclado, leitura assistiva, contraste, foco e responsividade devem ser testados;
11. a interface deve funcionar adequadamente em desktop e mobile;
12. testes de usabilidade devem usar pessoas reais de diferentes perfis e familiaridade digital.

Indicadores de produto:

- tempo até primeira resposta útil;
- taxa de sucesso sem reformular a pergunta;
- taxa de abertura das citações;
- respostas úteis versus negativas;
- perguntas sem resposta;
- tempo para resolver um `knowledge_gap`;
- uso por área e perfil;
- retorno de usuários;
- abandono da investigação;
- volume de “perguntei a uma pessoa porque não confiei na resposta”.

## 35. O que não fazer

- expor a arquitetura técnica na interface;
- criar uma tela cheia de filtros antes da primeira pergunta;
- obrigar o usuário a escolher um agente ou fonte para começar;
- entregar apenas chat, sem resultados, objetos e navegação;
- misturar web e fontes internas sem identificação;
- usar um percentual genérico de “confiança da IA”;
- esconder conflito para produzir uma resposta mais limpa;
- automatizar alteração de fonte oficial sem aprovação;
- priorizar dezenas de conectores antes de validar as fontes nativas;
- criar experiências diferentes e inconsistentes em cada módulo.

## 36. Referências funcionais de mercado

- Glean — [Workplace Search](https://www.glean.com/enterprise-search)
- Guru — [Verification](https://www.getguru.com/features/verification), [Search and Chat](https://help.getguru.com/docs/searching-for-knowledge-in-guru) e [AI Agent Center](https://help.getguru.com/docs/training-guru-ai-agent-center)
- Atlassian — [Rovo Search](https://support.atlassian.com/rovo/docs/search/) e [Rovo Features](https://www.atlassian.com/software/rovo/features)
- Notion — [Enterprise Search](https://www.notion.com/en-gb/help/enterprise-search) e [Research Mode](https://www.notion.com/en-gb/help/research-mode)
- Microsoft — [Copilot Search](https://learn.microsoft.com/en-us/microsoft-365/copilot/connectors/copilot-search) e [Admin Experience](https://learn.microsoft.com/en-us/microsoft-365/copilot/microsoft-365-copilot-search-admin-experience)
- Google Cloud — [Gemini Enterprise](https://cloud.google.com/gemini-enterprise) e [Knowledge Graph](https://docs.cloud.google.com/gemini/enterprise/docs/use-knowledge-graph-search)
- Slack — [Enterprise Search](https://slack.com/features/enterprise-search) e [Guide to AI Features](https://slack.com/help/articles/25076892548883-Guide-to-AI-features-in-Slack)
- Slite — [Ask](https://slite.com/ask) e [Self-maintaining Knowledge Base](https://slite.com/changelog/the-self-maintaining-knowledge-base)

## 37. Decisão integrada proposta

Evoluir para uma SPEC que trate a camada como produto, e não apenas como mecanismo de busca:

- **núcleo robusto:** tenant-safe, híbrido, temporal, citável, auditável e extensível;
- **superfície simples:** uma porta de entrada, resposta direta e complexidade progressiva;
- **governança operacional:** curadoria, verificação, gaps, conflitos e responsáveis;
- **diferencial APP Versus:** Trilha Decisão–Execução conectando gestão e realidade operacional;
- **adoção mensurável:** critérios de usabilidade e indicadores de valor desde o MVP.

## 38. Sapiens como porta de entrada

O botão global do Sapiens deve abrir a mesma capability de conhecimento em um painel lateral, preservando a página atual. A experiência proposta possui dois escopos primários:

- `Minha empresa`: processos, decisões, reuniões, projetos, atividades, estratégia e indicadores;
- `Como usar o APP Versus`: manual interativo e orientação contextual do produto.

O Sapiens deve rotear automaticamente a intenção, mas o escopo selecionado precisa permanecer visível e alterável. Perguntas combinadas podem usar `Todos`, identificando claramente quais afirmações vieram do produto e quais vieram da empresa.

O painel recebe contexto autorizado da tela atual:

- route e módulo;
- objeto aberto, quando aplicável;
- empresa ativa;
- usuário, perfil e capabilities;
- versão do APP Versus;
- idioma.

O contexto aparece como sugestão removível. Ele não pode limitar silenciosamente a pesquisa nem substituir a validação de permissão.

## 39. Fonte governada `product_help`

O manual interativo deve entrar na camada como uma família de fontes global, separada das fontes tenant-owned.

Campos conceituais adicionais:

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
- `verified_at`;
- `content_checksum`.

Tipos de ajuda:

- `concept`: significado de módulo, campo ou conceito;
- `how_to`: passos para realizar uma tarefa;
- `navigation`: localização de funcionalidade;
- `permission_explanation`: motivo de uma ação não estar disponível;
- `troubleshooting`: resolução orientada de dificuldade conhecida;
- `guided_tour`: sequência interativa sobre a interface;
- `release_change`: mudança relevante entre versões.

Regras de governança:

1. somente conteúdo publicado e compatível com a versão ativa pode ser oficial;
2. toda orientação possui proprietário, audience e data de verificação;
3. mudança de rota, template, capability ou fluxo deve invalidar a orientação afetada;
4. ajuda para funcionalidade sem permissão explica a restrição sem oferecer bypass;
5. conteúdo global do produto nunca recebe `company_id` artificial;
6. customização específica da empresa permanece em `company`, não em `product`;
7. drift entre interface, manual, tour e capability bloqueia publicação da orientação.

## 40. Manual interativo

Uma resposta de uso do APP Versus deve oferecer, conforme disponibilidade:

- orientação curta;
- passos numerados;
- fonte e versão do manual;
- `Levar-me até lá`;
- `Iniciar orientação`;
- `Mostrar nesta tela`;
- `Abrir manual completo`;
- `Não encontrei esta opção`;
- `Reportar orientação desatualizada`.

### 40.1 Navegação assistida

`Levar-me até lá` resolve um `route_key` registrado e autorizado. Não deve executar URL arbitrária produzida pelo modelo.

Antes de navegar:

1. validar empresa ativa quando a rota for tenant-owned;
2. validar perfil, surface e capability;
3. validar existência e disponibilidade da rota;
4. preservar retorno à página anterior;
5. registrar telemetria sem conteúdo sensível desnecessário.

### 40.2 Tour guiado

Tours devem usar identificadores estáveis, como `data-help-id`, e não seletores CSS frágeis. Cada passo pode:

- destacar um elemento;
- explicar sua finalidade;
- aguardar ação do usuário;
- navegar para uma route registrada;
- avançar, voltar ou encerrar.

O tour não pode:

- preencher ou enviar dados sensíveis sem confirmação;
- clicar automaticamente em ações destrutivas;
- contornar aprovação;
- executar mutação por texto gerado;
- continuar quando a tela ou capability não corresponder à definição publicada.

### 40.3 Diagnóstico contextual

Quando o usuário disser “não encontro o botão”, o Sapiens deve distinguir:

- elemento mudou de localização;
- etapa anterior não foi concluída;
- objeto está em status incompatível;
- capability não concedida;
- funcionalidade não está habilitada para a empresa;
- orientação está desatualizada;
- erro real de interface.

A resposta deve explicar a causa observável e indicar o próximo passo seguro.

## 41. Ciclo de manutenção do manual

O manual precisa participar do ciclo de release:

1. mudança funcional identifica artigos e tours impactados;
2. conteúdo atualizado entra como rascunho;
3. QA valida links, routes, capabilities e `data-help-id`;
4. responsável funcional revisa a orientação;
5. publicação ocorre vinculada à versão;
6. versão anterior permanece auditável;
7. feedback e falhas reais alimentam a fila de melhoria.

Indicadores específicos:

- perguntas de ajuda por módulo;
- taxa de resolução sem suporte humano;
- uso de `Levar-me até lá`;
- início e conclusão de tours;
- abandono por etapa;
- orientação avaliada como desatualizada;
- routes ou elementos não encontrados;
- funcionalidades descobertas após orientação;
- redução de chamados recorrentes.

## 42. Jornada de referência

Pergunta:

> “Como publico um processo no Portal de Processos?”

Comportamento esperado:

1. o Sapiens detecta intenção `product_help`;
2. mostra o escopo `Como usar o APP Versus`;
3. considera a página e o processo abertos como contexto sugerido;
4. verifica se o usuário pode editar e publicar;
5. apresenta pré-requisitos e passos compatíveis com a versão atual;
6. oferece `Levar-me até o processo` e `Iniciar orientação`;
7. o tour destaca `Fluxo / POP`, valida os pré-requisitos e conduz até a publicação;
8. a confirmação final continua no workflow oficial;
9. qualquer divergência pode ser reportada como orientação desatualizada.

## 43. Decisão complementar

Incluir `product_help` no domínio `knowledge` e usar o botão do Sapiens como front door compartilhado, mantendo:

- separação rigorosa entre produto e conhecimento da empresa;
- uma interface simples com escopo visível;
- manual versionado e governado como fonte oficial;
- navegação por route registrada;
- tours por identificadores estáveis;
- RBAC e capability gates;
- nenhuma mutação autônoma;
- cockpit de qualidade e telemetria de adoção.

## 44. Evolução executável — busca citada

O primeiro corte de recuperação deve permanecer determinístico e simples:

1. o backend materializa um `QueryPlan` validado;
2. o escopo da empresa vem do contexto autenticado;
3. conteúdo global do produto e conteúdo tenant-owned são filtrados antes do ranking;
4. PostgreSQL FTS é a estratégia primária, com SQL portável nos testes;
5. ausência de evidência gera abstenção explícita;
6. toda afirmação retornada aponta para citação e URI registrada;
7. o MCP apenas delega ao mesmo service;
8. o usuário nunca informa `company_id` no texto ou argumento da tool.

Esse corte valida o núcleo de resposta antes do painel Sapiens e antes de qualquer busca semântica.

## 45. Evolução executável — fontes corporativas com acesso projetado

A primeira expansão tenant-owned deve privilegiar fontes de alta autoridade e
preservar a autorização da origem:

1. somente a publicação vigente de cada Processo/POP entra no índice;
2. atas entram apenas quando a reunião estiver concluída;
3. o índice recebe grants de empresa, usuário ou colaborador;
4. recuperação acontece somente após a validação desses grants;
5. grants contextuais ainda não representáveis, como processo ou atividade, são
   ignorados com falha fechada;
6. reunião sem participante interno identificável pode ser projetada, mas não
   recuperada;
7. cada empresa é sincronizada isoladamente e deixa evidência no ledger.

Essa decisão mantém a interface simples sem transformar o índice em um atalho de
acesso. A fonte continua soberana, e a projeção só amplia a descoberta dentro do
mesmo perímetro de autorização.

## 46. Evolução executável — catálogo integral do manual

Em 2026-07-31, o manual passou a combinar três bases globais complementares:

1. artigos `product_help` curados para procedimentos críticos;
2. catálogo de navegação compilado automaticamente a partir do menu oficial;
3. Papers e SPECs projetados pelo adapter `system_documentation`.

O catálogo inicial cobre todas as entradas navegáveis identificadas no menu e
inclui procedimentos curados para títulos financeiros em aberto e conciliação
bancária. Novas entradas de menu passam a produzir ajuda de navegação na próxima
sincronização, enquanto novos Papers e SPECs entram por checksum e versão.

A compilação automática não autoriza inventar procedimentos: ela garante a
cobertura mínima de descoberta e navegação. Passos operacionais específicos
continuam exigindo artigo curado e validação contra a interface publicada.


## 47. Evolução cognitiva supervisionada

A qualidade percebida do Sapiens depende de duas competências distintas: recuperar
a fonte correta e entender a intenção real da pergunta. A experiência recente mostrou
que uma resposta pode estar tecnicamente correta e ainda assim ser inútil quando o
roteamento inicial escolhe o domínio errado. Por isso, a camada de conhecimento deve
ganhar uma etapa explícita de entendimento antes do ranking de fontes.

A etapa de entendimento classifica pelo menos:

- `product_help`: aprender a usar o APP Versus;
- `corporate_knowledge`: consultar decisões, POPs, atas, processos ou estratégia;
- `operational_action`: executar ou preparar uma ação operacional;
- `diagnostic`: analisar situação, tendência ou indicador;
- `technical`: arquitetura, API, MCP, SPEC ou implementação.

Perguntas iniciadas por expressões como “como faço”, “onde vejo”, “como cadastro”,
“como gero” e “como filtro” devem favorecer `product_help` quando não houver pedido
explícito de execução. Quando a confiança for baixa, a resposta correta é perguntar
um esclarecimento curto, não acionar uma tool adjacente nem devolver documentação
técnica.

A evolução cognitiva deve ser supervisionada por usuários e curadores. O usuário
avalia cada resposta como `certo`, `parcial` ou `errado`; nos casos `parcial` ou
`errado`, pode indicar o motivo e o que esperava. Esses sinais alimentam uma base
de treinamento do APP Versus, não treinam diretamente o modelo de linguagem em
produção. A aprendizagem inicial ajusta aliases, roteamento, priorização de fontes,
perguntas de esclarecimento e artigos de manual.

O Robô Treinador do Sapiens opera como curador assistido:

1. agrupa perguntas semelhantes com baixo acerto;
2. identifica intenção/domínio provável e fontes usadas indevidamente;
3. sugere aliases, novos artigos ou ajustes de ranking;
4. mantém propostas em fila de curadoria;
5. só aplica mudanças após aprovação humana ou política explícita de baixo risco.

Esse ciclo transforma o feedback real em melhoria auditável, tenant-safe e
reversível, sem permitir que uma avaliação isolada oficialize conhecimento ou
contorne ACL, capability ou autoridade da fonte.

## 48. Fase 1 — Golden Set antes de ampliar inteligência

A primeira execução prática da evolução cognitiva deve começar por um conjunto
pequeno e versionado de perguntas reais. O objetivo não é aumentar complexidade,
mas proteger a experiência simples do usuário contra respostas longas, técnicas ou
fora de assunto.

O Golden Set Fase 1 cobre perguntas de uso recorrente do APP Versus:

1. minhas atividades;
2. conta a pagar;
3. títulos financeiros em aberto;
4. conciliação bancária;
5. publicação de processo em Fluxo / POP.

Cada pergunta registra a intenção esperada, domínio, atalhos internos e termos que
devem aparecer na resposta. A validação também bloqueia termos técnicos internos
para usuário comum, como MCP, API, endpoint, SPEC, Paper e nomes de funções.

Essa abordagem cria uma régua objetiva para treinar o Sapiens: antes de discutir
RAG vetorial ou modelos mais sofisticados, o sistema precisa acertar o básico com
linguagem simples e ação navegável.

