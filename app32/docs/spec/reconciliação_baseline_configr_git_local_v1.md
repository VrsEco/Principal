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

### Pendências para validação do Squad de Engenharia

1. **PR #34 (RAG/pgvector):** não mesclar nem publicar antes de ensaio em PostgreSQL de teste com a extensão pgvector (runbook `runbook_pgvector_banco_teste_conhecimento_v1.md`) e decisão sobre o custo de embeddings. A migração `20260924_1400` falha de forma segura sem a extensão. `KnowledgeEmbeddingUsageEvent` não está exportado em `models/__init__.py`; revisar. O ambiente de teste precisa de `OPENAI_API_KEY` (pode ser fictícia) para coletar alguns testes.
2. **Quatro testes de UI já falham na `main` pura** e não vêm deste trabalho: `tests/test_sapiens_knowledge_ui.py` (2) e `tests/test_sapiens_widget_knowledge_ui.py` (2) leem `app32/static/js/...`, mas os assets agora ficam em `static/` na raiz. Tratar em tarefa separada.
3. **Aposentar o checkout legado** somente após conferir o backup; criar novo ponto de partida limpo a partir de `main`.
4. Validação visual dos gráficos e equivalência de banco, ignored e runtime continuam **não verificadas** neste registro.

## Limites e atualização

Esta SPEC registra fatos daquele momento e um procedimento de segurança. Não diz que o estado de produção ou da máquina continua igual hoje, não autoriza merge/deploy futuro e não prova igualdade de bancos, runtime ou segredos. Atualizar a SPEC quando novas evidências forem obtidas, preservando os limites e os dados sensíveis.
