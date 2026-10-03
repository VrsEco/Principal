# Runbook — Reparo pontual de referências de conciliação Inter

## Card local da entrega

`[Reparo pontual de referências Inter]`. Sem MCP autenticado disponível e sem
autorização de escrita em produção, o card e checklist ficam registrados aqui;
nenhum script SSH de cards é executado.

- [x] Diagnóstico e contrato: preservar matches, baixas e campos financeiros.
- [x] Serviço interno, adaptador PostgreSQL e testes sintéticos isolados.
- [x] Validação local final, revisão dos três arquivos novos e entrega de evidências.
- [x] Reteste PostgreSQL isolado, regressões e revisão dos locks: 53 + 21 testes.
- [x] Revisão local de sintaxe/whitespace e escopo dos quatro arquivos do reparo.
- [x] Staging exclusivo dos quatro arquivos, sem executar commit.
- [ ] Black e Flake8 (ausentes; não instalados e não aprovados).
- [ ] Aprovação separada e aplicação autenticada em produção (fora do escopo).

## Escopo e evidência

As identidades e o estado inicial foram fornecidos pelo usuário/engenharia, não
consultados novamente neste ambiente. Empresa 9, conta 1 Inter, lote 84,
`REC-20260918-INTER-CSV-V2`:

| Linha | Match confirmado | Entrada | Baixa posted/pending |
|---|---|---|---|
| 9577 | 538 | 2673 | 2752 |
| 9581 | 539 | 2615 | 2684 |
| 9584 | 540 | 2618 | 2687 |

O plano constante `INTER_REFERENCE_REPAIR_PLAN` é configuração inerte. Os testes
usam empresa 77, conta 20 e IDs sintéticos distintos. O serviço não cria app,
não carrega `.env`, não escolhe conexão e não tem rota, CLI ou ferramenta MCP.
Somente novos arquivos desta entrega são alterados; trabalhos anteriores são
preservados. Nenhum plano foi aplicado a dados reais.

## Contrato

`FinancialReconciliationReferenceRepairService(repository)` oferece `dry_run`,
`apply` e `recover`. Todas exigem um plano explícito e escopo de empresas;
escritas também exigem ator autenticado e confirmação de autorização financeira
de edição pelo chamador. Esses argumentos não autenticam ninguém: uma futura
integração autorizada deve obter identidade/RBAC do contexto confiável existente,
nunca de campos livres enviados pelo cliente. Nenhuma permissão nova é publicada.

`dry_run` retorna snapshot e fingerprint do plano para revisão. `apply` exige esse
snapshot aprovado, revalida identidades, natureza, valores exatos com Decimal,
datas presentes, ausência de cancelamento/exclusão, conta e referências. As datas
financeiras não precisam coincidir entre banco e baixa: são preservadas e sua
aprovação exata fica vinculada ao fingerprint do snapshot. Havendo divergência
desde o dry-run, a operação aborta antes da escrita. Plano máximo: três pares
distintos. Reparo completo já existente retorna `changed=false`, sem flush ou
novo evento de auditoria, somente com snapshot atual aprovado; referências
parciais compatíveis podem ser completadas. Snapshot obsoleto sempre aborta,
inclusive quando as referências já estão completas.

Alterações permitidas:

- Match: `metadata_json.financial_settlement_id` e histórico de auditoria da operação.
- Baixa: `metadata_json.import_batch_id/import_row_id/reconciliation_match_id` e
  `reconciliation_status=reconciled`.
- `updated_at` dos registros alterados segue o mecanismo normal do ORM.

Não alterar `settlement.import_batch_id` (coluna), valores, contas, datas, status
financeiros, códigos, componentes, grupos de transferência ou registros de entrada.
Não cancelar/recriar baixas ou matches. Pontas CEF 2674/2753 e EFI 2619/2688 e os
cinco casos anteriormente corrigidos ficam fora da lista de escrita. Antes do
ensaio/aplicação, registrar snapshots dessas sentinelas e confirmar seus grupos
`trf-c8a7328f7918` e `trf-77716ceb3679` apenas por leitura.

## Transação, concorrência e limitações

`PostgresReferenceRepairRepository(engine)` exige um engine PostgreSQL que o
operador já tenha autorizado. Não há engine padrão. Ele abre uma sessão dedicada
e faz um único commit para todos os pares; qualquer exceção faz rollback.
O dry-run usa REPEATABLE READ READ ONLY. Escritas adquirem locks de tabela
SHARE ROW EXCLUSIVE NOWAIT nas seis tabelas participantes antes de ler/validar.
Além disso, a leitura dos registros alvo em transações de escrita usa
`SELECT FOR UPDATE NOWAIT`: o lock de tabela é compatível com ROW SHARE de um
escritor que já tenha travado uma linha, portanto sozinho não evita espera no
flush. O dry-run continua somente leitura e não adquire locks de escrita.
Assim, escritores legados que não cooperam com advisory locks também não podem
inserir vínculos durante a checagem. Os locks abrangem outros tenants e podem
rejeitar a execução durante atividade financeira: manter a operação breve e
usar janela controlada. Falha de lock não autoriza retry automático.

