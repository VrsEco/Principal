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

## Limites e atualização

Esta SPEC registra fatos daquele momento e um procedimento de segurança. Não diz que o estado de produção ou da máquina continua igual hoje, não autoriza merge/deploy futuro e não prova igualdade de bancos, runtime ou segredos. Atualizar a SPEC quando novas evidências forem obtidas, preservando os limites e os dados sensíveis.
