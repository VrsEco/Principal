# Matriz de Alinhamento dos 4 Pilares — Versus Gestão Corporativa

## Status
Versão inicial v1 para controle executivo-operacional da coerência entre os pilares da Versus Gestão Corporativa.

## Natureza do documento
Este documento complementa:

- `C:/GestaoVersus/app32/app32/docs/specifications/estruturacao_versus_gestao_corporativa_paper_v1.md`
- `C:/GestaoVersus/app32/app32/docs/specifications/mapa_formal_versus_gestao_corporativa_v1.md`

Seu papel não é aprofundar conceito, mas controlar execução, evitar drift entre pilares e dar critério de prontidão para avanço.

---

## 1. Finalidade da matriz
A matriz existe para garantir que a Versus evolua de forma coerente e concomitante em quatro pilares inseparáveis:

1. `Forma de Trabalho`
2. `Ferramenta`
3. `Agentes`
4. `Orquestração`

O objetivo é evitar situações como:
- método prometendo mais do que a plataforma suporta
- capability pronta sem papel operacional claro
- agentes mais maduros do que a governança
- orquestração indefinida para fluxos já em implantação
- adoção acelerada com arquitetura incompleta

---

## 2. Como usar esta matriz
Toda frente relevante de execução deve ser analisada sob os quatro pilares.

Para cada frente, deve-se verificar:
- o que já está definido
- o que ainda falta
- o risco de desalinhamento
- a condição mínima para entrar em execução

Esta matriz deve ser usada:
- na abertura de backlog
- na priorização executiva
- na revisão arquitetural
- no planejamento de MVP e pilotos
- na avaliação de prontidão de rollout

---

## 3. Estrutura de leitura
Cada linha da matriz deve responder:

- qual é a frente ou decisão
- qual é a definição necessária na `Forma de Trabalho`
- qual é a sustentação exigida da `Ferramenta`
- qual é o papel esperado dos `Agentes`
- qual é a regra mínima de `Orquestração`
- qual é o status atual
- qual é o risco
- qual é a próxima ação

---

## 4. Escala de status sugerida
- `Não iniciado`
- `Inicial`
- `Parcial`
- `Consistente`
- `Pronto para execução`

## 5. Escala de risco sugerida
- `Baixo`
- `Médio`
- `Alto`
- `Crítico`

---

## 6. Matriz de alinhamento atual

| Frente / Decisão | Forma de Trabalho | Ferramenta | Agentes | Orquestração | Status | Risco | Próxima ação |
|---|---|---|---|---|---|---|---|
| Operating Model da Versus | Direção correta definida, mas ainda precisa maior decomposição em fases, ritos, entregáveis e handoffs | APP32 e MCP já posicionados como suporte estrutural | Squads já conceituados em alto nível | Coordenação geral definida, mas ainda sem regra operacional completa por rito | Parcial | Alto | Detalhar o operating model oficial da Versus |
| APP32 como núcleo operacional | Alinhado ao método como base operacional | Bem definido conceitualmente como domínio + dados + services + governança | Squads dependem desse desenho | Orquestração já pressupõe APP32 como espaço comum | Consistente | Médio | Confirmar isso capability a capability |
| MCP como contrato canônico | Coerente com a metodologia | Definido como interface oficial dos squads | Coerente com runtime externo | Orquestração depende do MCP para governança real | Consistente | Baixo | Manter monitoramento e evoluir OAuth/roteiros por frente |
| Runtime externo dos squads | Alinhado à estratégia | Ainda convive com runtime interno legado no APP32 | Premissa definida para Squad Versus e Squad Cliente | Orquestração futura assume reasoning externo | Parcial | Alto | Separar principal, fallback e legado no plano técnico |
| Squad Versus | Papel consultivo e governante bem definido | Ferramenta ainda precisa capability map adequado | Arquitetura-base já definida | Ainda faltam regras operacionais detalhadas de acionamento | Parcial | Médio | Derivar a arquitetura operacional do Squad Versus |
| Squad Cliente | Papel contextual e operacional bem definido | Depende de surfaces, identidade e capabilities mais maduras | Arquitetura-base já definida | Ainda faltam regras claras de entrada, precedência e handoff | Parcial | Alto | Derivar a arquitetura operacional do Squad Cliente |
| Squad de Engenharia | Papel técnico claramente definido | Altamente aderente ao APP32/MCP | Escopo do squad está coerente | Falta encaixe formal na governança contínua dos demais pilares | Consistente | Médio | Formalizar ritos de alinhamento com método e produto |
| Papel do Sapiens / front door | Ainda precisa fechamento final | APP32 pode suportar, mas depende de decisão de experiência | Pode operar como entrada do Squad Versus ou camada neutra | É central para despacho e adoção | Parcial | Alto | Fechar o papel oficial do Sapiens e o canal inicial de uso |
| Identidade e autorização por ator | Conceito reconhecido | Ainda não detalhado em contratos e políticas suficientes | Fundamental para humano/agente Versus, humano/agente Cliente e Engenharia | Base de toda orquestração segura | Inicial | Crítico | Executar o passo de identidade, autenticação, papéis e surfaces |
| Objetos colaborativos | Conceito bem amadurecido | Ainda precisa modelo operacional e possivelmente modelo de dados | Essencial para colaboração real entre squads e humanos | Handoffs e revisões dependem disso | Inicial | Alto | Modelar objetos colaborativos mínimos no APP32 |
| Utilização assistida | Bem tratada no papel | APP32 e experiência ainda precisam materialização | Impacta sobretudo Squad Cliente e entrada do sistema | Exige despacho e postura dinâmica | Parcial | Médio | Implementar o modo assistido no fluxo inicial |
| Maturidade assistida | Roteiros MCP das quatro frentes definidos e versionáveis | Cockpit já expõe seção de Análise Assistida, registro, validações e decisão | Squads têm papel explícito por frente | Orquestração começa pela IA/CLI via MCP, registra retorno no APP32 e exige gate do consultor | Parcial | Médio | Validar uso real dos roteiros nas quatro frentes e evoluir protocolos tenant/global |
| Canal inicial de uso | Ainda em aberto | Pode ser APP32, chat, experiência guiada ou híbrido | Afeta diretamente a adoção dos squads | Define o front door real | Inicial | Alto | Decidir canal inicial do Modelo B híbrido assistido |
| Primeiro fluxo MVP | Intuição boa para começar pelo operacional assistido | Capabilities ainda não inventariadas | Squads já sugerem foco operacional inicial | Orquestração ainda precisa recorte mínimo | Inicial | Alto | Confirmar o fluxo MVP após o inventário de capabilities |
| Governança de mudança entre pilares | Problema reconhecido | Ainda não institucionalizada | Ainda sem disciplina formal por squad | Ainda sem change control cruzado | Não iniciado | Crítico | Definir rito formal de revisão cruzada entre os pilares |

