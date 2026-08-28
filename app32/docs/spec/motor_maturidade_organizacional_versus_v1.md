# SPEC — Motor de Maturidade Organizacional Versus v1

## 1. Decisão

O APP32 deve possuir um **núcleo único de maturação organizacional**, aplicável às quatro frentes da Estruturação Empresarial. Regras específicas ficam em protocolos versionados; não devem ser duplicadas no motor nem codificadas por cliente.

Esta SPEC trata da maturidade dos elementos organizacionais. Ela não substitui a especificação legada de maturidade de uso assistido, que avalia autonomia de consultores e usuários na interação com Squads e agentes.

## 2. Escopo

| Frente | Elementos abrangidos |
|---|---|
| Identidade Organizacional | entendimento da empresa, mercado e sócios; MVV; posicionamento; organograma; competências e capacidade organizacional |
| Processos | arquitetura; modelagem; SIPOC/riscos; BPMN; atividades; controles; responsabilidades; indicadores; checklists; formulários; POPs; implantação; estabilização; auditoria e melhoria |
| Planejamento Estratégico | implantação ou evolução; direcionadores; objetivos; OKRs; metas; iniciativas; conexões; priorização e desdobramento |
| Gerenciamento Estratégico | definição e monitoramento de indicadores; rotinas; Business Reviews; análise de desempenho; incentivos; decisões; ações corretivas e aprendizado |

## 3. Ciclo comum

Todo elemento percorre:

1. compreender;
2. discutir;
3. identificar gaps;
4. definir;
5. validar;
6. consolidar como vigente;
7. acompanhar alinhamento;
8. amadurecer novamente.

O ciclo é iterativo. Uma versão vigente pode ser reaberta para nova discussão sem perder seu histórico nem deixar de representar a última definição válida até que outra seja aprovada.

## 4. Estados

### 4.1 Estado do conteúdo

- `in_discussion` — **Em discussão**;
- `current` — **Vigente**;
- `discarded` — **Descartado**.

### 4.2 Estado de maturidade relativa

- `behind` — **Atrasado**;
- `aligned` — **Em linha com os demais**;
- `ahead` — **Adiantado**.

As duas classificações são independentes. Um conteúdo pode estar vigente e atrasado; em discussão e adiantado; ou vigente e em linha. `Adiantado` sinaliza desalinhamento potencial, não superioridade automática.

## 5. Registro mínimo do ciclo

Cada ciclo deve manter:

- `company_id` e elemento avaliado;
- protocolo e versão utilizados;
- estado do conteúdo e estado de maturidade relativa;
- histórico de discussões;
- evidências e respectivas origens;
- gaps encontrados;
- alternativas consideradas;
- definições aprovadas;
- itens descartados e justificativas;
- ideias ainda abertas;
- responsáveis e gates de validação;
- versão vigente resultante;
- dependências e impactos transversais;
- próxima ação recomendada.

Registros históricos são imutáveis para fins de auditoria. Correções produzem novo evento, versão ou ciclo, sem reescrever a fotografia metodológica anterior.

## 6. Protocolo por elemento

O protocolo contém:

1. perguntas orientadoras;
2. evidências mínimas;
3. critérios de qualidade;
4. dependências com outros elementos;
5. gaps verificáveis;
6. entregável esperado;
7. gates humanos;
8. critérios para vigência e reavaliação.

A resolução segue `tenant → global → fallback`. O protocolo tenant-owned pode adaptar nomenclatura e requisitos do cliente, mas não alterar estados, gates globais, isolamento multi-tenant ou regras canônicas sem decisão metodológica explícita.

## 7. Avaliação relacional

O motor não deve calcular maturidade apenas por completude cadastral ou nota isolada. Deve confrontar dependências entre elementos, incluindo:

- identidade versus estratégia;
- estratégia versus processos e capacidades;
- processos versus organograma, competências e controles;
- objetivos versus indicadores;
- indicadores versus dados e rotinas;
- incentivos versus comportamentos e resultados desejados.

O diagnóstico deve explicitar o desalinhamento, seu efeito provável na execução e a próxima decisão recomendada.

## 8. Relação com projetos

Gap não cria projeto automaticamente. Após validação humana, o tratamento pode ser:

- definição ou ajuste simples;
- ação operacional;
- projeto de implantação, correção ou melhoria.

O Gestor de Projetos administra o projeto. O Motor de Maturidade registra o vínculo, recebe evidências de execução e reavalia o elemento afetado.

## 9. Contrato de apresentação

A interface padrão deve priorizar:

1. onde a empresa está;
2. o que está vigente;
3. o que está em discussão;
4. gaps e desalinhamentos relevantes;
5. próxima decisão recomendada.

Discussões, evidências, eventos, versões e dependências permanecem acessíveis em detalhe, sem sobrecarregar a visão principal.

## 10. Guardrails