A leitura de conflitos percorre matches e baixas ativos da empresa. Ensaiar
tempo/volume em clone PostgreSQL autorizado antes de produção. Não trocar locks
por advisory locks sem adaptar todos os escritores. A instância não deve ser
compartilhada entre threads. Os testes em memória verificam o contrato e a
atomicidade simulada, não provam locks, deadlocks ou rollback do PostgreSQL real.

## Snapshot, auditoria e recuperação

O recibo inclui IDs, estados, versões, hashes SHA-256 dos campos escalares e
metadados, e presença/valor anterior das chaves permitidas. Não exporta payload
bruto, descrições, documentos, notas, credenciais ou metadados financeiros inteiros.
Cada match recebe evento persistido com operação, ator, instante, par e campos
anteriores estritamente necessários. Preservar o recibo em trilha autorizada,
com acesso restrito e associado à aprovação; não adicionar segredos.

`recover` exige o recibo da aplicação, nova autoridade de edição e snapshot atual
igual ao posterior. Também revalida ausência de novos conflitos/dependências e
compara os valores de restauração com a auditoria persistida, impedindo edição do
recibo para restaurar valores arbitrários. Restaura só as chaves alteradas
(distinguindo ausente de null) e o status anterior; mantém auditoria e acrescenta
evento de recuperação. Não restaura timestamps históricos. Mudança concorrente
ou segunda recuperação bloqueia e exige revisão, nunca sobrescreve mudanças.

Na busca de dependências fora do plano, IDs JSON numéricos em string também
contam como vínculos, como no workspace existente. Referências não nulas que
não sejam inteiros positivos ou strings convertíveis em inteiro positivo
abortam o reparo; não são ignoradas. As referências dos próprios alvos continuam
sujeitas à validação estrita original. Isso não amplia a lista de escrita.

## Validação futura e prevenção separada

1. Confirmar contexto autenticado, tenant/RBAC, engine autorizado e sentinelas.
2. Executar dry-run somente leitura; revisar snapshot e pré-condições. Obter
   autorização específica de aplicação; a autorização local não cobre produção.
3. Aplicar uma vez pelo serviço dentro da futura integração autorizada; guardar
   recibo. Não chamar a rota de conciliação de grupo: ela rejeita matches confirmados.
4. Consultar lote 84 e baixas pelos GETs oficiais. No workspace da empresa 9,
   conta 1, lote 84 e mesmos filtros, conferir cada linha com um match confirmado,
   cada baixa com um banco vinculado, modo 1:1 e `is_reconciled=true`.
5. Não esperar aumento em `summary.confirmed_matches`: os três matches já existem.
   As três baixas deixam o grupo sem vínculo quando visíveis no mesmo recorte.
   Confirmar sentinelas, componentes e campos financeiros invariantes.

Prevenção de recorrência é outra entrega: confirmação e baixa/vínculo atômicos,
referências bidirecionais em todos os caminhos, contagem distinta de linhas e
vínculos. Este serviço não modifica `review_match`, a UI ou o contador.

## Evidências locais — rodada original

Em 03/10/2026, suíte específica executada com plugins pytest desabilitados,
sem cache/bytecode e somente repositório sintético: **37 testes passaram**.
A suíte extrai por AST os dois serializadores reais do workspace, sem importar
a aplicação: antes (3 matches confirmados, 0 vínculos de baixa, 0 baixas
conciliadas), depois (3, 3, 3). O contrato do adaptador também foi testado com
session/engine/models substituídos por doubles, sem conexão PostgreSQL.

