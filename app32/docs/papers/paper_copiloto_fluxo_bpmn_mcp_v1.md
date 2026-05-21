# Paper — Copiloto de Fluxo BPMN via MCP

Status: em evolução  
Classe: Paper

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