- `company_id` obrigatório em toda leitura e escrita operacional;
- MCP First para consumo por CLI, Squads e agentes;
- IA recomenda; responsáveis validam; consultor decide; executor autorizado publica;
- cobertura cadastral não equivale a maturidade;
- protocolo novo não reescreve avaliações antigas;
- configuração específica de cliente não vira regra global automaticamente;
- nenhuma expansão do APP32 deve ocorrer sem análise de aderência, impacto multi-tenant e complexidade.

## 11. Fora de escopo desta decisão

- desenho definitivo de banco, APIs ou telas;
- migração automática de registros existentes;
- cálculo de score percentual universal;
- gestão operacional de projetos dentro do motor;
- publicação autônoma de conteúdo canônico por agentes.

## 12. Protocolo oficial de maturação da modelagem

A modelagem de processos utiliza o protocolo global `process-modeling-official-v1.0`, com jornada `process-modeling-maturity-v1.0`. A resolução permanece `tenant → global → fallback` e o contexto operacional exige `company_id`, `process_id` e referência da versão BPMN avaliada.

### 12.1 Estados da jornada

1. `collecting_evidence` — reunir fatos operacionais e fontes;
2. `contracting_process` — confirmar objetivo, fronteira, gatilho, SIPOC, responsável e recebedores;
3. `mapping_as_is` — representar a realidade observada;
4. `designing_to_be` — propor o desenho futuro com rastreabilidade;
5. `completing_operational_model` — decidir responsabilidades, rotina, POPs seletivos, indicadores mínimos e artefatos aplicáveis;
6. `awaiting_client_validation` — validar evidências e AS-IS com o Cliente;
7. `awaiting_versus_validation` — validar método, fronteira e TO-BE com a Versus;
8. `awaiting_consultant_decision` — aprovar, ajustar ou rejeitar a proposta;
9. `approved_for_publication` — aguardar execução autorizada;
10. `published` — manter a versão vigente e sua evidência de releitura;
11. `due_for_review` — abrir novo ciclo quando houver mudança ou desvio relevante;
12. `blocked` — registrar impedimento, responsável e condição de desbloqueio.

### 12.2 Dimensões metodológicas

- `contract`: objetivo, fronteira, gatilho e SIPOC bidirecional;
- `reality_alignment`: evidências, exceções e aderência do AS-IS;
- `bpmn_semantics`: eventos, atividades, gateways, raias, finais e conectividade;
- `executability`: responsável, executores, recursos, rotina e artefatos necessários;
- `governance`: versões, gates, rastreabilidade, tenant e publicação;
- `learning`: desvios observados, reavaliação e evolução do modelo.

As dimensões produzem diagnóstico e gaps, não score percentual universal. A maturidade metodológica da modelagem não pode ser inferida de completude cadastral, XML válido ou existência de BPMN publicado.

### 12.3 Gates e separações

- Squad Cliente valida fatos e AS-IS;
- Squad Versus valida método e TO-BE;
- Engenharia valida aspectos técnicos quando acionada;
- consultor decide a aprovação;
- executor autorizado publica e relê;
- desempenho operacional e maturidade de implantação são avaliados separadamente da maturidade da modelagem.

### 12.4 Artefato canônico

O contrato detalhado fica em `.agent/skills/versus-modelagem-processos-bpmn/references/process-modeling-official-v1.0.json`. Esta decisão formaliza método e atuação dos Squads; persistência tenant-owned e automação da próxima ação no motor exigem recorte técnico próprio antes de produção.

### 12.5 Visão executiva

Por padrão, o usuário recebe uma única tela com seis dimensões:

1. Fluxo;
2. POP, Checklist e Formulários;
3. Indicadores;
4. Rotina;
5. Recursos;
6. Responsável e Time Executor.

Cada dimensão exibe apenas `status`, `principal_gap` e `next_action`. Os estados permitidos são `not_defined`, `building`, `validating`, `validated` e `review_required`. Não há média percentual obrigatória. Evidências, critérios técnicos e histórico permanecem no segundo nível.

### 12.6 Modo conversacional

O coordenador dos Squads conduz uma dimensão por vez e:

1. lê via MCP identidade, objetivos estratégicos, arquitetura, modelagem e evidências do tenant;
2. escolhe o gap com maior impacto no objetivo do processo e na estratégia;
3. faz uma pergunta por vez e no máximo três perguntas antes de sintetizar;
4. pesquisa referências internas, mercado, normas ou legislação apenas quando puderem alterar a decisão;
5. separa fato, fonte, inferência e recomendação;
6. apresenta conclusão, contribuição estratégica e uma única próxima ação;
7. solicita aprovação antes de alterar conteúdo canônico.

O Squad Cliente conduz realidade e AS-IS; o Squad Versus confronta o desenho com Identidade, Planejamento Estratégico e método. Engenharia só participa quando houver gap técnico. Não se cria um novo agente neste recorte.
