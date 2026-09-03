# SPEC — Agente de Arquitetura de Processos Versus v1

## 1. Objetivo

Definir o contrato operacional do agente que cria, refatora, revisa e discute arquiteturas de processos empresariais, preservando a distinção entre método universal Versus e configuração específica de cada cliente.

## 2. Cadeia obrigatória

1. Identidade;
2. resultados empresariais necessários;
3. áreas ou cadeias;
4. macroprocessos — geração de valor e grandes entregas;
5. processos — entregas;
6. atividades — microentregas;
7. clientes ou processos recebedores.

Cada elemento deve ter propósito, entrega, origem, recebedor e vínculo com o nível superior. Lacunas de evidência são registradas como hipótese ou gap, nunca preenchidas como fato.

### 2.1 Nomenclatura e fatoração dos processos

- O nome deve ser direto, concreto e compreensível pela operação, usando verbo(s) de ação e objeto ou entrega reconhecível.
- Verbos só permanecem agrupados quando convergem para uma mesma entrega e compartilham fronteira, recebedor, responsável e ciclo de gestão coerentes.
- Mudança de entrega principal, recebedor, handoff, responsável, momento de controle ou ciclo operacional exige avaliar a separação em outro processo.
- É vedado condensar uma jornada ponta a ponta em um nome amplo quando existirem entregas gerenciáveis distintas.
- A clareza direta adotada pelo consultor Versus prevalece sobre padrões de nomenclatura de mercado que tornem a comunicação abstrata ou extensa.

Exemplo canônico de orientação:

```text
Em vez de:
AA.C.2.2.2 - Desenhar, precificar, propor, negociar e contratar soluções

Usar:
AA.C.2.2.2 - Desenhar, precificar, confeccionar e enviar proposta
AA.C.2.2.3 - Fazer follow-up, negociar e fechar contratos
AA.C.2.2.4 - Formalizar contrato e realizar onboarding financeiro e operacional
```

### 2.2 Contrato de ingestão e classificação semântica

O agente aceita como ponto de partida áudio, texto, documento legado ou combinação dessas fontes. Antes de propor arquitetura ou BPMN, deve:

1. preservar a fonte: tipo, identificação, data/versão quando disponível e localização do trecho; em áudio, manter timestamp, interlocutor e incerteza de transcrição quando possível;
2. decompor o conteúdo em declarações atômicas, sem resumir elementos distintos em uma única classificação;
3. marcar a vigência da evidência como `current_confirmed`, `current_unconfirmed`, `legacy`, `conflicting` ou `unknown`;
4. classificar cada declaração como fato, hipótese, pendência ou não aplicável e registrar justificativa e evidência;
5. confrontar documentos antigos com executores e estado MCP atual antes de tratá-los como verdade vigente.

#### 2.2.1 Boundary de ingestão local

- áudio, texto e documento legado são processados pela IA/CLI do cliente; não existe dependência de tool MCP para upload, OCR ou transcrição;
- o material bruto permanece local, salvo autorização e integração específicas;
- o MCP recebe o envelope normalizado `process_modeling_intake.v1` e continua responsável por discovery, leitura do estado atual, handoff e persistência autorizada;
- o CLI não pode usar a transcrição como aprovação, preencher desconhecidos por inferência ou publicar BPMN.

#### 2.2.2 Roteiro mínimo para gravação do cliente

O cliente deve narrar, preferencialmente um processo por áudio: empresa/unidade e variante; entrevistado/função/data; objetivo; gatilho/início; fim e saída principal; cliente/recebedor; responsável do processo; executores; fornecedores e entradas; sequência real; decisões; exceções e retrabalho; interfaces; frequência; recursos/sistemas; restrições/riscos; indicadores; e, por atividade, POP, checklist, formulário, dado/evidência ou IA existente/necessária. Informação desconhecida, inexistente ou não aplicável deve ser declarada como tal.

#### 2.2.3 Envelope `process_modeling_intake.v1`

O CLI entrega JSON com:

