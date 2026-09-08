# Triagem local SE-COORD v1

Classe: **Runbook**. Escopo: execução local sem DB/LLM; não implanta runtime remoto.

## Exemplo PowerShell

```powershell
'{"task_id":"exemplo-1","objective":"Corrigir calculo acumulado","files":["services/indicator_service.py"]}' | python C:\GestaoVersus\app32\app32\scripts\assess_engineering_task.py
```

Esperado: `success=true`, `entry_agent=SE-COORD`, domínio `backend_service`, tipo `maintenance`, recomendação Backend Service + QA, `advisory_only=true`. O arquivo indicado é referência ilustrativa, não é aberto pelo classificador.

Para contexto empresarial, informar `context_scope=company` e `company_id` inteiro positivo. Isso apenas valida formato e separação de escopo; autenticação/RBAC continuam obrigatórios fora da triagem. Não incluir credenciais no objetivo, pois o assessment devolve o objetivo informado.

## Validação e erros

```powershell
python C:\GestaoVersus\app32\app32\scripts\run_engineering_baseline.py
```

- Exit 0 do classificador: assessment emitido, não tarefa executada. Conferir `requires_clarification` mesmo com sucesso.
- Exit 2: JSON/schema inválido ou entrada excede 65536 caracteres; corrigir sem ampliar campos de autoridade.
- Baseline com operação externa bloqueada: falha mesmo com testes verdes; investigar a dependência, não remover os bloqueios.
- Output de telemetria contém métricas mínimas e valores desconhecidos como null; não é uso real do provedor e não é persistido automaticamente.

## Limites e reversibilidade

Para não usar triagem, continuar o processo manual existente; nenhuma flag ou serviço foi ativado. Não selecionar um harness incompatível para contornar a validação do registry. Atualizar/sanitizar o clone e validar MCP real antes da integração operacional. Sem comandos de deploy, alteração de banco, execução de RAG ou inicialização Flask neste runbook.

## Composição de contexto — Fase 2

```powershell
$identity = @{ repository_id = 'app32' }
$request = @{
    task = @{ task_id = 'contexto-1'; objective = 'Corrigir calculo acumulado' }
    identity = $identity
    budget_tokens = 16000
    items = @(@{
        item_id = 'regra1'; identity = $identity; kind = 'decision'
        source = 'decisao:regra1'; version = 'v1'; state = 'ACTIVE'
        content = 'Preservar a regra de arredondamento existente.'
        reason = 'Restricao confirmada da tarefa'
    })
}
$request | ConvertTo-Json -Depth 10 | python C:\GestaoVersus\app32\app32\scripts\compose_engineering_context.py
```

Resultado esperado: pacote pronto com `regra1` e governança integral; nenhuma leitura de arquivo ou banco. O exemplo usa uma decisão ilustrativa: substituir somente por uma decisão realmente confirmada. Não incluir segredos nos snapshots; o conteúdo ACTIVE aparece no payload de saída.

Dependências devem ser enviadas antes dos dependentes. Na CLI, a identidade é de repositório; escopo empresarial é rejeitado porque não há adapter autenticado. `freshness_mode` explicita que snapshots recebidos não foram comparados com disco.

- Exit 0: pacote disponível para revisão; conferir itens adiados/obsoletos antes de usar.
- Exit 2: schema/escopo inválido, dependência ausente/cíclica, bundle incompatível ou entrada acima de 1048576 caracteres; sem eco do payload no erro.
- Exit 3: governança+objetivo não cabem no orçamento estimado; aumentar orçamento ou reduzir objetivo, nunca remover guardrails.
- Fases 1–2 são verificadas pelo mesmo `run_engineering_baseline.py`; não executar testes de integração contra o clone antigo.

Uso programático: `EngineeringContextGovernorService.create/upsert/transition/refresh_registry/compose/delta`. Working Sets não são persistidos nem autenticados por esses métodos. Deltas precisam do pacote anterior exato e não são compactação nativa. Não há comandos `squad context` instalados por esta entrega.

## Sapiens Engenharia — retorno de complexidade e economia

Enviar ao entrypoint local `scripts/assess_engineering_task.py` um JSON com `task_id`, `objective` e, quando conhecido, `task_intent`: `execution`, `correction` ou `planning`. A saída contém `assessment.complexity` e `token_economy`:

- `minimal_active`: usar objetivo, fonte/função afetada e teste/evidência direta.
- `symbol_and_delta`: incluir contrato, dependências diretas e regressão; continuar somente com delta.
- `architecture_then_expand`: começar por resumo arquitetural versionado, decisões e invariantes.
- `clarify_before_expand`: não carregar novos módulos antes de esclarecer domínio ou arquivo.

