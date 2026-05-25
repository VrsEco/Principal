# Paper — Manual Unificado de Utilização do APP32 por IA e Usuário via APP e MCP v1

Status: em evolução  
Classe: Paper

## 1. Tese

O APP32 deve possuir um **manual unificado de utilização** que sirva simultaneamente para:

- orientar o **usuário humano** no uso do sistema;
- orientar a **IA** a operar com segurança e explicar o sistema;
- padronizar a operação tanto **direto no APP** quanto **via conexão MCP**.

A ideia central não é manter dois universos documentais desconectados, um “manual do usuário” e outro “manual da IA”.  
O alvo correto é um **núcleo conceitual único**, com camadas diferentes de exposição:

- **camada humana**: linguagem operacional, navegação, objetivo, passo a passo e cuidados;
- **camada IA/MCP**: domínio canônico, surface permitida, filtros, restrições, exemplos e limites de atuação.

Em outras palavras:

> o usuário e a IA devem aprender o mesmo sistema,  
> mas com níveis diferentes de detalhe, risco e autonomia.

---

## 2. Problema

Hoje a documentação do APP32 já contém peças importantes, mas ainda dispersas:

- papers arquiteturais;
- guias MCP por feature;
- contratos MCP;
- runbooks de instalação e operação;
- telas e módulos já publicados no APP.

O problema é que ainda não existe uma fonte conceitual única que responda, ao mesmo tempo:

1. **como o usuário entende e usa cada módulo;**
2. **como a IA deve ensinar esse uso;**
3. **como a IA deve operar com segurança no APP e no MCP;**
4. **quando a IA pode agir, quando deve apenas orientar e quando deve bloquear.**

Sem esse manual unificado, surgem riscos de:

- drift entre o que a UI mostra e o que a IA ensina;
- drift entre o uso via APP e o uso via MCP;
- explicações boas para humano, mas ruins para automação;
- documentação técnica boa para MCP, mas insuficiente para treinamento de usuário;
- falsa impressão de que qualquer capability MCP equivale automaticamente a um fluxo pronto de uso humano.

---

## 3. Objetivo deste paper

Este paper propõe a tese e o desenho conceitual do **Manual Unificado de Utilização do APP32 por IA e Usuário**.

Ele não congela ainda o formato oficial final.  
Seu papel é amadurecer:

- a estrutura do manual;
- os princípios de escrita;
- a relação entre APP, MCP e surfaces;
- a organização por módulos;
- a esteira documental posterior (`Paper -> SPEC -> Playbook -> Runbook/Harness`).

---

## 4. Princípio central

O manual unificado deve nascer com a seguinte regra:

> a IA não inventa como usar o sistema;  
> a IA explica e opera a partir de documentação canônica do produto.

Isso implica que a IA deve:

- ensinar navegação e uso com base no manual;
- consultar contratos e guias MCP quando operar por integração;
- respeitar `company_id`, `surface`, perfil e domínio canônico;
- diferenciar claramente:
  - **explicação de uso**;
  - **execução assistida**;
  - **execução automatizada**;
  - **bloqueio por governança**.

---

## 5. Escopo do manual unificado

O manual unificado deve cobrir, no mínimo, dois eixos.

### 5.1. Eixo de uso humano

Para cada módulo, o usuário deve conseguir entender:

- o que o módulo faz;
- para que situação ele serve;
- qual é a entrada principal pelo APP;
- quais são as ações mais comuns;
- quais são os principais filtros, cadastros e decisões;
- quais erros/limites operacionais merecem atenção.

### 5.2. Eixo de uso por IA

Para cada módulo, a IA deve conseguir entender:

- qual é o **domínio canônico**;
- se existe operação via **APP**, **REST**, **MCP** ou combinação;
- quais **surfaces** podem acessar aquela capacidade;
- quais entradas mínimas são obrigatórias;
- quais restrições e bloqueios devem ser respeitados;
- como ensinar o usuário sem expor implementação interna;
- quando deve apenas responder e quando pode executar.

---

## 6. Canais de operação que o manual deve contemplar

O manual unificado deve assumir quatro formas de interação:

1. **Usuário operando direto no APP**
2. **IA ensinando o usuário a operar no APP**
3. **IA operando via MCP**
4. **IA operando via MCP e traduzindo o resultado para linguagem de usuário**

Esses quatro cenários compartilham a mesma base conceitual, mas não o mesmo nível de permissão.

### Regra obrigatória

Uma explicação funcional do módulo não pode depender de detalhe técnico interno.  
Mas uma operação MCP precisa conhecer:

- `surface`;
- `company_id`;
- contratos de entrada/saída;
- restrições de sensibilidade;
- se a ação é leitura, mutação, aprovação ou operação privilegiada.

---

## 7. Estrutura recomendada para cada módulo do manual

Cada módulo do APP32 deve evoluir para um pacote documental mínimo com duas leituras integradas:

### 7.1. Leitura humana

- nome do módulo;
- objetivo;
- quando usar;
- como acessar no APP;
- passo a passo operacional;
- principais conceitos da tela;
- erros comuns;
- boas práticas.

### 7.2. Leitura IA/MCP

- domínio canônico;
- capabilities ou features relacionadas;
- surfaces permitidas;
- entradas obrigatórias;
- saídas esperadas;
- restrições de governança;
- exemplos de perguntas do usuário;
- exemplos de resposta segura;
- regras do que nunca expor.

### 7.3. Resultado esperado

O mesmo módulo deve permitir:

