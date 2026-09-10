# Harness — reconciliação Alembic para OAuth

**Classe documental:** Harness
**Status:** read-only; obrigatório antes de qualquer `stamp` ou upgrade OAuth

## Uso

Execute contra uma cópia isolada do banco:

```powershell
python app32/scripts/qa/audit_alembic_reconciliation.py --database-url <url-local>
```

O harness compara o ledger `alembic_version` com marcadores físicos
conhecidos (tabelas, colunas, índices, constraints nomeadas e fragmentos de
definições sensíveis) e mapeia a
cadeia pendente até os heads Alembic. Ele nunca executa DDL, seed, backfill,
`stamp` ou upgrade.

Para cada revision pendente, ele também identifica estaticamente no trecho de
`upgrade` as classes que exigem evidência: schema idempotente, schema não
idempotente, mutation de dados e SQL bruto. A classificação não autoriza nem
substitui a validação de schema/dados; ela evita que migrations de seed ou
`CREATE TABLE IF NOT EXISTS` sejam tratadas como inofensivas.
Operações Alembic como `add_column`, `create_index`, `alter_column` e criação
de FKs/constraints também são tratadas como schema não idempotente.
O classificador extrai a função `upgrade` pela AST; operações presentes apenas
em `downgrade`, inclusive em funções com anotação de retorno, não entram na
evidência do avanço.

Para alterações que reutilizam o mesmo nome de constraint, o marcador exige
um fragmento semântico da definição. Assim, a presença do nome não mascara a
ausência de um novo valor permitido, como `conversion_requested`.
O mesmo mecanismo valida fragmentos dos defaults de colunas quando a migration
altera comportamento de escrita sem criar uma nova tabela.
Seeds de protocolos são auditados separadamente por versão, nota e escopo
global/tenant-AA. Ausência total é compatível com revision pendente; presença
parcial ou divergente exige reconciliação, nunca `stamp`.
Backfills de dados possuem marcadores próprios: candidatos ainda pendentes,
artefatos gerados e vínculos materializados são comparados para diferenciar
uma revision ainda ausente de uma execução parcial.

## Regra de decisão

`complete_candidate` significa somente que os objetos-base existem. Antes de
alterar o ledger é obrigatório validar colunas, índices, constraints, conteúdo
de seeds e reversibilidade para toda a sequência. Enquanto isso não ocorrer,
o caminho OAuth continua bloqueado e R05 não pode ser ligado.

## Evidência local em 2026-09-10

O primeiro marcador da cadeia, `20260630_1845`, também já possui as três
tabelas (`urgent_need_overlays`, `business_review_records` e
`structural_learning_links`) na cópia. Como a migration usa `CREATE TABLE IF
NOT EXISTS`, elas foram adicionadas ao fingerprint antes de prosseguir. O
resultado é `complete_candidate` para tabelas, colunas, índices e constraints
nomeadas, mas não atualiza o ledger nem comprova FKs/defaults/dados.

As três revisions subsequentes (`20260701_1015`, `20260701_1030` e
`20260701_1045`) já possuem as tabelas/alteração de vínculo de protocolo no
schema. Elas receberam marcadores separados para que a reconciliação mantenha
a ordem Alembic, mesmo quando múltiplas alterações atingem a mesma tabela.
As duas primeiras são `complete_candidate`; `20260701_1045` é parcial: as
colunas já existem, mas faltam seus dois índices. Há uma FK semântica com nome
automático (`consultive_assisted_analyses_protocol_id_fkey`), enquanto a
revision procura outro nome; reexecutá-la criaria redundância. A tabela está
vazia nesta cópia, mas isso não autoriza DDL ou ledger.

A `20260702_1800` reutiliza o nome da constraint de status. A validação
semântica confirmou que sua definição já contém `conversion_requested`; ela é
`complete_candidate`, continua com `stamp_allowed=false` e a tabela está
vazia. A classificação corrigida da cadeia indica 30 de 34 revisions exigindo
evidência: 10 idempotentes, 14 não idempotentes, 8 com mutation de dados e 20
com SQL bruto (classes podem coexistir).

