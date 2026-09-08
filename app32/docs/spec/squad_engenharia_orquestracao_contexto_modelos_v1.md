# Squad Engenharia — Orquestração, contexto e modelos v1

Classe: **SPEC**  
Data: 2026-09-07  
Status: Fases 1–3 e núcleo local da Fase 4 implementados; rollout operacional e fases 5–6 pendentes.  
Responsável técnico: SE-COORD / @ARQUITETO.  
Escopo inicial: diagnóstico e especificação. Continuidade: Fases 1–3 locais (seções 16–18), sem deploy ou Model Broker.

## 1. Objetivo e princípios

Evoluir o Squad Engenharia existente para selecionar o menor contexto suficiente e a menor intervenção segura, preservando qualidade, rastreabilidade e isolamento. Esta SPEC é a referência de continuidade da conversa “Otimizar tokens com Skills”; não exige transportar o histórico do chat.

- O Squad deve ser complexo na decisão e simples na estrutura.
- O modelo é consequência da tarefa; a tarefa não é consequência do modelo.
- Contexto deve ser carregado por necessidade, não por disponibilidade.
- Preservar `engineering`, `SE-COORD`, os oito harnesses registrados, Runtime Profiles, Instruction Registry, contratos MCP e Permission Matrix.
- Manter **code-first + mcp-validated**: código para evolução técnica; MCP para discovery e comprovação operacional. Nenhum deploy é implicitamente autorizado por esta SPEC.
- Python/Flask/PostgreSQL; regra de negócio em service, nunca em rota; sem SQLite, catálogo MCP paralelo ou ampliação implícita de acesso.
- Um especialista líder por padrão; colaboração adicional apenas quando necessária e permitida pelo runtime e pela autorização vigente. Não iniciar agentes apenas para cumprir uma lista de personas.

## 2. Diagnóstico e fontes canônicas

Raiz dos caminhos desta seção: `C:\GestaoVersus\app32\app32`. Inspeção realizada sobre HEAD `e3acd8d64`, com alterações locais preexistentes; não representa auditoria da produção.

| Fonte inspecionada | Evidência / responsabilidade preservada |
|---|---|
| `src/intelligence/security/runtime_profiles.py` | `engineering` tem entrada `harness_coordenador_engenharia_v1`, surface padrão `ops`, permite `ops/admin/analytics`; oito harnesses incluindo coordenador. |
| `src/intelligence/mcp_contracts/instruction_registry.py` | Contratos estritos, quatro layers `global/runtime/agent/tenant_override`, versões, checksum, cache, referências e guia de `SE-COORD`. |
| `services/instruction_registry_service.py` | Serviço de bundles e rollout para três runtimes; versão observada `2026-09-03.1`; resolução local sem DB disponível. |
| `src/core/mcp_squad_runtime_tools.py` | Bootstrap específico para Cliente; Engenharia utiliza descrição genérica derivada do Runtime Profile. Registro de harnesses não equivale a um orquestrador adaptativo implementado. |
| `src/intelligence/mcp_contracts/permission_matrix.py` | Overlays para os oito harnesses de Engenharia, escopo e gates por ação. Roteamento não concede permissões. |
| `src/core/mcp_session_harness_tools.py` | Seleção de harness ligada à identidade/token e descrita para o mesmo Squad Cliente; não presumir suporte equivalente para Engenharia. |
| `docs/specifications/implantacao_cli_harness_squads_v1.md` | Separação papel/harness/snippet/playbook/smoke; harness thin e proteção da metodologia. |
| `docs/specifications/mcp_perfis_tools_liberacoes_por_squad_v1.md` | Um MCP canônico e separação por runtime, identidade, surface e tenant; contém inventário histórico. |
| `docs/architecture/CONVERGENCIA_SAPIENS_SQUAD_MCP_TOOL_FIRST.md` | Reuso de services/REST/MCP; filtros de superfície de UI não são nomes das surfaces MCP. |
| `.ai/codex-squad-engenharia-laboratorio.md` | Code-first + mcp-validated, startup ops, proibição de assumir operação de negócio; contexto específico do laboratório. |
| `docs/spec/plano_correcao_arquitetural_dos_squads_v1.md` | Plano transversal existente; esta SPEC detalha apenas a evolução técnica da Engenharia, sem substituí-lo. |
| `docs/harnesses/squad_cliente/harness_coordenador_cliente_v1.md` | Coordenação econômica e menor privilégio como precedente, não cópia integral para Engenharia. |
| `docs/harnesses/squad_versus/harness_business_architect_versus_v1.md` | Fronteiras consultivas e discovery explícito; não transferir metodologia completa para Engenharia. |
| `.agent/skills/gestao_versus_core/SKILL.md`, `.agent/router/orchestrator.md`, `.agent/router/routing-matrix.md`, `.agent/references/constitution.md` | Governança obrigatória, liderança de arquitetura, contenção de contexto e card por entrega. |
| `docs/governance/governanca_documental_oficial_v1.md` | Classificação documental única e prioridade para atualização de fontes existentes. |

A busca por `TaskAssessment`, `WorkingSet`, `ContextGovernor`, `ModelBroker` e `engineering_context_governor` em `src/` e `services/` não encontrou esses identificadores. Isso indica ausência dos componentes com esses nomes, não prova ausência de toda lógica semelhante.

### Reconciliações obrigatórias

1. **Destino documental:** usar `docs/spec/`; não criar cópia em `docs/specifications/` como sugerido no chat. Não foi encontrada SPEC equivalente dedicada a esta orquestração.
2. **Registro versus execução:** oito harnesses registrados = coordenador + sete especialistas, não oito especialistas além do coordenador. A futura seleção deve consumir esse registro.
3. **Bootstrap e identidade:** não reutilizar seleção de sessão do Cliente para Engenharia sem contrato e teste explícitos. O mapa `_AGENT_BY_HARNESS` do registry contém o coordenador de Engenharia, mas não mapeia todos os seus especialistas; reconciliar especialização antes de publicar roteamento operacional.
4. **Tenant:** `company_id=10` no laboratório é contexto histórico específico, não default global. O projeto de cards pertence à empresa AA e é resolvido pelo marcador vigente, não por ID fixo.
5. **Surfaces:** `engineering/sapiens/onboarding` no catálogo de UI não substituem `user/admin/analytics/ops` no MCP. Não renomear policy a partir desse documento histórico.
6. **Estado local versus publicado:** testes locais com fakes não comprovam catálogo remoto nem autorização real. Nesta sessão não há tools MCP APP32 disponíveis; validação operacional permanece pendente.
7. **Economia:** 35–60% é hipótese do chat, não garantia nem medição. Contexto ativo menor não apaga histórico já enviado ao modelo nem equivale a redução idêntica da cota.

## 3. Arquitetura-alvo e boundaries

Fluxo: demanda → SE-COORD → TaskAssessment → Instruction Registry + Context Governor → especialista → QA → evidência MCP quando aplicável → conclusão ou handoff.

- `TaskAssessment` e decisões de contexto devem ser determinísticos inicialmente; nenhuma chamada de IA apenas para classificar uma alteração trivial.
- Contratos puros no domínio de inteligência; serviços coesos em `services/`, seguindo o padrão já usado pelo registry. Caminhos finais de novos módulos serão fechados na respectiva fase, após busca de reuso.
- Tools e rotas são adaptadores finos dos serviços existentes/novos; não duplicar regras nos transportes.
- Context Governor seleciona referências e contexto da tarefa; Instruction Registry continua dono das instruções, versões, layers e rollout.
- Model Broker é extensão posterior, não pré-requisito para economia de contexto.

## 4. TaskAssessment e roteamento

Contrato proposto: `schema_version`, `task_id`, `objective`, `domain`, `task_type`, `complexity`, `risk`, `scope`, `specialists`, `context_domains`, `requires_architect`, `requires_dba`, `reasons`, `unknowns`.

Vocabulários iniciais: complexidade e risco `low/medium/high`; escopo `file/module/cross_module`; tipo `diagnosis/documentation/maintenance/feature/incident`. Separar domínio técnico do especialista de domínio operacional MCP; aliases operacionais devem ser normalizados antes de policy e telemetria.