- **manual de uso humano** no front;
- **guia de explicação** para a IA;
- **guia de uso por IA / MCP**;
- **guia de governança / limites**;
- **consistência entre UI, APP e catálogo MCP**.

---

## 8. Organização inicial por módulos

O manual unificado deve considerar, pelo menos, a seguinte árvore funcional inicial:

1. **Squad de Agentes**
2. **Utilização Agentes x Versus APP x Internet x IA**
3. **Gestão da Rotina**
4. **Gestão Financeira**
5. **Gestão Estratégica**
6. **Gestão Comercial**
7. **Sistema**
8. **Meu Perfil**
9. **Usos Transversais**
10. **Análises e Relatórios**

### 8.0. Opção estrutural recomendada: manual em árvore

A forma mais adequada para este manual não é um texto linear longo.  
O formato recomendado é uma **árvore navegável de conhecimento**, onde cada módulo vira um nó principal e cada nó se desdobra em camadas de uso, operação e governança.

Essa escolha é melhor porque:

- reduz ambiguidade para usuário e IA;
- facilita manutenção incremental;
- permite crescer sem perder clareza;
- aproxima a documentação da navegação real do sistema;
- facilita consumo por APP, IA e MCP sem duplicar conteúdo.

Em tese:

> o manual deve ser lido como árvore de capacidades e jornadas,  
> e não como apostila corrida.

### 8.0-A. Estrutura-base da árvore

Cada módulo principal deve poder se desdobrar em:

- **visão do módulo**
- **submódulos**
- **jornadas principais**
- **operações comuns**
- **uso por IA / MCP**
- **governança / limites**
- **dúvidas e erros comuns**

### 8.0-B. Árvore conceitual inicial proposta

```text
Manual Unificado APP32
├── 1. Squad de Agentes
│   ├── visão do ramo
│   ├── agentes disponíveis
│   ├── papel de cada agente
│   ├── limites de atuação
│   ├── handoff e escalonamento
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 2. Utilização Agentes x Versus APP x Internet x IA
│   ├── visão do ramo
│   ├── quando usar o APP
│   ├── quando usar MCP
│   ├── quando usar internet
│   ├── quando usar apenas raciocínio da IA
│   ├── limites de segurança
│   ├── fontes permitidas
│   ├── bloqueios e escalonamento
│   └── auditoria da decisão operacional
├── 3. Gestão da Rotina
│   ├── visão do módulo
│   ├── tarefas
│   ├── agenda / jornada
│   ├── acompanhamento operacional
│   ├── processos relacionados
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 4. Gestão Financeira
│   ├── visão do módulo
│   ├── fluxo de caixa
│   ├── entradas e saídas
│   ├── conciliação
│   ├── orçamento
│   ├── automações financeiras
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 5. Gestão Estratégica
│   ├── visão do módulo
│   ├── planos
│   ├── indicadores
│   ├── metas
│   ├── projetos estratégicos
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 6. Gestão Comercial
│   ├── visão do módulo
│   ├── pipeline
│   ├── oportunidades
│   ├── propostas
│   ├── contratos comerciais
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 7. Sistema
│   ├── visão do módulo
│   ├── configurações
│   ├── auditoria
│   ├── API / MCP
│   ├── integrações
│   ├── permissões
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 8. Meu Perfil
│   ├── visão do módulo
│   ├── dados pessoais
│   ├── identidade operacional
│   ├── preferências
│   ├── vínculo com empresa/perfil
│   ├── uso no APP
│   ├── uso orientado por IA
│   └── uso via MCP
├── 9. Usos Transversais
│   ├── como navegar no APP
│   ├── como pedir ajuda para a IA
│   ├── como a IA decide entre orientar e executar
│   ├── company_id e isolamento por tenant
│   ├── surfaces e perfis de acesso
│   ├── boas práticas de operação
│   ├── erros comuns e bloqueios
│   └── segurança, privacidade e auditoria
└── 10. Análises e Relatórios
    ├── visão do módulo transversal
    ├── relatórios operacionais
    ├── relatórios gerenciais
    ├── análises executivas
    ├── filtros e recortes
    ├── leitura no APP
    ├── apoio da IA na interpretação
    └── uso via MCP / analytics
```

### 8.0-C. Camadas transversais da árvore

Além dos módulos, o manual deve ter nós transversais que atravessem toda a árvore:

- **como funcionam os squads/agentes**
- **como a IA escolhe APP, MCP, internet ou resposta direta**
- **como navegar no APP**
- **como pedir ajuda para a IA**
- **como a IA decide entre orientar e executar**
- **como funciona o acesso por surface**
- **como funciona o uso via MCP**
- **boas práticas de uso**
- **segurança, privacidade e tenant**
- **erros comuns e bloqueios**

Esses itens não pertencem a apenas um módulo.  
Eles são regras estruturais do sistema inteiro.

### 8.1. Situação atual percebida

Hoje o acervo documental e MCP já indica maior maturidade em:

- **governança de agentes e harnesses**
- **Gestão da Rotina**
- **Gestão Financeira**
- **Processos**
- **catálogo e bootstrap MCP**
- **alguns fluxos de análise/analytics**

E ainda apresenta lacunas mais fortes em:

- **árvore pedagógica unificada dos squads/agentes** para usuário final;
- **regras de decisão explícitas entre APP, MCP, internet e IA** em formato de manual;
- **Gestão Estratégica** como manual MCP funcional consolidado;
- **Gestão Comercial** como manual de uso e capability canônica madura;
- **Sistema** como módulo funcional ensinável por IA;
- **Meu Perfil** como fluxo formalizado para explicação e operação assistida.
- **Usos Transversais** ainda dispersos entre múltiplos documentos;
- **Análises e Relatórios** sem árvore pedagógica unificada por público, surface e sensibilidade.

