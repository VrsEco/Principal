# Harness — Rollout financeiro v3 (ainda não executado)

## Conteúdo validado
Seis serviços definidos no manifesto v3; 20 testes PostgreSQL e 37 unitários na cópia isolada, hashes normalizados LF. Sem migração. Preserva a permissão de estorno contratual observada em produção. Não altera configuração WSGI.

## Gates antes de publicação
- Revisar o commit isolado e publicar a branch antes de qualquer reset remoto.
- Comparar novamente hashes remotos e dependências. A base desta branch não representa todas as correções frontend já publicadas: NÃO fazer reset/deploy integral desta branch sobre produção sem integração dessas entregas.
- Inventariar processos HTTP, MCP HTTPS/stdio e tarefas agendadas que escrevem finanças; confirmar entrypoints e supervisor. Não presumir que reiniciar WSGI atualize MCP existente.
- Definir janela coordenada sem novas escritas financeiras e aguardar operações em curso. Não interromper sessões de usuários sem aviso.
- Idempotência não implementada: nenhum retry automático de mutações. Contenção de numeração exige nova tentativa explícita somente após resposta negativa.
- Medir novamente RAM disponível, RSS/PSS quando acessível, conexões e pool por processo. Segundo worker é mudança separada, não simultânea a este rollout.

## Execução futura controlada
1. Backup verificável dos seis caminhos remotos, registrando hashes e ausência prévia do módulo novo; preservar configurações e demais entregas.
2. Publicar somente conteúdo versionado revisado pelo procedimento de deploy do projeto. Não copiar arquivos do checkout compartilhado.
3. Atualizar coordenadamente todos os escritores e conferir arquivos carregados/versão por processo. Escritores antigos não respeitam a nova trava.
4. Smoke de saúde, login e leitura tenant-safe; MCP saúde, negação sem autenticação e surfaces. Não criar baixas reais como smoke sem cenário autorizado.
5. Observar erros, tempo de resposta, contenção de numeração e recursos. Liberar escritas somente com versões alinhadas.

## Reversão
Manter pausa de escritas, restaurar somente os arquivos do backup e reiniciar os mesmos escritores coordenadamente. Remover o módulo novo apenas se sua ausência anterior foi registrada e nenhum outro componente depender dele. Sem migração, não há reversão de schema; rollback de código não desfaz operações já confirmadas. Verificar saúde e versões antes de reabrir.

## Limites
Retenções bruto/líquido continuam com rejeição segura no cenário incompatível. A numeração ainda varre histórico. Resultados locais não provam eliminação da causa histórica da lentidão nem capacidade de dois workers. Arquivos de resultado contêm caminhos locais apenas para rastreabilidade; o PostgreSQL portátil deve estar provisionado para reproduzir o runner.

## Inventário confirmado — 20/09/2026 04:08 UTC
- MCP HTTP: listener 127.0.0.1:8101, PID 626833; health local e público retornaram HTTP 200. Cgroup de sessão, sem unidade MCP dedicada encontrada nas listagens consultadas.
- Web: árvore uWSGI sob python3.12-uwsgi.service; não contar master/emperor como workers HTTP.
- Scheduler: processo run_scheduler.py PID 626770 no snapshot anterior; deploy reinicia via manage_scheduler.sh e exige heartbeat válido.
- Scripts remotos manage_mcp_http.sh, start_mcp_http.sh e deploy_configr.sh coincidem por hash com os inspecionados localmente. start_mcp_http.sh usa Python via stdin e runpy: buscas somente por nome de script não bastam para inventariar esse runtime.
- O deploy atual usa RESTART_MCP=false por padrão. Para este pacote, a futura execução precisa incluir explicitamente o MCP HTTP (RESTART_MCP=true), além de garantir reconexão de clientes stdio que possam manter processos antigos.
- O trecho de deploy MCP registra avisos quando health falha; não tratar o sucesso geral do script como aprovação desse componente. Gate independente: exigir health local/público, auth negativa, smoke autenticado tenant-safe e versão alinhada antes de reabrir escritas.
- Nenhum restart ou deploy foi executado. PIDs são snapshots e precisam ser atualizados na janela. Não usar kill por PID antigo como procedimento de rollout.
