# Teste sintético de redução de contexto v3 — três pares

Status: concluído. Evidência exploratória da seleção de contexto em tarefas de leitura; não é benchmark de produção, custo ou qualidade geral.

## Protocolo

- Três pares sequenciais independentes, mesmo modelo observado `gpt-5.5` e esforço `low` em todos os seis turnos.
- Ordem alternada: P1 baseline→candidate; P2 candidate→baseline; P3 baseline→candidate.
- Solicitação e fonte relevante idênticas dentro de cada par; rótulo P1/P2/P3 muda entre pares para evitar reutilizar exatamente o mesmo prompt.
- Candidate: 815 caracteres; baseline: 11807 caracteres, incluindo 24 módulos sintéticos explicitamente não relacionados. Redução textual específica: 93,10%.
- Sem ferramentas, rede, banco, arquivos locais, mudanças de código ou dados empresariais. O runtime anteriormente recusou envio de código-fonte local, então todas as fontes deste teste são sintéticas.

## Telemetria por turno

| Par | Ordem | Baseline total | Candidate total | Redução total | Cache baseline/candidate |
|---|---|---:|---:|---:|---:|
| P1 | baseline→candidate | 24417 | 21970 | 10,02% | 1408 / 1408 |
| P2 | candidate→baseline | 24454 | 21515 | 12,02% | 11648 / 1408 |
| P3 | baseline→candidate | 24425 | 21911 | 10,29% | 11648 / 11648 |
| **Média** | alternada | **24432,00** | **21798,67** | **10,78%** | não agregar como consumo |

Média observada: **2633,33 tokens a menos por turno** no candidate. Mediana de redução: 10,29%. A variação entre pares foi 10,02%–12,02%. `total_tokens` é input+output; não somar `cached_input_tokens` ou `reasoning_output_tokens` novamente.

## Qualidade técnica observada

As seis respostas ficaram entre 100 e 145 palavras, abaixo do limite de 180. Todas cobriram baseline/candidate, hashes/condições de comparação, percentual desconhecido e códigos 0/2/3/4; nenhuma mencionou as fontes irrelevantes como regra válida. Esta é inspeção técnica do coordenador, não revisão cega independente.

## Limitações

- P2 mostra cache desigual; não inferir preço, custo ou economia financeira a partir de tokens ou cache.
- Mesmo modelo/effort nominal não prova snapshot interno, equivalência total de runtime nem resultado em tarefas reais.
- O mínimo observado do runtime ainda foi aproximadamente 21–22 mil tokens; reduzir o prompt do usuário não reduz esse envelope.
- Três pares sintéticos não comprovam a meta de 35–60%, causalidade ou qualidade em correções, arquitetura, MCP, multi-tenancy ou produção.

## Conclusão operacional

Para tarefas baixas de leitura delimitada, enviar somente fontes relevantes reduziu em torno de **10,78%** o total de tokens neste experimento. O próximo passo de maior retorno não é anexar mais documentos: é construir resumos versionados e recuperar trechos somente quando necessários. Qualquer experimento com código real deve usar ambiente autorizado que permita esse contexto, com revisão humana independente e nova autorização explícita.