### 8.2. Regra de expansão

O manual unificado não deve esperar cobertura perfeita de todos os módulos para nascer.  
Ele pode começar com:

- módulos já maduros;
- módulos parcialmente cobertos;
- gaps explicitados com roadmap documental.

### 8.3. Estrutura mínima de cada nó da árvore

Cada nó relevante da árvore, seja módulo, submódulo ou jornada, deve responder:

1. **o que é**
2. **quando usar**
3. **quem usa**
4. **como acessar no APP**
5. **como se dá o uso por IA / MCP**
6. **quais capacidades, leituras ou ações podem ser apoiadas**
7. **quais são as regras de governança / limites**
8. **quais são os riscos, bloqueios e restrições**

### 8.4. Regra de leitura por profundidade

A árvore deve permitir pelo menos três níveis de leitura:

- **nível 1 — executivo/navegação:** o que existe no sistema;
- **nível 2 — operacional:** como usar o módulo e suas jornadas;
- **nível 3 — IA/MCP/governança:** como operar, explicar e limitar a automação.

Isso resolve um problema importante:

- o usuário comum não precisa ler contratos MCP;
- a IA não pode operar apenas com descrições superficiais de tela.

### 8.5. Itens adicionais que considero importantes incluir

Minha opinião é que a árvore não deve ficar restrita apenas aos nomes dos módulos.  
Ela deve incluir também nós obrigatórios de suporte estrutural:

#### a) Personas e perfis de acesso
- colaborador
- gestor
- administrador
- perfis especiais por surface

#### b) Canais de interação
- uso direto no APP
- uso assistido por IA
- uso remoto via MCP
- uso administrativo / analítico

#### c) Jornadas principais
- consulta
- cadastro
- atualização
- revisão
- aprovação
- análise
- operação recorrente

#### d) Governança operacional
- `company_id`
- `surface`
- sensibilidade dos dados
- confirmação humana
- trilha de auditoria

#### e) Mapa de capabilities
- capability APP
- capability REST
- capability MCP
- capability ainda não canônica

#### f) Estado de maturidade
- já operacional
- parcialmente coberto
- em construção
- apenas conceitual / roadmap

### 8.6. Regra de honestidade documental

O manual em árvore não deve fingir completude onde ela ainda não existe.

Cada ramo deve poder receber um marcador claro como:

- **operacional**
- **operacional com restrições**
- **em construção**
- **planejado**
- **não exposto via MCP**

Essa honestidade é importante para:

- alinhar expectativa do usuário;
- impedir a IA de prometer capability inexistente;
- manter coerência entre produto real e documentação.

---

## 9. Relação com o MCP

O MCP não deve ser tratado como um apêndice técnico separado do produto.  
No APP32, ele deve funcionar como uma **surface operacional governada** para leitura, assistência e automação controlada.

Por isso, o manual unificado deve ensinar que:

- algumas operações existem apenas no APP;
- outras podem ser ensinadas pela IA, mas não executadas por ela;
- outras podem ser executadas via MCP, desde que a surface permita;
- sensibilidade financeira, administrativa e de governança depende da surface correta.

### Princípio MCP First

Quando a IA precisar consultar estado operacional real do sistema, o caminho preferencial deve ser:

- MCP;
- ou outra fonte viva equivalente;

e não memória inferida ou suposição.

### Princípio de segregação

O manual deve sempre deixar claro:

- o que é `user`;
- o que é `admin`;
- o que é `analytics`;
- o que é `ops`;
- e quais módulos/ações exigem bloqueio ou escalonamento.

---

## 10. Árvore expandida dos 10 ramos principais

Esta seção propõe a expansão conceitual inicial da árvore principal do manual.  
Ela ainda não congela o formato oficial, mas já define como cada ramo deve ser pensado.

### 10.1. Squad de Agentes

**Objetivo do ramo**  
Organizar a explicação sobre quais agentes/squads existem, para que servem, quando entram em ação e quais limites precisam respeitar.

**Subárvore inicial**

```text
Squad de Agentes
├── visão do ramo
├── agentes disponíveis
├── papéis e especialidades
├── limites e bloqueios
├── handoff e escalonamento
├── relação com usuário
├── relação com APP
├── relação com MCP
└── governança do runtime
```

**Leitura humana esperada**
- entender que nem toda IA faz a mesma coisa;
- saber qual agente ajuda em cada contexto;
- entender quando há transferência, escalonamento ou bloqueio.

**Uso por IA / MCP**
- explicitar papéis, boundaries e especialidades;
- evitar sobreposição indevida entre agentes;
- reforçar governança de handoff, profile, surface e runtime.

**Governança / limites**
- o ramo deve deixar explícito qual agente pode atuar em cada tipo de demanda;
- deve impedir transferência invisível de responsabilidade entre agentes;
- deve registrar quando há necessidade de handoff, bloqueio ou confirmação humana.

**Maturidade atual percebida**
- **forte em governança técnica**;
- ainda precisa virar **árvore pedagógica unificada** para uso no manual.

**Desdobramento inicial recomendado**

