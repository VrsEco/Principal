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
