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

## Mitigação de conexões sem resposta — AA.J.21.349

Implantada em 19/09/2026, release `05be68ec9`, por publicação cirúrgica dos três
arquivos de runtime. Backup restrito e reversão preparados; captura de pilha
preservada. Log do worker confirmou política efetiva 120/5/5/15000 e reset do
pool após fork. Health local respondeu HTTP 200 após reinício.

Validação: 20 testes locais passaram. Em processo isolado no servidor, testes
read-only confirmaram opções TCP efetivas no kernel, recuperação de conexão
fechada, reciclagem e pool independente após fork com conexão do pai preservada.
O teste de reciclagem usou intervalo reduzido apenas no processo isolado.
Isso valida a mitigação, não prova a causa original nem ausência de reincidência.

Pilha observada: carregamento do usuário -> checkout SQLAlchemy -> `do_ping`.
Uma conexão independente respondeu rapidamente; isso identifica a espera, mas não
prova perda de rede nem compartilhamento de socket entre processos.

Política de produção ativa: reciclar conexões com idade maior que 120s no
próximo checkout (não é uma limpeza periódica); espera por vaga no pool 5s;
abertura de conexão 5s por host; keepalive habilitado com idle 15s, intervalo 5s,
3 tentativas; `tcp_user_timeout=15000` ms. `pool_pre_ping` permanece habilitado.
Não há limite global novo de duração SQL nem repetição de transações financeiras.

Variáveis: `SQLALCHEMY_POOL_RECYCLE`, `SQLALCHEMY_POOL_TIMEOUT`,
`DB_CONNECT_TIMEOUT_SECONDS`, `DB_KEEPALIVES_IDLE_SECONDS`,
`DB_KEEPALIVES_INTERVAL_SECONDS`, `DB_KEEPALIVES_COUNT`, `DB_TCP_USER_TIMEOUT_MS`.
Valores explícitos prevalecem e devem ser positivos. Desenvolvimento preserva
suas opções anteriores; as opções de transporte novas são de produção.

Um middleware preventivo troca pools herdados antes da primeira requisição em
cada processo filho usando `dispose(close=False)`, antes do ping/autenticação.
Ele preserva as conexões do pai, não modifica a sessão do cliente e não repete
operações. Aplicável ao prefork WSGI cujo master não atende requisições; jobs e
processos que compartilhem sessões/transações exigem tratamento próprio.

Importante: timeout TCP limita dados não confirmados pela rede; não limita
qualquer espera SQL, DNS ou servidor que continue confirmando pacotes. Keepalive
não se aplica a sockets Unix. Portanto, os valores não prometem resposta total
em 5 ou 15 segundos. Manter captura e validar novos acessos após ociosidade.