```text
Squad de Agentes
├── Agente Coordenador
│   ├── triagem inicial
│   ├── entendimento do objetivo do usuário
│   ├── escolha do próximo agente
│   └── consolidação da resposta final
├── Agente Comercial
│   ├── clientes e oportunidades
│   ├── propostas e negociação
│   ├── acompanhamento comercial
│   └── leitura do contexto de mercado comercial do cliente
├── Agente Operacional
│   ├── rotina e execução
│   ├── tarefas, agenda e follow-up
│   ├── processos e acompanhamento
│   └── apoio à operação do dia a dia
├── Agente Adm/Financeiro
│   ├── leitura financeira controlada
│   ├── fluxos administrativos
│   ├── sensibilidade e aprovações
│   └── governança de operações críticas
├── Especialistas técnicos
│   ├── arquiteto
│   ├── backend/api
│   ├── backend/service
│   ├── frontend
│   ├── DBA
│   ├── AI engineer
│   └── QA automation
└── Regras de handoff
    ├── quando manter no agente atual
    ├── quando escalar
    ├── quando bloquear
    └── quando exigir confirmação humana
```

**Regras conceituais de handoff**

- o **Coordenador** deve ser a porta de entrada quando a intenção do usuário ainda estiver ambígua;
- o **Comercial** entra quando o assunto principal for cliente, oportunidade, proposta, negociação ou contrato comercial;
- o **Operacional** entra quando o assunto principal for rotina, execução, agenda, tarefa ou acompanhamento processual;
- o **Adm/Financeiro** entra quando houver contexto administrativo, financeiro ou sensível;
- os **especialistas técnicos** entram quando a necessidade sair do campo de uso do produto e entrar em arquitetura, implementação, contrato, dados, quality gate ou runtime.

**Limite importante**

O manual não deve fazer o usuário decorar a engenharia interna dos agentes.  
Ele deve explicar isso de modo funcional:

- “quem ajuda com o quê”;
- “quando a IA troca de contexto”;
- “quando a resposta precisa de validação humana”;
- “quando a IA não pode seguir sozinha”.

### 10.2. Utilização Agentes x Versus APP x Internet x IA

**Objetivo do ramo**  
Explicar como decidir corretamente entre operar direto no APP, consultar MCP, usar internet, acionar agente especializado ou responder apenas com raciocínio local da IA.

**Subárvore inicial**

```text
Utilização Agentes x Versus APP x Internet x IA
├── visão do ramo
├── quando usar o APP
├── quando usar MCP
├── quando usar internet
├── quando usar apenas IA
├── critérios de escolha
├── limites de segurança
├── auditoria e rastreabilidade
└── bloqueios e escalonamento
```

**Leitura humana esperada**
- entender por que a IA às vezes consulta o sistema;
- entender por que em outros casos ela precisa consultar internet;
- saber quando a resposta é explicativa e quando é baseada em dado vivo.

**Uso por IA / MCP**
- formalizar a política de decisão entre fontes;
- reforçar MCP First para estado operacional;
- diferenciar dado vivo do APP, conhecimento geral da IA e internet externa;
- impedir uso inadequado de canal em contexto sensível.

**Governança / limites**
- internet não substitui o APP32 para dado operacional interno;
- IA não deve inventar estado vivo do sistema;
- MCP não deve ser usado fora da surface e do perfil corretos;
- operação sensível não deve ser escondida dentro de explicação aparentemente inocente;
- sempre que houver risco de tenant crossing, a operação deve ser bloqueada.

**Maturidade atual percebida**
- **forte em princípio**, ainda **disperso em múltiplos documentos**;
- ramo muito importante para reduzir erro operacional e drift de explicação.

**Matriz conceitual inicial de decisão**

```text
Pergunta ou ação do usuário
├── É uso do próprio APP32?
│   ├── Sim
│   │   ├── Precisa de dado vivo?
│   │   │   ├── Sim -> APP/MCP primeiro
│   │   │   └── Não -> IA pode explicar com base no manual
│   │   └── Envolve ação sensível?
│   │       ├── Sim -> surface/perfil/confirmacao humana
│   │       └── Não -> orientação ou execução permitida
│   └── Não
├── É informação externa e atual?
│   ├── Sim -> internet/fonte externa confiável
│   └── Não
├── É explicação conceitual ou educacional?
│   ├── Sim -> resposta da IA com base no manual/paper/spec
│   └── Não
└── É tema misto?
    ├── usar APP/MCP para estado operacional
    ├── usar internet para contexto externo
    └── usar IA para síntese e explicação
```

**Ordem conceitual de precedência**

Quando houver dúvida sobre qual canal usar, a ordem preferencial deve ser:

1. **APP/MCP** para estado operacional interno do APP32
2. **internet** para contexto externo, atual e não interno ao APP32
3. **IA por raciocínio/documentação** para explicação, síntese, treinamento e apoio conceitual

### Regra de ouro

> dado operacional do APP32 deve nascer do APP32 ou do MCP;  
> contexto externo atual deve nascer de fonte externa;  
> explicação e síntese podem nascer da IA, desde que ancoradas no manual canônico.

**Exemplos práticos de decisão**

#### a) “Como faço para lançar uma rotina no sistema?”
- canal principal: **IA explicando o APP**
- fonte principal: **manual unificado + tela/módulo correspondente**
- internet: **não necessária**

#### b) “Quais são minhas tarefas de hoje?”
- canal principal: **MCP/APP**
- fonte principal: **estado operacional vivo**
- IA: interpreta e resume o resultado

#### c) “Qual a cotação atual de um índice externo?”
- canal principal: **internet/fonte externa**
- APP/MCP: não é a fonte primária
- IA: traduz e contextualiza