A `20260718_1200` é a primeira revision auditada que está fisicamente
ausente: não há `last_harness_key` nem seu índice em `user_mcp_tokens`. Isso
é compatível com o ledger ainda anterior e não requer reparo isolado; ela só
pode ser aplicada quando a sequência anterior for reconciliada.

Na `20260719_0900`, as três tabelas de execução de auditoria já existem. Elas
foram adicionadas ao fingerprint com colunas, índices e constraints para
separar uma materialização completa de uma colisão mascarada por `IF NOT
EXISTS`.

Na `20260719_1030`, as tabelas de papéis de trabalho, achados e evidências
também já existem. O fingerprint cobre os três contratos antes que a cadeia
avance para migrations de seed e alteração de dados.
O resultado mostrou `audit_evidence_links` parcial: falta
`ck_audit_evidence_links_parent`, que exige um vínculo com papel de trabalho
ou achado. A tabela está vazia, mas isso não permite criar a constraint nem
alterar o ledger fora da reconciliação integral.

A `20260720_0900` está ausente por completo: não existem as três colunas de
classificação, seus defaults, a constraint de tipo nem o índice de elegibilidade
em `consultive_assisted_analyses`. Como a tabela está vazia, o `UPDATE` da
migration não produziu dados nesta cópia; ainda assim ela não pode ser aplicada
fora da ordem Alembic.

O seed da `20260721_0900` está `absent_or_pending`: nenhum protocolo
`mission-official-v1.0` foi encontrado, embora a empresa AA exista e fossem
esperados os registros global e tenant. Essa ausência total é coerente com a
revision pendente; não há seed parcial a reparar nem autorização de ledger.

Os dois seeds da `20260721_2130` (`vision-official-v1.0` e
`values-official-v1.0`) são auditados individualmente, cada um com expectativa
global e tenant-AA; uma ausência parcial de um deles não pode ser mascarada
pelo outro. Ambos estão `absent_or_pending`, com zero dos dois registros
esperados, o que é compatível com a cadeia ainda pendente.

O backfill da `20260723_1000` está `absent_or_pending`: existe um projeto
elegível sem portfólio, mas não há portfólio com a marca do backfill nem
vínculo materializado. Não aplicar esse `INSERT`/`UPDATE` fora da cadeia.

Os seeds de Posicionamento (`20260727_1800`) e Organograma (`20260727_2100`)
foram registrados com o mesmo contrato global/tenant-AA antes de sua leitura
no banco isolado. Ambos estão `absent_or_pending`, sem nenhum dos dois
registros esperados para cada protocolo.

O primeiro marcador agora é `20260730_1600`: suas tabelas usam `CREATE TABLE
IF NOT EXISTS`, que pode mascarar drift durante um upgrade. As duas tabelas
(`audit_reports` e `audit_follow_ups`) já existem na cópia. O fingerprint de
tabelas, colunas, índices e constraints nomeadas está completo, mas permanece
apenas `complete_candidate`: ainda não autoriza `stamp`, pois faltam a
validação de FKs/defaults/dados e a reconciliação das revisions anteriores.

Na cópia isolada `app32_oauth_hml`, com ledger em `20260614_1200`, os três
objetos da revision `20260730_1700` já existem fisicamente. O fingerprint
detectou a ausência de `ix_knowledge_chunks_content_fts` em
`knowledge_chunks`; a inspeção de `pg_indexes` também não encontrou um FTS
equivalente. Existem 181 `knowledge_sources`, 2.297 `knowledge_chunks` e 716
`knowledge_index_runs`. Portanto, a revision está **parcialmente
materializada**: `reconciliation_required=true`, `stamp_allowed=false`. Não
executar `stamp`, DDL manual, recriação das tabelas ou upgrade OAuth até
reconciliar toda a cadeia em banco descartável com evidência por revision.

A `20260730_1800` também tem `knowledge_source_grants` fisicamente presente.
O contrato de colunas, índices parciais e constraint de escopo foi adicionado
ao harness antes de qualquer decisão sobre a revision seguinte.