Referências oficiais: [libpq](https://www.postgresql.org/docs/current/libpq-connect.html)
e [pool/fork SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork).

Reversão: restaurar os arquivos de app/config anteriores via backup da entrega,
reiniciar o worker e validar saúde. Remover apenas o módulo novo se não existir
na versão anterior. Preservar a captura de pilha implantada no card anterior.

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

## Auditoria de execução financeira CLI/SSH — AA.J.21.350

Janela analisada: 19h00–22h15 de 19/09/2026, horário da Bahia. Histórico da tarefa
financeira mostra 150 chamadas de ferramenta; 62 contêm código de acesso SSH,
das quais 53 contêm `create_app`. São contagens de registros de ferramenta, não
requisições HTTP, usuários simultâneos ou medições de carga. Scripts executados
por nome podem não conter novamente o código e não entram nesses subconjuntos.

As chamadas inspecionadas executam serviços financeiros em processos Python
separados, via SSH, não via MCP/OAuth nem via worker web. Compartilham PostgreSQL,
CPU, memória e disco. Não foi repetida nenhuma operação financeira na auditoria.
Sessenta saídas registram que o bootstrap de serviços de background foi ignorado;
não há evidência nessa amostra de schedulers duplicados iniciados pelos scripts.

Há sobreposição: execução SSH iniciada às 21h56min24 e requisição web iniciada às
21h56min27. A pilha web capturada aponta `load_user -> checkout -> do_ping`, não
serviço financeiro. A simultaneidade não demonstra causalidade.

`create_app` também varre assets e uploads e pode copiar arquivos divergentes.
Foram contados 149 arquivos estáticos e 421 uploads na origem; a enumeração levou
cerca de 1 ms por árvore na amostra. Não é benchmark completo de inicialização,
comparação de metadados ou cópia; não sustenta atribuir os 300s a essa varredura.
Repetir a inicialização é custo evitável, mas seu peso ainda não foi isolado.

Snapshot às 22h18: worker livre, quatro requisições após ativação, nenhuma nova
pilha lenta ou harakiri na janela disponível; 15 conexões DB ociosas, sem transação
ativa na amostra. Duas amostras atuais de vmstat sem swap in/out e sem iowait.
Ausência de carga nesse instante não descreve os recursos durante o incidente.

### Próximas medidas priorizadas

1. Observar acessos autenticados após ociosidade e cruzar nova pilha com operação
   CLI, horário, duração e metadados de espera do banco, sem payload financeiro.
2. Planejar entrada financeira governada (tenant, autorização, confirmação e
   idempotência), em vez de scripts SSH avulsos; nunca expor finanças na surface
   MCP `user`. Não migrar escritas para um endpoint ainda não homologado.
3. Medir inicialização separadamente em homologação; se relevante, usar contexto
   CLI enxuto, sem sincronizar assets/uploads. Não remover funções de bootstrap
   de produção sem identificar dependências e validar publicação.
4. Testar concorrência controlada de humanos e agentes em homologação antes de
   aumentar workers/pool. Esta auditoria não estabelece capacidade por usuário.
5. Prosseguir com inventário e medições de todas as telas; esta análise de CLI não
   substitui auditoria funcional e de performance de cada tela.

Conclusão: ponto de bloqueio web comprovado no ping de conexão; relação causal
com SSH/IA não comprovada. Nenhuma alteração de runtime adicional nesta etapa.

## Inventário e triagem de telas — AA.J.21.351

Classe dos artefatos: Harness (inventário reproduzível, não medição de navegador).
Gerador: `scripts/qa/build_screen_performance_inventory.py`. Saídas em
`docs/harnesses/screen_performance_inventory_v1`: `screen_inventory.json`,
`routes.csv`, `templates.csv`, `remote_comparison.json`.

Cobertura local canônica: 263 fontes Python em app/api/src, 603 declarações de
rota, 228 registros de resource/url_rule, 337 templates HTML (incluindo legado e
parciais), 58 arquivos JavaScript. Dentre as rotas, 164 declarações GET referenciam
templates literais diretamente; 147 nomes distintos de templates são referenciados.
Cinco handlers têm renderização dinâmica. Um nome literal referenciado não possui
template correspondente (`logs/user_activity.html`), achado de integridade separado.

Nenhuma falha de parsing; cinco testes do gerador aprovados (rotas/prefixos,
imports de blueprint, herança/ciclos, sinais CSS, erros explícitos e determinismo).
Não se importou Flask nem se executou código de inicialização para inventariar.

Comparação read-only com produção: 660 arquivos, incluindo serviço/modelo de
faturamento; 635 idênticos após normalizar finais de linha, 25 diferentes em
src/MCP/IA; nenhum ausente. Os templates, JS, rotas API e serviço/modelo revisados
correspondem ao remoto. JS público remoto e JS canônico não apresentaram diferenças.
Isso verifica arquivos, não cache do navegador/CDN nem rotas efetivamente ativas.

### Achados prioritários revisados

| Prioridade | Evidência de código | Consequência a medir / ação proposta |
|---|---|---|
| P1 | `entry_direct.html:14-29` nasce payable; `financial_entry_direct.js:878-890` aplica receivable somente após `await loadOptions()` | Eliminar dependência de rede para tema/tipo inicial; testar primeiro paint com API lenta e falha. |
| P1 | `contracts_service.py:2705` materializa `.all()` e executa `billing.items.count()` por linha; relacionamento dynamic em `models/contracts.py` | Paginar e agregar contagens; medir número de SQLs com diferentes volumes, preservando filtros/tenant/totais. Não atribuir o timeout antigo a isso sem captura. |
| P1 | `financial_reports.py:148-187` busca opções e constrói relatório antes de renderizar filtros em vários tipos | Separar primeiro carregamento de processamento, ou medir/otimizar consultas; validar valores e filtros. |
| P1 | `financial_entry_direct.js:617` aguarda POST sem bloquear os dois botões de salvar; helper fetch não define timeout local | Melhorar feedback e proteção contra envio repetido; timeout cliente não cancela transação e não autoriza retry financeiro automático. |
| P2 | `financial_borderos_list.js:28,129` usa fetch sem deadline local; botões de filtros permitem novas cargas enquanto anteriores aguardam | Tratar respostas fora de ordem e estado de carregamento; já existe paginação de 50, não classificá-la como lista integral. |
| P2 | Quatro templates têm links CSS em blocos de conteúdo | Revisar carregamento em head: entry_direct, ai_capabilities_central, ai_config_simple_page e process_instance_v2. Primeiro paint precisa ser medido. |
| P2 | Input formatter global inicializa no DOMContentLoaded e observa nós adicionados; lançamento rápido também tem handlers próprios de moeda/data | Medir digitação/renderização de rateio; não remover máscara global sem regressão de formatos e serialização. |

Sinais globais para revisão, não contagem de defeitos: fetch em 40 arquivos JS e
171 templates; reload integral em 1 arquivo JS e 53 templates; AbortController
aparece em 2 arquivos JS. Ausência local do marcador não exclui wrapper compartilhado.
Tamanho de fonte não equivale a payload comprimido nem prova lentidão. Templates
legados e parciais não equivalem a telas acessíveis.

### O que falta para afirmar “todas as telas testadas”

1. Confrontar declarações com `url_map` de ambiente controlado e navegação real;
   considerar blueprints condicionais, aliases, prefixos sobrescritos e slugs.
2. Abrir cada tela com sessão autorizada por empresa/perfil; resolver IDs de teste
   em homologação, sem presumir que todo GET é isento de efeitos colaterais.
3. Medir cache frio/quente, TTFB, primeiro paint, estabilidade visual, JS e duração
   das APIs/SQL; registrar erros e capturas lentas com horário e ID de correlação.
4. Testar salvar/processar apenas com dados de teste e autorização específica;
   avaliar botão ocupado, feedback, dupla submissão e atualização final.
5. Repetir com rede lenta e concorrência controlada em homologação; nunca usar
   estresse ou operações financeiras reais para preencher a matriz.

Todos os registros de rota estão com `runtime_verified=false`. O inventário de
arquivos e a triagem estática estão concluídos, mas a auditoria autenticada global
continua pendente. Nenhuma correção visual ou de consulta foi publicada nesta etapa.

## Validação local

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest app32/tests/test_slow_request_probe.py app32/tests/test_request_performance_observability.py -q`

11 testes passaram: captura real de espera, privacidade, limpeza em sucesso/erro,
streaming, timers independentes, limite, falha de timer e configuração inválida.
Autoload desabilitado devido a incompatibilidade preexistente pytest-flask/Flask
no Python local. Esta validação não equivale a teste no uWSGI de produção.

### Amostra autenticada após login — AA.J.21.352
92 destinos navegados na empresa Versus, somente leitura. Reproduzida inicialização de recebíveis com texto de conta a pagar antes da aplicação assíncrona do tipo correto. Borderôs e faturamentos não travaram nesta passagem. Maiores tempos de retorno do controlador: painel estratégico 2071 ms, DRE01 1923 ms, reuniões 1397 ms; não são TTFB/FCP. Carregamentos assíncronos revisitados. Cobertura ainda não inclui todos os detalhes, ações ou tenants. Evidência e limites: `../harnesses/screen_performance_inventory_v1/authenticated_navigation_sample.md`. Card permanece aberto; nenhuma nova correção/deploy nesta etapa.

### Segunda rodada de fluxos internos
Amostra ampliada para 95 destinos/visões: novo borderô, novo título e novo projeto, sem submissões. Confirmado no código que borderôs só registra handlers após carregar dependências; títulos inicializa tipo/formulário após opções; salvamento de títulos aguarda anexos/releituras antes de terminar o fluxo. Evidências e prioridades no Harness de navegação autenticada. Não houve teste de carga nem mudança em produção.

### Crescimento das listagens
Confirmado em inspeção: lista de títulos carrega títulos e depois borderôs sem paginação; modo compact reduz payload por item, não cardinalidade. Projetos não solicita paginação já disponível na API. Notas fiscais também materializa coleção e conta itens via relação dinâmica por linha, além do achado de faturamentos. Harness atualizado com fonte, impacto e validação pendente. Não houve benchmark nem mudança de runtime.

### Primeira correção local — AA.J.21.353
Recebíveis diretos: template agora entrega dataset, banner, chip ativo e hidden com tipo normalizado; CSS passa ao bloco head; assets recebem versão por static_asset_version. JS inicializa tipo antes da espera por opções, sem reaplicar payable depois da resposta. Sugestão de índice continua após carregar os catálogos. Nenhuma mudança em API, tenant, persistência ou retry financeiro.
Validação: 5 testes isolados de renderização/ordem aprovados, node --check e git diff --check aprovados. Pytest precisou de PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 por incompatibilidade preexistente pytest_flask/Flask. Testes de ordem são contratos estáticos, não substituem browser com API atrasada. Sem publicação: validar em navegador/homologação e manter rollback antes de deploy. Auditoria global continua aberta.

### Validação em navegador local — AA.J.21.353
Harness Flask isolado em 127.0.0.1:5087, template/JS/CSS reais, layout pai mínimo, sem banco ou rotas de gravação. API de opções sintética com atraso de 8 s. Recebíveis: antes da resposta, dataset receivable/banner correto, 0 opções/0 linhas; depois, mesmo tipo/banner, 1 opção placeholder/1 linha de rateio. Payable: banner e dataset corretos antes da resposta. CSS específico confirmado no head. Não houve submissão financeira. Dez testes locais (5 da correção + 5 do inventário), node --check e diff --check aprovados. Limite: não é homologação integral do layout real nem medição em produção. Publicação permanece pendente, não executada.

### Layout completo e preparação de publicação — AA.J.21.353
Harness reproduzível: scripts/qa/direct_entry_browser_harness.py. Herança real entry_direct -> layouts/workspace -> layouts/base, sidebar/widget reais; permissões/usuário sintéticos e links sem rota mapeados para placeholder local. Não é teste de autenticação, RBAC ou integração com banco. Inicialmente faltou rota de menu no harness (500 local); corrigido apenas no harness, sem mudar aplicação.
Browser: antes da API atrasada 8 s, workspace presente, tipo receivable, banner correto, CSS no head e 0 opções. Após API, tipo preservado, 1 placeholder e 1 linha de rateio; sem warnings/errors capturados na leitura final. Testes de render completo para payable/receivable incluídos. Total 12 testes focados aprovados.
Manifesto de publicação preparado em ../harnesses/screen_performance_inventory_v1/direct_entry_release_manifest.json, com hashes, destinos e rollback. Ainda NÃO commitado/publicado/deployado. Alterações alheias no workspace não podem acompanhar release.
Precisão sobre auditoria anterior: .fade-in no workspace está no conteúdo padrão do bloco substituído pela tela de recebíveis; não atribuir automaticamente animação a toda página que herda workspace. Verificar DOM/CSS efetivos por tela.
Observação adicional do log HTTP do harness: /static/js/date_utils.js retornou 404 no diretório canônico local. A inicialização verificada completou, mas a ausência desse asset limita a equivalência com produção; checar origem/sincronização do asset antes de publicar. Ausência de console errors não substitui verificação de HTTP dos assets.

### Pendência date_utils resolvida para o teste
Comparação SSH somente leitura: date_utils.js ausente em app32/static também em produção, mas presente em www/static. Hash normalizado remoto público idêntico ao arquivo público local: ed30586968b77c2fb58ee46e7773a0cdd76b567613b1ea5fefc9c3929cb9030b. Sincronização do app é incremental não destrutiva; não remove assets existentes só na raiz pública. Portanto o 404 anterior era limitação da origem estática do harness, não evidência de indisponibilidade em produção. Harness ajustado para servir especificamente esse asset da raiz pública; teste GET exige 200 e assinatura App32DateUtils. 12 testes seguem aprovados. Nenhum arquivo de runtime adicional foi alterado. Divergência estrutural de pastas fica registrada, sem migração incidental nesta correção.

### Publicação em produção — AA.J.21.354
Release e5600a9f4, branch codex/direct-entry-initial-render, criada em worktree isolado para não interferir no index.lock do checkout compartilhado. Drift remoto conferido contra parent antes da troca. Publicados somente template entry_direct.html e financial_entry_direct.js nos destinos canônico/público. Backup: /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/backups/direct_entry_e5600a9f4/originals-1789870007. Reinício validado: master 839517 preservado, novo worker 933635, health200, stack probe habilitado. Sem migrações e sem reset de checkout remoto.
Smoke autenticado Versus: recebíveis apresentou tipo/banner correto antes de opções (0); após API 30 opções e 1 linha de rateio, mantendo tipo. CSS no head. Contas a pagar apresentou banner/tipo correto. Sem gravações. Esse smoke não homologa processamento financeiro nem encerra investigação de travamentos.
ATENÇÃO: integrar branch dedicada ao fluxo principal antes de próximo deploy completo, para não sobrescrever esta correção. Demais alterações locais não foram incluídas.

### Prontidão de borderôs — AA.J.21.355, implementação local
Status aria-live no HTML inicial; formulário, ações financeiras e filtros começam inert, enquanto link de volta permanece acessível. Listeners vinculados antes de iniciar leituras, uma única vez. Inicialização aguarda ambas as dependências via allSettled, depois detalhe se necessário; só libera interação ao concluir. Falha mantém bloqueio e oferece repetir leituras, sem chamar endpoints de mutação. Guarda evita dupla inicialização. Não altera regras disabled de baixa/exclusão: usa inert independente.
Teste Node isolado da função real: atraso, duplicidade de inicialização, falha com outra leitura pendente, retry após ambas concluírem, recuperação e erro de detalhe aprovados. node --check e diff --check aprovados. Ainda falta validação browser e publicação. Não há novo deadline HTTP: request pendente mantém mensagem de carga; retry só é oferecido após falha. Este escopo NÃO implementa ainda trava de duplo clique após prontidão, nem feedback pós-gravação, nem mudanças em títulos. Nenhuma operação real executada.

### Browser local de prontidão — AA.J.21.355
Harness scripts/qa/bordero_readiness_browser_harness.py: layouts reais, primeira leitura de títulos falha (503 após 3s), contas retorna após 6s; retry retorna ambas com dados vazios sintéticos. Status de carga/falha/repetição observados, sem operações reais.
Browser revelou duas falhas locais corrigidas antes de publicar: classe btn sobrepunha hidden do botão de retry (adicionada classe hidden); NodeList capturado antes de sidebar ser parseada deixava filtro lateral fora da liberação (consulta agora dinâmica ao aplicar cada estado). Teste unitário inclui guard de sidebar inserido após script. Produção inalterada nesta etapa.

### Publicação de prontidão dos borderôs — AA.J.21.355
Release 98a380a7b publicada na branch codex/direct-entry-initial-render. Drift dos três destinos conferido; backup backups/bordero_readiness_98a380a7b/originals-1789870863. Troca restrita ao template borderos.html e JS canônico/público. Novo worker 936337, health200, stack probe preservado, hashes pós-troca conferidos. Sem migração e sem reset amplo.
Smoke autenticado Versus: novo borderô a receber começou com 4 guards inert/aria-busy=true; concluiu com os 4 false e retry oculto. Detalhe existente navegado por link da listagem: bloqueio inicial e liberação final confirmados; botões baixa/exclusão permaneceram disabled conforme regra de negócio. Sem criar, salvar, baixar ou excluir. Fail/retry testado só localmente, não se provocou falha em produção.
Limites: somente prontidão inicial; trava contra duplo clique após inicialização, feedback pós-gravação e títulos financeiros ainda pendentes. Integrar branch ao fluxo principal antes de próximo deploy completo para preservar ambas as correções.

### Proteção de operações dos borderôs — AA.J.21.356, local
Implementada trava única na página para criar/salvar/excluir borderô e criar/editar/excluir baixa. Guards inert bloqueiam campos e ações sem sobrescrever disabled financeiro. Clique concorrente não executa callback. Validação local/cancelamento sem envio liberam; sucesso com atualização concluída libera; redirecionamento mantém trava. fetchJson marca envio antes do fetch e confirmação após HTTP ok, antes de interpretar JSON. Falha após envio mantém trava e orienta conferir registros, sem retry automático. Se gravação foi confirmada e releitura falhou, mensagem distingue claramente os estados. Tratamento conservador também bloqueia após resposta HTTP não-ok (ainda sem classificação por contrato de erros).
Testes Node isolados executam funções reais com fetch sintético: dupla chamada gera 1 envio, validação/cancelamento, conexão perdida, releitura após confirmação falha, JSON inválido após HTTP ok, resposta rejeitada, trava no redirect, disabled preservado. Readiness anterior permanece aprovada; sintaxe e diff aprovados. Sem rede/banco nesses testes. Pendente: browser com endpoints financeiros estritamente sintéticos, revisão e deploy. Essa trava é por página: NÃO equivale a idempotência backend entre abas/clientes, não cancela requests ao fechar navegador e não elimina espera de WSGI.

### Browser de mutações sintéticas — AA.J.21.356
Harness local 5091, scripts/qa/bordero_mutation_browser_harness.py, sem banco/serviços externos. Testados clique duplo em salvar (PUT sintético com 4s) com bloqueio imediato e desbloqueio após sucesso; resposta503 ao salvar com bloqueio persistente/mensagem de resultado não confirmado; clique duplo em baixa sintética com POST200 seguido de GET503, preservando bloqueio e exibindo gravação confirmada mas atualização falhou. Logs locais observaram apenas um PUT no cenário503 e um POST no cenário de baixa/releitura. Contagem estrita de chamada única em todos os cenários assegurada nos testes Node com fetch simulado; endpoint de métricas não pôde ser exibido pelo navegador e não foi usado como evidência. Nenhuma operação financeira real executada. Testes anteriores/sintaxe/diff continuam aprovados. Deploy ainda pendente.

### Publicação da trava de operações — AA.J.21.356
Release 705b1fb21 na branch codex/direct-entry-initial-render, commit isolado com JS e dois artefatos de teste. Drift verificado contra parent 98a380a7b nas cópias canônica e pública. Publicação restrita a financial_borderos.js, sem alterações de schema/API/regras financeiras. Backup: backups/bordero_mutation_guard_705b1fb21/originals-1789871428. Novo worker 937912; health200; stack probe preservado; hashes pós-troca verificados.
Smoke autenticado de leitura em detalhe existente Versus: script v=1789871428, carga inicial bloqueada, estado final pronto/desbloqueado, botões baixa e exclusão continuam disabled conforme dados. Nenhuma gravação real executada. Duplicidade e falhas pós-envio foram testadas em Node e browser local sintético, não em mutações de produção.
Risco residual/limites: trava por página não substitui idempotência backend entre abas/IA/clientes. Respostas não-ok de escrita bloqueiam conservadoramente até conferência. Títulos financeiros e paginação seguem pendentes. Integrar esta branch ao fluxo principal antes de futuro deploy completo para preservar as três correções.

### Prontidão de títulos financeiros — AA.J.21.357, local
Adicionados status aria-live e botão de retry ao formulário de títulos; shell e formulário de composição da baixa começam inert. Inicialização bloqueia concorrência, carrega opções, detalhe (ou novo título/lista legada) e eventual simulação automática antes de liberar. Mantém regras disabled independentes. Falha deixa controles bloqueados e oferece nova carga. Se abertura automática de composição falhar, fecha modal para não encobrir recuperação. Não altera salvamento, anexos, geração, exclusão ou baixa assistida.
Importante: a abertura automática de composição usa POST de simulação já existente; não confundir com POST de efetivação de baixa. Não há retry automático de mutação financeira; o retry manual refaz inicialização/simulação. Testes Node das funções reais com dependências sintéticas passaram: atraso/dupla inicialização, novo recebível, detalhe, lista legada, falha/recuperação e falha de simulação/modal. Sintaxe e diff aprovados. Browser/integração ainda pendentes; sem deploy nesta etapa. Trava de operação após prontidão dos títulos continua fora deste escopo.

### Validação browser dos títulos — AA.J.21.357
Harness local em 127.0.0.1:5092, layout e assets reais, dependências sintéticas sem banco. Novo recebível: atraso de 5 s, primeira resposta 503, status de falha com campos protegidos; retry manual recuperou a carga e retirou inert/aria-busy. Detalhe sintético vinculado a borderô: carga concluída e campos principais/botões de salvar e baixar permaneceram disabled. O rateio apareceu editável apesar do bloqueio de negócio; não afirmar bloqueio integral do detalhe e investigar essa inconsistência separadamente (não foi submetida alteração). Simulação automática e fechamento do modal validados apenas em Node. Testes Node de prontidão dos títulos e proteção de mutações de borderôs, syntax e diff aprovados novamente. Nenhuma gravação financeira real. Esta alteração de títulos continua local, ainda não publicada.

### Diagnóstico de dois workers WSGI — AA.J.21.358 — 19/09/2026, 23:43–23:47 BRT
Somente leitura via SSH, configuração/estatísticas uWSGI e consulta PostgreSQL agregada em conexão dedicada read-only. Nenhuma alteração de configuração, restart, encerramento de processo ou carga artificial. Scripts locais de coleta: app32/tmp/wsgi_capacity_readonly.py e wsgi_db_readonly.py; não importam create_app.

**Evidência:** uWSGI 2.0.31, workers=1, um core HTTP; master839517 e worker937912 não equivalem a dois atendentes. enable-threads=true habilita threads Python, não adiciona um segundo core HTTP. harakiri=300. Worker idle/fila0/harakiri0 na coleta; somente5 requisições desde último restart, amostra insuficiente para estabilidade. Host2CPUs,3930MiB RAM,610MiB disponíveis,511MiB swap ocupados. vmstat em duas amostras curtas sem si/so; swap cheia não prova thrashing presente. RSS worker314744KiB (~307MiB). Cgroup uWSGI ~350MiB, sem limite local e sem OOM contabilizado; PSS e ambiente dos processos inacessíveis, não somar RSS como memória exclusiva nem extrapolar consumo exato de um novo worker.

Três processos Python/SSH (931822,931855,931943) executam mcp_server.py via runpy, com RSS317980/314504/314104KiB, soma aproximada925MiB. Não são workers HTTP; não há evidência de que estejam órfãos ou ociosos funcionalmente. Não foram encerrados. MCP HTTP possui listener próprio em127.0.0.1:8101 (PID626833), scheduler dedicado PID626770. Regras Nginx encontradas apontam /mcp para8101, mas também existem arquivos .off/.disabled: presença em disco não comprova include ativo. Compartilham recursos do host/banco; OAuth não identificado como causa de bloqueio.

PostgreSQL: max_connections100,3reservadas;21 conexões no banco incluindo1probeativo e20idle; zero idle-in-transaction e zero esperas Lock visíveis no instante. Contagens são globais/agregadas, sem leitura de dados de clientes. statement_timeout5000 retornado na coleta foi imposto somente na conexão diagnóstica: NÃO representa política da aplicação. Ambiente .env sem overrides pool_size/max_overflow; código remoto default10+20 por engine/processo. Dois workers permitem teto teórico60 conexões web, sem abertura antecipada; master, MCP, scheduler e demais serviços entram no orçamento global. Overrides reais no ambiente do processo não puderam ser lidos.

**Concorrência:** proteção ProcessLocalDatabasePools instalada em app.py remoto e engine.dispose(close=False) por PID já publicado. Produção desabilita bootstrap de scheduler/engenharia por default; verificar explicitamente ausência de override APP_BOOTSTRAP_RUNTIME_SERVICES antes de rollout. Não ligar lazy-apps, threads HTTP ou scheduler incidentalmente. Trava frontend por página não oferece idempotência entre workers, abas ou IA; fluxos financeiros concorrentes precisam de teste de atomicidade/locks/idempotência. Dois workers reduzem o impacto de uma requisição presa, mas dois pedidos presos ainda saturam a web. Não existe número fixo de usuários suportados.

**Decisão:** alvo inicial candidato é2workers com1core/thread HTTP por worker, não duas stacks completas. Não ativado: primeiro atribuir ciclo de vida dos3MCPstdio e medir folga de memória sob uso; não matar conexões ativas por suposição. Verificar orçamento de pools de todos os serviços e bootstrap efetivo. Se folga insuficiente, reduzir processos redundantes de forma acordada ou ampliar RAM antes do rollout. Pool web menor é candidato a teste, não mudança autorizada ou executada nesta análise.

**Plano de validação/rollback:** versionar configuração e backup; testar dois workers em ambiente isolado, com atraso sintético sem gravações reais e segunda requisição concluindo antes da primeira; confirmar pools separados e segregação company_id; testar concorrência financeira em banco de homologação. Em janela controlada, rollout mínimo, health + login + leitura financeira, observar ambos PIDs, fila, p95, erros/timeouts, MemAvailable, swap-in/out, eventosOOM e conexões PostgreSQL sob tráfego representativo. Rollback para configuração anterior se regressão, OOM, swapping sustentado ou aproximação do teto de conexões. Limiares finais devem ser definidos com baseline; snapshot ocioso não certifica capacidade. Diagnóstico concluído, implantação permanece pendente.

Referências primárias consultadas: https://uwsgi-docs.readthedocs.io/en/latest/ThingsToKnow.html (workers/threads, prefork e dimensionamento empírico); https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork (isolamento de pools entre processos).

### Laboratório de concorrência e atribuição MCP — AA.J.21.359
Conexões locais SSH identificadas por metadados, sem expor argumentos/credenciais: PID11568/admin,14188/analytics,31320/user; pais pwsh2304/33640/21168, todos filhos de claude.exe34096; criados19/09/2026 23:02:06. Correspondência com trio remoto por launcher/horário é forte, mas sem prova individual por socket. Não atribuir essas conexões a uma tarefa Codex específica. Três surfaces do mesmo cliente não são automaticamente redundância ou vazamento.
Amostra remota10s: PIDs931822/931855/931943 em estadoS, do_epoll_wait,6threads cada, sem incremento de CPU ticks/rchar/wchar; stdin/out/err ligados a pipes. Isso indica espera no intervalo, não abandono. MemAvailable636164–698904KiB. Evidência: mcp_lifecycle_samples.jsonl. Nenhum processo existente encerrado.
Laboratório reproduzível: scripts/qa/wsgi_isolated_concurrency_lab.py. Executável exato do APP32 identificado no cmdline; virtualenv explicitado por --home. Tentativas iniciais falharam por seleção do uWSGI genérico sem plugin Python e ausência de virtualenv; corrigido apenas no harness. Aplicação Flask sintética em diretório temporário, listener127.0.0.1 em porta efêmera; não importa APP32, não usa banco/config produção e não gera movimentação financeira.
Resultado:1worker, lenta4.002s e rápida3.982s (mesmoPID);2workers, lenta4.002s e rápida0.004s (PIDs diferentes). Transporte FastMCP sintético encerrou com EOF em0.852s/código0. Todos processos criados pelo teste encerrados; diretório temporário removido pelo contexto do teste. Evidência wsgi_isolated_lab_result.json. Isso prova isolamento de atendimento no cenário artificial, não capacidade sustentada, segurança financeira, tenant isolation ou encerramento do servidor MCP APP32 real.
Gates ainda abertos: ambiente PostgreSQL de homologação separado e dados sintéticos para testar APP32 real, corrida financeira/idempotência e company_id; identificar ciclo de encerramento do cliente real sem interromper tarefas; memória sob uso representativo; bootstrap efetivo, orçamento de pools e aprovação da janela de rollout. Solicitação de informação sobre homologação enviada ao usuário. Nenhuma publicação/restart de produção nesta etapa. Não consolidar as três surfaces em uma surface privilegiada para economizar RAM.

### Homologação disponível e baseline local
Usuário confirmou: Configr possui somente produção; homologação existente é local. Encontrados binários PostgreSQL16 portáteis já instalados no workspace. Runner existente run_audit_p0_postgresql_lab.py executado em cluster NOVO, porta loopback dinâmica, sem usar DATABASE_URL de trabalho/produção. Primeira tentativa sob sandbox falhou na criação de processo Windows; repetida com permissão de execução fora do sandbox. Suíte PostgreSQL P0:11 testes aprovados em7.92s (auditoria, consumo concorrente único de aprovação, negação cross-scope e grant tenant OAuth). Esses testes usam modelos sintéticos e componentes reais específicos, não representam validação integral de baixa financeira/APP32 com2workers. Log local: tmp/audit_p0_pg_lab/run_18b612bf52d946f899d9829c0b1e7e9f. Próxima entrega deve adicionar integração concorrente dos serviços financeiros contra banco sintético local, preservando o banco de desenvolvimento.
Checagem pós-lab remoto: PIDs sintéticos942770/942777/942778 ausentes; master839517/worker937912 e trioMCP originais preservados; /healthz200 em0.001461s. Nenhuma alteração de configuração de produção.

### Gate financeiro de concorrência — AA.J.21.360 — 20/09/2026
Teste reproduzível: scripts/qa/run_financial_concurrency_lab.py e tests/test_financial_concurrency_postgresql.py. Cluster PostgreSQL portátil NOVO em porta dinâmica127.0.0.1, senha efêmera, sem DATABASE_URL/DEV_DATABASE_URL, sem create_app, sem scheduler ou integração externa. Flask mínimo usa modelos, constraints, FinancialService.create_settlement, validação de referências, componentes e commits reais. DDL vem dos modelos locais; não homologa a cadeia de migrations nem prova equivalência integral do schema publicado. Criação global de metadata falhou inicialmente em índice duplicado ix_organizational_identities_company_id de módulo alheio; fixture passou a criar somente tabelas financial_* e fechamento transitivo de suas FKs. Nenhum modelo/runtime foi editado para acomodar o teste.

Resultado:2passed/1failed em11.54s. Sequencial:primeira baixa60 aceita e segunda60 rejeitada em lançamento100. Negativos de company_id cruzado e conta bancária de outra empresa rejeitados sem gravação. Concorrência: duas sessões PostgreSQL/backendPIDs33936 e21892, com códigos distintos RACE-1/RACE-2, leram saldo ainda não baixado e ambas confirmaram60; soma persistida120 em lançamento100. Barreira de teste sincroniza após a consulta SQL real de SUM; não falsifica saldo nem substitui funções financeiras. Threads são clientes com app_context/sessão SQL independentes: reproduz corrida no banco, não é teste uWSGI multiprocess completo.

Causa no caminho testado: validação read-then-write do saldo não serializa transações sobre o lançamento; SELECT de entrada não possui lock FOR UPDATE nesse método. Códigos únicos diferentes não protegem o limite financeiro agregado. A falha não depende de2workers para existir se web/CLI/MCP escreverem concorrentemente. Não há evidência de ocorrência passada em clientes; reprodução restrita aos dados sintéticos. Teste negativo fica vermelho de propósito até correção, sem xfail ou afrouxamento de assert.

Decisão: BLOQUEAR promoção de2workers enquanto a integridade financeira concorrente não estiver corrigida e retestada. Próxima entrega: proteção transacional com escopo company_id e ordem de locks definida, rechecagem de saldo após lock, estudo de idempotência e revisão dos caminhos relacionados (borderô, exclusão/estorno, alteração de principal). Não usar trava Python/front-end como garantia entre processos. Adaptar sincronização do teste para não bloquear artificialmente o detentor de futuro row-lock. Revalidar negativos tenant e operações independentes. Ainda não testados nesta entrega: baixa de borderô concorrente, estornos, automação, recorrências e corrida de geração de código. Não declarar todas as operações financeiras seguras.

Evidências duráveis: financial_concurrency_test_result.txt e financial_concurrency_lab_result.json em docs/harnesses/screen_performance_inventory_v1. Cluster run_bf8ef2e4a19946ba8c23fba07f66014b encerrado (listener_stopped=true). Runtime de produção não alterado. Comparação de hashes estruturais dos métodos com arquivos publicados é etapa complementar, não execução financeira remota.
Comparacao SFTP somente leitura concluida: hashes AST iguais em create_settlement, normalizacao de codigo, base de principal, modelos FinancialEntry/FinancialSettlement e get_active_bordero_for_entry. Evidencia financial_concurrency_fingerprints.json. Confirma igualdade desses trechos com arquivos publicados, nao reproduz incidente em producao nem valida todo o schema remoto.

### Correção local de criação de baixa concorrente — AA.J.21.361
FinancialService.create_settlement agora adquire SELECT FOR UPDATE NOWAIT na linha FinancialEntry, filtrada por id/company_id/deleted_at, antes de ler a soma baixada. populate_existing atualiza objeto já presente no identity map. Lock persiste na transação até commit/rollback; conflito SQLSTATE55P03 faz rollback e retorna mensagem de operação concorrente, sem aguardar liberação nem repetir gravação. Não é trava Python e funciona entre processos que seguem o mesmo protocolo. Saídas de validação que já retornavam sem commit continuam dependendo do teardown/rollback do chamador para encerrar a transação. Erros de transporte não recebem retry automático.

5 testes PostgreSQL real aprovados em7.66s:sequencial; negativos empresa/conta cruzada; corrida com duas conexões e uma única baixa aceita; lock externo recusado emmenos2s, outro lançamento independente aceito e recuperação após unlock; identity map carregado100 e banco alterado40 corretamente rejeita baixa60. Sincronização de corrida foi movida para ANTES da aquisição de lock, com janela200ms após consulta de soma: manter barreira entre duas leituras após lock causaria deadlock artificial no próprio teste. Nenhuma regra ou saldo foi mockado.18 testes unitários existentes aprovados em2.61s, doubles de query ganharam somente suporte a populate_existing/with_for_update. Sintaxe e diff aprovados. Cluster run_ab882c831c594cbe99fa3b672f3c4b8f encerrado.

Apenas import OperationalError e bloco de aquisição de entrada em create_settlement foram alterados pelo trabalho atual. Arquivo compartilhado já contém mudança alheia em exclusão de baixas contratuais: não incluir essa mudança incidentalmente em release. Patch cirúrgico financial_settlement_nowait.patch e manifesto financial_settlement_nowait_release_manifest.json preparados; ainda sem commit/deploy. Resultados preservados separadamente dos testes vermelhos anteriores. Esta correção cobre o defeito reproduzido de duas criações de baixa do mesmo lançamento; não certifica todos os caminhos de borderô, estorno, atualização de principal, geração concorrente de código automático ou idempotência de repetição após resposta perdida. Dois workers continuam pendentes de gates restantes e publicação controlada. Nenhuma alteração em produção nesta entrega.

### Atomicidade de borderôs e estornos — AA.J.21.362 — 20/09/2026
Suite PostgreSQL local ampliada para8cenarios, preservando os5verdes da correcao de criacao de baixa. Fixture persistida com modelos reais:2titulos/2lancamentos/2itens em bordero, baixa-pai120 e2filhas60, segunda conciliada. Sem mock de falha: a regra real impede estornar a filha conciliada. Negativo cross-company de estorno do bordero passou.
Resultado6passed/2failed em15.93s. Falha1:delete_settlement do bordero chama delete_settlement individual, que commita cada filha. Primeira filha ID7 excluida logicamente;segunda recusada por conciliacao;pai permanece ativo. Mesmo rollback explicito no chamador nao reverte a primeira filha ja commitada. Prova de estorno parcial em dados sinteticos, nao evidencia de ocorrencia em cliente. Falha2:estorno individual sob row-lock externo espera6.22s e retorna erro de lock_timeout. Esse limite6s pertence exclusivamente ao laboratório; nao inferir limite equivalente em producao. A protecao NOWAIT anterior cobre apenas create_settlement, nao delete_settlement.

Inspecao adicional: update_settlement de bordero chama delete seguido de create; criacao percorre composicao/titulo/baixa com commits internos. Sao riscos de atomicidade identificados em codigo, ainda NAO reproduzidos por esses testes. Esta entrega nao valida criacao/edicao de bordero integral nem paralelismo desses caminhos. O service financeiro local tem alteracao preexistente de exclusao contratual alheia;fixture sem contratos evita atribuir a ela os resultados.

Plano de correcao: estabelecer dono unico da transacao no service composto; filhos devem permitir flush sem commit quando chamados pelo bordero;rollback integral em qualquer erro. Prevalidar conciliacao de todos os filhos, mas prevalidacao sozinha nao substitui transacao atomica. Serializar estorno e criacao pela mesma linha de lancamento, reler baixa apos lock, definir ordem consistente bordero->lancamentos ordenados->baixas e tratar NOWAIT sem retry automatico. Cobrir falha no segundo filho, sucesso integral, tenant, lock externo e criacao concorrente com estorno. Aplicar contrato transacional tambem na substituicao de baixa (delete+create) antes de aprovar2workers.

Evidencias:bordero_reversal_test_result.txt e bordero_reversal_lab_result.json. Cluster run_2d3c7375182d4dc896c386d24c78358d encerrado. Nenhum runtime ou dado de producao alterado nesta etapa. Gate de2workers continua REPROVADO;correcoes ainda pendentes.

### Estorno atomico local — AA.J.21.363
FinancialService.delete_settlement recebe commit=True por default;quando chamado pelo bordero com commit=False usa flush e deixa confirmacao para o servico composto. Obtem lock NOWAIT na entrada tenant-scoped,depois relê/atualiza e bloqueia a baixa para revalidar existencia/conciliacao.55P03 retorna conflito amigavel com rollback. Bordero delete_settlement adquire locks NOWAIT em bordero e baixa-pai,ordena filhos por financial_entry_id/id,chama todos sem commit e faz rollback em qualquer erro. Prepara serializacao antes do unico commit final para nao transformar erro de montagem de resposta em falsa falha financeira apos commit. Helpers de carga mantem comportamento anterior nos chamadores sem for_update.

Resultados:29unitarios aprovados4.69s;10testes PostgreSQL real aprovados15.53s. O teste anteriormente vermelho de falha no segundo filho agora preserva os dois filhos e pai apos rollback. Estorno individual em entrada bloqueada agora recusa emmenos2s. Novo teste de sucesso observa exatamente1evento commit e reabertura integral do bordero200/itens100;novo teste de lock do bordero preserva filhos/pai. Negativos tenant e5cenarios anteriores de baixa concorrente continuam passando. Sem mocks de regra financeira nos testes PG;DDL derivado de modelos locais,não cadeia de migrations. Cluster run_e24c803c652e479f9e611225305f3ced encerrado.

Escopo/limites:correcao local da exclusao/estorno de baixa individual e estorno completo do bordero. Criacao de bordero e update_settlement(delete+create) ainda possuem contratos de commits a revisar;nao declarar substituicao atomica nem liberar2workers. Nao garante idempotencia apos resposta perdida,corrida de geracao de codigo,atualizacao concorrente de principal ou reconciliacao por caminhos que nao compartilhem o protocolo de lock. Os retornos de validacao sem escrita continuam dependendo do teardown/rollback do chamador para finalizar transacao. Alteracoes preexistentes de exclusao contratual em financial_service.py preservadas e nao devem ser publicadas incidentalmente.
Evidencias: bordero_reversal_fix_test_result.txt e bordero_reversal_fix_lab_result.json. Arquivos alterados nesta entrega:services/financial_service.py,services/financial_bordero_service.py,tests/test_financial_bordero_guardrails.py,tests/test_financial_concurrency_postgresql.py. Sem schema migration,commit ou deploy nesta etapa;requer release isolada,comparacao com publicado e janela de rollout apos gates restantes.
# Validação local complementar — 20/09/2026 (AA.J.21.364)

Publicação da branch: `codex/financial-atomicity-v3`, commit `918aabce60a177265321cd4aeeb05cbea1d952f5`, enviada ao origin (sem merge, dispatch de workflow ou deploy). Workflow de deploy da branch inspecionada é manual. Inventário remoto somente leitura em 2026-09-20 04:07 UTC identificou scheduler PID 626770 e árvore uWSGI sob `python3.12-uwsgi.service`, incluindo worker anteriormente identificado PID 937912. Quantidade de processos uWSGI não equivale a quantidade de workers HTTP. Duas buscas em cmdline por nomes de scripts/módulos MCP não encontraram correspondências acessíveis neste snapshot; isso não prova ausência de listeners, outros runtimes ou futuras sessões CLI. Evidência `financial_atomicity_writer_inventory.json`. Antes do rollout, confirmar listener/supervisor MCP e política de reconexão dos clientes; incluir scheduler na avaliação de escritores. Nenhum restart executado.

AA.J.21.365 — candidato v3 isolado: dois novos testes reproduziram retenção da trava de numeração após lançamento inexistente e valor acima do saldo (18 aprovados/2 falhas). `create_settlement` passou a usar o proprietário transacional: operação direta confirma uma vez ou reverte ao retornar erro; operação aninhada preserva o proprietário externo. Correção validada com contexto Flask ainda aberto e outra conexão adquirindo a trava imediatamente após rejeição. **20 testes PostgreSQL aprovados (14,38 s)** e **37 unitários (8,93 s)** na cópia isolada. Patch v3 aplicado à base limpa reproduziu os seis hashes; cluster encerrado. Evidências `financial_numbering_release_before_*`, `financial_atomicity_v3_*` e manifesto/patch `financial_atomicity_candidate_v3*`.

Escopo concluído localmente: proteção contra colisão com conflito sem espera, rollback das rejeições e integração ao pacote mantendo regra contratual de produção. Sem publicação, versionamento ou ativação do segundo worker. Idempotência, atualização coordenada de todos os escritores HTTP/MCP, nova checagem de drift e dimensionamento de memória/conexões continuam como gates de rollout. A varredura histórica na geração do código ainda existe.

AA.J.21.365 — correção local da numeração: validação de payload/escopo antes de consultar códigos; `pg_try_advisory_xact_lock(1735816302, company_id)` antes da numeração automática, mantido até commit/rollback. Contenção retorna mensagem explícita e rollback imediato, sem espera ou retry automático. Códigos manuais fora do padrão numérico BX/LIQ não adquirem essa trava. **18 testes PostgreSQL aprovados (13,54 s)** e **37 unitários (5,57 s)**. Testes cobrem disputa em títulos distintos (uma operação recebe conflito e a nova tentativa gera código diferente), outra empresa independente, código manual e resposta sob lock externo em menos de 2 s; cluster encerrado. Evidências `financial_auto_code_lock_tests.txt` e `financial_auto_code_lock_result.json`.

Trade-off explícito: não garante que ambas as requisições simultâneas tenham sucesso na primeira tentativa; prefere conflito controlado à espera do worker. Ainda usa varredura histórica para gerar número e não implementa idempotência. Participantes antigos que não tomam a trava não são protegidos por ela; alinhar runtime HTTP/MCP no rollout. Alteração ainda no checkout compartilhado, fora do candidato v2 validado. Pendentes integração ao pacote isolado, teste de caminhos de rejeição/liberação da sessão e rollout; produção inalterada.

AA.J.21.365 — numeração concorrente: reproduzida no candidato v2 isolado com duas sessões PostgreSQL e títulos diferentes da mesma empresa. Barreira antes do INSERT, sem substituir a geração real: ambas escolheram `BX-000001`; uma confirmou e a outra sofreu `UniqueViolation` na constraint `uq_financial_settlements_company_code`. **16 testes aprovados/1 falha em 11,78 s**. Evidências `financial_auto_code_race_before_tests.txt` e `financial_auto_code_race_before_result.json`. Não houve duplicidade persistida; houve rejeição indevida da segunda baixa legítima. Confirma risco entre clientes concorrentes, não prova causa do travamento histórico em produção. Próxima etapa: alocação atômica de numeração com escopo por empresa e espera limitada, preservando códigos manuais e rollback composto. Produção inalterada.

Candidato v2: preservada a permissão de estorno contratual observada em produção, sem restaurar a restrição antiga. `financial_atomicity_candidate_v2.patch` aplicado à base limpa reproduziu os seis hashes; **37 testes unitários aprovados (4,01 s)**, incluindo a expectativa permissiva vigente, e **16 testes PostgreSQL aprovados (13,78 s)** na cópia isolada. Cluster encerrado. Logs `financial_atomicity_v2_unit_tests.txt`, `financial_atomicity_v2_pg_tests.txt`, `financial_atomicity_v2_pg_result.json`; manifesto v2 com hashes. O candidato v1 permanece registrado como não publicável. Compatibilidade funcional específica resolvida, mas não houve versionamento/deploy; geração concorrente de códigos, idempotência e capacidade para dois workers continuam pendentes. Os arquivos remotos não foram alterados nesta rodada.

Compatibilidade remota (consulta SFTP somente leitura, 2026-09-20 03:49 UTC): quatro serviços existentes coincidem com a base; `financial_transaction.py` ainda não existe; `financial_service.py` diverge em `delete_settlement`. **A remoção da restrição contratual anteriormente excluída do candidato já está em produção.** Publicar o candidato atual restauraria uma restrição antiga e mudaria comportamento vigente. Logo, validação local verde não significa compatibilidade para deploy. Rebasear o candidato preservando explicitamente a regra remota e reexecutar os testes correspondentes; não sobrescrever o arquivo remoto inteiro. Evidências `financial_atomicity_production_compatibility.json` e `financial_atomicity_production_reversal_drift.patch`.

Revisão estática de concorrência: `_generate_settlement_code` lê todas as baixas da empresa e calcula máximo + 1 antes do lock do lançamento. Locks por lançamento não serializam títulos distintos da mesma empresa; há risco de colisão, limitado pela constraint única, e custo de leitura crescente. Isso é hipótese fundamentada em código, não nova reprodução concorrente nesta rodada. Avaliar alocador atômico por empresa e política de repetição/idempotência em entrega delimitada. Nenhum banco consultado, arquivo remoto alterado ou worker reiniciado nesta verificação.

Conclusão da regressão local do pacote: **37 testes unitários aprovados (4,95 s)** após restaurar literalmente, só na cópia isolada, `test_delete_settlement_rejects_contract_managed_title_outside_bordero_context` do commit-base. Não houve remoção de proteção nem alteração do checkout compartilhado. Diferença de escopo dos testes em `financial_atomicity_candidate_test_scope.patch`; resultado em `financial_atomicity_isolated_unit_tests.txt`. Os seis hashes de runtime permanecem idênticos aos candidatos que passaram nos **16 testes PostgreSQL**. Manifesto marcado `isolated_local_validation_passed_not_deployed`. Isso conclui a validação local delimitada, não o incidente de produção: faltam versionamento isolado, verificação de divergências com produção, concorrência na geração de códigos/idempotência e dimensionamento/rollout dos workers. Integração de retenções bruto/líquido permanece separada.

Teste do candidato exato: exportados arquivos Python rastreados do commit-base em diretório descartável e aplicado o patch; conferidos hashes dos seis serviços (normalização LF antes da conferência final). Sem .env de produção. **16 testes PostgreSQL aprovados (13,05 s)** e cluster encerrado. Suite unitária copiada do checkout compartilhado: **36 aprovados/1 falha (7,89 s)**. A falha é `test_delete_settlement_allows_contract_managed_title_without_bordero`, que exige justamente a mudança de permissão contratual excluída deste pacote. Não remover a proteção nem silenciar o teste para obter verde: separar a alteração e o teste correspondente da outra entrega, restaurando a expectativa do contrato-base no conjunto isolado. Manifesto atualizado; logs PostgreSQL em `financial_atomicity_isolated_pg_tests.txt` e `financial_atomicity_isolated_pg_result.json`. Não publicado.

Pacote candidato isolado: `financial_atomicity_candidate.patch` e `financial_atomicity_candidate_manifest.json` no harness de performance, seis arquivos de serviço, hashes e commit-base explícitos. Excluída do pacote a remoção preexistente da proteção de estorno de títulos contratuais; arquivo compartilhado não foi revertido. Sintaxe dos seis candidatos validada por AST. Verificação de aplicação deve usar a base limpa registrada, não o checkout já modificado. Os resultados anteriores (16 PostgreSQL/37 unitários) são do checkout compartilhado e **não certificam este candidato isolado**. Próximo passo: executar a regressão contra os arquivos exatos do pacote antes de qualquer publicação. Integração bruto/líquido de retenções segue separada e sem suposição de regra financeira.

Revisão da integração contratual: o borderô distribui `gross_amount` entre itens, soma somente `allocated_to_item` aos saldos e reconstrói estornos a partir de `metadata_json.allocations`. O motor satélite cria uma compensação adicional no principal e uma baixa no título satélite. Portanto, apenas propagar `ignore_bordero_lock=True` deixaria a contabilização/auditoria do borderô sem representar essas compensações e não resolve a reversão delas. Não implementar esse bypass.

Decisão funcional pendente solicitada ao usuário: em título de 1.000 com retenção de 50, o valor informado no borderô é 950 líquidos ou 1.000 brutos? Essa definição determina rateio, valor bancário, quitação do principal e estorno. Até confirmação, preservar rejeição atômica testada; integração funcional de retenções não deve ser confundida com a investigação de capacidade WSGI. Nenhuma nova alteração de runtime nesta revisão.

Validação de política persistida: **16 testes PostgreSQL aprovados (11,35 s)** e **37 unitários (4,71 s)**. Cenário sintético usa `FinancialSatellitePolicy` e `FinancialScheduleLink` reais, retenção proporcional e motor contratual sem mock. A compensação automática tenta baixar um título bloqueado pelo próprio borderô; a regra existente rejeita e a correção faz rollback integral (zero commits, zero baixas e zero execuções satélites, saldo preservado). Não foi introduzido bypass de bloqueio. Evidências `bordero_real_policy_tests.txt` e `bordero_real_policy_result.json`. Cluster encerrado.

Achado funcional: a política proporcional testada é incompatível com esse fluxo de borderô sob o bloqueio atual. O teste valida rejeição segura, **não sucesso de todas as políticas**. Antes da liberação ampla, definir e testar a integração da compensação ao borderô sem duplicar principal ou contornar company_id. A primeira execução teve apenas falha de referência expirada no teste, corrigida guardando o ID antes do fechamento da sessão. Pacote isolado ainda não concluído; produção inalterada.

Atualização contratual: injeção de exceção de aplicação, sem rollback, na chamada do motor satélite reproduziu confirmação indevida do borderô (14 aprovados/1 falha). Corrigido localmente com `abort_owned_financial_operation`: a captura de exceção em `create_settlement_from_schedule` marca a transação composta como abortada e retorna erro; o proprietário efetua rollback. Resultado: **15 testes PostgreSQL aprovados (12,93 s)** e **37 unitários aprovados (8,02 s)**. Evidências `bordero_satellite_before_tests.txt`, `bordero_satellite_after_tests.txt`, `bordero_satellite_after_result.json`; ambos os clusters encerrados. Teste verifica zero commits, zero baixas pai/filho e saldo original preservado.

Escopo exato: falha injetada na fronteira do motor contratual, não execução completa de políticas contratuais reais. Comportamento legado fora de transação composta permanece inalterado. Não atribuir a este teste cobertura integral de satélites, release preparado ou deploy. Próximo gate: revisão do diff isolado/dependências e cenários contratuais reais antes de publicação.

Atualização: caminhos positivos de criação e edição aprovados, com exatamente um commit por operação, saldos persistidos de 100 baixados/100 abertos, soma dos itens/filhos consistente e original cancelado na edição. Total **14 testes PostgreSQL aprovados (12,58 s)**, listener encerrado; evidências `bordero_creation_edit_success_tests.txt` e `bordero_creation_edit_success_result.json`. Regressão ampliada com testes contratuais existentes: **37 aprovados (3,97 s)**, executados a partir de `app32/`.

Pendência de revisão contratual: `FinancialScheduleService.settle_schedule` captura exceção do motor satélite e retorna informação de erro dentro do resultado; uma exceção sem rollback pode não marcar o proprietário de transação como abortado. Os testes contratuais existentes não substituem um cenário integrado com política satélite real. Manter gate de publicação aberto até reproduzir e definir o comportamento obrigatório para essa falha.

- Criação/edição de baixas de borderô: reprodução anterior com 10 testes aprovados e 2 falhas por persistência parcial. Evidência preservada em `../harnesses/screen_performance_inventory_v1/bordero_creation_edit_before_tests.txt`.
- Ajuste local: proprietário de transação por sessão; serviços internos fazem flush, e apenas o proprietário confirma. Commit intermediário ou rollback interno capturado abortam a operação composta. Locks de borderô com NOWAIT e company_id preservado.
- Nova execução PostgreSQL descartável: **12 aprovados**, incluindo falha no segundo filho e falha na substituição da baixa original; listener encerrado. Evidências `bordero_creation_edit_after_tests.txt` e `bordero_creation_edit_after_result.json` no mesmo harness.
- Regressão unitária: **33 aprovados**, incluindo quatro testes do proprietário de transação (sucesso aninhado, commit indevido, rollback capturado e erro aninhado).
- Limites: ainda faltam casos positivos de criação/edição composta com conferência de commit único e cobertura de efeitos satélites contratuais. Isso não valida concorrência WSGI multiprocesso nem autoriza publicação. Produção e quantidade de workers não foram alteradas nesta etapa.

### Publicacao financeira v3 — 20/09/2026 UTC

- Publicados cirurgicamente os seis arquivos do pacote versionado em `77355c063b9c391b26d88f0095733295ca612dc4` (codigo `918aabce60a177265321cd4aeeb05cbea1d952f5`), sem reset geral do checkout de producao e sem migracao de modelo.
- Primeira tentativa revertida: verificacao exigia novo PID do master; uWSGI preservou o PID do master em reexec e substituiu o worker. Corrigido o criterio para verificar a substituicao efetiva do worker.
- O restart revelou drift preexistente no MCP: quatro arquivos em disco estavam incompatíveis com o runtime. Restaurados `src/core/mcp_surface_registry.py`, `src/intelligence/tooling/capabilities.py`, `src/intelligence/tool_catalog.py`, `src/core/mcp_financial_tools.py` a partir do proprio HEAD de producao `7886d25152b6740adf68ce0d31459b739ae6fad1`, preservando backups. MCP voltou a iniciar pelo manager oficial.
- Segunda tentativa concluida: snapshot `financial_atomicity_v3_1789878353`; seis hashes finais conferidos; worker `959746` substituido por `962309`; master `839517` preservado; scheduler reiniciado com health aprovado; MCP reiniciado com health local/publico aprovado.
- Smoke final: web e MCP HTTPS 200; oito surfaces anunciadas retornaram 401 ao initialize sem credencial (seguindo redirect do mesmo host quando necessario); fila uWSGI zero, unico worker idle, harakiri zero nesta amostra.
- Navegador autenticado na empresa 9: reload do bordero 54 concluiu e exibiu “Dados carregados. Bordero pronto para operar.” Somente leitura; nenhum lancamento/baixa de teste efetuado em producao.
- Memoria na amostra final: 708 MiB disponiveis; swap 508/511 MiB utilizada. Mantido UM worker. Isso nao constitui aprovacao de capacidade para dois workers nem prova de eliminacao de toda lentidao.
- Validacao ainda pendente: smoke MCP com credencial positiva e segregacao efetiva de surfaces/tenants apos recuperacao. Negacao sem auth e leitura web autenticada nao substituem esses testes. Card AA.J.21.366 permanece com passo 3 pendente ate completar esta verificacao.
- Evidencias: `financial_atomicity_deploy_attempt1_plan.json`, `financial_atomicity_deploy_attempt1_result.json`, `financial_atomicity_deploy_plan.json`, `financial_atomicity_deploy_result.json`, `financial_atomicity_postdeploy_smoke.json` no Harness `screen_performance_inventory_v1`.

### Complemento — smoke autenticado MCP apos publicacao

- Credencial interna existente, vinculada a empresa Versus (9), reutilizada apenas em `initialize` e `tools/list`; nenhum segredo impresso e nenhuma tool de negocio executada.
- `admin`: autenticacao positiva e catalogo com 284 ferramentas. `ops`: autenticacao positiva e apenas `list_ops_app32_capabilities` no catalogo.
- `user` e `analytics`: token interno rejeitado com HTTP 401. Configuracao server-side confirmada: estas duas surfaces usam OAuth; admin/ops nao. Portanto, a rejeicao do token legado nao demonstra falha do OAuth.
- Limite: ainda nao realizado smoke positivo com token OAuth de usuario nem exercicio de isolamento entre tenants. O token interno e amplo e nao prova negacao de surface a uma identidade de menor privilegio. Nao alterar allowlists nem emitir credenciais para contornar esse gate.
- Evidencia: `financial_atomicity_mcp_authenticated_smoke.json`. Card AA.J.21.366 segue pendente no passo 3.

### Disponibilidade do conector OAuth no cliente — 20/09/2026

- Consulta sanitizada por `codex mcp list --json`, sem ler/exibir tokens: no ambiente restrito desta tarefa aparece `app32-pilot`, habilitado, auth_status `unknown`.
- No contexto local fora do sandbox aparece `mcp-versus`, habilitado, auth_status `o_auth`. Este valor identifica o mecanismo configurado; nao comprova validade atual do token ou sucesso de uma chamada.
- As ferramentas APP32 nao estao expostas no catalogo desta tarefa. Nao foi iniciado outro agente/CLI autonomo nem extraido token do cofre para contornar essa limitacao.
- Proxima evidencia necessaria: consulta somente leitura pela conexao OAuth existente. Nao substituir esse teste por token interno, nem fechar o gate de isolamento apenas com initialize/tools-list.