| Sinal | Harness líder / apoio condicionado |
|---|---|
| Arquitetura transversal, auth, tenant, segurança | `harness_arquiteto_engenharia_v1` |
| Jinja, CSS, interação visual | `harness_frontend_engenharia_v1` |
| Rotas, schemas e contratos REST/MCP | `harness_backend_api_engenharia_v1` |
| Regra de negócio | `harness_backend_service_engenharia_v1` |
| Agentes, RAG, LangGraph | `harness_ai_engineer_engenharia_v1` |
| Migração, query, índice, modelo PostgreSQL | `harness_dba_engenharia_v1` |
| Regressão, smoke, evidência | `harness_qa_automation_engenharia_v1` |

SE-COORD permanece a entrada. Priorizar risco sobre tamanho do diff; alterações de auth/tenant exigem arquitetura, migrações exigem DBA. Ambiguidade relevante gera pergunta ou diagnóstico, não certeza artificial. Emitir razões e regras acionadas. Escolher harness não altera credencial, role, surface ou modelo automaticamente.

## 5. Context Governor / Working Set

`EngineeringWorkingSet` proposto: versão, tarefa/objetivo, revisão, escopo de identidade, módulos, arquivos, documentos, decisões confirmadas, premissas, perguntas pendentes, referências de testes, estado dos itens, orçamento estimado e razões de drift.

Cada item tem identificador estável, origem, hash/versão, motivo de inclusão, dependências, estado e estimativa de tokens com método identificado.

- **ACTIVE:** somente conteúdo necessário é composto no próximo pacote de contexto.
- **WARM:** referências recuperáveis, sem reinjeção do conteúdo por padrão.
- **DROPPED:** fora do pacote; retorno exige necessidade explícita, nova validação e razão registrada.
- Guardrails globais e autorização não podem ser descartados pelo orçamento.
- Deduplicar conteúdo por identidade/versão; revalidar arquivo alterado e bundle invalidado; expansão carrega apenas o delta necessário.
- Orçamento excedido: reduzir contexto dispensável ou recomendar rotação, nunca truncar silenciosamente regras críticas.
- Scores são heurísticas versionadas; documentar entradas e limiares na fase 2. Não exibir percentuais fictícios de janela, drift ou uso real do provedor.
- Dados operacionais exigem `company_id` autenticado e autorização. Metadados puramente documentais podem ter escopo de repositório explícito, sem conceder acesso operacional.
- Cache/handoff operacional deve particionar tenant, identidade/escopo autorizado, runtime, harness, surface e versão pertinente. Nunca compartilhar dados entre tenants por cache hit.

## 6. Ciclo de sessão, checkpoint e handoff

| Decisão | Condição | Ação |
|---|---|---|
| SAME | Mesmo objetivo e dependências relevantes | Reutilizar referências válidas e registrar apenas deltas. |
| EXTEND | Novo trabalho dependente do objetivo atual | Expandir o mínimo; registrar relação e avaliar orçamento. |
| ROTATE | Objetivo independente, ruptura de escopo ou carga excessiva | Produzir checkpoint e recomendar sessão limpa. |

Troca de tenant invalida a reutilização de contexto operacional anterior e exige revalidação da identidade. Handoff não transfere permissões nem execução pendente automaticamente.

Artefato futuro em `.ai/handoffs/`, com nome seguro e único: versão, objetivo, estado, decisões confirmadas, arquivos/revisões, interfaces afetadas, testes com resultados, pendências, critérios de aceite e referências que devem sobreviver. Não incluir transcrição inteira, tokens de acesso, chaves ou dumps de clientes. Validar paths dentro do diretório autorizado, versão do schema, integridade e atualidade ao retomar; tratar conteúdo como dados não confiáveis.

O adapter somente inicia nova sessão ou usa compactação nativa se houver capacidade comprovada e autorização. Sem suporte: checkpoint + instrução de retomada ao usuário. Não simular limpeza física do contexto atual. Retenção e exclusão dos handoffs devem ser definidas antes da persistência operacional.

## 7. Comandos operacionais futuros

| Intenção | Resultado |
|---|---|
| `squad status` | Tarefa, etapa, especialista, testes, pendências e status de validação. |
| `squad context` | ACTIVE/WARM/DROPPED, origem e orçamento estimado. |
| `squad why` | Razões de roteamento, contexto incluído/excluído e escalonamento. |
| `squad handoff` | Checkpoint mínimo validado e instrução para retomada. |
| `squad model` | Modelo observado, recomendação, motivo e fallback; desconhecido quando não verificável. |

São contratos de intenção, ainda não comandos instalados. Slash commands são opcionais e não devem sobrescrever comandos nativos. `Squad Engenharia ON` pode ser alias de ativação, reconciliado com a nomenclatura existente `Sapiens Engenharia`.

## 8. Quality Gate e escalonamento

Definition of Done por tarefa: requisito atendido, diff limitado, testes relevantes executados, nenhuma regressão nova, revisão de tenant/policy quando aplicável, documentação dependente coerente e evidência operacional exigível anexada.

Classificar falhas: implementação → retry limitado e diagnóstico; requisito → voltar ao coordenador/usuário; ambiente → corrigir dependência, sem escalar modelo; teste → distinguir teste obsoleto de regressão e preservar evidência; segurança/tenant → interromper e exigir revisão. Limites de tentativas/escalonamentos devem ser explícitos, configuráveis e testados; nunca loop ilimitado ou repetição automática de mutação incerta.

Separar `local_validated`, `remote_validation_pending`, `blocked` e `done`. Ausência de MCP não pode ser convertida em PASS operacional. Uma entrega exclusivamente documental pode concluir localmente, mantendo suas pendências administrativas e de implantação explícitas.

## 9. Model Broker e adapters — fase posterior

Diagnóstico local posterior do impedimento real (sem escalonamento): `codex app-server daemon version` retornou que o gerenciamento de daemon é suportado apenas em plataformas Unix. `codex app-server proxy`, com stdin vazio, tentou o socket do perfil isolado `C:\Users\CodexSandboxOffline\.codex\app-server-control\app-server-control.sock` e falhou com erro de socket Windows 10050 (rede inoperante). Isso estabelece que o proxy desta sessão não alcança o runtime desktop; não demonstra que a aplicação desktop esteja desligada nem que modelos estejam indisponíveis na conta. Não houve mudança de CODEX_HOME, socket, permissões, configuração, daemon ou modelo. Não tentar outro perfil/socket como contorno. A validação viva exige um transporte suportado e autorizado fora dessa limitação; o adapter atual permanece experimental e não operacional no ambiente verificado.

Continuidade no card Fase 5: [x] unir Broker e consulta de catálogo via RPC confiável; [x] validar seleção explícita e fallback sem substituição; [x] baseline/documentação: **292 passed em 10,43 s**, zero tentativas externas detectadas. AST válido, diff check sem erros. Nenhuma conexão real ou chamada de geração executada neste recorte; sem novo card paralelo.

`EngineeringModelBrokerService.resolve_selection` aceita `RuntimeSelection` (modelo explícito e esforço opcional), Working Set/pacote atuais e conexão RPC nova fornecida por adapter confiável. Consulta catálogo a cada avaliação, sem cache nem JSON de catálogo fornecido pelo usuário. Combinação exata listada retorna `listed_for_manual_selection`; modelo ausente, esforço não listado ou erro de consulta retorna `manual_fallback`, preservando a escolha sem substituição. Suspensão da recomendação ou escopo empresarial bloqueiam antes da consulta. Não infere provider, modelo atual, preço, adequação do modelo ao perfil lógico ou acesso real de geração.

Os 13 testes adicionais usam RPC simulado, inclusive reconsulta após remoção do modelo e rejeição de pacote divergente antes do I/O. A conexão viva continua indisponível/não validada. A integração deste método é programática; a CLI `model` permanece offline e não aceita catálogo arbitrário nem executa descoberta implicitamente. Chamador futuro deve autenticar o transporte e aplicar QA antes de qualquer execução. `catalog_match` significa apenas correspondência com a listagem recebida, não permissão ou aprovação.

Continuidade de robustez no mesmo card da Fase 5: [x] limitar/encerrar transporte; [x] simular sucesso, falhas e timeout; [x] registrar baseline: **279 passed em 10,72 s**, zero tentativas externas detectadas. AST válido e diff check sem erros. Sem nova tentativa real ou mudança de permissões.

