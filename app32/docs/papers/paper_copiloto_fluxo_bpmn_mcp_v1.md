# Paper — Copiloto de Fluxo BPMN via MCP

Status: em evolução  
Classe: Paper
Atualizado em: 2026-08-01

## 1. Tese

O Fluxo BPMN do APP32 não deve ser automatizado como desenho livre por agentes.  
Ele deve evoluir como **copiloto de modelagem**, onde:

- o **BPMN continua sendo a fonte canônica**;
- o **MCP lê, critica e sugere**;
- a **intervenção humana continua obrigatória** para semântica final, layout e publicação.

## 2. Problema

Fluxo possui:
- gateways com múltiplas saídas e reconvergências;
- lanes e swimlanes com responsabilidade visual;
- atividades com potencial de POP, contrato de execução, automação ou integração;
- dependência de julgamento humano para fechamento do desenho.

Sem uma camada intermediária, a IA tende a:
- simplificar demais a semântica;
- confundir layout com execução;
- sugerir automações sem governança suficiente.

## 3. Direção proposta

O copiloto de fluxo deve operar em três frentes:

1. **análise estrutural do BPMN**  
   nós, edges, lanes, gateways e eventos;

2. **análise operacional da atividade**  
   POP, contrato de execução, lane, executor e oportunidade de automação;

3. **sugestão de conexão/automação**  
   dentro do APP32, via MCP interno ou via API/app externo na internet.

## 4. Princípio central

> O copiloto não publica o fluxo.  
> O copiloto prepara a decisão humana com contexto técnico e rascunhos governados.

## 5. O que o copiloto deve sugerir

- abrir formulário/tela do APP32;
- executar MCP task governada;
- disparar API/webhook externo;
- usar AI Task / AI Gateway quando a semântica permitir;
- manter tarefa humana quando o risco ou a ambiguidade ainda forem altos.

## 6. Limite inegociável

Automação de Fluxo não substitui:
- decisão de split/join;
- organização visual fina;
- confirmação de lane/executor;
- validação final de publicação.

## 7. Decisão sobre agentes

Neste momento, **não é necessário criar um agente novo**.  
O tema cabe na combinação:

- `@ARQUITETO` para boundary, governança e semântica do fluxo;
- `@AI_ENGINEER` para copiloto MCP, sugestões de automação e integração;
- `@BACKEND_API` para surface, contrato e publicação MCP.

Se no futuro surgir operação recorrente e autônoma de auditoria massiva de BPMNs, aí sim pode nascer um agente especializado.

## 8. Evolução da tese: atividade como ponto de composição

Uma atividade BPMN não deve incorporar formulário, checklist, POP ou integração como conteúdo solto dentro do próprio elemento. Ela deve funcionar como **ponto de composição** de artefatos externos, especializados e versionados.

Família conceitual proposta:

- `POP` — orientação operacional e conhecimento;
- `FORM` — coleta estruturada de dados;
- `CHECK` — verificação, aceite e evidência item a item;
- `IA` — execução ou decisão assistida pelo Sapiens;
- `IN` — conexão de dados recebidos;
- `OUT` — conexão de dados enviados.

Os artefatos podem ser usados isoladamente ou combinados na mesma atividade. A atividade continua representando **o trabalho a executar**; os artefatos representam **instruções, dados, controles e conexões necessários para concluí-lo**.

## 9. Linguagem visual no BPMN

A evolução deve preservar a linguagem já compreendida no APP32 para o POP:

- artefato externo ligado à atividade por associação BPMN pontilhada;
- mesma base geométrica/visual do artefato atual;
- cor e nome próprios para distinguir `POP`, `FORM`, `CHECK`, `IA`, `IN` e `OUT`;
- clique no artefato abre diretamente seu editor especializado;
- uma atividade pode exibir um, vários ou todos os artefatos, sem inflar o retângulo da tarefa.

O BPMN permanece legível e padronizado; a riqueza operacional fica nos objetos associados.

## 10. Editores especializados e dados reutilizáveis

Cada tipo precisa de tela própria, baseada no padrão atual do editor de POP, mas adaptada à sua semântica:

- `POP`: conteúdo, passos, mídia, versões e POP para IA;
- `FORM`: seções, campos, validações, regras condicionais e destino dos dados;
- `CHECK`: itens, obrigatoriedade, evidências, reprovação e aceite;
- `IA`: task/gateway, objetivo, prompt/contrato, tools MCP, autonomia, confiança e fallback humano;
- `IN`: origem, autenticação, schema, mapeamento, idempotência e política de erro;
- `OUT`: destino, autenticação, payload, gatilho, retry e confirmação de entrega.

Formulários e checklists devem ser persistidos no banco por tenant (`company_id`), versão, instância e execução da atividade. Não devem depender de uma URL pública como identidade. O endereço eletrônico é apenas uma rota de acesso ao runtime autenticado; links assinados e temporários ficam reservados a participantes externos autorizados.

## 11. Instância como workspace operacional

Quando uma instância estiver ativa, a tela de execução deve reunir:

- BPMN vivo com a atividade atual destacada;
- contexto da instância e SLA;
- lista dos artefatos vinculados à atividade atual;
- progresso individual de cada artefato;
- ação principal coerente com o próximo requisito pendente;
- bloqueio de conclusão enquanto artefatos obrigatórios não estiverem válidos;
- histórico de leitura, respostas, evidências, integrações e decisões de IA.

O runtime deve criar registros de execução dos artefatos a partir de uma versão publicada e imutável da definição. Assim, uma alteração futura do modelo não modifica retroativamente instâncias já iniciadas.

## 12. Descoberta do trabalho no Portal de Processos

O Portal de Processos deve contextualizar o trabalho pessoal sem substituir o `Meu Trabalho`:

- no mapa geral, cada processo pode exibir o badge `N atividades para você`;
- no detalhe do processo, uma seção `Minhas execuções neste processo` aparece antes da ação de iniciar nova instância;
- cada card representa uma **atividade executável**, e não apenas a instância inteira;
- o card mostra processo, instância, atividade atual, prazo/SLA e progresso dos artefatos;
- a ação `Continuar` abre diretamente a execução e a atividade corretas;
- atividades automáticas de `IA`, `IN` e `OUT` aparecem como status da instância, não como pendência humana, salvo fallback, revisão ou aprovação.

Essa abordagem preserva três perspectivas complementares:

1. `Portal de Processos`: descoberta e contexto do processo;
2. `Meu Trabalho`: fila pessoal consolidada entre processos;
3. `Instância`: execução detalhada da atividade e de seus artefatos.

## 13. Hipótese de valor consolidada

A composição `BPMN + artefatos + contrato + runtime` transforma o fluxo de desenho estático em sistema operacional de processos. O ganho não está apenas em anexar documentos: está em tornar cada atividade verificável, orientada por dados, integrável e acionável pelo humano ou pelo Sapiens, com a mesma trilha de governança.
