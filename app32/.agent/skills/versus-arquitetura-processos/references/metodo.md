# Método Versus de Arquitetura de Processos

## 1. Pergunta central

> O que a empresa precisa fazer continuamente para cumprir sua identidade, entregar valor aos seus clientes e alcançar seus objetivos?

## 2. Cadeia de derivação

```text
Identidade
→ resultados empresariais necessários
→ áreas/cadeias
→ macroprocessos (geração de valor → grandes entregas)
→ processos (entregas)
→ atividades (microentregas)
→ clientes ou processos recebedores
```

### Identidade

Compreender propósito, missão, visão, valores, posicionamento, clientes, mercados, produtos, serviços, objetivos, restrições e diferenciais. Não inferir definição ausente como fato.

### Resultados empresariais necessários

Traduzir a identidade em resultados que a empresa precisa produzir continuamente: direção, aquisição de clientes, entrega principal, receita, sustentação, conformidade, pessoas, recursos e aprendizado.

### Áreas ou cadeias

Agrupar grandes famílias de geração de valor. Usar Gestão, Finalísticos e Apoio apenas quando forem adequados; não torná-los obrigatórios.

### Macroprocessos — grandes entregas

Representar grandes entregas ou capacidades empresariais permanentes. Um macroprocesso deve ter finalidade, fronteira, recebedor e conjunto coerente de processos. Deve sobreviver a mudanças razoáveis de organograma.

### Processos — entregas

Representar transformações recorrentes e gerenciáveis. Exigir gatilho, entradas, transformação, saída, cliente/recebedor, responsável possível e indicador possível.

### Atividades — microentregas

Representar ações executáveis que produzem avanço verificável no processo. Associar controles, responsáveis, checklists, formulários, POPs e indicadores quando aplicável.

### Passos de procedimento e demais elementos

Um passo de procedimento descreve como executar uma atividade. Ele não possui entrega de negócio, recebedor, handoff, responsável ou ciclo de gestão autônomos e deve permanecer dentro do conteúdo versionado do POP. POP não é atividade: é o artefato instrucional que pode servir a uma ou várias atividades.

- checklist verifica condição, conformidade ou evidência;
- formulário captura dados estruturados para uso definido;
- indicador mede resultado, prazo, qualidade ou capacidade;
- regra ou decisão altera o caminho;
- evento representa ocorrência, mensagem, tempo ou condição;
- documento, dado ou evidência entra, sai ou comprova;
- recurso ou sistema habilita a execução;
- projeto é esforço temporário para criar, corrigir ou melhorar o sistema permanente.

Uma mesma declaração pode conter vários elementos. Exemplo: “Conferir a nota pelo checklist e registrar divergências no formulário” contém uma atividade, um checklist, um formulário e possivelmente uma regra; não deve ser reduzida a um único tipo.

### Ingestão de áudio, texto e documentos legados

O levantamento pode começar por áudio, texto, documento antigo ou combinação dessas fontes. Antes de fatorar:

1. identificar fonte, data/versão e trecho; para áudio, preservar timestamp, interlocutor e incerteza quando possível;
2. quebrar o conteúdo em declarações atômicas;
3. marcar vigência como `current_confirmed`, `current_unconfirmed`, `legacy`, `conflicting` ou `unknown`;
4. separar fatos, hipóteses, pendências e itens não aplicáveis;
5. confrontar material legado com executores e estado MCP atual antes de declará-lo vigente.

“Digerir” significa extrair, rastrear, classificar, confrontar e organizar o conteúdo na Metodologia Versus; nunca copiar a estrutura do documento de origem nem transformar texto antigo em verdade atual automaticamente.

### Clientes ou processos recebedores

Fechar a cadeia explicitando quem recebe cada entrega. Validar se a saída de um processo é entrada útil de outro ou resultado percebido pelo cliente.

## 3. Fatoração

Para cada item, perguntar:

1. É permanente ou temporário?
2. É uma grande entrega, uma entrega ou uma microentrega?
3. Possui início e fim próprios?
4. Produz saída reconhecível?
5. Tem cliente ou processo recebedor?
6. Pode ter responsável e indicador?
7. Está no mesmo nível de granularidade dos irmãos?
8. Continua fazendo sentido se o organograma mudar?

Aplicar também a árvore de decisão:

