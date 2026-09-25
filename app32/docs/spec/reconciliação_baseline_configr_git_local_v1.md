# SPEC — Linha de base de reconciliação Configr, Git e checkout local

**Estado:** referência operacional histórica verificada em 25/09/2026. Revalidar antes de cada release; estes valores não são uma autorização permanente de deploy.

## Linha de base observada

- Run diagnóstico somente leitura #1458: https://github.com/VrsEco/Principal/actions/runs/36124196901. Ator/triggering actor VrsEco. Produção em `c0b487f90b19a3e5dc17bf0efa470ee9ed8be09d`, tree `9bedcd3bd5ea06c4a7e0ad4aa510025c841796eb`; Git reportou status, staged e unstaged vazios.
- O inventário #1458 não cobriu arquivos ignored, dados do banco, nginx, dependências do host ou conteúdo de arquivos. Status Git vazio não prova igualdade integral do runtime.
- Após PR #30, run #1459 publicou `dbfbf36a81e41c918f602cbdabc837a21952bfdc`: https://github.com/VrsEco/Principal/actions/runs/36127065468. Ator/triggering actor VrsEco, `quick`, `restart_mcp=false`, correlation `manual-unlinked`; validação e deploy verdes, diagnóstico skipped.
- O checkout isolado e limpo foi avançado ao SHA `dbfbf36...`; nesse SHA o Git main e o runtime publicado foram alinhados ao nível de commit. Não confundir com o checkout legado, que permanece preservado para análise de evoluções.
- Smoke pós-deploy: `/healthz` 200 e `ok=true`; Chart.js, adapter de date-fns e `process_architecture.js` 200 com tipo JavaScript. Os hashes dos três assets coincidiram com o commit publicado. O operador confirmou visualmente que os gráficos de `/indicators/dashboard` renderizaram.

## Recuperação e proteção de dados locais

- Foi validado por restauração em diretório isolado um bundle Git completo com o histórico e refs relevantes; `git fsck --full` passou. Um snapshot separado de 66 arquivos e um incremental posterior também passaram em CRC/SHA-256. Evidência armazenada em backups locais externos ao repositório; não incorporar backups ao Git.
- O snapshot não cobre todo o ambiente, arquivos ignored, segredos ou consistência transacional do banco. O arquivo local `data/chroma_db/chroma.sqlite3` é dado e nunca deve ser commitado; cópia de arquivo não equivale a backup consistente do banco.
- O checkout legado deve permanecer intacto até revisar as divergências. Nunca executar `git clean`, `reset --hard`, restore ou cópia em massa para fazê-lo coincidir com produção.

## Procedimento obrigatório para novos trabalhos

1. Antes de trabalhar, verificar branch, HEAD e status do checkout e comparar main, produção e base local por SHAs. Usar clone/worktree isolado e limpo de main para novas alterações; não desenvolver em cima do estado legado com drift.
2. Fazer inventário separado de arquivos tracked, untracked e ignored. Para diagnóstico remoto, registrar explicitamente o que o método não observa. Não exibir conteúdo sensível nos logs.
3. Comparar cada divergência com main e classificar como já publicado, evolução candidata ou dado/runtime sensível. Diferença não é automaticamente evolução. Separar assuntos em entregas isoladas e testar.
4. Preservar snapshot externo, manifesto e checksums antes de qualquer restauração ou remoção. Nunca incluir `.env`, credenciais, uploads privados, bancos locais ou artifacts sensíveis em commit.
5. Preservar o caminho de publicação oficial `.github/workflows/deploy-app32.yml`. Sem MCP de Deploy autenticado, agente prepara e acompanha; o operador autorizado dispara e aprova o gate. Não usar sessão humana como identidade do agente nem SSH manual.
6. Pós-deploy, verificar run verde, SHA exato, ator, parâmetros, `/healthz` 200/`ok=true`, assets críticos 200 + MIME e hash compatíveis. Declarar validação visual separadamente; se não houver acesso, pedir ao operador confirmar após Ctrl+F5.
7. Não declarar equivalência completa até haver evidência adequada de banco/schema, arquivos ignored e configurações de runtime, além do código. Se não foram verificados, registrar como pendências explícitas.

