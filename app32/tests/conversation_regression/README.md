# Suíte de Regressão Conversacional do Sapiens / WhatsApp

## V2
Esta versão troca casos hardcoded por um **catálogo externo declarativo**:

- `fixtures/cases.json` — catálogo único dos casos reais
- `runner.py` — executor declarativo por tipo de caso
- `reporting.py` — relatório consolidado por capítulo

## V3
Esta evolução adiciona:
- `taxonomy.py` — taxonomia de falhas (`parsing`, `routing`, `multi_turn`, `execution`)
- `real_case_catalog.py` — exportação de casos reais vindos de Flow Gap/backlog
- `smoke_assisted.py` — plano assistido de smoke para produção

## V4
Esta evolução adiciona:
- `operational_report.py` — relatório operacional serializável em JSON/HTML
- inferência automática de capítulo/tipo/classe a partir de `WorkflowGapCandidate`
- payload de sincronização para backlog `AA.J.31`

## V5
Esta evolução adiciona:
- `C:\GestaoVersus\app32\services\conversation_regression_service.py`
- `C:\GestaoVersus\app32\scripts\generate_conversation_regression_snapshot.py`
- coleta real de `WorkflowGapCandidate` via banco
- geração persistível de artefatos operacionais

## V6
Esta evolução adiciona:
- `C:\GestaoVersus\app32\services\conversation_regression_backlog_service.py`
- `C:\GestaoVersus\app32\scripts\sync_conversation_regression_backlog.py`
- sincronização real com o backlog `AA.J.31`
- estratégia de upsert para cards de regressão

## V7
Esta evolução adiciona:
- endpoint API para disparar a pipeline operacional
- fechamento automático de cards quando o caso real já está coberto no catálogo base
- suporte a dry-run na sincronização operacional

## Capítulos
- `a_consultar`
- `b_cadastrar_iniciar`
- `c_encerrar`
- `d_analisar`

## Tipos de caso suportados
- `parsing`
- `routing`
- `multiturn`

## Objetivo
Transformar casos reais do Sapiens em regressão permanente para detectar:
- falhas de parsing
- falhas de roteamento
- falhas de multi-turn
- regressões semânticas entre intenção e execução

## Fluxo de manutenção
1. capturar o caso real do WhatsApp/Sapiens
2. adicionar um item novo em `fixtures/cases.json`
3. classificar no capítulo correto
4. registrar o comportamento esperado
5. corrigir o código até a regressão passar
6. se o caso nasceu em produção, gerar stub via `real_case_catalog.py`
7. incluir o caso priorizado no smoke assistido
8. gerar payload de sync do backlog para acompanhamento operacional

## Execução
```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'; pytest -q C:\GestaoVersus\app32\tests\conversation_regression
```

## Relatório consolidado
O relatório por capítulo é gerado por:
- `test_catalog_v2.py`

Ele valida:
- quantidade de capítulos
- total de casos
- distribuição por tipo
- distribuição por classe de falha

## Smoke assistido
A V3 passa a gerar um plano de smoke priorizando:
- casos reais de WhatsApp
- cenários multi-turn
- cenários mais sensíveis a execução

## Relatório operacional
A V4 permite gerar:
- sumário consolidado por capítulo
- plano de smoke assistido
- renderização em JSON
- renderização em HTML

## Integração com backlog
A V4 também gera payload canônico para sincronização com:
- `AA.J.31`

## Operação V5
Fluxo operacional:
1. ler gaps abertos do banco
2. converter em catálogo regressivo
3. mesclar com o catálogo base
4. gerar relatório operacional
5. persistir artefatos JSON/HTML
6. produzir payload de sync para o `AA.J.31`

Comando:
```powershell
python C:\GestaoVersus\app32\scripts\generate_conversation_regression_snapshot.py --output-dir C:\GestaoVersus\app32\artifacts\conversation_regression
```

## Operação V6
Sincronização operacional com backlog:
```powershell
python C:\GestaoVersus\app32\scripts\sync_conversation_regression_backlog.py --snapshot-dir C:\GestaoVersus\app32\artifacts\conversation_regression
```

Fluxo:
1. coleta gaps do banco
2. gera snapshot operacional
3. monta payload de sync
4. atualiza cards existentes
5. cria cards faltantes no `AA.J.31`

## API operacional V7
Endpoint:
- `POST /api/agents/conversation-regression/run`

Capacidades:
- executar pipeline sob demanda
- persistir snapshot
- sincronizar backlog
- operar em `dry-run`/sem persistência do backlog
- devolver relatório e resultado do sync
