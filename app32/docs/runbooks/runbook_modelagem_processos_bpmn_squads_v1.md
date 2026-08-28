# Runbook — Modelagem de Processos BPMN pelos Squads

Classe: Runbook  
Status: oficial

## 1. Entrada

- processo identificado e `company_id` autorizado;
- objetivo da rodada: AS-IS, TO-BE, revisão ou importação;
- responsável humano disponível para os gates.

## 2. Execução

1. ativar a skill do Squad correspondente;
2. executar discovery e `list_process_hierarchy`;
3. carregar o fluxo com `analyze_process_flow_copilot_tool`;
4. confirmar contrato do processo e responsabilidades;
5. construir progressivamente `gatilho → fornecedores → entradas → transformação → saídas → recebedores → objetivo`;
6. validar regressivamente `objetivo → saídas → transformação → entradas → fornecedores → gatilho`;
7. modelar com `versus-modelagem-processos-bpmn`;
8. validar o arquivo:

```powershell
python .agent\skills\versus-modelagem-processos-bpmn\scripts\validar_bpmn_versus.py fluxo.bpmn --process-code AA.C.2.1.1
```

9. importar e revisar visualmente no modelador APP32;
10. apresentar diferenças, POPs seletivos, rotina e indicadores mínimos;
11. gravar rascunho somente após autorização e reler;
12. publicar somente após confirmação humana explícita.

## 3. Bloqueios

- código fora do processo ou atividade órfã;
- responsável confundido com time executor;
- gateway sem decisão ou sincronização real;
- caminho final sem saída intencional ou recebedor;
- objetivo usado como sinônimo de saída ou atividade sem contribuição demonstrável;
- tentativa de duplicar POP compartilhado;
- ausência de capability MCP;
- inconsistência de `company_id`.

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
3. abrir o editor especializado e conferir configuração e obrigatoriedade;
4. validar completion policy e evidência esperada;
5. conferir preservação no XML, reabertura e Book quando aplicável;
6. tratar cor personalizada e overlay de execução como camadas separadas.

