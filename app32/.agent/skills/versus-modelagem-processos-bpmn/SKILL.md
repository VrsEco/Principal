---
name: versus-modelagem-processos-bpmn
description: Modelar, revisar e preparar fluxos BPMN 2.0 de processos já delimitados pela Metodologia Versus, incluindo gatilhos, raias executoras, atividades, decisões e vínculos seletivos com POP. Não use para definir sozinho a arquitetura corporativa nem para publicar fluxo sem gate humano.
---

# Modelagem de Processos BPMN Versus

Transformar um processo validado em BPMN 2.0 simples, coerente e importável no APP32. Aplicar primeiro `gestao_versus_core` e, quando a fronteira do processo ainda estiver em discussão, `versus-arquitetura-processos`.

## Modos

- `modelar`: criar o fluxo a partir de evidências operacionais.
- `revisar`: localizar falhas semânticas, desconexões e drift com o processo.
- `refatorar`: corrigir fluxo existente preservando rastreabilidade.
- `preparar-importacao`: gerar BPMN 2.0 validado sem gravar estado operacional.
- `maturar`: diagnosticar o estado da modelagem e recomendar a próxima ação pelo protocolo oficial.

## Sequência obrigatória

1. Confirmar `company_id` e executar discovery MCP quando houver estado do APP32.
2. Ler a arquitetura, o objetivo e a fronteira do processo; separar fatos, hipóteses e decisões.
3. Confirmar gatilho, fornecedores, entradas, saídas, recebedores, objetivo, responsável único pelo processo e times executores.
4. Construir progressivamente do gatilho ao objetivo e validar regressivamente do objetivo ao gatilho, usando o SIPOC como contrato transversal conforme `references/metodo-bpmn.md`.
5. Decidir POP, rotina e indicadores sem aplicar relação automática 1:1.
6. Validar o XML com `scripts/validar_bpmn_versus.py` e revisar o diagrama visualmente no `bpmn-js`.
7. Entregar diagnóstico, fluxo proposto, pendências e estado `Em discussão` até o gate humano.
8. Gravar apenas rascunho autorizado via MCP; reler após a escrita. Publicar somente após confirmação humana explícita.
9. Quando a demanda envolver maturação, aplicar `references/process-modeling-official-v1.0.json`, informar estado da jornada, dimensões com evidência/gaps e próxima ação recomendada.

## Invariantes Versus

- O processo possui um responsável; as raias representam times, papéis ou participantes executores.
- SIPOC orienta a coerência do fluxo, sem relação automática `1:1` com atividades e sem exigir snapshot persistido.
- Saída é a entrega concreta; objetivo é o resultado pretendido. Todo caminho final produz saída intencional e recebedor identificado.
- Rotina define periodicidade e gatilho do processo, não a repetição isolada de cada atividade.
- POP existe somente quando risco, variabilidade, complexidade ou conformidade exigirem instrução detalhada.
- Um POP pode documentar várias atividades. Seu título lista, na ordem do fluxo, o código e o nome de todas as atividades vinculadas.
- Indicadores são mínimos e orientados a resultado, prazo, qualidade ou capacidade do processo; não criar indicador por atividade.
- Código da atividade começa pelo código do processo e termina em sequência de dois dígitos.
- Gateway representa decisão ou sincronização real, possui pergunta clara quando decisório e saídas rotuladas.
- Nenhuma atividade fica órfã, desconectada ou tipada como automática sem contrato de execução compatível.

## APP32 e MCP

- Usar `list_process_hierarchy` antes de propor criação estrutural.
- Usar `analyze_process_flow_copilot_tool` para ler diagrama existente e gaps.
- Usar `create_process_bpmn_activity_tool` somente quando a capability e a alteração incremental atenderem ao desenho.
- Quando o contrato MCP não representar o fluxo completo, gerar `.bpmn` externo validado e encaminhar para importação; nunca contornar com SQL direto.
- A ausência de POP não é, isoladamente, um defeito. Reclassificar o alerta do copiloto pela necessidade metodológica.
- O vínculo legado de POP do APP32 não autoriza duplicar POP quando várias atividades compartilham a mesma instrução. Registrar o gap de cardinalidade até existir vínculo canônico adequado.

## Gates

- Squad Cliente valida realidade e evidências.
- Squad Versus valida método, fronteira e desenho.
- Consultor ou responsável autorizado aprova o rascunho final.
- Publicação no APP32 exige autorização explícita, `company_id` e releitura posterior.

## Referências

- `references/metodo-bpmn.md`: semântica e decisões de modelagem.
- `references/contrato-saida.md`: entrega mínima e estados.
- `references/process-modeling-official-v1.0.json`: protocolo oficial de maturação da modelagem.
- `../versus-arquitetura-processos/SKILL.md`: arquitetura e fatoração do processo.