Nove testes adicionais do transporte usam processo e thread simulados: sucesso, executável ausente, falha de criação, EOF, JSON inválido, erro RPC, prazo excedido, falha de cleanup e kill após timeout de encerramento. O adapter só emite resultado depois de tentar encerrar o próprio proxy; falha de cleanup retorna erro específico sem traceback/payload. Fecha pipes quando o leitor terminou. Esses testes não provam comportamento de concorrência ou IPC real no Windows. Prazo de 20 s é para processamento/espera de respostas, não limite absoluto de wall-clock: criação, escrita em pipe e encerramento têm limites próprios ou dependem do SO. A integração viva permanece não validada.

Continuidade Fase 5 no mesmo card preparado: [x] adapter somente leitura do catálogo Codex; [x] teste de protocolo e tentativa local sem iniciar daemon; [x] documentação da evidência. Registro remoto segue pendente pelo bloqueio já documentado.

Evidência final deste recorte: **270 passed em 10,96 s**, zero tentativas externas detectadas no baseline protegido; AST dos três arquivos novos válido e diff check sem erros. Nove casos novos do parser/protocolo usam RPC simulado; não validam o transporte de subprocesso real, cujo smoke separado retornou indisponibilidade. Status local_validated apenas para o recorte unitário, não para integração viva.

