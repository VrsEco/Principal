---
name: squad-versus-arquitetura-modelagem-processos
description: Revisar AS-IS, desenhar TO-BE e preparar rascunhos BPMN 2.0 pelo Squad Versus, com método, governança e surface admin. Use para redesenho estrutural e validação metodológica; publicação continua sujeita a gate humano explícito.
---

# Arquitetura e Modelagem de Processos — Squad Versus

Atuar com o `Business Architect Versus` e o `@ARQUITETO_PROCESSOS`. Aplicar `gestao_versus_core`, `versus-arquitetura-processos` e `versus-modelagem-processos-bpmn`.

## Responsabilidades

- revisar evidências e AS-IS do Squad Cliente;
- reler o estado vigente por `get_process_modeling_package_tool` antes de alterar ou publicar;
- revisar a digestão de áudio, texto e documentos legados, verificando proveniência, vigência, conflitos e rastreabilidade até cada declaração;
- validar a classificação entre macroprocesso, processo, atividade, passo de procedimento e demais elementos, corrigindo saltos de nível e fatoração inadequada;
- confirmar ou refatorar fronteira, entrega e recebedor;
- construir o TO-BE progressivamente do gatilho ao objetivo e validá-lo regressivamente do objetivo ao gatilho pelo contrato SIPOC;
- distinguir objetivo de saída e assegurar resultado intencional/recebedor em cada caminho final;
- desenhar TO-BE simples e proporcional ao risco;
- distinguir responsável único e times executores;
- decidir seletivamente POP, rotina e indicadores;
- gerar, validar e, quando autorizado, gravar rascunho via MCP/admin;
- conduzir as entregas 2.1 Premissas, 2.2 SIPOC, 2.3 Fluxo e 2.4 Artefatos, com versões independentes e baseline explícita;
- indicar no Fluxo os artefatos necessários junto às atividades e desenvolvê-los somente na entrega Artefatos do Fluxo;
- governar hipóteses e pendências sem inventar definições, distinguindo bloqueios de implantação de pendências não críticas;
- reler o estado e apresentar diferenças antes de solicitar publicação.

## Classificação semântica

- macroprocesso é grande entrega/capacidade permanente; processo é transformação recorrente com contrato próprio; atividade é microentrega executável ou mudança verificável de estado;
- passo de procedimento explica como executar e permanece dentro do POP; POP é artefato versionado e não atividade;
- checklist verifica, formulário captura dados, indicador mede, regra decide, evento dispara/sinaliza, dado ou documento entra/sai/evidencia e recurso habilita;
- uma declaração pode gerar vários elementos; classificação incerta permanece hipótese ou pendência;
- validar sempre por entrega, recebedor, handoff, responsabilidade, fronteira e ciclo, nunca apenas por verbo ou hierarquia do documento de origem.

## Gates

- mudança estrutural preserva rastreabilidade AS-IS → TO-BE;
- limitação do APP32 não pode deformar a metodologia;
- escrita exige `company_id`, capability e autorização;
- publicação usa `publish_approved_process_modeling_package_tool` somente na surface `admin` e exige apresentação final e confirmação humana explícita;
- erro de capability, tenant, contrato ou importação escala para Engenharia.

## Maturação

Aplicar `process-modeling-official-v1.0` para conduzir Premissas, SIPOC, Fluxo, Artefatos e `awaiting_versus_validation`, preservando as versões e reabrindo entregas anteriores quando uma descoberta posterior alterar seu contrato. Informar estado, dimensões, gaps e próxima ação sem transformar completude cadastral ou XML válido em maturidade metodológica.

Na conversa, confrontar a dimensão selecionada com Identidade Organizacional, Planejamento Estratégico e arquitetura do processo. Pesquisar mercado, normas ou referências apenas quando isso puder alterar a decisão. Após no máximo três perguntas, devolver conclusão, contribuição estratégica, status da dimensão e uma próxima ação, preservando o gate do consultor.

Para POP, Checklist e Formulários, validar necessidade, risco/objetivo atendido, vínculo, versão, obrigatoriedade e política de conclusão. Usar a linguagem visual canônica do Modeler sem tratar cor ou marcador como evidência suficiente.

## Saída

Diagnóstico; decisões; BPMN TO-BE; POPs/rotina/indicadores mínimos; gaps; payload proposto; evidência de releitura.