#### d) “Me explique a diferença entre surface user e admin.”
- canal principal: **IA com base em documentação canônica**
- fonte principal: **manual + docs de governança**
- APP/MCP: só se houver necessidade de validar contexto real de acesso

#### e) “Pode executar essa leitura financeira?”
- primeiro decidir:
  - há surface compatível?
  - o perfil atual permite?
  - o dado é sensível?
  - exige confirmação humana?
- só depois a IA decide entre **explicar**, **consultar** ou **bloquear**

### 10.3. Gestão da Rotina

**Objetivo do ramo**  
Organizar o uso operacional do dia a dia, com foco em tarefas, agenda, jornada, acompanhamento e execução recorrente.

**Subárvore inicial**

```text
Gestão da Rotina
├── visão do módulo
├── tarefas
├── agenda / jornada
├── acompanhamento operacional
├── processos relacionados
├── pendências e prioridades
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- o que precisa ser feito;
- por quem;
- em que prazo;
- em que ordem;
- como acompanhar a execução.

**Uso por IA / MCP**
- domínio canônico `routine`;
- filtros por responsável, status, data e contexto;
- leitura operacional tenant-safe;
- apoio na priorização e no resumo da rotina;
- eventual vínculo com jornadas materializadas e processos.

**Governança / limites**
- `company_id` é obrigatório em qualquer leitura ou mutação real;
- a IA deve diferenciar orientação operacional de execução automatizada;
- a surface `user` deve permanecer no menor privilégio possível;
- não pode haver cruzamento de tarefas ou jornadas entre tenants.

**Maturidade atual percebida**
- **operacional** no APP;
- **parcialmente coberto** no MCP com boa base para evolução;
- bom candidato para ser um dos primeiros ramos formalizados.

#### 10.3.1. Agenda / jornada — coerência entre APP e MCP

Na agenda operacional do APP, a camada visual pode reorganizar a leitura do usuário em seções como:
- instâncias de processos;
- atividades de projetos;
- reuniões;
- eventos avulsos;
- planejamento operacional.

Essa organização é **semântica de UI**, não contrato canônico de tool.

Para este ramo, a regra de coerência é:
- mudanças de ordem, rótulo, colapso padrão, cor e agrupamento visual **não obrigam** mudança de tool MCP;
- mudanças de payload, permissão, surface, shape de entrada/saída ou risco operacional **obrigam** revisão de catálogo e contrato MCP;
- a IA deve explicar a agenda no vocabulário do APP, mas operar no vocabulário canônico do domínio.

No estado atual, a agenda MCP já comporta itens operacionais como:
- `process_instance`
- `project_task`
- `meeting`
- `manual`

Portanto, a evolução recente do calendário reforça uma diretriz importante: **UI pedagógica pode evoluir sem forçar alteração imediata do contrato MCP**, desde que a intenção operacional permaneça a mesma.

### 10.4. Gestão Financeira

**Objetivo do ramo**  
Organizar a leitura e a operação financeira controlada, diferenciando claramente consulta, revisão, classificação, conciliação e execução sensível.

**Subárvore inicial**

```text
Gestão Financeira
├── visão do módulo
├── fluxo de caixa
├── entradas e saídas
├── lançamentos
├── classificação
├── conciliação bancária
├── orçamento
├── automações financeiras
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- consultar posição financeira;
- entender entradas, saídas e saldo;
- revisar classificações;
- acompanhar conciliações e automações;
- operar com atenção a aprovações e sensibilidade.

**Uso por IA / MCP**
- domínio canônico `finance`;
- bloqueio explícito em `surface=user` para leituras sensíveis;
- separação entre consulta executiva, operação administrativa e automação;
- forte exigência de `company_id`, surface e trilha de auditoria.

**Governança / limites**
- leituras financeiras sensíveis não devem nascer em `surface=user`;
- mutações financeiras exigem política de risco, trilha e, quando aplicável, confirmação humana;
- a IA deve distinguir consulta, classificação, conciliação e automação;
- qualquer risco de tenant crossing é falha crítica.

**Maturidade atual percebida**
- **operacional com restrições**;
- ramo já forte em cobertura MCP;
- exige documentação pedagógica e governança especialmente rigorosas.

### 10.5. Gestão Estratégica

**Objetivo do ramo**  
Organizar a camada de direção, metas, indicadores, planos e projetos estratégicos do negócio.

**Subárvore inicial**

```text
Gestão Estratégica
├── visão do módulo
├── planos
├── objetivos e direcionadores
├── indicadores
├── metas
├── projetos estratégicos
├── acompanhamento de evolução
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- entender o plano e seus direcionadores;
- acompanhar metas e indicadores;
- revisar iniciativas e projetos estratégicos;
- conectar estratégia com execução.

**Uso por IA / MCP**
- apoio na explicação de indicadores, metas e contexto;
- leitura de análises e resumos;
- eventual operação assistida de acompanhamento;
- necessidade de amadurecimento do catálogo MCP funcional.

**Governança / limites**
- a IA não deve prometer capability estratégica que ainda não esteja formalizada;
- análises estratégicas devem respeitar perfil, escopo e superfície de leitura;
- explicações executivas não devem virar mutações implícitas sem gate adequado.

**Maturidade atual percebida**
- **operacional no APP**;
- **parcialmente coberto** do ponto de vista MCP/manual canônico;
- ramo prioritário para consolidação documental.

### 10.6. Gestão Comercial

**Objetivo do ramo**  
Organizar o uso comercial do sistema, cobrindo pipeline, oportunidades, propostas e contratos comerciais.

**Subárvore inicial**

```text
Gestão Comercial
├── visão do módulo
├── pipeline
├── oportunidades
├── propostas
├── negociação
├── contratos comerciais
├── acompanhamento comercial
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- visualizar oportunidades;
- acompanhar avanço comercial;
- apoiar elaboração de proposta;
- entender status e próximos passos de negociação.