---

## 7. Critérios de prontidão para execução
Uma frente só deve entrar em execução quando houver, no mínimo:

### 7.1 Forma de Trabalho
- definição suficiente do fluxo ou rito envolvido
- clareza mínima de responsabilidade humana e agentic
- objetivo operacional claro

### 7.2 Ferramenta
- capability existente ou backlog explícito e priorizado
- surface prevista
- escopo por `company_id`
- trilha mínima garantida

### 7.3 Agentes
- papel do squad claramente definido
- limites explícitos do que o agente pode e não pode fazer
- coerência com a maturidade real da capability

### 7.4 Orquestração
- regra mínima de entrada
- regra mínima de handoff
- regra mínima de aprovação, quando aplicável
- critério de fallback ou intervenção humana

---

## 8. Sinais de alerta
Não avançar para execução ampla quando houver:

- agente mais maduro do que a capability real
- capability fora do MCP em fluxo relevante
- decisão humana importante não modelada
- promessa metodológica sem sustentação da ferramenta
- identidade, papel ou surface indefinidos
- fluxo sem trilha mínima de evidência
- experiência assistida sem estratégia de autonomia progressiva

---

## 9. Aplicação imediata sobre o backlog atual
Esta matriz aponta que os itens corretos para abrir a execução agora são:

1. inventário de capabilities APP32/MCP
2. identidade, autenticação, papéis e surfaces por ator
3. definição do front door, do Sapiens e do canal inicial de uso
4. modelagem dos objetos colaborativos mínimos
5. recorte do primeiro fluxo MVP operacional assistido

Essa sequência está aderente ao backlog já aberto no projeto `AA.J.15`.

---

## 9.1 Aplicação imediata após estabilização do MCP

Com a conexão MCP estável, o avanço recomendado passa a ser:

1. consolidar os roteiros MCP das quatro frentes no Cockpit do Consultor;
2. testar a IA/CLI do cliente usando o MCP para ler contexto, evidências e gaps;
3. registrar a análise recebida, validações dos squads e decisão do consultor no APP32;
4. evoluir protocolos versionados por tenant/global conforme o método amadurecer;
5. usar Business Review apenas para registrar valor agregado quando a frente gerar resultado mensurável.

## 10. Governança de atualização da matriz
A matriz deve ser revista sempre que houver:

- criação de novo fluxo estratégico
- entrada de novo squad ou agente relevante
- mudança na metodologia Versus
- abertura de capabilities novas no MCP
- mudança de canal de uso
- mudança nas regras de identidade, surface ou governança

---

## 11. Veredito executivo
A Versus já possui hoje:
- bom alinhamento conceitual
- mapa formal consolidado
- backlog inicial coerente

Mas ainda precisa transformar esse alinhamento em disciplina operacional contínua.

Esta matriz existe para isso:
- impedir drift entre pilares
- controlar prontidão real
- orientar priorização segura
- preservar coerência entre método, sistema, agentes e orquestração