Comando executado na raiz, PowerShell:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
& .venv\Scripts\python.exe -B -m pytest -c pytest.ini -p no:cacheprovider app32\tests\test_financial_reconciliation_reference_repair.py -q
```

Os dois arquivos Python foram compilados em memória, sem importar código nem
gerar bytecode. A revisão whitespace dos três arquivos via `git diff --no-index
--check` não apontou erros; retornou código 1 por comparar arquivos novos com NUL
e aviso de conversão futura LF/CRLF. `flake8` foi tentado e está ausente; a
descoberta local confirmou ausência de flake8, pycodestyle, ruff e mypy. Não foram
instalados. PostgreSQL real, validação de tela em produção, lint e typecheck
permanecem pendentes; nenhum sucesso nesses controles é presumido.

## Tentativa de integração nativa — bloqueio histórico do Windows

Esta seção registra a tentativa original. O reteste autorizado e suas correções
de bootstrap/proteção de linha são registrados na seção final; os erros abaixo
não representam aprovação nem o resultado dessa nova rodada.

Em 03/10/2026 foram encontrados os binários instalados de PostgreSQL **14.20-2**
em `C:\Program Files\PostgreSQL\14\bin`; o serviço PostgreSQL existente não foi
acessado. O Docker foi consultado apenas pelo named pipe local, com diretório de
configuração vazio temporário; não há daemon em `npipe:////./pipe/docker_engine`.
Não foram instalados componentes, iniciados serviços existentes ou baixadas imagens.

A suíte opt-in `test_financial_reconciliation_reference_repair_postgres.py`
tentou criar um único cluster novo sob o TEMP autorizado, com binários existentes.
O bootstrap falhou em `initdb`, antes de iniciar servidor ou conectar ao banco:

```text
initdb: error: could not create restricted token: error code 87
initdb: error: could not re-execute with restricted token: error code 3
initdb: error: could not create directory "C:/Users/mff20": File exists
```

Resultado real: **6 erros de setup compartilhando a mesma falha; zero testes de
banco executados**. O diretório temporário criado pela suíte foi removido por seu
cleanup; nenhuma porta de PostgreSQL novo ficou ativa. Não houve retry com
escalonamento, modificação de ACL/permissão, conexão ao serviço existente ou
contorno do sandbox. O pré-requisito é uma execução local autorizada sob usuário
Windows capaz de iniciar `initdb`/`postgres` no diretório temporário, ou um runtime
local de containers já disponível com imagem PostgreSQL existente e isolamento
comprovado. Isso precisa ser resolvido fora deste sandbox, sem usar produção.

A suíte permanece desabilitada por padrão. Para um operador autorizado executar
fora do bloqueio, no mesmo notebook e sem reutilizar banco existente:

```powershell
$env:APP32_REFERENCE_REPAIR_NATIVE_TESTS='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
& .venv\Scripts\python.exe -B -m pytest -c pytest.ini -p no:cacheprovider app32\tests\test_financial_reconciliation_reference_repair_postgres.py -q -s
```

O bootstrap não aceita DSN externo; liga apenas em localhost, usa porta livre e
diretório novo, valida `SHOW data_directory`, endereço/porta e pidfile antes dos
fixtures. O cluster é parado e removido ao terminar. Os testes extraem colunas,
defaults e constraints reais por AST, removendo relações/FKs com o restante do
app para não carregar sua configuração. Portanto, mesmo quando passarem, não
substituirão um ensaio das FKs, triggers e schema completo do ambiente aprovado.

Casos preparados: persistência/idempotência/recuperação, erro de constraint com
rollback integral, snapshot obsoleto, escritor legado causando NOWAIT, impacto
em outro tenant e leituras concorrentes, nova dependência impedindo recovery.
Tempos e códigos PostgreSQL só serão afirmados depois de execução bem-sucedida.

### Revisão do escopo dos locks

É plausível reduzir os seis locks de tabela para locks nas tabelas de matches e
baixas, combinados com `SELECT FOR UPDATE NOWAIT` nos registros específicos de
conta, lote, linha e entrada. Locks apenas nas linhas atuais não protegem contra
inserção de novos vínculos; advisory locks também exigiriam cooperação de todos
os escritores legados. A alternativa de dois locks ainda bloqueia escrita nessas
duas tabelas para outros tenants e precisa provar ausência de deadlocks, proteção
contra inserções concorrentes e validação de deletes/cascades. Como o bootstrap
foi bloqueado, **nenhuma redução de locks foi implementada ou validada**.

## Reteste autorizado — 03/10/2026

### Execução e correções locais

O HEAD permaneceu `72adf7f3c399891f89f4677515831b9e1e8ce557`, na branch
`feat/agenda-unificada-google-calendar`. O staging estava vazio no início. Não
havia AGENTS.md na raiz, ancestrais nem diretórios aplicáveis destes arquivos;
foram lidos a skill canônica e os padrões de código, banco e ORM. Há 38 arquivos
rastreados modificados de outros trabalhos; seu conteúdo foi preservado.

O Docker continuou sem daemon no named pipe local. A consulta usou configuração
vazia temporária, sem ler credenciais, iniciar serviços ou baixar imagens.
Os binários existentes PostgreSQL 14.20 foram usados exclusivamente para criar
clusters novos, um por tentativa e nunca simultâneos. O serviço existente não
foi acessado, e o plano real permaneceu inerte.