## Atualização 25/09/2026 — alinhamento após os PRs #32 e #33

Evidência histórica; revalidar antes de cada release.

- PRs #32 (validação de update de tarefas MCP) e #33 (guarda de orçamento de contexto dos prompts de Squad) foram mesclados em `main`, que passou a `283f5446158fe21a37b153be4f1e73586365cd67`.
- Run #1462 publicou esse SHA: https://github.com/VrsEco/Principal/actions/runs/36137055337. Ator VrsEco, `quick`, `restart_mcp=true`, sem migrações. O MCP HTTP foi reiniciado (nova porta 8101, novo PID) e `/mcp/healthz` público respondeu. Um run anterior no mesmo SHA (#1461) usou `restart_mcp=false` e não recarregou o MCP; o #1462 é o que vale para a validação nova de tarefas.
- Run diagnóstico somente leitura #1463: https://github.com/VrsEco/Principal/actions/runs/36137831225 (leitura de `HEAD`, `TREE` e status, sem conteúdo de arquivos). Resultado: `HEAD` igual a `283f5446158fe21a37b153be4f1e73586365cd67`, `TREE` igual a `a1fbea6c11aecd16218cd6e2c8a877a2a076050a` (idêntico ao tree do commit no Git) e `status`, `unstaged` e `staged` vazios. Git `main` e Configr estão alinhados ao nível de commit e de tree. As mesmas limitações do #1458 se aplicam: não cobre ignored, banco, nginx, dependências do host nem conteúdo de arquivos.
- Evoluções do checkout legado (`codex/root-reconciled-20260923`) classificadas e preservadas em worktree isolado, sem alterar o original:
  - já publicadas e idênticas à `main` (33 arquivos: controle de deploy de agentes, MCP de empresa e atividades pessoais, SIPOC, Keycloak, Chart.js local); não reaplicar;
  - promovidas por PR e mescladas: #32 e #33;
  - **em evolução, ainda fora da `main`: PR #34** (RAG governado com projeção pgvector, desligado por padrão; migrações `20260924_1400` e `20260924_1500`);
  - defasadas, **não portar**: `app.py` (reintroduziria a cópia de assets no boot que a `main` removeu), `.github/workflows/deploy-app32.yml`, `scripts/deploy_configr.sh`, `PRODUCAO_RUNBOOK.md` e os `SKILL.md` antigos;
  - dado sensível, nunca commitar: `data/chroma_db/chroma.sqlite3`; e material de auditoria em `reconciliation-review/`, que não pertence ao produto.
- Backup do estado local antes de qualquer alteração: cópia de 75 arquivos com hashes conferidos, armazenada fora do repositório (não incorporar ao Git).

### Pendências para validação do Squad de Engenharia (posição após o #33; superadas pela "Atualização final" abaixo)

1. **PR #34 (RAG/pgvector):** não mesclar nem publicar antes de ensaio em PostgreSQL de teste com a extensão pgvector (runbook `runbook_pgvector_banco_teste_conhecimento_v1.md`) e decisão sobre o custo de embeddings. A migração `20260924_1400` falha de forma segura sem a extensão. `KnowledgeEmbeddingUsageEvent` não está exportado em `models/__init__.py`; revisar. O ambiente de teste precisa de `OPENAI_API_KEY` (pode ser fictícia) para coletar alguns testes.
2. **Quatro testes de UI já falham na `main` pura** e não vêm deste trabalho: `tests/test_sapiens_knowledge_ui.py` (2) e `tests/test_sapiens_widget_knowledge_ui.py` (2) leem `app32/static/js/...`, mas os assets agora ficam em `static/` na raiz. Tratar em tarefa separada.
3. **Aposentar o checkout legado** somente após conferir o backup; criar novo ponto de partida limpo a partir de `main`.
4. Validação visual dos gráficos e equivalência de banco, ignored e runtime continuam **não verificadas** neste registro.

## Atualização final 25/09/2026 — RAG implantado e estado atual

Evidência histórica; revalidar antes de cada release.