`token_economy` não recomenda modelo, provider, esforço, preço ou percentual de economia. Escolha manual de modelo fica fora deste contrato. `estimated_token_savings: null` não é falha: evita converter hipótese em métrica. Em escopo empresarial, o retorno pode exigir MCP autenticado, mas não faz a leitura nem autoriza acesso.

Na ativação canônica, `SapiensActivationService.resolve_activation(role='admin', squad='engineering')` expõe `engineering_guidance`; o bootstrap MCP `describe_app32_squad_runtime_tool` expõe o mesmo contrato em `task_assessment`. Ambos são somente orientação e não substituem a execução local do entrypoint. Não interpretar a presença do manifesto como publicação remota, permissão, execução de harness ou acesso aos dados empresariais.

Para a interação guiada, chamar o tool canônico de ativação com `squad='engineering'` e `engineering_task={task_id, objective, task_intent?, files?, domain_hints?}`. O retorno é `guided_triage`; sucesso significa apenas classificação local. O tool rejeita `company_id`, `context_scope`, `surface`, `user_id`, `role` e qualquer squad diferente de Engenharia. Não usar esse caminho para evidência empresarial ou execução.

## Fase 3 — consultas e handoffs locais

Complemento Fase 4: o service `EngineeringQualityGateService.evaluate(state, packet, evidence, target='local', policy=QualityPolicy())` avalia `QualityEvidence` com IDs/fingerprints do estado e pacote atuais. Informar resultados pass/fail/unknown e referências revisadas. Não executa testes nem verifica o conteúdo dessas referências. Executar o baseline protegido para validar o código do gate. Alvo `operational` nunca conclui apenas com declarações do chamador; requer futuro adapter autenticado. Contadores de retries/escalonamentos devem vir de histórico confiável.

### Model Broker local — primeiro recorte da Fase 5

### Comparação local — primeiro recorte da Fase 6

CLI disponível: `python C:\GestaoVersus\app32\app32\scripts\compare_engineering_measurements.py`. Recebe JSON em stdin com chaves `baseline` e `candidate`, cada uma no contrato EngineeringMeasurement. Em PowerShell, enviar um arquivo previamente revisado com `Get-Content -Raw -LiteralPath 'C:\caminho\medicoes.json' | python C:\GestaoVersus\app32\app32\scripts\compare_engineering_measurements.py`; substituir o caminho ilustrativo pelo arquivo real. Não enviar prompts, credenciais ou conteúdo empresarial. Entrada máxima 64 Ki caracteres; contagens inteiras de 0 até 10^15.

Exit 0: comparação declarada calculável; 2: inválida/incomparável; 3: qualidade não estabelecida; 4: percentual de tokens reportados indisponível. `success: true` significa relatório calculado, não aprovação de qualidade ou economia demonstrada. Economia de custo permanece null. A CLI não coleta, grava ou autentica medições.

Uso programático: `EngineeringMeasurementService.compare(baseline, candidate)` com dois contratos `EngineeringMeasurement`. Informar fingerprints equivalentes de carga, identidade, avaliação e runtime; variantes baseline/candidate; qualidade pass/fail/unknown; estimativa de contexto e, separadamente, input_tokens/output_tokens reportados. Não inventar números para preencher ausências. `usage_source='provider_reported'` é declaração, não verificação automática. Resultado suprime percentuais se a qualidade não passar nos dois lados e não calcula economia de custo. Não existe coleta ou comando de medição real instalado; dados de teste são sintéticos. Manter pendentes o experimento real e a integração com runtime.

### Operação do Broker

Integração programática adicional: `EngineeringModelBrokerService.resolve_selection(state, packet, RuntimeSelection(requested_model='modelo-escolhido', requested_effort='esforco-escolhido'), rpc=conexao_confiavel_nova)`. Os nomes do exemplo são placeholders, não modelos/esforços disponíveis. Exige nova conexão inicializável por consulta; não passar conexão já inicializada. `listed_for_manual_selection` confirma apenas combinação listada; `manual_fallback` não substitui a escolha; `blocked` exige revisão antes da consulta. Não há cache ou importação de catálogo JSON. A CLI `model` segue offline e este método ainda não foi validado contra conexão viva. Não contorna QA nem autoriza geração.

Tratamento de falhas do transporte: `runtime_catalog_cleanup_failed` indica que não foi possível confirmar encerramento normal do proxy/leitor; não interpretar como catálogo disponível. A rotina tenta terminate e, após timeout, kill apenas no subprocesso que criou. Não repetir automaticamente. O baseline usa processos simulados, não valida IPC real ou concorrência Windows. O timeout de respostas não constitui deadline absoluto para todas as chamadas de sistema.