| Rodada | Passaram | Falhas | Erros de setup | Pulados | Evidência |
|---|---:|---:|---:|---:|---|
| Sintética original | 37 | 0 | 0 | 0 | 0,97 s |
| Nativa habilitada no sandbox | 0 | 0 | 6 | 0 | token restrito 87/3; nenhum teste de banco executou |
| Nativa original via aprovação oficial | 0 | 0 | 6 | 0 | timeout de pg_ctl start; cluster próprio encerrado pelo fluxo oficial |
| Regressões sintéticas antes da correção | 0 | 14 | 0 | 0 | 37 outros casos deselected; vínculos string/malformed expuseram a falha |
| Suíte ampliada, primeira rodada | 53 | 0 | 21 | 0 | parâmetro service vazio inválido; cleanup confirmado |
| Suíte ampliada, segunda rodada | 53 | 0 | 21 | 0 | cast inet::text acrescentava /32; cleanup confirmado |
| **Suíte pertinente completa final** | **74** | **0** | **0** | **0** | **53 sintéticos + 21 PostgreSQL; 16,13 s** |

Cada execução fora do sandbox foi solicitada por `exec_command` com
`sandbox_permissions=require_escalated`, inclusive o encerramento do primeiro
cluster preso. Não houve alteração de ACL, privilégios/configurações de segurança
do sistema, instalação, contorno de token, conexão externa ou retry automático
do serviço de reparo.

Correções dentro do escopo:

