# Playbook — Copiloto de Fluxo BPMN

Classe: Playbook
Atualizado em: 2026-08-01

## 1. Quando usar

Use este playbook quando o pedido envolver:
- análise de fluxo BPMN;
- descoberta de automação por atividade;
- sugestão de conexão APP32/MCP/API;
- revisão de gaps entre lane, artefatos e contrato;
- configuração de POP, FORM, CHECK, IA, IN ou OUT;
- definição de como uma atividade chega ao usuário no Portal de Processos.

## 2. Sequência oficial

1. carregar processo e diagrama no tenant correto, sempre validando `company_id`;
2. analisar lanes, atividades e gateways;
3. identificar POPs, FORM, CHECK, IA, IN, OUT e contratos já existentes, sem presumir que toda atividade exige POP;
4. verificar assignment, SLA, completion rules e dados exigidos por atividade;
5. propor artefatos, automação ou conexão por atividade;
6. simular a execução da instância e os gates de conclusão;
7. simular a descoberta no Portal e no Meu Trabalho;
8. sinalizar explicitamente o que ainda depende de revisão humana.

## 3. Regra de resposta

Sempre separar em quatro blocos:
- diagnóstico do fluxo;
- artefatos e dados necessários por atividade;
- oportunidades de automação APP32/MCP e integração externa;
- pendências de intervenção humana.

## 4. Regra de linguagem

Nunca apresentar sugestão como fato consumado.

Preferir expressões como:
- “o copiloto recomenda”
- “há aderência para”
- “o contrato rascunho sugerido é”
- “a publicação continua dependendo de validação humana”

## 5. Escalonamento interno

- semântica BPMN/gateway -> `@ARQUITETO`
- sugestão IA/MCP/API -> `@AI_ENGINEER`
- surface/capability/permissão -> `@BACKEND_API`
- persistência, versionamento e multi-tenancy -> `@DBA`
- editores, Portal e shell da instância -> `@FRONTEND`
- completion rules, assignment e runtime -> `@BACKEND_SERVICE`
- regressão, isolamento tenant e E2E -> `@QA_AUTOMATION`

## 6. O que não fazer

- não automatizar layout fino;
- não publicar contrato sem humano;
- não ocultar risco de gateway;
- não usar lane como única verdade de executor real.
- não embutir os artefatos como conteúdo informal dentro da activity;
- não concluir atividade por clique quando houver artefato obrigatório pendente;
- não colocar execução automática de IA/IN/OUT na fila pessoal sem gate ou exceção;
- não criar URL pública permanente como identidade do formulário ou checklist;
- não persistir segredo de integração no JSON do artefato.

## 7. Checklist de desenho por atividade

Para cada elemento executável, registrar:

1. **trabalho** — nome, objetivo, lane e criticidade;
2. **responsabilidade** — colaborador, equipe, papel e regra de fallback;
3. **artefatos** — tipos, ordem, obrigatoriedade e versão;
4. **dados** — entradas, saídas, variáveis da instância e evidências;
5. **execução** — humana, IA, integração ou composição híbrida;
6. **conclusão** — completion rule verificável em service;
7. **exceção** — retry, fallback humano, aprovação e escalonamento;
8. **visibilidade** — Portal, Meu Trabalho, timeline e responsáveis autorizados.

## 7.1 Checklist transversal SIPOC do processo

Antes do checklist por atividade, aplicar o contrato do processo nos dois sentidos:

1. **progressivo:** gatilho → fornecedores → entradas → transformação/atividades → saídas → clientes/recebedores → objetivo;
2. **regressivo:** objetivo → saídas necessárias → transformações suficientes → entradas requeridas → fornecedores adequados → gatilho coerente.

Confirmar que:

- objetivo descreve o resultado pretendido e não repete apenas o nome da saída;
- cada caminho final entrega uma saída intencional a um recebedor;
- nenhuma atividade existe sem contribuir para uma saída necessária;
- entradas e fornecedores são suficientes para executar a transformação;
- exceção, rejeição ou item fora do corte atual possui destino explícito, como classificação para reanálise futura;
- SIPOC e BPMN permanecem transversais, sem cardinalidade `1:1` artificial.

## 7.2 Condução da maturação da modelagem