1. É esforço temporário com término único? Tratar como projeto.
2. É grande entrega/capacidade permanente que agrupa transformações? Avaliar como macroprocesso.
3. Possui transformação recorrente, gatilho, saída, recebedor, responsável e ciclo próprios? Avaliar como processo.
4. Produz microentrega, mudança de estado ou handoff executável dentro do processo? Avaliar como atividade BPMN.
5. Apenas explica como executar uma atividade? Tratar como passo de procedimento dentro de POP.
6. Verifica, coleta, mede, decide, dispara, evidencia ou habilita? Classificar respectivamente como checklist, formulário, indicador, regra, evento, dado/documento/evidência ou recurso/sistema.

Não forçar tipo único quando a declaração contiver elementos diferentes. Registrar classificação proposta, evidência, justificativa, confiança e pergunta de validação.

Dividir quando houver resultados, recebedores, owners ou ciclos claramente distintos. Agrupar quando os itens forem apenas etapas inseparáveis da mesma entrega.

### Nomenclatura direta e fronteiras

O nome do processo deve comunicar rapidamente o trabalho realizado e a entrega que encerra sua fronteira. Usar verbos concretos e objetos reconhecíveis pela equipe, evitando títulos abstratos ou descrições que tentem conter toda a jornada ponta a ponta.

Verbos podem permanecer no mesmo nome quando convergem para uma única entrega e mantêm recebedor, responsável e ciclo de gestão coerentes. Separar em processos distintos quando surgir nova entrega principal, novo recebedor, handoff relevante, novo responsável, decisão autônoma ou ciclo de acompanhamento próprio.

Exemplo de refatoração preferida:

```text
Evitar:
AA.C.2.2.2 - Desenhar, precificar, propor, negociar e contratar soluções

Preferir:
AA.C.2.2.2 - Desenhar, precificar, confeccionar e enviar proposta
AA.C.2.2.3 - Fazer follow-up, negociar e fechar contratos
AA.C.2.2.4 - Formalizar contrato e realizar onboarding financeiro e operacional
```

No exemplo, o envio da proposta encerra uma entrega reconhecível. O acompanhamento, a negociação e o fechamento possuem outro momento de controle e outra entrega final; por isso formam um processo próprio. Após o fechamento, a formalização e o onboarding iniciam a relação contratada e preparam a operação e o fluxo financeiro, caracterizando uma terceira fronteira gerenciável.

## 4. Encadeamento

Validar dois eixos:

- `vertical`: identidade → grande entrega → entrega → microentrega;
- `horizontal`: saída → recebedor/entrada seguinte → nova transformação.

Localizar órfãos, lacunas, duplicidades, sobreposições e saltos de nível.

### 4.1 Validação bidirecional pelo SIPOC

Para cada processo, executar dois percursos complementares:

1. `progressivo`: gatilho → fornecedores → entradas → transformação/atividades → saídas → clientes/recebedores → objetivo;
2. `regressivo`: objetivo → saídas necessárias → transformações suficientes → entradas requeridas → fornecedores adequados → gatilho coerente.

O SIPOC é contrato transversal de fronteira e coerência, não decomposição `1:1` do BPMN. O objetivo explica o resultado pretendido; a saída identifica a entrega concreta. Todo caminho final deve produzir saída intencional e recebedor, inclusive quando o resultado for classificação para tratamento futuro.

## 5. Relação com capacidades e projetos

- Processo declara as capacidades habilitadoras de que necessita.
- Dimensão apenas classifica capacidades: ativos; pessoas; tecnologia/dados; documentos/conhecimento; materiais/serviços.
- Projeto cria, corrige ou melhora processo/capacidade; não deve ser incorporado como processo permanente.
- Agente Gestor de Projetos recebe gaps aprovados; o Arquiteto de Processos não cria projeto automaticamente.

## 6. Gates de qualidade

Uma proposta só pode ser apresentada para validação quando:

- deriva de identidade/evidências explícitas;
- cobre geração de valor, gestão e sustentação necessárias;
- mantém níveis coerentes;
- usa nomes diretos e fronteiras perceptíveis, sem condensar entregas distintas no mesmo processo;
- fecha entregas em clientes ou recebedores;
- separa organização, processos, projetos, ativos e atividades;
- registra dúvidas e hipóteses sem mascará-las como decisão;
- explica por que dividiu, agrupou, incluiu ou removeu elementos.
