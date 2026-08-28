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

