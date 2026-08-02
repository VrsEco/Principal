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
3. identificar POPs, FORM, CHECK, IA, IN, OUT e contratos já existentes;
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

## 8. Checklist por tipo de artefato

- `POP`: existe versão publicada e a evidência de leitura/aceite está definida?
- `FORM`: schema, validações, condicionais e destino dos dados estão definidos?
- `CHECK`: itens obrigatórios, evidências, N/A e regra de reprovação estão definidos?
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

## 12. Detalhe do processo e artefatos

- manter todos os acessos principais em uma única linha: SIPOC, Recursos, Fluxo, POP, Formulários, Checklists, IA, Rotinas e Indicadores;
- em telas estreitas, usar rolagem horizontal em vez de quebrar a navegação em múltiplas linhas;
- usar Formulários e Checklists como visões de consulta e edição; criar/vincular novos artefatos pelo Modeler;
- configurar AI Task e AI Gateway no Modeler, preservando o contexto do elemento BPMN;
- validar vazio, carregado, rascunho, publicado e arquivado, sem expor dados de outra empresa.

## 12. Criação e edição de artefatos no modelador

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