A `20260801_0900` possui as três tabelas de interações, feedback e propostas
de treinamento fisicamente presentes; seus contratos foram adicionados ao
fingerprint para detectar drift além da simples presença de tabelas. O resultado
é parcial: faltam os nomes de índice esperados e `ix_knowledge_training_pattern`.
As unicidades UUID existem sob nomes diferentes, mas reexecutar a migration
criaria índices redundantes porque ela usa os nomes históricos. As duas tabelas
afetadas estão vazias, mas não haverá DDL ou ledger isolado.

A `20260801_1500` possui as três tabelas de artefatos de processo fisicamente
presentes. O fingerprint cobre schema e constraints; o backfill de POPs será
classificado separadamente para não confundir estrutura com dados. O backfill
está parcial: existem 4 definições geradas e todas possuem vínculo, mas 17
rotinas elegíveis ainda não têm definição. Não executar o backfill isolado nem
alterar o ledger.

A `20260801_1530` possui a tabela de atribuições de execução fisicamente
presente; colunas, índices parciais e constraints de alvo/status entram no
fingerprint antes da próxima revision.

Na triagem da `20260802_2100`, as quatro tabelas de Árvore Estratégica já
existem, mas o fingerprint detalhado é parcial: falta a FK nomeada
`fk_strategic_trees_root_node` de `strategic_trees.root_node_id` para
`strategic_tree_nodes.id` com `ON DELETE SET NULL`. A capability
`knowledge.strategic_tree` também está ausente. Isso separa schema
materializado de schema/rollout pendentes; não criar a FK, a capability nem
alterar o ledger isoladamente. O marcador de rollout confirmou
`absent_or_pending`: zero capability e zero configurações habilitadas para a
empresa 9.

Na `20260813_1200`, `project_tasks` existe, mas falta o índice composto
`ix_project_tasks_board_page` (`project_id`, `is_deleted`, `stage`, `id`). A
revision continua fisicamente pendente; não criar o índice isoladamente nem
avançar o ledger.

Na `20260821_1200`, as quatro tabelas do catálogo corporativo existem, mas
falta a constraint `ck_process_resource_links_criticality`. O seed canônico de
cinco dimensões também é parcial: faltam 20 dimensões para as empresas 3, 4, 5
e 13, de 65 esperadas para 13 tenants. Não reparar constraint ou seed fora da
execução reconciliada da cadeia.

Na `20260826_1800`, `indicator_goals` existe, mas faltam as quatro colunas de
versionamento, cinco constraints e os dois índices de período. Não há linhas
pendentes para as duas normalizações históricas de datas, porém isso não
autoriza aplicar somente o schema nem avançar o ledger.

Na `20260826_2000`, o schema de `indicator_goal_routines` está completo no
fingerprint, mas o backfill está ausente: existem duas metas elegíveis com
`routine_id` válido e nenhum dos vínculos foi materializado. É divergência de
dados; não executar o `INSERT` isoladamente nem avançar o ledger.

Na `20260901_1900`, as quatro estruturas de execução de rotinas existem, mas
o fingerprint é parcial: falta `routines.execution_mode`, sua constraint, seis
constraints das tabelas auxiliares e os índices de código de gatilho e de
responsável único. Não aplicar fragmentos dessa revision fora da cadeia.

Na `20260903_1200`, a tabela de interações de artefatos já está completa, mas
faltam `execution_scope` e `scope_key`, com suas constraints e índices, nas
tabelas anteriores de definição e execução. Não completar esses fragmentos
isoladamente nem avançar o ledger.

A `20260903_1300` está fisicamente ausente: não há
`user_presence_sessions`, seus índices ou constraint. A ausência é compatível
com o ledger pendente; não criar a tabela isoladamente.

Na `20260904_1400`, `roles` existe, mas falta
`qualification_requirements`. Não adicionar a coluna fora da sequência
reconciliada.

Na `20260904_1500`, faltam as unicidades compostas tenant-safe de `roles` e
`employees`, e `employee_role_occupancies` está ausente. Não criar tabela ou
constraints isoladamente.