- `source`: tipo, identificação, data, idioma, hash e versão legada quando houver;
- `transcript[]`: segmento, interlocutor, timestamps, texto e confiança;
- `statements[]`: declaração atômica, referências à fonte, `assertion_kind`, vigência, confiança e classificações justificadas;
- `methodology_coverage`: cobertura de Arquitetura, 2.1 Premissas, 2.2 SIPOC, 2.3 Fluxo e 2.4 Artefatos;
- `candidate_process`: normalização operacional sem promoção canônica;
- `conflicts[]` e `open_questions[]` rastreáveis.

O contrato completo é devolvido pelo `resolve_app32_instruction_bundle_tool` no campo `process_modeling_intake_contract`.

O classificador deve aplicar os seguintes testes:

| Tipo | Critério determinante |
|---|---|
| Macroprocesso | Grande entrega ou capacidade empresarial permanente que agrupa processos coerentes e sobrevive a mudanças razoáveis do organograma. |
| Processo | Transformação recorrente e gerenciável com gatilho, entradas, saída principal, recebedor, responsável e ciclo próprios. |
| Atividade BPMN | Unidade executável por papel/time que produz microentrega, mudança verificável de estado ou handoff dentro do processo. |
| Passo de procedimento | Instrução de como executar uma atividade, sem entrega de negócio, recebedor, handoff ou ciclo próprios; pertence ao conteúdo de um POP. |
| POP | Artefato instrucional versionado que prescreve como executar uma ou mais atividades e pode conter passos, pré-condições, riscos e evidências. |
| Checklist | Artefato de verificação ou controle com itens, critérios, resultado e evidência; não substitui automaticamente um POP. |
| Formulário | Artefato de captura estruturada com campos, validações, finalidade e destino dos dados. |
| Indicador | Medida de resultado, prazo, qualidade ou capacidade com fórmula, unidade, fonte, periodicidade, meta/faixa e responsável. |
| Regra/decisão | Condição que altera o caminho ou resultado; deve ser representada como regra ou gateway quando aplicável. |
| Evento | Ocorrência, mensagem, tempo ou condição que inicia, espera, interrompe ou encerra o fluxo. |
| Dado/documento/evidência | Entrada, saída ou comprovação consumida ou produzida; não representa trabalho executável. |
| Recurso/sistema | Meio, ativo ou capacidade que habilita a execução; não representa por si só uma atividade. |
| Projeto | Esforço temporário para criar, corrigir ou melhorar uma capacidade/processo; não integra a arquitetura permanente como processo. |

Regras de decisão:

- não classificar apenas pelo verbo, título, quantidade de palavras ou nível de indentação da fonte;
- quando houver saída própria, recebedor, handoff, responsável ou ciclo autônomo, avaliar processo ou atividade antes de passo de POP;
- quando o item apenas explicar “como fazer” algo já executável, classificá-lo como passo de procedimento, não como atividade BPMN;
- uma frase pode gerar vários elementos relacionados, por exemplo atividade + checklist + formulário + regra;
- ambiguidade permanece `hypothesis` ou `pending`; o Squad Cliente confirma a realidade e o Squad Versus valida nível, fronteira e fatoração;
- classificação canônica exige justificativa, evidência e gate humano.

## 3. Modos

- **Criar:** propor arquitetura inicial a partir da identidade e das evidências disponíveis.
- **Refatorar:** reorganizar arquitetura existente com rastreabilidade entre origem e proposta.
- **Revisar:** apontar inconsistências, lacunas, sobreposições e quebras de encadeamento.
- **Discutir:** apoiar consultor e gestores na formulação, sem promover mudanças canônicas.

## 4. Repertório de casos

O catálogo `references/cases.json` mantém casos com os estados `candidate`, `reference` e `retired`. A promoção de caso pode substituir uma referência ativa, mas deve preservar a anterior como `retired`, registrar `superseded_by` e manter o histórico auditável. Casos de cliente exigem `company_id` e acesso MCP quando houver superfície operacional disponível.

## 5. Governança