- Os seis locks de tabela foram mantidos. `get` agora usa FOR UPDATE NOWAIT
  nas linhas alvo de transações de escrita; dry-run não adquire esses locks.
  ROW SHARE de um SELECT FOR UPDATE preexistente é compatível com SHARE ROW
  EXCLUSIVE, portanto o lock de tabela sozinho não tornava o flush NOWAIT.
  Referência: [locks PostgreSQL 14](https://www.postgresql.org/docs/14/explicit-locking.html).
- Dependências JSON em string numérica passam a ser detectadas; valores
  malformados abortam sem escrita. As referências dos próprios alvos continuam
  estritas, e nenhum campo financeiro entrou na lista de mutação.
- O harness redireciona stdout/stderr dos comandos para arquivos do próprio
  diretório temporário: PIPE herdado pelo postmaster mantinha o communicate
  preso no Windows. Cleanup não depende de startup ter retornado sucesso;
  verifica pidfile e status antes de parar/excluir somente o cluster criado.
- Libpq não herda PG*, usa senha exclusivamente sintética não vazia e passfile
  vazio próprio; não lê .env nem arquivos de conexão/credenciais existentes.
  O ambiente do processo pytest é restaurado no finally. Não é informado
  service: string vazia solicita um serviço inválido, em vez de desativá-lo.
- A identidade usa `host(inet_server_addr())`, mantendo a exigência de
  endereço exatamente 127.0.0.1, porta reservada e data_directory próprio.
  O cast inet::text inclui máscara, não um endereço distinto.
  Referência: [funções de rede PostgreSQL 14](https://www.postgresql.org/docs/14/functions-net.html).

### Isolamento e concorrência comprovados

Na execução final:

- `data_directory=C:\Users\mff20\AppData\Local\Temp\app32-reference-repair-pg-ldtqbig9\cluster`;
  `host=127.0.0.1`, porta **52081**, postmaster PID **19652**. SHOW data_directory,
  endereço/porta, versão e pidfile foram verificados, e o marcador
  `fresh-synthetic-only` foi criado antes do schema reduzido. Empresa 77, conta 20 e IDs
  sintéticos; outro tenant 88 somente para provar impacto dos locks.
- Aplicação dos três pares: **0,043323 s**. Erro real de constraint na baixa do
  terceiro par reverteu integralmente todos os registros/auditoria. Segunda
  aplicação não produziu mudanças; snapshot do recibo corresponde ao estado
  persistido. Metadados não envolvidos, valores, contas, datas e entradas foram
  preservados; recuperação respeitou absent/null e manteve auditoria.
- Escritor UPDATE preexistente em cada uma das seis tabelas rejeitou o reparo
  com **55P03**, entre **0,000657 e 0,032872 s**. Aquisição parcial malsucedida
  também liberou locks anteriores, comprovado por outra transação ainda com
  o escritor original aberto.
- SELECT FOR UPDATE e FOR KEY SHARE preexistentes em match/baixa rejeitaram
  com **55P03**, entre **0,004300 e 0,007545 s**, sem alteração e sem locks
  remanescentes do reparo. Outro reparo concorrente rejeitou em cerca de 1,1 ms.
- Um backend observador distinto confirmou exatamente os seis
  ShareRowExclusiveLocks em pg_locks. SELECT simples continuou permitido nas
  seis tabelas. Inserts de match/baixa do tenant 77 e lote do tenant 88 foram
  bloqueados até o lock_timeout de **150 ms do escritor de teste** (55P03);
  não houve redução de locks nem timeout usado para mascarar NOWAIT do reparo.
- Retenção observada nas transações propositalmente abertas para esses probes:
  **0,500646 s** até commit e **0,480481 s** até rollback. Após ambos, nenhum
  ShareRowExclusiveLock restou e outra transação adquiriu os seis modos de
  escrita NOWAIT. Esses tempos não estimam o custo com volume real.
- Shutdown confirmado em **0,509762 s**; pg_ctl status retornou **3** (parado),
  pidfile ausente e diretório temporário removido. Todos os clusters das
  tentativas anteriores também foram encerrados/removidos antes do seguinte.

### Comandos e qualidade

Na raiz `C:\GestaoVersus\app32`, comando final executado pelo fluxo oficial de
aprovação (sem cache, bytecode ou autoload de plugins):

```powershell
$env:APP32_REFERENCE_REPAIR_NATIVE_TESTS='1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
& .venv\Scripts\python.exe -B -m pytest -c pytest.ini -p no:cacheprovider app32\tests\test_financial_reconciliation_reference_repair.py app32\tests\test_financial_reconciliation_reference_repair_postgres.py -q -s --tb=short
```

Também executados: suíte sintética separada; suíte PostgreSQL original habilitada;
seleção das regressões com `-k 'legacy_string_dependency or malformed_existing_dependency'`;
collect-only das duas suítes (**74 coletados**); `compile()` em memória dos três
Python; `git status --short`, `git branch --show-current`, `git rev-parse HEAD`,
`git diff --stat`, `git diff --cached --stat`, e revisão dos arquivos novos com
`git diff --no-index --check -- NUL <arquivo>` (sem achados; código 1 significa
diferença NUL/arquivo novo, com aviso LF/CRLF).

Comandos de qualidade tentados nos três Python do reparo:

```powershell
& .venv\Scripts\python.exe -B -m black --check app32\services\financial_reconciliation_reference_repair_service.py app32\tests\test_financial_reconciliation_reference_repair.py app32\tests\test_financial_reconciliation_reference_repair_postgres.py
& .venv\Scripts\python.exe -B -m flake8 --config app32\.flake8 app32\services\financial_reconciliation_reference_repair_service.py app32\tests\test_financial_reconciliation_reference_repair.py app32\tests\test_financial_reconciliation_reference_repair_postgres.py
```

Ambos retornaram `No module named ...` (código 1); **Black e Flake8 não foram
executados nem aprovados**. Ruff, pycodestyle e mypy também estão ausentes na
.venv. Nada foi instalado. Compilação em memória não substitui lint/typecheck.

### Limites da aprovação local

Este aceite comprova os 74 casos pertinentes no PostgreSQL isolado, não a
segurança de executar o plano real. O schema AST preserva colunas/defaults/checks
mas omite FKs, relações e triggers externos. Não houve ensaio de schema completo,
volume/carga representativos, UI/rotas reais, stack Docker ou produção. Os locks
globais continuam atingindo outros tenants, e os novos locks de linha também
podem rejeitar leitores que travem os alvos. É necessária janela controlada e
validação posterior autorizada; sem retry automático ou mudança de permissões.

O candidato de revisão é restrito ao serviço, aos dois testes e a este runbook.
Não inclui segredos, recibos reais, valores financeiros reais, logs/cluster
temporários nem arquivos de outros trabalhos. As identidades do plano e das
sentinelas já documentadas são a configuração necessária e permanecem inertes.
Não se executa commit, push, merge, migração, deploy, aplicação/recovery real ou
publicação de rota/MCP nesta entrega.

### Índice preparado para revisão

Após os 74 testes aprovados, o fluxo oficial de aprovação selecionou somente
os quatro arquivos novos abaixo. `git diff --cached --check` retornou **0**;
`git diff --exit-code -- <quatro arquivos>` não apontou diferença entre arquivo
testado/revisado e índice. SHA-256 dos **38 arquivos rastreados modificados de
outros trabalhos** foi comparado ao baseline e permaneceu idêntico. Nenhum
arquivo desses trabalhos foi adicionado ao staging.

```powershell
git add -- app32/services/financial_reconciliation_reference_repair_service.py app32/tests/test_financial_reconciliation_reference_repair.py app32/tests/test_financial_reconciliation_reference_repair_postgres.py app32/docs/runbooks/runbook_reparo_referencias_conciliacao_inter_v1.md
git diff --cached --check
git diff --cached --name-status
git diff --cached --stat
```

O manifesto do índice contém exatamente quatro entradas `A`, todas do reparo.
Mensagem proposta: `fix(finance): reparar referências de conciliação com atomicidade e NOWAIT`.
**Commit não executado.** Black/Flake8 e ensaio de schema/volume completo continuam
pendentes; staging para revisão não é autorização de commit ou produção.

## Continuação controlada — 03/10/2026

O mesmo card `[Reparo pontual de referências Inter]` permanece aberto. Esta
solicitação autoriza preparação e validação locais, não commit, push, deploy,
aplicação ou recuperação em produção. Não criar outro card nem executar SSH.

- [x] Revalidar branch/HEAD, os quatro arquivos staged e baseline SHA-256 dos
  38 arquivos rastreados modificados de outras entregas.
- [x] Repetir a suíte sintética existente: 53 aprovados em 15,13 s.
- [x] Revisar o código final e acrescentar regressões necessárias.
- [x] Repetir testes pertinentes sobre o código final, incluindo PostgreSQL
  novo e isolado pelo fluxo de aprovação do sandbox.
- [x] Preparar escopo exato, snapshot, auditoria, janela e recuperação condicionada.
- [ ] Dry-run oficial atual e snapshots das sentinelas em produção.
- [ ] Obter aprovações específicas de commit/publicação e aplicação delimitada.
- [ ] Aplicar e verificar por leitura posterior autorizada antes de encerrar.

MCP First foi verificado nesta sessão: os servidores configurados `mcp-versus`
e `mcp-versus-diagnostico` estão habilitados, mas `resources/list` falhou no
startup com `OAuth authorization required` nos dois. Nenhuma leitura de dados
de produção ocorreu; não foram obtidas credenciais nem usado acesso alternativo.
O estado descrito anteriormente continua evidência histórica, não snapshot atual.

Após o operador informar que concluiu a autenticação, foi consultado novamente o
cliente oficial: `mcp-versus` retornou `timed out awaiting tools/list after 30s`;
`mcp-versus-diagnostico` ainda retornou `OAuth authorization required`. Não há
ferramentas desses servidores disponibilizadas ao agente. Reconectar/autenticar
pelo fluxo oficial é pré-requisito; nenhuma configuração, grant ou credencial
foi modificada para contornar o bloqueio.

### Revisão e evidência do candidato final

As regressões anteriores à correção reproduziram **8 falhas**, com 1 teste
aprovado e 53 deselected. Foram corrigidos exclusivamente dois guardrails:

1. Comparar o snapshot aprovado antes do retorno idempotente. Referências já
   completas não ocultam mudança de valor, data, metadados ou vínculos. Uma
   nova revisão do estado completo permite `changed=false` sem flush/auditoria.
2. Rejeitar `external_reference` da baixa com prefixo `reconciliation-match:`
   que não corresponda exatamente ao match alvo. Referência válida e demais
   referências externas são preservadas; o campo não entrou na lista de escrita.

| Validação nesta continuação | Resultado real |
|---|---|
| Suíte sintética original | 53 passed in 15.13s |
| Regressões antes da correção | 8 failed, 1 passed, 53 deselected in 1.06s |
| Suíte sintética final | 62 passed in 15.22s |
| Suíte final completa | **87 passed in 13.87s: 62 sintéticos + 25 PostgreSQL** |
| Compilação em memória dos três Python | aprovada, sem import da aplicação/bytecode |
| Whitespace do delta local e do índice anterior | sem erros, exit code 0 |
| Black, Flake8, Ruff, pycodestyle e mypy | ausentes; não executados/instalados |
| SHA-256 dos 38 arquivos rastreados modificados alheios | idênticos ao baseline |

O teste PostgreSQL executou pelo fluxo `exec_command(require_escalated)` aprovado,
usando exclusivamente cluster novo `app32-reference-repair-pg-gvtspjop`, em
127.0.0.1:64393, PostgreSQL 14, postmaster PID 40676. Identidade de diretório,
host, porta e pidfile conferida. Encerramento confirmado com status 3, sem
pidfile; diretório temporário removido. Nenhum banco existente foi acessado.

Resultados observados: aplicação sintética 0,023729 s; escritores preexistentes
nas seis tabelas rejeitados com 55P03 em 0,000812–0,001133 s; locks de linha
UPDATE/KEY SHARE em match/baixa rejeitados em 0,004215–0,007356 s. Leitores SELECT
simples continuaram permitidos; inserts de outro tenant também foram bloqueados.
Os probes com transação propositalmente aberta retiveram os seis locks por
0,479622 s (commit) e 0,508498 s (rollback), sem locks remanescentes. Esses tempos
não estimam volume/carga reais. O novo teste nativo confirmou REPEATABLE READ,
READ ONLY (UPDATE rejeitado com 25006), snapshot estável e escritor paralelo
permitido durante dry-run. Constraint no terceiro par reverte todo o plano.

O schema isolado continua sem FKs/relações/triggers externos: ensaio de schema
completo e volume representativo, CI, lint/typecheck e UI de produção pendentes.
Não reduzir locks nem adicionar retries para suprir essas evidências.
NOWAIT protege a aquisição dos locks explicitados, não garante duração máxima
da transação nem ausência de espera em triggers/FKs/recursos externos. Não foi
simulada toda combinação de deadlock do schema completo. A mitigação preparada
é janela controlada, revisão de triggers/FKs e rollback integral, não supor
segurança a partir dos milissegundos sintéticos.

SHA-256 dos arquivos Python efetivamente testados:

| Arquivo (relativo à pasta app32 interna) | SHA-256 |
|---|---|
| services/financial_reconciliation_reference_repair_service.py | `8CB8965FCE4F68C9DDAFA56C85C18168E82D8C4EE0CC30467F0DACBFB534A47D` |
| tests/test_financial_reconciliation_reference_repair.py | `EEF0C40A09A1954B4B7EF1B212231C7E9DA87FEB38DEC2A193BA1ED6D7B3D236` |
| tests/test_financial_reconciliation_reference_repair_postgres.py | `501C85748931D9151A905AD8F8CB84E496E5B3DE8BCEC8CADC228603C83B3382` |

Os quatro arquivos do índice anterior não foram re-staged nesta continuação:
o working tree final contém delta local adicional nos mesmos quatro arquivos.
**Não commitar o índice antigo como se fosse o candidato final testado.**

### Plano delimitado de aplicação — preparado, ainda não autorizado

Empresa 9, conta 1, lote 84 e código exato `REC-20260918-INTER-CSV-V2`.
Após dry-run atual, alterar somente as seguintes referências, mantendo as
demais chaves dos metadados:

| Match | metadata_json.financial_settlement_id | Baixa | metadata_json.import_batch_id | metadata_json.import_row_id | metadata_json.reconciliation_match_id |
|---|---:|---|---:|---:|---:|
| 538 | 2752 | 2752 | 84 | 9577 | 538 |
| 539 | 2684 | 2684 | 84 | 9581 | 539 |
| 540 | 2687 | 2687 | 84 | 9584 | 540 |

Nas três baixas: `reconciliation_status=reconciled`. Nos três matches: acrescentar
somente `metadata_json.reconciliation_reference_repair_audit`, preservando eventos
existentes. Evento inclui `operation_id`, ação, ator autenticado, instante UTC,
par exato e presença/valor anteriores das chaves permitidas e status anterior.
`updated_at` segue o ORM. Não escrever na coluna `FinancialSettlement.import_batch_id`,
nem em external_reference, linhas, lançamentos, valores, contas, datas, componentes,
grupos, status financeiro ou registros de outros casos.

**Pré-condições e snapshot anterior (pendentes de acesso oficial):**

1. Validar principal OAuth, surface/RBAC, empresa 9 e ambiente/versão por fonte
   confiável. Leituras analytics não concedem financial.edit. Confirmar a
   disponibilidade real das tools de diagnóstico antes de chamá-las; a SPEC
   local dessas leituras não comprova que estejam publicadas.
2. Reler lote 84 com filtro `[9577,9581,9584]`, matches persistidos e baixas
   `[2752,2684,2687]`, sem inferir pares por valor ou data. Comparar com as
   identidades/estados históricos: confirmed, posted/pending, sem vínculo à
   baixa no match e sem referências inversas nas baixas. Qualquer divergência
   interrompe e é apresentada, inclusive reparo parcial ou já completo.
3. Coletar os valores/datas atuais exatos, versões, status e referências, hashes
   dos campos e das chaves alheias, componentes e grupos. O prompt/runbook
   histórico não informa os valores/datas reais: não é possível afirmar ausência
   de mudança histórica nesses campos sem snapshot anterior autorizado. Exigir
   essa evidência ou revisão humana explícita da baseline atual; nunca inventar.
4. Identificar por evidência oficial os cinco casos Casa/prestação/cartão de
   agosto e Casa/prestação de setembro; registrar IDs e snapshots como sentinelas.
   Somar CEF entrada/baixa 2674/2753, EFI 2619/2688 e grupos já indicados. Não
   descobrir identidade por aproximação de texto/valor. Brasnorte fica excluída.
5. Ensaiar schema completo e volume representativo em clone isolado autorizado.
   Planejar janela curta para os seis SHARE ROW EXCLUSIVE globais. Não bloquear
   ou ampliar grants de produção como parte desta preparação.
6. Obter `dry_run` do serviço por integração oficial que forneça engine já
   autorizado e contexto autenticado/RBAC. Snapshot transacional READ ONLY dos
   14 registros (conta, lote e quatro por par), fingerprint do plano e proposta
   ficam em trilha restrita aprovada, não em Git. Chamadas GET/MCP separadas
   ajudam o diagnóstico, mas não substituem esse snapshot transacional.

**Aplicação após aprovação específica:** uma única chamada `apply`, em sessão
dedicada, com ator/scope/RBAC confiáveis e snapshot aprovado. Locks NOWAIT nas
seis tabelas e nos 14 alvos; revalidar todos os pares/conflitos antes de mutar.
Um único commit dos três pares e auditoria. Qualquer conflito, drift, erro de
constraint ou 55P03 faz rollback integral; sem retry automático. Guardar recibo
com before/after/operation_id em trilha restrita correlacionada à autorização.

**Leitura posterior independente:** conferir os três pares exatos nos dois
sentidos, um match confirmed por linha e uma linha vinculada por baixa,
`is_reconciled=true`, `reconciliation_status=reconciled` e diferença monetária
Decimal zero por par. Comparar todos os campos financeiros/contas/datas e
metadados alheios ao before; coluna import_batch_id intacta. Validar componentes,
grupos e todas as sentinelas. Matches confirmados continuam três; não esperar
aumento do contador. A evidência sintética do serializador é (3,0,0) → (3,3,3)
para matches/vínculos/baixas conciliadas, não evidência da tela de produção.
Se houver efeitos inesperados, interromper e não declarar produção corrigida.

**Recuperação condicionada:** antes do commit, rollback integral. Depois,
`recover` apenas com nova autorização específica, recibo íntegro e snapshot atual
igual ao after; revalidar dependências e auditoria persistida. Restaurar somente
chaves/status alterados, distinguindo ausência de null, preservar auditoria e
acrescentar recover. Não restaurar timestamps históricos. Drift ou dependência
nova impede recuperação automática e exige investigação, sem sobrescrita.

### Aprovações e publicação — não executadas

Plano proposto para aprovação **somente de commit local**: criar branch
`codex/reparo-referencias-conciliacao-inter` a partir de
`72adf7f3c399891f89f4677515831b9e1e8ce557`; preservar o working tree alheio,
sincronizar staging exclusivamente dos quatro arquivos deste runbook e criar
commit `fix(finance): reparar referências de conciliação com atomicidade e NOWAIT`.
Aceite: manifesto final conferido, 87 testes, compilação/whitespace e limites de
qualidade informados. Não inclui push, merge, publicação ou escrita financeira.

Publicação futura exige outra aprovação delimitada de SHA/branch/destino,
preflight de drift, modo `quick` (sem dependência/schema), migrations `nenhuma`,
`restart_mcp=false` para este serviço interno, company_id/RBAC/ledger e
deployment_id pelo MCP de Deploy, executor GitHub Actions. Esses parâmetros são
proposta, não dispatch autorizado; restart web normal pode ocorrer. Integração
oficial para executar o serviço não existe nestes quatro arquivos e deve ser
definida/aprovada sem publicar mutação em analytics/user. Não adicionar CLI,
engine padrão, credenciais, SQL livre ou rota de execução como atalho.

Aplicação em produção exige terceira autorização, vinculada ao snapshot atual,
campos exatos acima, janela e mecanismo oficial de execução/auditoria. Sem esses
pré-requisitos, preparar não equivale a publicar ou aplicar.

### Prevenção separada — proposta, sem alteração de código

A leitura do código atual de `FinancialReconciliationService.review_match`
mostra um risco verificável: ele marca o match e chama a baixa automática, mas
faz commit e devolve `auto_settlement_error` mesmo quando essa chamada retorna
erro. O caminho existente que reutiliza uma baixa por external_reference retorna
a baixa sem completar, ali, a referência do match. Isso evidencia fragilidade
atual; **não prova a causa histórica destes três registros** nem qual caminho
foi executado. Obter auditoria/logs/versionamento para estabelecer a origem.

Entrega futura separada: falhar sem commit se associação/baixa não for válida;
confirmar match, baixa e referências bidirecionais na mesma unidade transacional;
selecionar baixa existente explicitamente (sem criar pagamento/transferência
duplicados), garantir idempotência e conflitos em todos os caminhos, tenancy/RBAC
e testes de erro/concorrência/contadores. Não foi modificada review_match, UI,
contrato público, criação de pagamentos ou lógica de datas nesta entrega.
