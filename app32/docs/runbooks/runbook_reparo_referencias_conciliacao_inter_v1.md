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
novo evento de auditoria; referências parciais compatíveis podem ser completadas.

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


## Continuação aprovada — PR isolado para main

Em 03/10/2026 o usuário aprovou branch isolada, commit dos quatro arquivos,
push, PR e merge condicionado às validações, sem deploy. Também autorizou
Black/Flake8 em venv temporária exclusiva de qualidade, sem alterar a .venv
do projeto. O card local da mesma entrega prossegue aqui, sem SSH/produção.

- [x] Atualizar main e criar checkout independente sem tocar no staging original.
- [x] Formatar/revisar os três Python e executar Black/Flake8.
- [x] Reexecutar os 74 testes sobre a main e PostgreSQL temporário isolado.
- [ ] Revisar quatro arquivos, executar commit isolado e publicar PR.
- [ ] Verificar gates e mergear somente este PR para main, sem deploy.

Base: `652da9e00cfeec5cb7a80f24bedf1865f8244c7f`;
branch: `codex/reparo-referencias-conciliacao`.
As evidências anteriores descrevem o staging original; esta continuação tem
checkout/índice próprios e não substitui as mudanças preexistentes.

### Evidências da main antes do commit

Black **26.5.1** e Flake8 **7.4.1** foram instalados do PyPI oficial somente em
`TEMP/app32-repair-quality-vxca05xt/venv`, mediante autorização explícita.
A .venv do projeto não foi alterada. Black inicialmente indicou formatação nos
três Python; Flake8 indicou E128 em indentação de continuação nos testes.
Black foi aplicado somente nesses arquivos e a AST dos três foi comparada
antes/depois: **idêntica**, sem relaxamento de validações ou redução de locks.

- `black --check <três Python>`: **0**, três arquivos sem mudanças necessárias.
- `flake8 --config app32/.flake8 <três Python>`: **0**, sem achados.
- Reteste completo na main: **74 passaram em 13,54 s** (53 sintéticos + 21
  PostgreSQL; zero falhas, erros ou pulados), com o Python da .venv original,
  `-B`, autoload de plugins desabilitado e sem cache, conforme comando anterior
  usando caminhos absolutos deste checkout independente.
- Cluster novo: `TEMP/app32-reference-repair-pg-o6v5f3dn/cluster`, localhost
  **59551**, postmaster PID **22720**; data_directory/host/porta/pidfile
  verificados. Shutdown confirmado, status 3 e diretório removido.
- Apply dos três pares **0,025039 s**; NOWAIT nas seis tabelas **55P03**,
  0,000644–0,031317 s. Locks de linha UPDATE/KEY SHARE em match e baixa: 55P03,
  0,005314–0,009057 s. Retenção nos probes de commit/rollback: **0,494442 s** /
  **0,500582 s**; locks liberados. Inserts concorrentes dos tenants 77/88
  bloqueados, leituras simples permitidas e outro reparo rejeitado.

Os workflows da main foram inspecionados sem executar produção: deploy apenas
`workflow_dispatch`; QA E2E por PR somente em paths que não incluem os quatro
arquivos deste reparo; backup tem schedule/dispatch. Portanto não se espera
check automático pertinente neste PR por esses workflows. Os gates reais do
GitHub devem ser inspecionados e eventuais ausências de checks/reviews devem
ser informadas antes do merge; não se publica CI adicional nem se faz bypass.
Os limites de schema AST/volume real continuam válidos. Não há deploy,
migração, restart_mcp ou plano real nessa aprovação.