Usar `process-modeling-official-v1.0` quando a pergunta deixar de ser apenas “o fluxo está válido?” e passar a ser “qual é o estado metodológico da modelagem e o que falta para avançar?”.

1. identificar `company_id`, `process_id` e versão/draft BPMN;
2. antes do AS-IS, confrontar evidências e transcrições com Arquitetura, Premissas, SIPOC, Fluxo e Artefatos, gerando a matriz de cobertura;
3. classificar cada elemento como `defined`, `hypothesis`, `pending` ou `not_applicable`, governando responsável, revisão e impacto das pendências;
4. determinar o estado da jornada pela evidência disponível;
5. avaliar contrato, aderência, semântica, executabilidade, governança e aprendizado;
6. separar gaps metodológicos, técnicos e operacionais;
7. indicar o gate pendente e uma próxima ação;
8. nunca converter cobertura, XML válido ou publicação em score de maturidade.

Apresentar separadamente maturidade da modelagem, maturidade da implantação e desempenho operacional.

### Digestão e classificação das fontes

O ponto de partida pode ser áudio, texto, documento legado ou combinação. Preservar proveniência, transcrever quando necessário, extrair declarações atômicas e avaliar vigência antes de encaixar o conteúdo na metodologia. Material antigo é evidência `legacy` até confirmação.

Classificar por contrato de entrega e execução: grande entrega permanente = macroprocesso; transformação recorrente com contrato próprio = processo; microentrega/mudança de estado/handoff = atividade; instrução de como executar = passo de POP. Checklist verifica, formulário captura, indicador mede, regra decide, evento dispara/sinaliza, dado/documento entra/sai/evidencia e recurso habilita. Uma frase pode produzir vários elementos vinculados.

### Conversa padrão

1. mostrar o quadro curto das seis dimensões;
2. selecionar a dimensão com maior impacto estratégico e explicar o motivo em uma frase;
3. perguntar uma coisa por vez;
4. sintetizar após no máximo três perguntas;
5. pesquisar somente se a referência puder mudar a decisão;
6. encerrar com conclusão, contribuição estratégica, novo status e uma próxima ação.

Não mostrar o diagnóstico técnico completo, a lista de agentes ou todos os gaps de uma vez. Abrir detalhes apenas por solicitação, divergência ou auditoria.

## 8. Checklist por tipo de artefato

- `POP`: a atividade realmente exige instrução detalhada? Quando várias atividades usam a mesma instrução, existe uma única definição compartilhada e título com todos os códigos/nomes?

## 8.1 Divisão de atuação entre Squads

- Squad Cliente evidencia e valida o AS-IS; não publica nem redefine estrutura sozinho.
- Squad Versus revisa fronteira, desenha TO-BE e valida o método.
- Consultor ou responsável autorizado decide a publicação.
- Engenharia corrige capability, cardinalidade, importação ou defeito do APP32.

O responsável pelo processo não deve ser inferido das lanes. Lanes representam times ou papéis executores.
- `FORM`: schema, validações, condicionais e destino dos dados estão definidos?
- `CHECK`: itens obrigatórios, evidências, N/A e regra de reprovação estão definidos?
- multipapel: o artefato deve ser isolado por atividade ou compartilhado na instância?
- compartilhado: cada vínculo possui fase, responsável, gate e permissão explícita de aprovação final?
- IA compartilhada: contexto comum e chamadas individuais auditáveis estão separados?
- `IA`: AI Task/Gateway, tools, autonomia, threshold e fallback estão definidos?
- `IN`: origem, schema, correlação, idempotência e erro estão definidos?
- `OUT`: destino, payload, retry, idempotência e confirmação estão definidos?

## 9. Validação da experiência ponta a ponta

Antes de recomendar concretização, validar o cenário completo:

```text
modelo publicado
→ instância iniciada com snapshot
→ atividade atribuída
→ usuário encontra a atividade no Portal/Meu Trabalho
→ shell abre no elemento correto
→ artefatos são executados e persistidos
→ completion rules são satisfeitas
→ BPMS move o token
→ timeline e evidências permanecem auditáveis
```

O card do Portal representa a atividade acionável. A instância fornece o contexto. Automações sem intervenção humana aparecem apenas como andamento ou histórico.