- PRs mesclados depois do #33: #35 (esta SPEC), #36 (16 testes de UI/contrato passam a ler `static/` da raiz), #37 (remoção de 4 gitlinks órfãos `.codex_deploy_*`, que geravam o aviso "git exit code 128" no checkout do Actions) e #38 (runners fixados em `ubuntu-24.04`, antecipando a migração do `ubuntu-latest` em 19/10/2026). Run #1464 (`quick`, `restart_mcp=false`, runner `ubuntu-24.04`) publicou `a153de739188c130c1557266921c03921714f66d`: https://github.com/VrsEco/Principal/actions/runs/36146332630. Inventário #1465: `HEAD` igual ao SHA e status vazio: https://github.com/VrsEco/Principal/actions/runs/36146761445.
- **Infraestrutura pgvector:** ticket Configr #241421. O suporte compilou e instalou o pgvector 0.8.6 para o PostgreSQL 14.24 do servidor e criou a extensão `vector` no banco `bdversusv2` (schema `public`). O usuário `app` não pode executar `CREATE EXTENSION`, mas a migração `1400` usa `IF NOT EXISTS`. Sem reinício do PostgreSQL. Atualizações do pgvector não são automáticas; exigem novo pedido ao suporte. Confirmado por consulta própria somente leitura em `pg_available_extensions`: `vector | 0.8.6 | 0.8.6`.
- **PR #34 (RAG governado com pgvector, desligado por padrão)** mesclado em `e20264f2f95c774bf7437dc6f3cbcee0e4741b29` e publicado pelo run #1466 (modo `full`, `restart_mcp=true`; migrações só rodam em `full`): https://github.com/VrsEco/Principal/actions/runs/36149299945. Migrações `20260924_1300 -> 1400 -> 1500`. Em `bdversusv2` (226 MB): `alembic_version` passou a `20260924_1500` e as duas tabelas do RAG passaram a existir (245 para 247 tabelas em `public`). Antes do deploy: backup manual, run #299 (`db_backup_20260925_113855.sql.gz`), com `gzip -t` no script. O log do backup não imprime o nome do banco; que o dump seja do `bdversusv2` é muito provável, mas **não foi provado**.
- **Governança:** o run #1466 foi disparado por engano pelo agente (clique por posição no navegador); os parâmetros coincidiram com o plano aprovado, o gate `production` foi aprovado pelo operador e nada foi implantado antes disso. Regra a manter: o agente **não** dispara workflow de produção (nem o inventário); prepara o formulário e o operador dispara. Ao marcar campos no navegador, usar o estado do formulário (não coordenadas) e conferir os valores antes de entregar.
- Inventário somente leitura #1467: https://github.com/VrsEco/Principal/actions/runs/36150956998. `HEAD` = `e20264f2f95c774bf7437dc6f3cbcee0e4741b29`, `TREE` = `1c0cb135923935edf3e9d477fdd805b00bcc5426` (idêntico ao tree do commit no Git), `status`, `unstaged` e `staged` vazios. Git `main` e Configr alinhados ao nível de commit e tree. As mesmas limitações do #1458 se aplicam.
- `/healthz` e `/mcp/healthz` públicos em 200 com `ok=true` após o #1466.

### Estado do RAG e decisões registradas

- Funcionalidade **desligada** (`KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED` ausente). Nenhuma variável `KNOWLEDGE_*` e nenhuma chave de embeddings foi configurada no servidor.
- Decisão de custo aprovada pelo operador (a executar somente ao habilitar): `text-embedding-3-small` (1536 dimensões nativas, compatível com `vector(1536)`), primeira onda limitada a `product_help`, chave da OpenAI dedicada com limite mensal de gasto definido no painel do provedor (sugestão US$ 10), `KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD` para estimar custo. Estimativa: corpus da primeira onda de cerca de 3,6 mil tokens (custo de indexação desprezível); custo recorrente dominado pelas consultas. Os preços por milhão de tokens devem ser conferidos na página do provedor no momento da habilitação.
- Antes de habilitar: comparar precisão contra o golden set com a flag ligada em empresa de teste (SPEC do RAG). O agente não manipula a chave da OpenAI.

### Pendências abertas (após o #1467; o item 1 foi atualizado depois, ver "Atualização após o #41")