Consulta explícita de catálogo: `python C:\GestaoVersus\app32\app32\scripts\read_engineering_runtime_catalog.py`. Conecta ao daemon Codex já existente via proxy; nunca inicia daemon ou turno. Não incluir no baseline protegido: é um smoke separado com subprocesso real. Sem acesso retorna `runtime_catalog_unavailable` e fallback manual. Sucesso lista nomes/esforços observados, não autentica execução futura e não altera a sessão. Não copiar esse catálogo para handoffs nem tratá-lo como configuração persistente. Nesta sessão o smoke não obteve catálogo; não contornar bloqueios de acesso.

Executar `python C:\GestaoVersus\app32\app32\scripts\squad_engineering.py model` com o JSON habitual. Opcional: `broker_preference: {"profile":"DEEP","failure":"none","retries_used":0}`. Perfis aceitos: ECONOMY/STANDARD/DEEP. Resultado separa preferência escolhida de sugestão técnica e avisa quando a preferência é inferior ao perfil sugerido; não muda configuração alguma.

Provider, modelo comercial e esforço permanecem null. Não há catálogo verificado, descoberta remota ou equivalência garantida entre providers. Risco/complexidade altos e revisão de arquitetura/DBA sugerem DEEP; documentação simples de baixo risco pode sugerir ECONOMY; demais tarefas STANDARD. Após duas falhas declaradas de implementação sugere revisão DEEP, mas isso não autoriza nova tentativa nem supera limites do Quality Gate. Falhas de ambiente/requisito/teste/segurança, ambiguidade ou contexto incompleto suspendem sugestão. O contador é declarado e deve vir de histórico confiável. Este adapter manual não conclui a integração com runtime da Fase 5.

### Quality Gate pela CLI

1. Executar `python C:\GestaoVersus\app32\app32\scripts\squad_engineering.py context` com JSON de tarefa, identidade, itens e orçamento em stdin. Copiar `data.evidence_binding` para `quality_evidence`; preservar exatamente a entrada original. Mudança de pacote exige nova revisão, não copiar fingerprints novos para evidências antigas.
2. Acrescentar a `quality_evidence` checks `requirements`, `limited_diff`, `tests`, `regression`, `documentation` e revisões aplicáveis, usando `pass`, `fail` ou `unknown`; informar `evidence_refs` com referências reais revisadas. Nenhuma referência é aberta ou autenticada pela CLI.
3. Enviar o JSON ampliado ao mesmo script com comando `qa`. Sem evidência, os checks ficam desconhecidos e o gate bloqueia. `quality_target` aceita `local` (padrão) ou `operational`; `quality_policy` permite limites explícitos.

Exit QA: **0** local_validated; **2** entrada inválida; **3** blocked; **4** remote_validation_pending. `success: true` significa que a avaliação executou, não que QA aprovou. Conferir `data.quality_gate.status`. `status` e `why` aceitam a mesma evidência e incluem o gate, mas mantêm exit 0 para consulta válida; sem evidência, `quality_gate` é null. Evidência QA em comandos de handoff/resume é rejeitada, impedindo impressão de aprovação ou persistência implícita. Checkpoints existentes não carregam aprovação de QA.

Enviar JSON de tarefa/identidade/itens via stdin para `python C:\GestaoVersus\app32\app32\scripts\squad_engineering.py status`. Alternativas: `context`, `why`, `model`. Nenhuma executa a tarefa.

- `decide`: acrescentar `next_task` (schema de `task`) e `depends_on` com o ID anterior se houver dependência explícita. Retorna recomendação SAME/EXTEND/ROTATE.
- `handoff`: acrescentar `name` (exemplo `revisao-01.json`), `summary` e `reviewed_for_export: true` somente após revisão humana. Opcionais: listas `decisions`, `test_evidence`, `pending`. Salva em `C:\GestaoVersus\app32\app32\.ai\handoffs`, sem sobrescrever.
- `resume`: informar `name`, mesma tarefa/identidade e snapshots revalidados. Resultado: `validated_for_human_review_not_executed`; não lê fontes no disco nem executa pendências.
- Exit 0 indica sucesso do comando, não aprovação de QA; exit 2 indica entrada/escopo/arquivo inválido.

Não salvar segredos ou dados empresariais. Filtro de segredos parcial; checksum não é assinatura. Revisar objetivo, origens e notas; manter checkpoints fora do Git e remover manualmente após consumo. Não há expiração automática. Mudança de registry/identidade ou fonte impede reuso. Baseline protegido cobre fases 1–3, sem integração no clone antigo.
