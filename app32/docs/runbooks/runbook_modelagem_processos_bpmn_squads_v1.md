# Runbook — Modelagem de Processos BPMN pelos Squads

Classe: Runbook  
Status: oficial

## 1. Entrada

- processo identificado e `company_id` autorizado;
- fonte inicial em áudio, texto, documento legado ou combinação, com identificação e contexto disponíveis;
- objetivo da rodada: AS-IS, TO-BE, revisão ou importação;
- responsável humano disponível para os gates.

## 2. Execução

Usar a sequência oficial de entregas:

`1 Arquitetura de Processos → 2.1 Premissas → 2.2 SIPOC → 2.3 Fluxo com indicação de artefatos → 2.4 desenvolvimento dos Artefatos do Fluxo`.

Cada entrega possui versão própria. Antes de avançar, validar seu gate; ao encontrar impacto posterior, reabrir a entrega afetada, registrar a alteração e recompor a baseline.


1. ativar a skill do Squad correspondente;
2. transcrever áudio quando necessário, preservar proveniência e decompor todas as fontes em declarações atômicas;
3. marcar vigência da fonte e confrontar documento legado com executores e estado atual;
4. classificar cada declaração com tipo, evidência, justificativa e pergunta de validação; permitir múltiplos elementos na mesma declaração;
5. executar discovery e `list_process_hierarchy`;
6. carregar o fluxo com `analyze_process_flow_copilot_tool`;
7. antes do AS-IS, gerar a matriz de cobertura de Arquitetura, Premissas, SIPOC, Fluxo e Artefatos, confrontando o estado MCP com transcrições e demais evidências;
8. classificar cada elemento como `defined`, `hypothesis`, `pending` ou `not_applicable`; para pendências, registrar fonte esperada, responsável, etapa de revisão e impacto;
9. confirmar contrato do processo e responsabilidades;
10. construir progressivamente `gatilho → fornecedores → entradas → transformação → saídas → recebedores → objetivo`;
11. validar regressivamente `objetivo → saídas → transformação → entradas → fornecedores → gatilho`;
12. modelar com `versus-modelagem-processos-bpmn`;
13. validar o arquivo:

```powershell
python .agent\skills\versus-modelagem-processos-bpmn\scripts\validar_bpmn_versus.py fluxo.bpmn --process-code AA.C.2.1.1
```

14. importar e revisar visualmente no modelador APP32;
15. apresentar diferenças, POPs seletivos, rotina e indicadores mínimos;
16. gravar rascunho somente após autorização e reler;
17. publicar somente após confirmação humana explícita.

## 3. Bloqueios

- código fora do processo ou atividade órfã;
- responsável confundido com time executor;
- gateway sem decisão ou sincronização real;
- caminho final sem saída intencional ou recebedor;
- objetivo usado como sinônimo de saída ou atividade sem contribuição demonstrável;
- tentativa de duplicar POP compartilhado;
- ausência de capability MCP;
- inconsistência de `company_id`.
- pendência bloqueante sem responsável ou condição de resolução;
- artefato apenas indicado no fluxo tratado como se estivesse desenvolvido;
- baseline sem as versões vigentes de Premissas, SIPOC, Fluxo e Artefatos.
- início ou revisão do AS-IS sem matriz de cobertura metodológica das cinco entregas.

## 4. Evidência

XML válido, renderização legível, checklist sem bloqueios, validações sem personificação de outro Squad, releitura MCP e confirmação humana da publicação.

## 5. Rito de maturação

1. carregar `references/process-modeling-official-v1.0.json`;
2. confirmar `company_id`, `process_id` e referência BPMN;
3. classificar o estado atual somente por evidência;
4. diagnosticar as seis dimensões sem score percentual;
5. devolver gaps, gate pendente e próxima ação;
6. abrir `due_for_review` quando mudança ou desvio invalidar premissas da versão vigente.

Até existir persistência tenant-owned e next action MCP específicos, registrar o diagnóstico no pacote de modelagem e não declarar transição operacional automática no APP32.

## 6. Rito conversacional

1. carregar identidade, objetivos estratégicos, arquitetura e modelagem via MCP;
2. exibir as seis dimensões com status, gap principal e próxima ação;
3. escolher uma dimensão e fazer até três perguntas, uma por vez;
4. consultar fonte externa apenas quando relevante para a decisão;
5. registrar fato, fonte, inferência e recomendação separadamente;
6. apresentar síntese curta e solicitar aprovação antes de qualquer escrita.

## 7. Verificação visual e semântica dos artefatos

1. confirmar `artifact_type`, definição, versão e vínculo com `bpmn_element_id`;
2. conferir marcador/rótulo e cores canônicas no Modeler: POP azul, FORM violeta e CHECK verde;
3. quando várias atividades operarem o mesmo FORM ou CHECK, confirmar `execution_scope=process_instance`, uma `phase_key` por vínculo e `can_finalize` apenas na etapa aprovadora;
4. executar o fluxo completo e comprovar que preenchimento, validação, correção e nova validação reutilizam o mesmo documento, sem perder a trilha individual de interações;
5. abrir o editor especializado e conferir configuração e obrigatoriedade;
6. validar completion policy e evidência esperada;
7. conferir preservação no XML, reabertura e Book quando aplicável;
8. tratar cor personalizada e overlay de execução como camadas separadas.