A `20260904_1800` está fisicamente ausente: não há
`employee_qualification_evidences`, seu índice ou constraints. A ausência é
compatível com o ledger pendente; não criar a tabela isoladamente.

A `20260907_1900` também está fisicamente ausente: não há
`usage_telemetry_hourly`, índices ou constraints. Não criar telemetria
isoladamente; a ausência é compatível com o ledger pendente.

A `20260909_1000`, head aditivo de identidade OAuth, está fisicamente ausente:
não há `identity_principals`, `external_identities` ou
`principal_company_grants`. Isso confirma que a persistência OAuth não foi
materializada; não aplicar somente essa migration enquanto a cadeia anterior
continuar divergente.

A cadeia canônica possui um único head, `20260909_1000`. A partir de
`20260614_1200` há 34 revisions pendentes; a primeira é `20260630_1845` e a
última é a migration aditiva de identidade. O plano é tratar cada colisão na
ordem da cadeia, registrar seu fingerprint completo e repetir o upgrade em
cópia descartável. Somente ao atingir o head sem drift poderá ser validada a
persistência OAuth.

Na classificação inicial, 30 das 34 revisions pendentes exigem evidência
explícita: 10 têm schema idempotente, 14 schema não idempotente, 8 mutation
de dados e 20 SQL bruto (as classes podem coexistir na mesma revision).
Portanto, não é tecnicamente aceitável resumir a reconciliação a um único
`stamp` ou ao índice FTS faltante.

Em 2026-09-10, a auditoria final confirmou cobertura explícita para as 34
revisions pendentes, do ledger `20260614_1200` ao head único `20260909_1000`,
sem executar mutação. Os gates permanecem: `schema_reconciliation_required`,
`data_reconciliation_required` e `reconciliation_required` são verdadeiros;
`seed_reconciliation_required` é falso. A cobertura completa é evidência para
planejar uma cópia descartável reconciliada, não autorização para `stamp` ou
execução parcial.

### Execução controlada R04

Foi criado o clone descartável `app32_oauth_r04_20260910` a partir da cópia
isolada, sem tocar a origem. A fase sequencial até `20260730_1600` foi aplicada
com sucesso e o ledger avançou de `20260614_1200` para `20260730_1600`.
Em seguida, a execução exclusiva da `20260730_1700` falhou como previsto com
`DuplicateTable` em `knowledge_sources`; o ledger permaneceu em
`20260730_1600`. Essa é a primeira barreira efetiva de R04 e deve receber uma
estratégia corretiva idempotente, validada nesse clone, antes de qualquer novo
avanço.

A `20260730_1700` foi corrigida para validar o contrato das tabelas já
existentes, preservar o fail-closed em caso de coluna/constraint ausente e usar
criação idempotente somente para tabelas e índices de seu próprio contrato.
No clone R04, ela aplicou com sucesso o índice FTS ausente e avançou o ledger
para `20260730_1700`; o fingerprint de conhecimento ficou
`complete_candidate`. A correção foi validada no clone, não na aplicação ou em
produção.

A `20260730_1800` apresentou o mesmo `DuplicateTable` em
`knowledge_source_grants`. Após correção fail-closed/idempotente equivalente,
foi aplicada com sucesso no clone R04; o fingerprint de grants ficou
`complete_candidate` e o ledger avançou a `20260730_1800`.

### Fechamento do clone R04

Em 2026-09-10, a cópia descartável `app32_oauth_r04_20260910` alcançou o head
`20260909_1000` após a cadeia Alembic completa. A auditoria final retornou
ledger/head iguais, nenhuma revision pendente e todos os gates de reconciliação
falsos. O smoke R05 criou principal, vínculo externo e grant apenas nessa
cópia, confirmou allow para `company_id=9` e deny para `company_id=10`, e
removeu os registros temporários antes de encerrar. A validação final repetiu
o fluxo com duas identidades SERVICE concorrentes, grants em empresas distintas
e quatro requests cruzados: somente os pares principal/empresa corretos foram
permitidos. A limpeza posterior confirmou zero vínculos temporários e nenhum
listener loopback. A base principal e a produção permanecem fora deste harness
e não foram alteradas.