1. Habilitação do RAG (chave dedicada, variáveis `KNOWLEDGE_*`, empresa piloto, golden set); backfill apenas com simulação primeiro e `--max-chunks` pequeno. **Só configuração não bastava** na `main` daquele momento: `KnowledgeQueryService()` era criado sem provedor de embeddings e a atualização automática não gera embeddings. O provedor foi ligado depois, pelo #41. Plano e ordem no runbook `runbook_pgvector_banco_teste_conhecimento_v1.md`, seção "Plano de habilitação em produção".
2. **Não** executar `git rm --cached` nos arquivos do ChromaDB (`app32/data/chroma_db*`, `data/chroma_db/chroma.sqlite3`): `src/intelligence/rag.py` lê `./data/chroma_db` em runtime e o próximo deploy apagaria os arquivos do servidor. Decidir antes o destino desses dados.
3. Aposentar o checkout legado (`codex/root-reconciled-20260923`, clone raso e com objeto ausente no `fsck`) com aprovação do operador, mantendo o backup externo; usar um clone completo e limpo de `main` como ponto de partida.
4. Avisos do Actions: `actions/checkout@v4` e `actions/setup-python@v5` ainda rodam forçados em Node 24; migrar as versões quando conveniente.
5. Continuam **não verificados**: validação visual dos gráficos, equivalência de banco (além da versão de migração e das tabelas do RAG), arquivos ignorados, nginx, dependências do host e a origem exata do dump de backup.

### Atualização após o #41 (25/09/2026)

Evidência histórica; revalidar antes de cada release.

- **#40** (plano de habilitação do RAG e lacuna de código) e **#41** (provedor de embeddings ligado ao runtime, desligado por padrão) mesclados; `main` = `8e13d50cfcd35efd5d9bf3172e7cfc40c72abf16`. Sem migrações e sem mudança de dependências.
- Run #1468 (`quick`, `restart_mcp=true`, `ubuntu-24.04`) publicou esse SHA: https://github.com/VrsEco/Principal/actions/runs/36156799209. Migrações preservadas no modo `quick`; MCP reiniciado (novo PID) e `/mcp/healthz` respondeu. O run saiu de um clique acidental do operador, com os parâmetros do plano aprovado, e passou pelo gate `production`.
- Inventário somente leitura #1469: https://github.com/VrsEco/Principal/actions/runs/36157295654. `HEAD` = `8e13d50cfcd35efd5d9bf3172e7cfc40c72abf16`, `TREE` = `3e6513197105489d36b8668c423385bea6a41a9b` (idêntico ao tree do commit no Git), `status`, `unstaged` e `staged` vazios. As mesmas limitações do #1458 se aplicam.
- **Estado do RAG:** código completo em produção e **desligado**; sem nenhuma variável `KNOWLEDGE_*` no servidor, a fábrica devolve `None` e a busca segue textual. Para habilitar (passos do operador, ver o runbook): projeto dedicado no provedor com limite mensal; chave em `KNOWLEDGE_OPENAI_API_KEY` (tem precedência sobre `OPENAI_API_KEY`, que outras funções do app podem usar); `KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED`, `KNOWLEDGE_EMBEDDING_MODEL`, `KNOWLEDGE_EMBEDDING_VERSION`, `KNOWLEDGE_EMBEDDING_INDEX_GENERATION`; piloto por empresa em `KNOWLEDGE_VECTOR_PILOT_COMPANY_IDS`; backfill manual (a atualização automática não gera embeddings). Com tudo ligado, cada pergunta envia o texto ao provedor de embeddings.
- **Legado:** triagem read-only em `C:\GestaoVersus\reconciliation-backups\triagem-legado-20260925\TRIAGEM-legado.md` (36 branches sem cópia no GitHub; 31 com patches únicos). O checkout legado hospeda 151 worktrees e não deve ser removido antes da triagem por branch.
- Continuam **não verificados**: validação visual dos gráficos, equivalência de banco além da versão de migração e das tabelas do RAG, arquivos ignorados, nginx, dependências do host e a origem exata do dump de backup #299.

## Limites e atualização

Esta SPEC registra fatos daquele momento e um procedimento de segurança. Não diz que o estado de produção ou da máquina continua igual hoje, não autoriza merge/deploy futuro e não prova igualdade de bancos, runtime ou segredos. Atualizar a SPEC quando novas evidências forem obtidas, preservando os limites e os dados sensíveis.