**Uso por IA / MCP**
- capacidade de explicar o fluxo comercial sem prometer capabilities inexistentes;
- possível apoio baseado hoje em estruturas indiretas de processos/projetos;
- necessidade de deixar explícito quando algo é roadmap e não capability canônica.

**Governança / limites**
- o manual deve deixar claro o que já é capability canônica e o que ainda é composição indireta;
- a IA não pode transformar roadmap comercial em promessa operacional;
- dados de pipeline, proposta e contrato devem respeitar perfil e tenant.

**Maturidade atual percebida**
- **em construção** como domínio canônico MCP;
- requer honestidade documental forte;
- ramo importante para amadurecimento semântico do produto.

### 10.7. Sistema

**Objetivo do ramo**  
Organizar o entendimento das áreas técnicas e administrativas do sistema, incluindo configurações, auditoria, integrações, permissões e API/MCP.

**Subárvore inicial**

```text
Sistema
├── visão do módulo
├── configurações
├── auditoria
├── permissões
├── integrações
├── API / MCP
├── console operacional
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- localizar configurações corretas;
- entender permissões;
- revisar integrações e auditoria;
- distinguir área funcional de área técnica.

**Uso por IA / MCP**
- explicar com cuidado o que o usuário pode fazer sozinho;
- bloquear orientação indevida em temas administrativos sensíveis;
- separar uso do APP de operação técnica via MCP.

**Governança / limites**
- configurações, permissões, auditoria e integrações exigem atenção especial a perfil e surface;
- a IA deve separar claramente explicação funcional de operação técnica privilegiada;
- nem toda capacidade do ramo Sistema deve ser exposta ao usuário final.

**Maturidade atual percebida**
- **operacional**, porém disperso em múltiplas telas e docs;
- precisa de consolidação pedagógica clara.

### 10.8. Meu Perfil

**Objetivo do ramo**  
Organizar tudo o que diz respeito à identidade operacional do usuário dentro do sistema.

**Subárvore inicial**

```text
Meu Perfil
├── visão do módulo
├── dados pessoais
├── identidade operacional
├── preferências
├── vínculos com empresa/perfil
├── contexto de acesso
├── uso no APP
├── uso orientado por IA
└── uso via MCP
```

**Leitura humana esperada**
- entender seus próprios dados;
- revisar perfil e contexto;
- saber como a identidade influencia acesso e operação.

**Uso por IA / MCP**
- explicar limites do perfil atual;
- orientar o usuário sem expor informações administrativas indevidas;
- eventualmente apoiar leitura do contexto de acesso e configuração do token MCP.

**Governança / limites**
- o usuário deve ver apenas o que pertence ao próprio contexto de identidade;
- a IA não deve expor dados administrativos além do necessário;
- mudanças ligadas a perfil, vínculo ou acesso precisam respeitar policy e trilha.

**Maturidade atual percebida**
- **operacional no APP**;
- documentação pedagógica ainda **parcial**;
- bom ramo para conectar identidade do usuário com governança do sistema.

### 10.9. Usos Transversais

**Objetivo do ramo**  
Reunir tudo o que atravessa vários módulos e não deve ficar espalhado em explicações duplicadas.

**Subárvore inicial**

```text
Usos Transversais
├── como navegar no APP
├── como pedir ajuda para a IA
├── como a IA decide entre orientar e executar
├── company_id e tenant
├── surfaces e perfis
├── boas práticas de operação
├── segurança e privacidade
├── auditoria e rastreabilidade
└── erros comuns e bloqueios
```

**Leitura humana esperada**
- entender como circular pelo sistema;
- saber quando pedir ajuda;
- saber por que determinados acessos ou ações são bloqueados.

**Uso por IA / MCP**
- operar com base em governança transversal;
- não repetir regras sensíveis em cada módulo;
- reaproveitar uma camada central de explicação sobre tenant, surface, perfil e segurança.

**Governança / limites**
- este ramo deve concentrar regras comuns para evitar drift entre módulos;
- tenant, surface, perfil, auditoria e segurança devem ser tratados aqui como base transversal;
- o que for regra estrutural não deve ser reescrito de forma conflitante em outros ramos.

**Maturidade atual percebida**
- **disperso** entre vários materiais;
- ramo crítico para reduzir drift global.

### 10.10. Análises e Relatórios

**Objetivo do ramo**  
Organizar a leitura analítica e os relatórios do APP32 como uma camada transversal com linguagem própria.

**Subárvore inicial**

```text
Análises e Relatórios
├── visão do ramo
├── relatórios operacionais
├── relatórios gerenciais
├── análises executivas
├── indicadores e consolidados
├── filtros e recortes
├── leitura no APP
├── apoio da IA na interpretação
└── uso via MCP / analytics
```

**Leitura humana esperada**
- localizar o relatório certo;
- entender o recorte e o filtro;
- diferenciar relatório operacional de leitura executiva;
- interpretar números com contexto.

**Uso por IA / MCP**
- apoiar leitura, resumo e explicação;
- respeitar sensibilidade e surface analítica;
- evitar misturar análise executiva com mutação operacional.

**Governança / limites**
- relatórios e análises devem explicitar recorte, filtro, origem e sensibilidade;
- a surface `analytics` deve permanecer orientada a leitura e não a mutação operacional;
- a IA deve diferenciar dado consolidado, dado operacional e inferência interpretativa.

**Maturidade atual percebida**
- **parcialmente estruturado**;
- muito importante para surface `analytics`;
- precisa nascer como ramo formal para não ficar pulverizado por módulo.

### 10.11. Regra de consistência entre os ramos

Todos os 10 ramos devem obedecer à mesma disciplina:

- visão humana;
- uso por IA / MCP;
- governança / limites;
- maturidade atual;
- roadmap de consolidação.

Isso evita que alguns ramos virem “manual de tela”, enquanto outros virem apenas “catálogo técnico”.

---

## 11. Matriz-resumo dos ramos principais

Esta matriz existe para consolidar, em leitura rápida, a função de cada ramo do manual unificado.

| Ramo | Foco principal | Uso por IA / MCP | Governança / limites | Maturidade |
|---|---|---|---|---|
| **Squad de Agentes** | Explicar quem atua, especialidades, handoffs e papéis | IA usa este ramo para decidir quem conduz, quando escalar e como compor resposta | Não pode haver sobreposição invisível de responsabilidade; handoff, bloqueio e confirmação humana precisam ser explícitos | **forte em governança técnica** |
| **Utilização Agentes x Versus APP x Internet x IA** | Explicar como escolher entre APP, MCP, internet e raciocínio da IA | IA usa este ramo para decidir a fonte/canal correto conforme tipo de pergunta ou ação | Dado operacional interno nasce de APP/MCP; contexto externo atual nasce de fonte externa; resposta sensível exige controle de surface e tenant | **forte em princípio, ainda disperso** |
| **Gestão da Rotina** | Operação do dia a dia, tarefas, jornada e acompanhamento | IA/MCP apoiam listagem, resumo, priorização e contexto da rotina | `company_id`, menor privilégio e segregação tenant-safe são obrigatórios | **operacional** |
| **Gestão Financeira** | Fluxo de caixa, lançamentos, classificação, conciliação e orçamento | IA/MCP apoiam leitura controlada, revisão, classificação e automações autorizadas | Leituras sensíveis não devem nascer em `surface=user`; mutações exigem trilha, perfil e, quando aplicável, confirmação humana | **operacional com restrições** |
| **Gestão Estratégica** | Planos, metas, indicadores e projetos estratégicos | IA/MCP apoiam leitura, síntese e acompanhamento assistido | Não prometer capabilities estratégicas ainda não formalizadas; análises devem respeitar perfil e escopo | **operacional no APP, parcial no MCP** |
| **Gestão Comercial** | Pipeline, oportunidades, propostas e contratos comerciais | IA/MCP apoiam explicação do fluxo e, quando houver, capabilities canônicas ou composições indiretas | Roadmap não pode ser tratado como capability já pronta; dados comerciais devem respeitar tenant e perfil | **em construção** |
| **Sistema** | Configurações, permissões, auditoria, integrações e API/MCP | IA/MCP podem orientar e, em alguns casos, operar tecnicamente em contexto autorizado | Nem toda capacidade do ramo deve ser exposta ao usuário final; atenção especial a surface e privilégio | **operacional, porém disperso** |
| **Meu Perfil** | Identidade operacional, dados pessoais, contexto e preferências | IA/MCP apoiam leitura de contexto, limites do perfil e orientação de uso | O usuário só deve ver o próprio contexto; mudanças de acesso e vínculo exigem policy e trilha | **operacional no APP, documentação parcial** |
| **Usos Transversais** | Regras comuns de navegação, ajuda, tenant, surface, segurança e bloqueios | IA/MCP usam este ramo como camada comum de comportamento e explicação | Regras estruturais devem nascer aqui para evitar drift entre módulos | **disperso, porém crítico** |
| **Análises e Relatórios** | Relatórios operacionais, gerenciais e análises executivas | IA/MCP apoiam leitura, resumo, interpretação e uso analítico controlado | `analytics` deve permanecer orientado a leitura; é preciso diferenciar consolidado, operacional e interpretação | **parcialmente estruturado** |

### 11.1. Como usar esta matriz

Esta matriz não substitui a árvore detalhada.  
Ela serve para:

- leitura executiva rápida;
- alinhamento de linguagem entre time, IA e produto;
- verificação de coerência entre ramo, uso por IA/MCP e governança;
- priorização da evolução documental posterior.

### 11.2. Função da matriz no amadurecimento do paper

Se a árvore é a estrutura principal do manual, a matriz é o quadro de controle resumido.

Ela ajuda a responder rapidamente:

- qual é a finalidade do ramo;
- qual é o tipo de uso por IA / MCP;
- qual é o principal limite de governança;
- qual é o estado atual de maturidade.

---

## 12. Papel da IA no manual

O manual unificado não serve apenas para o usuário “ler”.  
Ele serve para que a IA consiga cumprir quatro papéis com consistência:

### 12.1. Professora do sistema

A IA explica:

- onde clicar;
- o que cada área significa;
- como preencher;
- o que observar;
- como interpretar o resultado.

### 12.2. Copiloto operacional

A IA ajuda o usuário a:

- escolher o módulo certo;
- formular consultas;
- entender filtros;
- revisar contexto antes de executar uma ação;
- evitar erro operacional.

### 12.3. Operadora governada

Quando houver capability autorizada, a IA pode:

- consultar;
- listar;
- orientar;
- preparar rascunhos;
- executar ações permitidas;

sempre respeitando tenant, surface, perfil e risco.

### 12.4. Guardiã de boundary

A IA também deve saber dizer:

- “isso eu posso explicar, mas não executar”;
- “isso exige surface diferente”;
- “isso precisa de confirmação humana”;
- “isso não pode ser exposto neste contexto”.

---

## 13. Formato documental recomendado

O desenho mais consistente para o APP32 é separar o assunto em camadas complementares:

### 13.1. Paper

Define:

- a tese do manual unificado;
- a visão de produto/documentação;
- a relação entre IA, usuário, APP e MCP.

### 13.2. SPEC posterior

Deve congelar:

- a estrutura oficial do manual;
- o template por módulo;
- os campos obrigatórios;
- a relação entre docs humanas e docs MCP.

### 13.3. Playbooks posteriores

Devem orientar:

- como a IA ensina cada módulo;
- como faz handoff;
- como decide entre APP e MCP;
- como tratar bloqueios, ambiguidades e escalonamento.

### 13.4. Runbooks posteriores

Devem orientar:

- ativação;
- publicação;
- checklist de atualização documental;
- smoke de coerência entre APP, MCP e manual.

### 13.5. Harnesses posteriores

Devem empacotar:

- como os agentes ou squads usam esse material no runtime;
- quais tools consultar primeiro;
- quais bloqueios aplicar;
- como evitar drift entre explicação e operação.

---

## 14. Estrutura mínima sugerida do futuro template por módulo

Quando o assunto sair deste paper e virar SPEC, cada módulo deve ter ao menos:

1. **nome do módulo**
2. **objetivo**
3. **personas que usam**
4. **entrada pelo APP**
5. **principais jornadas**
6. **conceitos-chave**
7. **passo a passo base**
8. **perguntas frequentes**
9. **uso por IA / MCP**
10. **governança / limites**
11. **erros comuns**
12. **o que nunca expor**

---

## 15. Fontes já existentes que este manual deve reaproveitar

O manual unificado não deve nascer do zero ignorando o acervo atual.  
Ele deve consolidar e reaproveitar principalmente:

- `app32/docs/governance/governanca_documental_oficial_v1.md`
- `docs/paper_plataforma_modular_customizavel_app32.md`
- `docs/mcp_claude_code_app32.md`
- `docs/mcp_remote_claude_ai.md`
- `docs/mcp/catalogo_features.yaml`
- `docs/mcp/mcp_tools_contract.json`
- `docs/mcp/features/*.md`

Além disso, deve absorver a árvore canônica de módulos e domínios já consolidada no Sapiens/MCP.

---

## 16. Riscos que este paper tenta evitar

### 16.1. Drift entre UI e IA

A UI ensina uma coisa, a IA fala outra.

### 16.2. Drift entre APP e MCP

O fluxo do APP existe, mas a capability MCP não representa a mesma intenção operacional.

Nem toda mudança no APP caracteriza esse drift.

Exemplo importante: quando a agenda operacional muda apenas a organização visual — nomes de seções, ordem, cards e colapso padrão — sem alterar payload, permissão, surface ou semântica da ação, o efeito é de **apresentação**, não de contrato.

O drift real aparece quando:
- o APP passa a ensinar uma intenção operacional nova que a tool MCP não consegue representar;
- a UI passa a depender de dados que o contrato MCP não expõe;
- a IA, ao usar o catálogo, perde a capacidade de explicar corretamente o fluxo que o usuário vê no APP.

### 16.3. Manual humano sem governança operacional

Bom para treinamento, ruim para automação segura.

### 16.4. Manual técnico sem linguagem de negócio

Bom para integração, ruim para adoção pelo usuário.

### 16.5. Catálogo MCP sem semântica pedagógica

A IA consegue executar, mas não consegue ensinar corretamente.

---

## 17. Recomendação de evolução em fases

### Fase 1 — consolidar o paper

Confirmar esta tese como direção oficial de amadurecimento.

### Fase 2 — criar a SPEC do manual unificado

Congelar:

- template oficial;
- campos obrigatórios;
- política de ligação entre APP e MCP;
- política de surfaces e restrições.

### Fase 3 — publicar primeiros módulos prioritários

Prioridade sugerida:

1. **Squad de Agentes**
2. **Utilização Agentes x Versus APP x Internet x IA**
3. **Gestão da Rotina**
4. **Gestão Financeira**
5. **Gestão Estratégica**
6. **Gestão Comercial**
7. **Sistema**
8. **Meu Perfil**
9. **Usos Transversais**
10. **Análises e Relatórios**

### Fase 4 — ligar IA ao manual

Garantir que agentes, copilotos e conectores MCP consultem o material canônico antes de ensinar ou operar.

### Fase 5 — criar smokes de coerência documental

Validar periodicamente:

- se o APP continua coerente com o manual;
- se o MCP continua coerente com o manual;
- se a IA continua ensinando a versão certa do sistema.

---

## 18. Critério de saída deste paper

Este paper cumpre seu papel quando gerar, no mínimo:

1. uma **SPEC oficial** do Manual Unificado;
2. um **template canônico por módulo**;
3. pelo menos os primeiros módulos publicados no padrão novo;
4. um caminho explícito para consumo por IA e por MCP.

Quando isso acontecer, o tema deixa de estar apenas em amadurecimento conceitual e passa a exigir congelamento formal da estrutura oficial.