- IA recomenda; consultor e gestores validam; executor autorizado publica.
- Toda leitura ou escrita de estado operacional respeita multi-tenancy e MCP First.
- Conhecimento extraído de um cliente só vira regra metodológica após fatoração e validação explícita.
- O agente não cria complexidade de APP32 antes da análise de aderência, impacto nos demais tenants e necessidade real.

## 6. Artefatos operacionais

- Skill: `.agent/skills/versus-arquitetura-processos/SKILL.md`;
- persona: `.agent/agents/arquiteto_processos.md`;
- método: `.agent/skills/versus-arquitetura-processos/references/metodo.md`;
- contrato de saída: `.agent/skills/versus-arquitetura-processos/references/contrato-saida.md`;
- catálogo e política de casos: `.agent/skills/versus-arquitetura-processos/references/cases.json` e `casos.md`;
- ferramentas: `scripts/gerir_casos.py` e `scripts/validar_catalogo.py`.

## 7. Aceite mínimo

1. skill validada estruturalmente;
2. catálogo de casos válido;
3. saída de teste cobre todos os níveis da cadeia;
4. `company_id` é obrigatório em catálogos operacionais;
5. premissas, gaps e validações humanas aparecem separadamente.
6. nomes são diretos e não agrupam entregas ou ciclos de gestão distintos.
7. a validação bidirecional SIPOC demonstra que fornecedores, entradas, transformação, saídas, recebedores, gatilho e objetivo são coerentes.

## 8. Extensão oficial para modelagem BPMN

```text
versus-arquitetura-processos
→ processo delimitado
→ versus-modelagem-processos-bpmn
→ BPMN em discussão
→ validação Cliente
→ validação Versus
→ aprovação humana
→ publicação APP32
```

Regras oficiais:

- todo fluxo é construído progressivamente do gatilho ao objetivo e validado regressivamente do objetivo ao gatilho;
- o SIPOC funciona como contrato de fronteira e coerência, sem exigir relação 1:1 com atividades nem snapshot persistido;
- saída é a entrega do processo; objetivo é o resultado pretendido e não deve ser usado como sinônimo da saída;
- responsável do processo é único; lanes representam times ou papéis executores;
- rotina pertence ao disparo do processo;
- POP é seletivo e pode estar vinculado a várias atividades;
- o título do POP compartilhado lista código e nome de todas as atividades vinculadas, na ordem do fluxo;
- indicadores devem ser mínimos e não nascem automaticamente por atividade;
- limitações do vínculo legado `ProcessRoutine.bpmn_element_id` não autorizam duplicação de POP;
- publicação de BPMN depende de gate humano explícito.

Artefatos adicionais:

- núcleo: `.agent/skills/versus-modelagem-processos-bpmn/`;
- Squad Cliente: `.agent/skills/squad-cliente-descoberta-modelagem-processos/`;
- Squad Versus: `.agent/skills/squad-versus-arquitetura-modelagem-processos/`.

## 9. Extensão oficial para maturação da modelagem

O protocolo `process-modeling-official-v1.0`, com jornada `process-modeling-maturity-v1.0`, conduz a modelagem pelo Motor de Maturidade Organizacional. O agente deve informar estado, diagnóstico nas seis dimensões, gates e próxima ação, sem score percentual universal e sem confundir BPMN publicado com implantação ou desempenho.

O Squad Cliente valida evidências e AS-IS; o Squad Versus valida método e TO-BE; Engenharia participa quando houver gate técnico; o consultor decide; o executor autorizado publica e relê.

A interação padrão usa um coordenador e as seis dimensões executivas. O coordenador lê identidade, estratégia e modelagem, conduz uma dimensão por vez, faz no máximo três perguntas antes da síntese e expõe apenas conclusão, contribuição estratégica, status e próxima ação. Não é necessário criar novo agente.

A dimensão POP/Checklist/Formulários reconhece marcadores e cores canônicas do Modeler, mas sua avaliação usa tipo, vínculo, definição, versão, obrigatoriedade, completion policy, evidência e contribuição. Aparência isolada não comprova maturidade.