## 10. Evidências mínimas para avançar à implementação

- mock-up validado da modelagem, dos editores, da instância e do Portal;
- SPEC com modelo, estados, RBAC e boundaries aprovados;
- plano de compatibilidade com `ProcessRoutine`/POP atual;
- matriz de migração e feature flag;
- cenários E2E para POP, FORM, CHECK, combinação dos três, IA, IN, OUT e fallback humano;
- testes negativos de cross-tenant e tentativa de contornar completion rules.

## 11. Uso de cores no modelador

- usar o padrão do tipo como ponto de partida: tarefa azul, gateway âmbar, início verde, intermediário laranja e fim vermelho;
- personalizar apenas quando a cor melhorar a leitura do fluxo;
- não usar cor como única representação de regra, responsabilidade, criticidade ou estado;
- manter os artefatos nas cores canônicas e vinculados por associação BPMN;
- validar contraste e legibilidade antes de publicar;
- preservar no runtime a cor do modelo e representar execução por overlay, contorno ou badge.
- validar no Book/PDF que todos os marcadores externos mantêm cor de contorno, preenchimento e rótulo correspondente ao tipo.

Na maturação de POP/Checklist/Formulários:

- usar `artifact_type`, vínculo, definição, versão e status como evidência canônica;
- usar cor e marcador somente como apoio visual;
- verificar necessidade, configuração, obrigatoriedade, completion policy, evidência e contribuição ao objetivo/risco;
- classificar como gap divergência entre Modeler, editor, runtime ou Book;
- não elevar a maturidade pela simples presença do marcador.

## 12. Detalhe do processo e artefatos

- manter todos os acessos principais em uma única linha: SIPOC, Recursos, Fluxo, POP, Formulários, Checklists, IA, Rotinas e Indicadores;
- em telas estreitas, usar rolagem horizontal em vez de quebrar a navegação em múltiplas linhas;
- usar Formulários e Checklists como visões de consulta e edição; criar/vincular novos artefatos pelo Modeler;
- configurar AI Task e AI Gateway no Modeler, preservando o contexto do elemento BPMN;
- validar vazio, carregado, rascunho, publicado e arquivado, sem expor dados de outra empresa.

## 12. Criação e edição de artefatos no modelador

Na entrega `2.3 Fluxo`, adicionar o marcador e o vínculo para registrar que a atividade necessita do artefato, podendo manter sua definição como pendente. Na entrega `2.4 Artefatos do Fluxo`, abrir o editor especializado e desenvolver conteúdo, versão, obrigatoriedade, completion policy e evidência. Não tratar o marcador como artefato concluído.


- adicionar o marcador com `+ Artefato` sem interromper a modelagem nem abrir outra tela;
- configurar posteriormente com dois cliques no marcador POP, FORM, CHECK, IA, IN ou OUT;
- manter visíveis no próprio diagrama os artefatos vinculados à atividade;
- não criar uma visão geral paralela quando os marcadores e seus editores diretos já atendem à navegação.

## 13. Padrão de tela dos editores

- manter o cabeçalho compacto, com cor e identificação inequívoca do artefato;
- exibir retorno direto ao Modeler e ações de salvar/publicar no mesmo nível;
- reservar a área maior para conteúdo e contrato; usar a lateral para vínculo BPMN e regras;
- preservar a ordem, os rótulos e o comportamento das ações entre FORM, CHECK, IN e OUT;
- validar em desktop e largura reduzida, sem rolagem horizontal nem perda de contexto.
- ao abrir POP pelo diagrama, usar o modo focado e retornar pelo botão `Voltar ao Modeler`;
- no Modeler, preservar o canvas como área dominante e manter cabeçalho/ribbon em altura compacta.

## 14. Publicar após aprovação

1. confirmar novamente `company_id`, `process_id` e versão aprovada;
2. montar um pacote com perfil, XML BPMN, POP e definições/vínculos dos artefatos;
3. chamar `publish_approved_process_modeling_package_tool` somente com `human_gate_confirmed=true`;
4. reler o retorno e validar IDs, versões, status, `execution_scope` e `phase_key`;
5. não repetir cadastros manualmente: a chamada é idempotente para o mesmo conteúdo.
