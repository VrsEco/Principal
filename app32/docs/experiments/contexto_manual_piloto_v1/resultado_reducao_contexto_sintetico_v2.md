# Teste sintético de redução de contexto v2

Status: concluído; evidência exploratória de mecânica de contexto, não benchmark de produção, custo ou qualidade geral.

## Desenho

- Mesmo modelo observado: `gpt-5.5`; mesmo esforço: `low`.
- Duas tarefas projectless independentes, sem ferramentas, comandos, rede, banco ou alterações.
- Solicitação idêntica e limite de 180 palavras: explicar regras sintéticas de comparação de medições e códigos 0/2/3/4.
- Candidate recebeu fonte relevante e envelope mínimo: 794 caracteres.
- Baseline recebeu a mesma fonte mais 24 módulos sintéticos declarados como não relacionados: 11786 caracteres.
- Ordem sorteada e executada sequencialmente: candidate, baseline. A ordem é fator de confusão para cache; não medir latência ou custo a partir deste par.
- O envio anterior de código-fonte local foi recusado pelo controle de risco do runtime. Não houve contorno: este teste usa apenas fontes sintéticas.

## Telemetria por turno

| Métrica | Baseline | Candidate | Variação candidate vs. baseline |
|---|---:|---:|---:|
| Caracteres enviados | 11786 | 794 | -93,26% |
| Input tokens | 24180 | 21672 | -10,37% |
| Cached input tokens | 3456 | 1408 | não comparar como consumo adicional |
| Output tokens | 223 | 229 | +2,69% |
| Reasoning output tokens | 23 | 16 | -30,43% |
| Total tokens | 24403 | 21901 | **-10,25%** |

Diferença observada de total: **2502 tokens**. O total registrado equivale a input + output; `cached_input_tokens` e `reasoning_output_tokens` são subcampos de telemetria e não devem ser somados outra vez. A telemetria foi lida dos JSONL locais de cada tarefa, sem expor seu conteúdo integral.

## Qualidade observada

As duas respostas identificaram as condições de comparabilidade, as condições para percentual desconhecido e os quatro códigos de saída. Ambas ignoraram as fontes sintéticas irrelevantes. Não houve revisão cega independente; portanto este item é inspeção técnica, não aprovação formal de QA.

## Interpretação

Reduzir 93,26% do texto específico do usuário reduziu 10,25% dos tokens totais neste turno. Isso indica que havia aproximadamente 21–22 mil tokens de envelope/overhead do runtime e instruções que este teste não reduziu. É coerente com a estratégia de reduzir contexto, mas não estabelece uma taxa fixa: outro modelo, histórico, cache, ferramentas, complexidade ou ordem pode produzir resultado diferente.

Baseline teve mais tokens em cache porque executou depois; se o cache recebe preço diferenciado no plano, esta métrica não permite calcular custo sem tabela de cobrança e sem a semântica comercial confirmada. Não inferir economia financeira, causalidade plena ou meta de 35–60% a partir deste único par.

## Próximo experimento recomendado

Usar três pares sequenciais e alternar ordem (baseline/candidate, candidate/baseline, baseline/candidate), mantendo modelo/esforço e uma tarefa de mesma classe. Registrar telemetria por turno, revisão cega e cache separadamente. Não executar novos pares sem autorização explícita.