Adapter `engineering_runtime_catalog_service.py` projeta apenas nomes de modelos e esforços de `model/list`, com paginação limitada a 10 páginas de até 100 itens, sem metadados livres de descrição. Handshake initialize/initialized conforme [documentação oficial do App Server](https://learn.chatgpt.com/docs/app-server). Transporte explícito em `scripts/read_engineering_runtime_catalog.py` conecta somente via `codex app-server proxy` a daemon existente, limita espera a 20 segundos e encerra apenas o próprio subprocesso de proxy. Não inicia daemon, thread ou turn; não escreve configuração. Erros não expõem stderr ou payload do runtime.

Tentativa real nesta sessão retornou `runtime_catalog_unavailable`. O executável local e o subcomando proxy existem, mas o catálogo não foi obtido; causa exata não estabelecida. Sem nova tentativa por escalonamento ou bypass. `generation_access_verified` permanece false mesmo quando um catálogo é recebido: listagem não prova execução, preço, disponibilidade futura ou modelo atual da tarefa. Sem cache persistente, catálogo entregue pelo usuário ou mapeamento automático de perfil lógico para modelo comercial. Integração viva e consumo de catálogo pelo Broker permanecem pendentes.

Entrada: complexidade, risco, tipo, tamanho de contexto estimado, especialista, tentativas, causa da falha, modelos realmente disponíveis e preferências/autorização do usuário.

Saída: perfil lógico `ECONOMY/STANDARD/DEEP`, provider/model quando verificáveis, esforço suportado, razão e fallback. Não fixar nomes comerciais ou preços nesta SPEC. Provider-neutral significa contrato comum, não equivalência garantida de funcionalidades.

Implementar primeiro o adapter do runtime efetivamente escolhido. Descobrir capacidades sem inventá-las; sem suporte a troca automática, apenas recomendar mudança. Respeitar limites do host e escolha explícita do usuário. Outros providers entram após testes de conformidade. Catálogo remoto, tokens e credenciais nunca devem entrar no handoff.

## 10. Telemetria e validação da economia

## 20. Sapiens Engenharia — triagem de complexidade e economia de contexto

Card de continuidade preparado: **[Sapiens Engenharia — triagem de complexidade e economia de contexto]**. Registro remoto segue pendente pelo bloqueio de aprovação já documentado, sem contorno.

Decisão de produto: o SE-COORD/Sapiens Engenharia **não seleciona, recomenda ou troca modelos**. O usuário escolhe manualmente Astra, Terra ou 5.5 fora deste contrato. O núcleo local devolve somente intenção, complexidade, risco e como reduzir contexto sem remover guardrails.

Entrada opcional `task_intent`: `execution`, `correction` ou `planning`. Sem entrada explícita, manutenção/correção infere `correction`; sinal de planejamento infere `planning`; demais casos inferem `execution`. Complexidade base: baixa/média/alta respectivamente. Segurança, tenant, migração ou incidente não podem ser rebaixados pela intenção declarada. Risco continua uma dimensão distinta: planejamento pode ser alto em complexidade sem ser alto em risco.

`EngineeringTokenEconomyService` devolve estratégia determinística: `minimal_active` (objetivo, fonte afetada e evidência direta), `symbol_and_delta` (contrato, dependências diretas e regressão), `architecture_then_expand` (resumo versionado, decisões e invariantes) ou `clarify_before_expand`. WARM preserva interfaces/resumos recuperáveis; DROPPED mantém módulos não relacionados, documentação integral e logs brutos fora do pacote. Contexto empresarial/alto risco exige adapter MCP autenticado antes de qualquer evidência operacional, mas a orientação não concede acesso.

`scripts/assess_engineering_task.py` passa a emitir `token_economy` e telemetria mínima, sem conteúdo livre, tokens estimados, provider, modelo ou economia inventada. `selects_model=false` e `estimated_token_savings=null` são intencionais. O serviço é puro, não cria sessão, provider, task, rota ou mutação. Evidência: **331 passed em 21,71 s**, zero tentativas externas detectadas no baseline; contrato CLI exercitado. Integração MCP autenticada e rollout remoto continuam pendentes.

### Entrada canônica do Sapiens Engenharia

O bootstrap canônico `describe_app32_squad_runtime_tool(runtime_profile='engineering')` e `SapiensActivationService.resolve_activation(..., squad='engineering')` agora publicam o mesmo manifesto de orientação do SE-COORD. Ele informa os campos aceitos, complexidade/risco/economia como saída, as quatro estratégias de contexto e `model_selection=manual_outside_assessment`. Não cria uma nova tool, rota, catálogo, sessão, execução de especialista ou leitura operacional. Para evidência de empresa, continua obrigatório adapter MCP autenticado com `company_id`; o manifesto apenas torna o limite explícito. Esta é integração de orientação local; publicação/remoto autenticado segue pendente.

Checklist da entrega **[Sapiens Engenharia — triagem de complexidade e economia de contexto]**: [x] manifesto único em service; [x] ativação e bootstrap MCP canônicos; [x] interação guiada no tool canônico; [x] regressão protegida; [ ] materialização/fechamento remoto do card, bloqueados sem contorno pela aprovação externa já registrada.

O mesmo `resolve_app32_sapiens_activation_tool` aceita opcionalmente `engineering_task` **somente** depois de `squad='engineering'`. A resposta `guided_triage` é deliberadamente estreita: intenção, complexidade, risco, pendências e `token_economy`; não expõe seleção de especialista, não aceita `company_id`, `context_scope`, surface, usuário ou papel fornecidos pelo chamador, e não faz leitura empresarial. Entrada inválida ou tentativa fora de Engenharia falha fechada. Esta é a interação guiada local, sem nova tool ou alteração de catálogo.

Teste sintético v2 de seleção de contexto concluído após autorização: mesma tarefa, `gpt-5.5`/`low`, candidate com 794 caracteres e baseline com 11786. Telemetria por turno: baseline 24403 tokens, candidate 21901, diferença de 2502 (**-10,25%**). A redução textual de 93,26% não se traduziu proporcionalmente porque o envelope do runtime dominou aproximadamente 21–22 mil tokens. Candidate foi executado antes, baseline teve mais cache; não inferir custo, latência ou causalidade. Fontes sintéticas foram usadas porque o runtime recusou o envio de código-fonte local; não houve bypass. Relatório: `docs/experiments/contexto_manual_piloto_v1/resultado_reducao_contexto_sintetico_v2.md`.

Repetição v3 após autorização: três pares sintéticos sequenciais com ordem alternada e `gpt-5.5`/`low`. Média baseline 24432,00 tokens e candidate 21798,67; diferença média 2633,33 (**-10,78%**), mediana -10,29%, faixa -10,02% a -12,02%. As seis respostas atenderam à inspeção técnica solicitada e ficaram abaixo de 180 palavras, mas a revisão não foi cega. Cache desigual no P2 impede conclusão de custo. Relatório: `docs/experiments/contexto_manual_piloto_v1/resultado_reducao_contexto_sintetico_v3.md`. O resultado fortalece a hipótese de ganho por seleção de contexto em tarefas baixas; não valida meta 35–60%, produção ou equivalência de runtime.

Atualização da evidência real: telemetria recuperada dos JSONL locais específicos das duas tarefas, com turn_id correspondente e um token_usage_record por execução. Ambas registram gpt-6-astra/low, provider openai e CLI 0.153.4. Baseline: 31873 input + 635 output = 32508 tokens; candidate: 30233 + 592 = 30825. Diferença observada de 1683 tokens (5,1772%), sem dupla contagem de cache/raciocínio. Resolve ausência de tokens e configuração nominal; não resolve snapshot interno, equivalência integral do host, revisão cega ou sobreposição temporal. Relatório atualizado em `docs/experiments/contexto_manual_piloto_v1/resultado_exploratorio.md`. Nenhuma nova execução ou chamada paga; 35–60% não confirmado, custo e causalidade não demonstrados.

Revisão técnica posterior das duas respostas concluída sem nova execução: sete critérios atendidos em ambas, limite de 350 palavras respeitado (313 baseline, 316 candidate por whitespace) e hashes das fontes conferidos. Resultado é não cego, feito pelo coordenador; não substitui revisão independente, nem comprova consumo/equivalência do runtime. Ficha de medição continua pendente e nenhuma economia foi calculada.

Piloto posteriormente executado após autorização explícita de duas tarefas novas: candidate `01a07e72-37ca-7393-99eb-d8e7e2ceb0b4` e baseline `01a07e72-4cf5-75e2-9c13-0509a8b2dec5`. Ambas concluídas. Resultado e desvios em `docs/experiments/contexto_manual_piloto_v1/resultado_exploratorio.md`: sobreposição temporal, QA não cego, modelo/esforço efetivos e tokens por turno não verificados. Não executar comparação quantitativa sem os dados faltantes; nenhum ganho causal declarado.

Preparação manual do experimento autorizada pelo usuário, no mesmo card Fase 6: [x] roteiro e critérios de QA; [x] pacotes congelados e hashes; [x] verificação local dos artefatos. Roteiro em `docs/runbooks/experimento_manual_contexto_engenharia_v1.md`, kit em `docs/experiments/contexto_manual_piloto_v1`. Fontes, prompt e governança congelados; hashes dos artefatos conferidos por leitura dos bytes gravados. Ficha com medições null e identidade/runtime pendentes intencionalmente não é comparável ainda. Nenhuma task criada, coleta real ou chamada de geração. Registro remoto permanece pendente. Nenhum código de runtime mudou nesta preparação; baseline de código anterior permanece 318 testes, não reexecutado para documentos.

Continuidade no mesmo card Fase 6: [x] CLI limitada por stdin; [x] testes de entradas/saídas; [x] documentação e evidência: **318 passed em 11,08 s**, zero tentativas externas detectadas. AST válido; diff check sem erros. Sem coleta externa, persistência ou exportação de dados empresariais.

`scripts/compare_engineering_measurements.py` recebe par baseline/candidate via stdin limitado a 65536 caracteres. Contratos rejeitam extras e contagens acima de 10^15 (proteção aritmética, não limite comercial). Exit 2 para entrada inválida/incomparável; 3 para qualidade não estabelecida; 4 quando percentual de tokens reportados está indisponível, inclusive baseline zero; 0 apenas para comparação calculável declarada, nunca comprovação de economia. Erros não ecoam entrada. Nove casos CLI adicionais sintéticos. Não há experimento real realizado nem integração operacional concluída.

Card preparado **[Fase 6 comparação local de medições SE-COORD]**, remoto pendente pelo bloqueio já registrado. Checklist: [x] contrato mínimo e comparabilidade; [x] cálculos sem confundir estimativas/uso real; [x] baseline e documentação: **309 passed em 11,73 s**, zero tentativas externas detectadas. AST válido e diff check sem erros. Frente independente do transporte bloqueado da Fase 5; sem coleta real ou inferência de economia obtida.

Recorte inicial em `EngineeringMeasurementService.compare`: par baseline/candidate deve compartilhar fingerprints de carga, identidade, avaliação e runtime. São declarações do chamador, não autenticação ou prova de equivalência. Contagens inteiras não negativas, sem coerção booleana. Calcula redução percentual apenas quando ambos declaram qualidade PASS e baseline é positivo. Dados ausentes e baseline zero produzem null; aumentos são mantidos como redução negativa. Sem qualidade confirmada, preserva números mas suprime percentual.

Estimativa de contexto e total reportado de entrada+saída são métricas distintas. O total só é comparado quando ambos declaram fonte provider_reported e ambas as contagens estão presentes; não substitui ausência por estimativa/zero. O adapter futuro deve normalizar sem dupla contagem de cache/raciocínio e definir runtime_fingerprint incluindo provider/modelo/versão/esforço relevantes. Não compara modelos diferentes como se fossem experimento controlado.

Saída não contém fingerprints/objetivos/fontes livres e não persiste dados. Economia financeira e prova causal permanecem desconhecidas/falsas: uma dupla declarada não é evidência estatística, leitura de consumo do plano ou confirmação da hipótese de 35–60%. Dezessete testes novos usam dados sintéticos. Coleta autenticada, múltiplas amostras, integração com uso real, CLI e persistência permanecem fora deste recorte; Fase 6 completa não está concluída.

Registrar desde a primeira fase funcional: tarefa, versões de regras/bundle, contexto estimado e método, arquivos/documentos carregados, decisões de sessão, modelo/provider observado, tentativas, duração, testes, resultado e escalonamentos. Eventos sem conteúdo sensível por padrão; escopo tenant-safe para dados operacionais.

Separar tokens estimados do pacote, uso real informado pelo provedor, cache, tokens de saída/raciocínio e custo. Se indisponível, registrar `unknown`, não zero. Não inferir consumo de plano a partir do tamanho dos arquivos.

Comparar tarefas equivalentes antes/depois, por tipo/risco e mesma definição de uso: `(baseline - otimizado) / baseline`, apenas para baseline positivo e medido comparavelmente. Baseline contrafactual é estimativa e deve ser rotulado. Meta experimental: redução média de 40%, sem degradar first-pass, regressões, isolamento ou tempo de conclusão. Faixa de 35–60% permanece hipótese. Avaliar 50–100 tarefas antes de ranking empírico de modelos; não somar percentuais de fontes sobrepostas.

## 11. Plano incremental e critérios de aceite

| Fase | Entrega delimitada | Aceite / gate |
|---|---|---|
| 0 — esta entrega | Diagnóstico, baseline, SPEC e pendências | Fontes verificadas, resultados reais registrados, nenhum código funcional alterado. |
| 1 | TaskAssessment e roteamento via SE-COORD; telemetria mínima | Casos frontend/service/API/DB/segurança/ambiguidade determinísticos; oito harnesses preservados; reconciliar identidade dos especialistas; sem LLM obrigatório e sem ampliação de policy. |
| 2 | Working Set e Context Governor integrados ao registry | Testes ACTIVE/WARM/DROPPED, deduplicação, invalidation, orçamento, guardrails irremovíveis e isolamento tenant/identidade. |
| 3 | SAME/EXTEND/ROTATE, handoff e cinco intenções operacionais | Testes de retomada, fonte obsoleta, path inválido, payload malformado, troca de tenant e provider sem compactação; nenhuma capacidade nativa presumida. |
| 4 | QA e escalation | Falhas de requisito/ambiente/teste/implementação/segurança exercitadas; retries finitos, sem mutação duplicada; distinguir validação local da remota. |
| 5 | Model Broker e primeiro adapter | Respeitar modelos disponíveis, preferência explícita, falha de capacidade, fallback e recomendação manual; testes com adapter fake antes de runtime real. |
| 6 | Telemetria comparativa e demais adapters | Métricas auditáveis e comparáveis, custo separado de tokens, proteção de dados, regressão contratual por provider e amostra suficiente antes de ranking. |

Cada fase: card único por entrega → implementação limitada → teste → evidência → revisão; não avançar automaticamente. Antes da fase 1, reconciliar a falha do baseline abaixo (ou formalizar exceção com responsável e prazo), sem simplesmente atualizar expectativa para mascarar drift.

Governança documental por fase: revisar dependências na ordem Paper → SPEC → Manifesto → Playbook → Runbook → Harness. Nesta fase apenas a decisão-alvo é publicada; não alterar instruções ativas para prometer funcionalidades inexistentes. Nas fases funcionais, sincronizar playbook/runbook/harness e referências do registry antes do rollout. Não criar seis documentos duplicados apenas para preencher classes.

Rollout: opt-in para Engenharia, preservando Cliente e Versus; comparar comportamento com baseline. Reversão deve permitir retornar ao bootstrap atual sem remover contratos existentes ou apagar evidências/handoffs. Mudanças de schema/persistência exigem plano de compatibilidade e migração próprio.

## 12. Baseline executado e limitações

Data: 2026-09-07. PowerShell na raiz `C:\GestaoVersus\app32`; Python local, sem instalar dependências e sem alterar testes. Autoload de plugins desativado; isso não garante isolamento do bootstrap da aplicação ou do banco (ver ressalva do recorte complementar). Não executada a suíte completa ou E2E.

```powershell
$env:PYTHONPATH = 'C:\GestaoVersus\app32\app32'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -c pytest.ini app32/tests/test_mcp_squad_runtime.py app32/tests/test_mcp_instruction_registry.py app32/tests/test_instruction_registry_service.py app32/tests/test_mcp_permission_matrix.py app32/tests/test_mcp_connection_snippet_service.py app32/tests/test_mcp_connection_experience_spec.py app32/tests/test_core_mcp_session_harness_tools.py -q
```

Resultado: **37 passed, 1 failed em 5,60 s**; exit code 1. Falha preexistente observada antes de qualquer alteração desta entrega: `test_instruction_bundle_publishes_safe_discovery_and_retry_rules`, em `tests/test_instruction_registry_service.py:27`, espera `2026-08-28.5` e recebe `2026-09-03.1`. A primeira asserção impede validar as seguintes nesse teste; não concluir que apenas a versão precisa ser corrigida. Nenhuma correção incluída nesta etapa.

Cobertura identificada: bootstrap Cliente/Engenharia e runtime desconhecido; bundle/registry; permission matrix e overlays; snippets e experiência de conexão; seleção de harness com fakes. Não equivale a smoke remoto, migração, teste de carga ou validação PostgreSQL.

Recorte complementar: `test_core_mcp_runtime_http_context.py`, `test_core_mcp_surface_registry.py`, `test_mcp_profile_contracts.py`, `test_mcp_profile_scope_matrix.py`: **39 passed, 1 warning em 35,76 s**, exit code 0. Executado com o mesmo comando/configuração acima, substituindo a lista de arquivos. Warning de namespace protegido `model_role` no Pydantic.

**Ressalva de segurança do baseline:** após os testes, o processo emitiu logs de sincronização de conhecimento agendada, com registros de execução no banco configurado e `UniqueViolation` em `uq_knowledge_source_grants_employee`. Portanto, esse recorte não foi hermético e pode produzir efeitos persistentes; seu PASS não representa execução sem efeitos colaterais. O ambiente efetivo do banco e a extensão das alterações não foram auditados nesta entrega. Não repetir antes de isolar banco de teste e desabilitar jobs de background no bootstrap. Não foi tentada reversão automática de dados.

Uma reexecução já iniciada apenas de `test_mcp_profile_contracts.py` e `test_mcp_profile_scope_matrix.py` reportou **14 passed em 16,69 s**; é cobertura sobreposta e não deve ser somada. Total dos dois recortes distintos: **76 aprovados, 1 falha preexistente**, com as ressalvas acima. Novas execuções foram suspensas após identificação dos efeitos de background.

## 13. Card e pendências de continuidade

Card preparado: **[Especificacao orquestracao contexto modelos Squad Engenharia v1]**.

- [x] Diagnosticar fontes canônicas e reconciliar decisões: seções 2–3.
- [x] Identificar e verificar baseline: seção 12; baseline não está verde.
- [x] Consolidar e revisar SPEC e plano incremental: fontes tabuladas verificadas no filesystem, limites de escopo e fases revisados; pendências registradas.
- [ ] Materializar/sincronizar o card no projeto operacional vigente.

O wrapper oficial `aa_j_31_step_wrapper.py materialize` foi tentado, mas falhou ao carregar a chave SSH antes de listar/criar cards. Não há ID de card criado nem conclusão operacional declarada. Aplicado o fallback explícito da skill `aa-j-31-card-execution`: lista/card preparado localmente. Não acessar banco diretamente para contornar a ausência de credencial.

Sem tools MCP APP32 disponíveis nesta sessão; nenhuma validação de produção realizada. Sem deploy, migração, instalação, branch nova ou commit. Alterações preexistentes do workspace não fazem parte desta entrega.

Próximo comando sugerido: “Squad Engenharia ON. Consulte a seção 14, conclua a auditoria operacional pendente por acesso autorizado e prepare a Fase 1, sem avançar para a Fase 2.”

## 14. Continuidade — isolamento do baseline (2026-09-07)

Card preparado localmente: **[Isolamento e reconciliacao do baseline Squad Engenharia]**; mesma indisponibilidade de chave SSH, sem ID remoto ou fechamento fictício.

- [x] Diagnóstico estático do caminho de inicialização e dos efeitos potenciais.
- [x] Substituição da factory por Flask mínimo nos testes de surfaces; dois testes novos validam criação/reuso e liberação do contexto.
- [x] Reconciliação da versão no teste do registry e execução das asserções comportamentais subsequentes.
- [x] Executor dedicado de baseline com isolamento das dependências externas e bloqueios antes da coleta.
- [ ] Auditoria do ambiente/banco afetado e registro no card operacional.

### Causa e contenção

`_get_surface_manifest_in_app_context()` em `src/core/mcp_surface_registry.py` chama `create_app()` quando não há contexto Flask. Os testes de discovery exercitavam esse ramo sem substituir a factory. Em `app.py`, o bootstrap de runtime pode iniciar o worker e o scheduler. `setup_knowledge_jobs()` em `services/scheduler_service.py` agenda sincronizações com `next_run_time=datetime.now()`; portanto não depende de esperar quinze minutos.

O catálogo também importa singletons legados: `src/intelligence/rag.py` inicializa embeddings/Chroma; e-mail e WhatsApp consultam configuração persistida via `utils/integration_settings.py`. Nas primeiras tentativas protegidas, o bloqueio detectou acessos PostgreSQL mesmo com asserções verdes; o executor retornou erro, não sucesso. O RAG legado pode acessar armazenamento local e possui lógica de recriação em erro: bloquear rede sozinho não bastava. A versão final substitui RAG e configuração de integrações antes da coleta; não importa o singleton Chroma.

Mudanças limitadas a `tests/test_core_mcp_surface_registry.py`, `tests/test_instruction_registry_service.py` e `scripts/run_engineering_baseline.py`; nenhuma alteração no runtime produtivo. O teste de versão agora exige igualdade com `CURRENT_BUNDLE_VERSION`, preservando todas as asserções de regras e jornada. A execução confirmou essas asserções, não apenas a string de versão.

### Execução preferencial daqui em diante

```powershell
python C:\GestaoVersus\app32\app32\scripts\run_engineering_baseline.py
```

O executor possui lista fixa dos onze arquivos desta SPEC; não é um runner de integração. Desativa bootstrap de schema/runtime, substitui RAG/configuração de integrações e bloqueia sockets externos/DNS, subprocessos, PostgreSQL e SQLite. Qualquer tentativa capturada falha o comando mesmo que o código da aplicação capture a exceção. Pares privados de sockets para o wakeup do asyncio são pré-alocados antes dos bloqueios; localhost arbitrário não é liberado. A descoberta stdlib da plataforma Windows ocorre antes dos bloqueios e antes de importar aplicação/testes.

Resultado final, incluindo bloqueios SQLite: **79 passed em 14,62 s**, exit code 0, zero tentativas de I/O externo registradas. São os 77 testes originais mais dois testes de contexto; não somar com execuções anteriores. Verificação AST dos três arquivos Python e `git diff --check` dos testes também passaram. O runner é uma proteção em processo para este recorte conhecido, não sandbox de sistema operacional nem garantia para novos drivers ou módulos. Toda expansão da lista exige revisão prévia dos efeitos de importação.

### Efeito anterior: avaliação limitada, não incidente encerrado

`services/knowledge/repository.py` confirma commits separados em `start_run`, `sync_documents` e `complete_run`. Uma falha por chave duplicada pode desfazer aquela transação, mas não reverte runs anteriores já concluídos. Os logs anteriores demonstram execução do job e erro de unicidade; não estabelecem a extensão total das alterações, nem permitem afirmar corrupção ou ausência de impacto.

Pendência operacional: identificar o banco efetivamente usado sem expor credenciais, consultar os runs de conhecimento da janela da execução com escopo de tenant autorizado, conferir contagens/erros/fontes e grants afetados e comparar com evidência anterior disponível. Também conferir integridade do armazenamento RAG local devido ao import legado das primeiras tentativas. Não apagar runs, fontes, grants ou arquivos para simular reversão. Sem acesso MCP/SSH autorizado nesta sessão, esta auditoria permanece aberta; nenhuma alteração compensatória foi tentada.

A infraestrutura local de testes foi corrigida; o gate de auditoria operacional permanece separado e não deve ser omitido para declarar a Fase 1 implantada.

## 15. Auditoria somente leitura do ambiente afetado

Continuidade após validação SSH: autenticação como `app` confirmada com checagem estrita de host. A auditoria não usou esse servidor como substituto do ambiente realmente afetado.

### Identificação e método

- Configuração local inspecionada sem importar `config`, Flask, catálogo, RAG ou services: `.env` da raiz define development e `DATABASE_URL` para `localhost:5432/bdversusv2_prodclone`; sem override `DEV_DATABASE_URL` observado.
- Conexão direta de diagnóstico ao clone local com a credencial já configurada, pois não havia ferramenta MCP APP32 exposta nesta sessão. Não utilizada para contornar falta de credencial; nenhuma credencial impressa.
- PostgreSQL confirmou `current_database() = bdversusv2_prodclone` e `transaction_read_only = on`. Todas as conexões foram abertas com `default_transaction_read_only=on`, timeout de consulta de 10 s e encerradas com rollback.
- Janela consultada: `2026-09-07 23:00:00` a `2026-09-08 00:00:00` UTC, incluindo os logs de 23:18. IDs e horários locais coincidem com os logs originais, incluindo runs 711–716. Isso vincula o incidente observado ao clone; não é uma auditoria de produção.
- Inventário mínimo de IDs de empresas; demais consultas de negócio filtradas individualmente por `company_id`. Fontes globais filtradas explicitamente por `company_id IS NULL AND knowledge_scope='product'`. Sem leitura de conteúdo de documentos, dados pessoais ou mensagens.

### Evidência encontrada

| Escopo | Resultado |
|---|---|
| Empresas 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13 | 44 runs: 42 completed, 2 failed; contagens registradas de criação/atualização/inativação iguais a zero. Nenhuma fonte com `updated_at` na janela para esses tenants. |
| Empresa 2 | Runs 675 e 698 falharam em `meeting`, com erro associado a `uq_knowledge_source_grants_employee`. |
| Grants nos 11 tenants | Zero grupos duplicados por fonte/employee; zero grants órfãos ou com `company_id` divergente da fonte na consulta atual. Isso não prova igualdade com o estado anterior. |
| Produto global — run 671, `product_help` | 23:18:31.591726–23:18:31.990328; 71 descobertas, 2 criadas, 0 atualizadas, 69 inalteradas, 1 inativada. |
| Produto global — run 676, `system_documentation` | 23:18:32.098079–23:18:36.302629; 65 descobertas, 8 criadas, 2 atualizadas, 55 inalteradas, 0 inativadas. |
| Fontes globais com timestamp na janela | 2 `product_help/published`, 1 `product_help/inactive` e 10 `system_documentation/published`, coerentes com as contagens dos runs. |

Conclusão: houve **10 criações, 2 atualizações e 1 inativação** de fontes globais no clone local, além de registros de execução. Não é correto classificar a execução anterior como sem efeitos colaterais. Não foram encontrados os mesmos efeitos em fontes tenant-owned no recorte consultado. Nenhuma restauração ou exclusão foi executada.

### Armazenamento RAG local

Inspeção apenas como arquivo, sem abrir SQLite nem inicializar Chroma:

- `C:\GestaoVersus\app32\data\chroma_db\chroma.sqlite3`: 188416 bytes.
- Última escrita informada pelo filesystem: 2026-09-04 17:52:14 UTC, anterior ao incidente.
- SHA-256 atual: `a7e77245f2097520db37dcf68d0a1dbfc0eb45ef6ec557881df6260710b5ed8f`.
- O arquivo já aparecia modificado no Git antes do primeiro baseline. Não atribuir essa diferença ao incidente nem restaurá-lo a partir do Git.
- Metadados não demonstram integridade lógica nem cobrem todos os artefatos do diretório; não existe hash pré-incidente disponível para comparação. Essa limitação permanece explícita.

### Decisão e pendência

A auditoria de leitura do clone avançou e identificou o efeito persistido. Não há justificativa para rollback cego: runs não armazenam necessariamente o conteúdo anterior das fontes atualizadas/inativadas. Preservar evidência e obter comparação com backup/snapshot anterior caso seja necessária restauração. A correção de isolamento dos testes continua validada pelo baseline protegido de 79 testes; nenhum código produtivo foi alterado nesta auditoria.

Próxima decisão necessária: aceitar explicitamente o estado sincronizado do **clone local**, com as limitações registradas, ou fornecer backup/snapshot para planejar restauração seletiva. Isso não autoriza alteração ou deploy em produção. O card operacional ainda não foi sincronizado; a presente auditoria permaneceu estritamente somente leitura no banco.

## 16. Fase 1 — SE-COORD local e determinístico

Autorização de continuidade: o usuário confirmou avançar na classificação/roteamento com dados controlados e adiar a atualização do clone para antes da integração operacional. Isso não encerra as ressalvas históricas da auditoria nem autoriza deploy/restauração.

Card preparado: **[Fase 1 SE-COORD classificacao e roteamento]**.

- [x] Contratos puros e regras determinísticas: primeiro recorte validado com 108 testes.
- [x] Identidade canônica e entrada SE-COORD: recorte intermediário validado com 122 testes.
- [x] Baseline final: **129 passed em 11,11 s**, exit code 0, zero tentativas externas detectadas pelo executor protegido. Smoke da entrada JSON retornou Backend Service + QA para manutenção de cálculo. `git diff --check` passou nos arquivos rastreados alterados desta fase.
- [ ] Materialização do card remoto: tentativa via wrapper oficial bloqueada pelo auto-review por falta de créditos do workspace. Não houve execução remota nem contorno; aplicado fallback local da skill.

### Entrega implementada

- `src/intelligence/engineering_assessment.py`: request estrito e imutável, `TaskAssessment` e evento mínimo de telemetria sem objetivo, paths ou identificador livre da tarefa.
- `services/engineering_task_router_service.py`: classificação pura; não consulta DB, não lê arquivos, não chama LLM, não seleciona sessão nem executa especialistas. Referências de arquivo são metadados fornecidos pelo chamador.
- `scripts/assess_engineering_task.py`: entrada local JSON por stdin para o SE-COORD; retorna assessment e telemetria, não persiste eventos. Retorna código 2 em entrada inválida, sem expor o payload na mensagem de erro.
- `src/intelligence/security/runtime_profiles.py`: identidade declarada nos oito harnesses já existentes. Agentes: SE-COORD, SE-ARCH, SE-FRONTEND, SE-BACKEND-API, SE-BACKEND-SERVICE, SE-AI, SE-DBA e SE-QA. Não foram criados novos harnesses.
- `services/instruction_registry_service.py`: Engenharia resolve agente pelo harness canônico e rejeita harness de outra família ou par agente/harness incompatível antes do bootstrap de persistência. Cliente/Versus mantêm o comportamento anterior.
- `src/core/mcp_squad_runtime_tools.py`: descrição de Engenharia recebe metadados aditivos da triagem local e identidades; não registra nova tool de execução nem concede acesso.

### Regras e limites v1

Pedido: `task_id`, `objective`, `task_type` opcional, `files`, `domain_hints`, `context_scope` e `company_id`. Empresa exige ID inteiro positivo (não bool/string); repositório não aceita ID de empresa. Campos de autoridade como `surface`, `runtime_profile`, permissões e modelo não são aceitos no pedido.

Tipos inferidos, quando omitidos: incident → documentation → maintenance → feature → diagnosis, por vocabulário determinístico documentado no service. Tipo fornecido explicitamente não reduz risco detectado de incidente, segurança ou migração. Sete domínios técnicos equivalem aos especialistas da seção 4; não são domínios de autorização MCP.

Sinais de segurança/tenant priorizam Arquiteto; migração exige DBA, inclusive como apoio quando Arquitetura lidera. Alteração funcional recomenda QA. Domínio ausente ou múltiplos domínios sem líder inequívoco retorna `unknown`, perguntas pendentes e nenhum especialista executor. Não há despacho de subagentes: a lista é recomendação, sujeita à autorização do runtime.

Complexidade e escopo são heurísticas por quantidade de referências e diversidade técnica, não análise semântica dos arquivos. Palavras-chave inclusive em negações podem provocar escalonamento conservador. Não garantir compreensão de texto livre; `domain_hints` permite triagem explícita, mas não sobrepõe gates de risco. Não usar esses resultados como mecanismo de RBAC ou medição real de tokens.

`company_id` rotula o contexto solicitado, não autentica acesso. Toda futura execução operacional deve resolver identidade real e policy independentemente. Nenhuma alteração de surface/role/token, transporte, Permission Matrix ou autorização foi feita.

### Documentação operacional

Playbook: `docs/playbooks/playbook_triagem_se_coord_v1.md`. Runbook: `docs/runbooks/runbook_triagem_se_coord_local_v1.md`. Harness existente atualizado em `.ai/codex-squad-engenharia-laboratorio.md`. Paper/Manifesto revistos quanto ao escopo: princípios e identidade de negócio não mudam; não criada documentação duplicada. A SPEC define identidades técnicas que não equivalem a novos agentes de negócio.

O baseline protegido passa a incluir `tests/test_engineering_task_router.py`. Fase 1 é **local_validated**, não `remote_validated`: a descrição MCP alterada foi exercitada com fake e não publicada. Context Governor, lifecycle de sessões, broker, persistência da telemetria e comandos `squad ...` permanecem fora desta fase.

Próximo passo de desenvolvimento: Fase 2, somente após autorização, mantendo o runner protegido. Antes da integração operacional, atualizar/sanitizar o clone e validar o MCP real. O bloqueio de registro remoto exige regularização dos créditos de revisão pelo responsável do workspace; não foi contornado e o card não foi declarado concluído remotamente.

## 17. Fase 2 — Context Governor e Working Set locais

Card preparado: **[Fase 2 Context Governor e Working Set]**. Registro remoto ainda pendente devido ao bloqueio de aprovação por créditos, sem tentativa de contorno.

- [x] Contratos imutáveis, escopo e composição ACTIVE/WARM/DROPPED: primeiro recorte com 152 testes aprovados.
- [x] Integração explícita com bundle do Instruction Registry; orçamento, dependências, invalidação e deltas: recorte intermediário com 161 testes aprovados.
- [x] Baseline protegido final: **161 passed em 9,09 s**, exit code 0, zero tentativas externas detectadas. Entrada CLI exercitada em testes (sucesso, orçamento insuficiente, escopo empresarial recusado e payload inválido). AST dos quatro arquivos novos e revisão documental concluídos.

Limites: serviço local em memória, sem leitura automática de arquivos, persistência, mudança de permissões, compactação nativa, handoff ou nova sessão. Somente a Fase 2 foi autorizada nesta etapa.

### Contratos e responsabilidades

`src/intelligence/engineering_context.py` contém `ContextIdentity`, `ContextItem`, `EngineeringWorkingSet` e `ContextPacket`. São modelos imutáveis com campos extras proibidos. `services/engineering_context_governor_service.py` implementa criação, upsert, transição, refresh do registry, composição e delta lógico. `scripts/compose_engineering_context.py` liga a triagem da Fase 1 ao bundle do registry e à composição, via JSON local. `tests/test_engineering_context_governor.py` integra o runner protegido.

- Identidade particionada por repositório, escopo, empresa, usuário, revisão de autorização, runtime, harness e surface. Alteração em qualquer campo exige novo Working Set; sem cache compartilhado ou estado global.
- Contexto empresarial no service exige empresa/usuário inteiros positivos e revisão explícita de autorização. Esses descritores não autenticam ninguém: o adapter operacional futuro deverá obtê-los de uma identidade realmente autenticada. A CLI local aceita apenas contexto de repositório e recusa execução dentro de contexto Flask.
- Bundle aceito deve vir de resolução confiável no Instruction Registry, corresponder ao escopo/harness/agente/surface e passar pelo contrato existente. A validação de formato não prova autenticidade. A CLI resolve o bundle localmente, sem aceitar bundle instrucional do JSON fornecido pelo usuário.
- Guardrails são emitidos como bundle integral no campo `governance`, separado dos itens de tarefa; não podem ser editados ou descartados como item `registry`. A anotação de conteúdo como dados não confiáveis não substitui proteção contra prompt injection no consumidor.
- Até 128 itens, cada um com ID, tipo, origem, versão, conteúdo, estado, razão, prioridade e dependências. Tipos incluem arquivo, documento, módulo, decisão, premissa, pergunta e teste. Nenhum arquivo é aberto a partir da origem informada; conteúdo é snapshot explícito. Espaços e quebras de linha do conteúdo são preservados.

### Seleção e invalidação

1. Apenas ACTIVE pode entrar no pacote. WARM/DROPPED conservam conteúdo em memória para recuperação explícita, mas seu corpo nunca é reinjetado pela composição.
2. Ativação por `transition` exige razão e fingerprint revalidado; upsert não muda estado de item existente. Fonte modificada passa de ACTIVE para WARM e invalida dependentes transitivos. Não excluir guardrails para reduzir orçamento.
3. Dependências precisam existir e formar DAG; ciclos são rejeitados. Dependência WARM/DROPPED/obsoleta bloqueia o dependente, sem ativação implícita.
4. Toda composição recebe fingerprints verificados pelo chamador. Fingerprint ausente ou divergente torna o item ACTIVE obsoleto; nenhuma leitura automática é feita para verificá-lo. A CLI rotula a verificação como `supplied_snapshots_not_disk_verified` porque só conhece o snapshot recebido.
5. Mudança em versão/checksum/invalidation ou qualquer campo do bundle impede composição até `refresh_registry`. Refresh move ACTIVE para WARM para revalidação, sem reaproveitar permissões de outra identidade.
6. Mesma origem/tipo/versão/conteúdo é emitida uma vez com IDs de alias; versões conflitantes da mesma origem são rejeitadas. Prioridade decrescente e ID crescente tornam a seleção reproduzível; dependências entram atomicamente com o item quando cabem no orçamento.

### Orçamento e deltas

Estimativa v1: `ceil(bytes_utf8_do_payload_json / 4)`. O JSON inclui bundle completo, objetivo e itens selecionados. É aproximação, não tokenizer do modelo, custo ou janela efetivamente ocupada. Não é garantia de limite real de tokens; integrações futuras devem medir com o tokenizer apropriado e reservar margem.

Se só governança+objetivo excedem o orçamento, `ready=false` e `payload=null`; nenhum pacote parcial sem regras é enviado. Se apenas itens excedem, ficam em `deferred_ids`, com razão explícita. `ready=true` significa composição possível, não evidência suficiente para executar a tarefa: o consumidor deve revisar itens adiados/obsoletos e pendências da triagem.

Delta exige dois pacotes válidos da mesma tarefa, objetivo, identidade e bundle, sem retroceder revisão. Retorna itens adicionados/alterados, IDs removidos e fingerprints anterior/atual. Aplicação lógica deve remover IDs listados e substituir cada ID dos grupos adicionados/alterados; não concatenar os grupos cegamente. O consumidor deve confirmar o fingerprint anterior antes de aplicar. Delta não é pacote autossuficiente e não elimina histórico já entregue ao modelo.

Telemetria da composição contém apenas contagens, revisão, orçamento, estimativa e método; tokens reais ficam null. Não inclui conteúdo, origem, objetivo ou IDs livres. Não há cálculo de drift semântico nesta fase: somente invalidação verificável de snapshots/bundle; SAME/EXTEND/ROTATE ficam na Fase 3.

### Documentação e integração

Playbook/runbook locais e harness existente foram estendidos sem alterar os princípios dos Papers/Manifestos nem criar cópias paralelas. O Instruction Registry continua sendo a fonte das regras; o Governor não substitui seus layers ou rollout. Sem novas tools MCP, migração, restore, deploy ou ativação de provider. Nenhuma leitura operacional foi necessária para esta fase.

Status da entrega: **local_validated**. Registro remoto do card permanece pendente; integração operacional exige clone atualizado/sanitizado, autenticação real e MCP publicado. Próxima fase, somente mediante autorização: lifecycle SAME/EXTEND/ROTATE e handoffs. Não confundir a conclusão local desta fase com implantação remota.

## 18. Fase 3 — lifecycle e handoffs locais

Card preparado: **[Fase 3 lifecycle e handoffs locais SE-COORD]**. Registro remoto permanece bloqueado pela aprovação por créditos, sem contorno.

- [x] Políticas determinísticas SAME/EXTEND/ROTATE e consultas locais.
- [x] Handoff compacto, persistência local restrita e retomada fail-closed.
- [x] Testes protegidos, documentação e evidência final: **195 passed em 11,62 s**, exit 0, zero tentativas externas detectadas. AST dos quatro arquivos novos válido; `git diff --check` sem erros (avisos de CRLF e acesso ao ignore global). Teste de link simbólico usa simulação, não prova comportamento de junctions reais no Windows.

Limites: nenhuma task/sessão criada automaticamente; sem compactação nativa, troca de modelo, deploy ou retomada automática de mutações.

### Implementação e segurança

`engineering_session_service.py` decide SAME para mesma tarefa/objetivo/domínios, EXTEND somente com dependência explícita da tarefa anterior, ROTATE nos demais casos, mudança de identidade ou pressão de orçamento. São recomendações lógicas, não comandos de sessão do provedor. `status`, `context`, `why` e `model` não revelam corpos de itens; execução/testes/modelo reais permanecem desconhecidos.

`engineering_handoff_service.py` exporta referências selecionadas (origem, versão, fingerprint), objetivo e notas revisadas, sem corpos dos snapshots nem bundle instrucional. Exige revisão explícita, limita o documento a 32 KiB e rejeita alguns padrões comuns de segredos. O filtro é heurístico, não DLP: objetivo, nomes de arquivos e notas também podem conter dados sensíveis e exigem revisão humana.

Persistência somente de contexto de repositório em `.ai/handoffs/<nome>.json`, com nome restrito, checagem de confinamento, recusa de links simbólicos e criação exclusiva sem sobrescrever. Não é defesa contra alteração concorrente maliciosa do filesystem. Contexto empresarial não pode ser salvo neste armazenamento sem autenticação. Arquivos não são cifrados: manter fora de commits/compartilhamentos e excluir manualmente após consumo/revisão; não há retenção automática nem expiração temporal implementada.

Checksum detecta corrupção acidental, não autoria: quem altera o arquivo pode recalculá-lo. Retomada verifica schema, checksum, identidade, registry atual e fingerprints fornecidos pelo chamador. A CLI também verifica tarefa/objetivo. Nenhum arquivo referenciado é aberto, nenhuma permissão antiga é restaurada e nenhum conteúdo é executado. Pacotes e identidade devem vir de chamadores confiáveis; validação estrutural não autentica usuário nem prova origem.

`scripts/squad_engineering.py` oferece cinco intenções locais (`status`, `context`, `why`, `model`, `handoff`) e auxiliares `decide`/`resume`. Não instala slash commands nativos. Resolve registry atual e reconstrói Working Set a partir do JSON fornecido; a verificação é `supplied_snapshots_not_disk_verified`. Integração operacional permanece pendente, com clone atualizado/sanitizado e identidade autenticada.

Status: **local_validated**. Card remoto permanece pendente pelo bloqueio de aprovação já registrado. Nenhum deploy, restore, alteração operacional ou checkpoint real exportado nesta validação; arquivos de teste usam diretórios temporários. Próxima entrega: Fase 4, QA e escalonamento, mediante autorização.

## 19. Fase 4 — Quality Gate local

Continuidade autorizada: integrar CLI ao mesmo service, sem novo gate paralelo. Checklist adicional no mesmo card: [x] adapter QA/status/context; [x] testes de entrada e regressão (**242 passed em 11,80 s**, zero tentativas externas detectadas); [x] documentação final. Registro remoto continua pendente, sem contorno do bloqueio.

Card preparado: **[Fase 4 QA e escalonamento SE-COORD]**. Registro remoto pendente pelo bloqueio de aprovação, sem contorno.

Continuidade seguinte autorizada: card preparado **[Fase 5 Model Broker local SE-COORD]**, registro remoto igualmente pendente. Checklist do primeiro recorte: [x] política lógica e preferências; [x] adapter manual na CLI; [x] testes protegidos/documentação: **261 passed em 10,88 s**, zero tentativas externas detectadas (19 casos novos). Sem descoberta remota, troca automática, preços ou novos providers nesta etapa.

Primeiro recorte da Fase 5: `EngineeringModelBrokerService` puro, vinculado ao Working Set/pacote, integrado ao comando `model`. Sugere ECONOMY apenas para documentação simples de baixo risco, DEEP para risco/complexidade altos ou revisões arquiteturais/DBA, STANDARD como padrão. Duas falhas declaradas de implementação podem sugerir DEEP para revisão, sem autorizar retry. Falha de outra natureza, contexto incompleto ou ambiguidade suspendem a sugestão. Preferência explícita de perfil é preservada, com aviso se inferior à sugestão técnica.

Limites: perfis são heurísticas locais, não classes verificadas de modelos comerciais. Provider/modelo/esforço permanecem null e capacidades não verificadas. Não estima preços/economia nem altera runtime. Catálogo verificado, mapeamento de modelos disponíveis e adapter autenticado do runtime continuam pendentes; portanto a Fase 5 completa não está encerrada. Nenhuma credencial ou catálogo entra em checkpoints.

- [x] Contrato de evidência vinculado à tarefa, identidade e fingerprint do pacote.
- [x] Gate determinístico e recomendações limitadas de recuperação; primeiro baseline: 232 testes aprovados.
- [x] Baseline protegido final: **232 passed em 11,92 s**, zero tentativas externas detectadas, sem warnings de testes. AST dos dois arquivos novos válido; diff check documental/runner sem erros. São 37 casos novos do gate.

Escopo: avaliação local de evidências declaradas, sem executar testes, mutações, providers ou deploy.

Status do núcleo: **local_validated**. Card remoto e integração operacional autenticada continuam pendentes. A CLI agora consome o gate explicitamente via `qa` e evidência opcional em `status`/`why`. Não foi atualizado o clone nem alterado qualquer banco de dados.

Contrato `QualityEvidence` e política `QualityPolicy` no service puro `engineering_quality_gate_service.py`. Requisitos, diff limitado, testes, regressão e documentação exigem PASS explícito e referências não vazias. Revisões de arquitetura/DBA derivam da triagem; tenant/policy é obrigatório em contexto empresarial ou de arquitetura. Contexto incompleto e ambiguidade bloqueiam. Identidade, tarefa e pacote divergentes rejeitam evidências. Referências são declaradas, não abertas nem autenticadas; fingerprints não são assinaturas.

Falhas de segurança/efeito de mutação incerto interrompem; requisito retorna ao coordenador; ambiente exige reparo sem escalar modelo; falha de teste exige diagnóstico. Implementação recomenda diagnóstico antes de retry manual: padrão 2 retries (configurável 0–5), depois 1 revisão especializada (0–3), então interrupção humana. Contadores são informados pelo chamador, não persistidos nem incrementados pelo service; um adapter autenticado futuro deve manter o histórico para impedir reinicialização dos limites.

Resultado local pode ser `local_validated`, nunca autorização operacional. Alvo operacional com declaração PASS ainda retorna `remote_validation_pending`: falta verificação autenticada independente. FAIL operacional bloqueia. `done` está reservado no contrato e não é emitido neste adapter. O service não executa testes, não repete mutações e não chama agentes/modelos. A CLI expõe `evidence_binding` em context/qa e exige correspondência dos fingerprints recebidos. Status/why só avaliam QA quando recebem evidência; handoff/resume não transportam aprovação. Exit QA 3 indica bloqueio e 4 pendência remota, mesmo com avaliação tecnicamente bem-sucedida. Não há novos endpoints MCP ou autorização empresarial.
