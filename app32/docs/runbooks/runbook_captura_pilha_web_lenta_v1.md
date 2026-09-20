# Runbook — Captura de pilha de requisições web lentas

Classe: Runbook. Card: AA.J.21.348. Estado: ativado em produção em 19/09/2026.

## Evidência de ativação

- Release de código `650666449`, publicado na branch
  `codex/record-uploads-backup-activation`; deploy cirúrgico somente dos três arquivos
  de runtime, preservando alterações alheias. Nenhum reset de checkout nem migração.
- Teste isolado no mesmo binário uWSGI: HTTP 200 e captura real da função `blocked`
  por timer, via socket Unix local; nenhum endpoint de teste publicado no site.
- Worker de produção foi recriado; o master preserva PID ao re-executar.
  Validar troca do worker, não exigir troca do PID master.
- Log confirmou `python threads support enabled` e
  `slow_request_probe_enabled threshold_seconds=5.0 max_pending=16`.
- Health local HTTP 200. A primeira tentativa reverteu automaticamente devido à
  checagem incorreta de PID master; a reaplicação validou com o critério corrigido.
- Backup anterior à ativação final mantido fora do checkout, com acesso restrito.
  Localização e identificadores operacionais não são publicados neste documento.
- Próximo deploy completo: incorporar o commit à branch de release antes do reset
  para `origin/main`, ou a instrumentação será removida. Não publicar outras
  alterações da branch sem revisão. Flags ativas no ini canônico do uWSGI.
- Ativação não significa causa raiz identificada: aguardar evidência de um
  incidente real e correlacionar pilha/PID/horário antes de atribuir causa.

## Objetivo

Capturar a pilha Python ainda durante o bloqueio, antes do harakiri de 300s.
Não corrige, cancela ou repete a requisição. Não adiciona consultas ao banco.

## Publicação e ativação

1. Revisar/publicar somente `utils/slow_request_probe.py`, integração em `app.py`
   e configurações em `config.py`, com testes. Não incluir mudanças pendentes alheias.
2. Confirmar que o uWSGI permite threads Python (`enable-threads` ou configuração
   equivalente). Não presumir que threads funcionem apenas porque o import passou.
3. Configurar `SLOW_REQUEST_STACK_ENABLED=true` e
   `SLOW_REQUEST_STACK_SECONDS=5`. Desativado por padrão.
4. Reiniciar controladamente o serviço via protocolo oficial de deploy.
5. Validar primeiro em homologação um bloqueio sintético, inclusive no mesmo modo
   de uWSGI. Não criar endpoint público de sleep, não estressar produção.
6. Em produção, validar login e navegação autorizada, observar os logs restritos
   e conferir que nenhum erro novo surgiu. Marcar entrega completa somente após
   validar ativação no runtime real.

## Evidência

Buscar evento JSON `slow_request_stack` no destino configurado do logger Flask.
Inclui PID, ID aleatório, thread, duração e até 64 frames (arquivo, linha, função),
da função mais interna para a externa. Correlacionar PID/horário com stats uWSGI
e logs de acesso. Não registrar variáveis locais, texto de código-fonte, URL,
query string, cabeçalhos, corpo, usuário, empresa ou dados financeiros.
O ID é interno ao diagnóstico, não é propagado ao cliente nem aos access logs.
Não disponibilizar logs em rota web. Aplicar retenção/rotação e acesso operacional
restrito do ambiente; não criar um arquivo de log ilimitado adicional.

## Limites

- Uma captura por requisição após o limiar; máximo de 16 timers simultâneos por
  instância. Acima disso, atender normalmente sem instrumentar as excedentes.
- Timer criado no atendimento (após fork), nunca na inicialização da aplicação.
- Requer threads Python; código nativo retendo o GIL pode impedir a captura.
  Nessa situação será necessário profiler externo aprovado, não mais timers.
- A pilha mostra onde o Python está, não necessariamente a causa externa da espera.
- Abrange despacho WSGI e iteração da resposta. O servidor deve consumir a resposta
  na mesma thread do despacho, como no runtime síncrono alvo. Streaming legítimo
  pode ultrapassar o limiar e não representa automaticamente incidente.
- O probe não distingue banco, integração ou rede sem interpretar a pilha e
  correlacionar outras evidências. Ausência de evento não prova ausência de falha.

## Reversão

Definir `SLOW_REQUEST_STACK_ENABLED=false` e reiniciar controladamente. Não há
migração nem mudança em dados de clientes. Monitorar custo dos timers durante a
janela diagnóstica; não manter habilitado indefinidamente sem medir overhead.

## Validação local

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest app32/tests/test_slow_request_probe.py app32/tests/test_request_performance_observability.py -q`

11 testes passaram: captura real de espera, privacidade, limpeza em sucesso/erro,
streaming, timers independentes, limite, falha de timer e configuração inválida.
Autoload desabilitado devido a incompatibilidade preexistente pytest-flask/Flask
no Python local. Esta validação não equivale a teste no uWSGI de produção.
