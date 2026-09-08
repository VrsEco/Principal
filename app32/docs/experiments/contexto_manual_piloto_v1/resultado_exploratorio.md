# Piloto executado — resultado exploratório

## Atualização: telemetria local recuperada

Esta atualização supera as pendências históricas de tokens/modelo abaixo, mas não a falta de revisão cega nem os desvios do experimento. A leitura foi restrita aos JSONL das duas tarefas, sem credenciais ou alteração de configuração. Cada registro contém um turno, um token_usage_record e um token_count; contagens de turno, thread e última resposta coincidem. Os turn_ids correspondem às tarefas avaliadas.

| Campo observado | Baseline | Candidate |
|---|---:|---:|
| Modelo em turn_context | gpt-6-astra | gpt-6-astra |
| Esforço em turn_context | low | low |
| Provider em session_meta | openai | openai |
| Versão da CLI em session_meta | 0.153.4 | 0.153.4 |
| Input tokens | 31873 | 30233 |
| Output tokens | 635 | 592 |
| Total tokens | 32508 | 30825 |
| Cached input tokens | 14976 | 14976 |
| Cache write input tokens | 0 | 0 |
| Reasoning output tokens | 32 | 0 |

O total registrado é exatamente input+output. Não somar cached_input_tokens ou reasoning_output_tokens novamente. Input diminuiu 1640 tokens (5,1454%); total diminuiu 1683 tokens (5,1772%). São diferenças aritméticas observadas neste par, não efeito causal demonstrado, faturamento ou redução do uso percentual do plano. Modelo nominal/esforço/CLI coincidem; snapshot interno do modelo e equivalência integral das instruções/permissões do host não foram estabelecidos.

Fontes locais consultadas (não copiar o conteúdo integral, que contém contexto de sessão):

- `C:\Users\mff20\.codex\sessions\2026\09\07\rollout-2026-09-07T21-36-55-01a07e72-4cf5-75e2-9c13-0509a8b2dec5.jsonl`
- `C:\Users\mff20\.codex\sessions\2026\09\07\rollout-2026-09-07T21-36-49-01a07e72-37ca-7393-99eb-d8e7e2ceb0b4.jsonl`

Próximo passo necessário para conclusão mais forte: revisão independente e, mediante nova autorização de execuções, pares sequenciais adicionais em tarefas variadas. Não converter a revisão não cega em PASS independente. A ficha original permanece como template pendente; não preencher fingerprints de equivalência integral com suposições apenas para liberar o comparador. A comparação controlada formal continua pendente, mas a ausência de telemetria por turno foi resolvida.

## Histórico anterior à recuperação da telemetria

O usuário autorizou explicitamente a criação das duas tarefas. Pacotes verificados contra integridade.json antes do envio, sem histórico desta conversa ou referências aos resultados da outra variante. Destino projectless, apropriado à análise de fontes fornecidas sem checkout. Modelo e esforço não foram sobrescritos: ambos usaram o padrão configurado do aplicativo, cuja equivalência efetiva não foi confirmada pela resposta das ferramentas.

| Variante | Tarefa | Turno | Duração reportada pelo aplicativo |
|---|---|---|---|
| candidate | 01a07e72-37ca-7393-99eb-d8e7e2ceb0b4 | 01a07e72-3aee-7cc1-a108-5c7cd393903c | 18804 ms |
| baseline | 01a07e72-4cf5-75e2-9c13-0509a8b2dec5 | 01a07e72-5070-7e70-9857-86f968f8ba84 | 32770 ms |

Ordem sorteada: candidate, baseline. Ambas concluíram sem erro reportado. Houve sobreposição temporal das execuções: baseline iniciou antes de candidate terminar. Isso diverge da execução sequencial prevista e impede atribuir diferença de duração à seleção de contexto. Não calcular redução de latência como ganho causal.

## Leitura preliminar das respostas

As duas respostas abordaram fingerprints, validações, ausência de métricas, baseline zero, qualidade, códigos 0/2/3/4 e limites de evidência/custo. Candidate ficou centrada nos dois arquivos necessários; baseline acrescentou observações sobre catálogo/Broker. A inspeção dos turnos não mostrou chamadas de ferramentas dos agentes; há apenas um marcador de criação da tarefa e a resposta (além de um item de raciocínio sem resumo na baseline).

Essa leitura foi feita pelo coordenador que conhece as variantes; **não é QA cego independente**. Manter quality=unknown até a revisão prevista no roteiro. Não usar a síntese como substituta da avaliação de todos os critérios.

## Dados indisponíveis

- input_tokens/output_tokens: null; ferramentas de acompanhamento não retornaram uso por turno.
- Modelo/versão/esforço efetivos: não confirmados; usar padrão de criação não prova equivalência observada.
- Identidade/runtime fingerprints: pendentes; não preencher apenas para a CLI aceitar.
- Economia financeira, estatística ou causal: não demonstrada.

A duração acima é do turno, medida pelo aplicativo, não cronômetro manual nem benchmark isolado. O comparador não foi executado: faltam equivalência de runtime e métricas reais. Nenhuma configuração, dado empresarial, banco ou código foi alterado pelas tarefas conforme histórico disponível.

## Próxima ação

## Revisão técnica posterior — não cega

Coordenador confrontou as respostas integrais com os quatro arquivos. SHA-256 das fontes atuais coincide com o manifesto congelado, evitando revisar contra código diferente. Os sete critérios técnicos foram atendidos nas duas respostas:

| Critério congelado | Baseline | Candidate |
|---|---|---|
| Quatro fingerprints e variantes | atendido | atendido |
| Entrada inválida versus qualidade desconhecida | atendido | atendido |
| Qualidade PASS nos dois lados e baseline positivo | atendido | atendido |
| Estimativa versus uso reportado; null não vira zero | atendido | atendido |
| Exits 0, 2, 3, 4 | atendido | atendido |
| Sem alegação de custo/causalidade comprovados | atendido | atendido |
| Sem ferramentas/mutações observadas nem comportamento inventado | atendido no histórico disponível | atendido no histórico disponível |

Contagem reproduzível por separação em whitespace do texto integral retornado por read_thread: baseline 313 palavras; candidate 316. Ambas ficam abaixo do limite de 350 com esse método, que inclui marcadores Markdown isolados.

Ressalva editorial na candidate: a expressão “ambas as qualidades não são pass” pode soar ambígua isoladamente; o primeiro item exige PASS nas duas execuções, o que esclarece a regra. Não foi identificada falha funcional na explicação completa. A baseline traz informação adicional sobre Broker/catálogo, sustentada pelos arquivos extras, mas não necessária à resposta principal.

Conclusão desta revisão: **conteúdo técnico satisfatório nas duas respostas**. Isso não substitui QA cego/humano independente do protocolo, nem valida equivalência de runtime ou economia. O campo quality da ficha pendente continua unknown até a revisão prevista. Não houve nova execução, retentativa ou alteração nas respostas avaliadas.

## Pendência final do piloto

Revisão humana das respostas nas duas tarefas, seguida de verificação de modelo/esforço e relatório de uso por turno se o runtime os disponibilizar. Sem essas informações, encerrar como piloto qualitativo exploratório, não como comprovação de economia. Não repetir ou criar novas tarefas automaticamente.
