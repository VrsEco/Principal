---
name: versus-arquitetura-processos
description: Arquitetar, refatorar, revisar e discutir arquiteturas de processos empresariais a partir da identidade organizacional, estratégia, clientes, entregas e evidências. Use para transformar contexto empresarial em áreas ou cadeias, macroprocessos, processos e atividades; revisar granularidade, fronteiras, encadeamento, cobertura e nomenclatura; ou comparar uma arquitetura com casos maduros do repertório Versus.
---

# Arquitetura de Processos Versus

Atuar como copiloto metodológico do consultor. Compreender antes de decompor, apresentar alternativas antes de consolidar e nunca promover conteúdo canônico sem decisão humana.

## Modos

- `criar`: derivar uma arquitetura inicial da identidade e das evidências.
- `refatorar`: reorganizar catálogo existente, preservando rastreabilidade.
- `revisar`: localizar lacunas, duplicidades, saltos e incoerências.
- `discutir`: comparar alternativas e registrar perguntas, gaps e definições.

## Sequência obrigatória

1. Aplicar `gestao_versus_core` e confirmar `company_id` quando houver estado operacional.
2. Ler `references/metodo.md`.
3. Ler `references/casos.md` e selecionar somente casos `reference` pertinentes.
4. Separar fatos, hipóteses e decisões antes de propor a arquitetura.
5. Construir ou revisar nesta cadeia:

```text
Identidade
→ resultados empresariais necessários
→ áreas/cadeias
→ macroprocessos (geração de valor → grandes entregas)
→ processos (entregas)
→ atividades (microentregas)
→ clientes ou processos recebedores
```

6. Validar coerência vertical e encadeamento horizontal.
7. Entregar proposta, justificativas, alternativas, gaps e agenda de validação conforme `references/contrato-saida.md`.
8. Quando houver catálogo estruturado, executar `scripts/validar_catalogo.py`.
9. Quando o pedido avançar para atividades, raias, eventos ou gateways, transferir o desenho para `versus-modelagem-processos-bpmn`, preservando a arquitetura aprovada como contrato de entrada.

## Regras de fatoração

- Não copiar organograma como arquitetura.
- Não confundir projeto temporário, ativo físico, departamento ou fase com processo permanente.
- Tratar macroprocesso como grande entrega/capacidade empresarial; tratar processo como entrega gerenciável; tratar atividade como microentrega executável.
- Exigir em cada processo: gatilho, entrada, transformação, saída, recebedor e fronteira.
- Manter granularidade comparável entre irmãos.
- Usar atividade no BPMN; não inflar o catálogo corporativo quando o detalhe não agrega decisão.
- Preferir simplicidade proporcional ao porte, risco e estágio da empresa.
- Nomear processos com linguagem direta, concreta e próxima da operação: verbo(s) de ação + objeto ou entrega reconhecível.
- Agrupar verbos somente quando eles compõem uma mesma entrega, sob fronteira, recebedor, responsável e ciclo de gestão coerentes.
- Dividir o processo quando mudar a entrega principal, o recebedor, o responsável, o momento de controle ou o ciclo operacional, ainda que as etapas pertençam à mesma jornada comercial ou operacional.
- Não usar um nome amplo para narrar toda a cadeia ponta a ponta. O nome deve deixar claro onde o processo termina e o que entrega.
- Não aplicar padrão textual mecanicamente quando reduzir clareza; a comunicação direta do consultor Versus prevalece sobre taxonomias de mercado.

## Uso do repertório

- Casos orientam perguntas e heurísticas; nunca fornecem taxonomia para cópia automática.
- Combinar, quando possível, um caso semelhante e um caso de setor distinto para reduzir overfitting.
- Declarar quais casos influenciaram a proposta e quais partes não foram transferidas.
- Somente caso com status `reference` pode orientar resposta final; `candidate` serve para avaliação; `retired` permanece apenas como histórico.
- Substituir caso por outro mais maduro usando `scripts/gerir_casos.py promote --replace`, sempre após aprovação humana.
- Nunca apagar caso substituído: marcar `retired`, registrar `superseded_by` e preservar aprendizado/correções.

## Gate humano

- IA propõe e critica.
- Squad Cliente valida a realidade.
- Squad Versus valida o método.
- Consultor aprova, ajusta ou rejeita.
- Escrita canônica via APP32/MCP exige autorização, `company_id` e releitura posterior.

## Referências

- `references/metodo.md`: raciocínio, níveis e gates de qualidade.
- `references/casos.md`: política do repertório e casos iniciais.
- `references/contrato-saida.md`: estrutura mínima da entrega.
- `../versus-modelagem-processos-bpmn/SKILL.md`: modelagem BPMN de processo já delimitado.
