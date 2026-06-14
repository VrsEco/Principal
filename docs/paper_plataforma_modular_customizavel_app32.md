# APP32 como Plataforma Modular Customizável por Cliente

**Data:** 2026-04-30  
**Status:** Diretriz proposta para evolução arquitetural e comercial  
**Projeto estruturante:** AA.J.54 — Arquitetura APP32 — Plataforma Modular Customizável por Cliente  
**Escopo:** APP32 / Gestão Versus

---

## 1. Resumo executivo

O APP32 deve evoluir para uma **plataforma multi-tenant, modular e orientada a processos**, capaz de atender operações distintas por cliente sem transformar o core em um repositório de regras ad hoc.

A diretriz central é:

> vender ao mercado a percepção correta de software altamente adaptável ao processo do cliente, sem permitir que cada customização contamine a arquitetura base.

Isso significa que o APP32 **não deve ser um produto rígido**, mas também **não deve virar um sistema diferente por cliente dentro do mesmo código**.

---

## 2. Problema de negócio

Os clientes da Versus possuem operações heterogêneas:

- alguns exigem uma solução muito específica, com baixa reaplicabilidade imediata
- outros exigem capacidades amplas, porém com regras de cadastro, composição e operação acima do padrão
- parte relevante do valor comercial está justamente na percepção de adequação total aos processos do cliente

Exemplos discutidos:

- **GanduInvest**: necessidade fortemente específica, com baixa reutilização imediata
- **Ventana**: necessidade de vendas/estoque/compras com modelagem de catálogo complexa (produto base, cores, acabamentos, complementos, potências, metragem etc.)

O desafio é conciliar:

1. customização comercial agressiva
2. isolamento multi-tenant rígido
3. sustentabilidade técnica
4. capacidade futura de reuso e benchmarking

---

## 3. Tese arquitetural

A melhor direção para o APP32 é adotar o modelo:

**Core de Plataforma + Capacidades Reutilizáveis + Configuração por Tenant + Extensões Específicas**

### 3.1. O APP32 não deve ser definido como “produto fechado”

Ele deve ser definido como uma **plataforma operacional customizável por processos**, apoiada por:

- motor de processos / BPMN
- capacidades de domínio reutilizáveis
- configuração por empresa
- extensões controladas quando a regra for realmente exclusiva

### 3.2. O BPMN é o principal eixo de adaptação operacional

A evolução do módulo de processos para BPMN é estratégica porque permite adaptar:

- etapas
- responsáveis
- aprovações
- formulários por fase
- notificações
- SLAs
- gatilhos
- evidências e documentos

sem exigir alteração de código para toda variação operacional.

**Limite importante:** BPMN resolve fluxo, mas não substitui um modelo de dados de domínio bem desenhado.

### 3.2-A. Esteira oficial de descoberta a partir do processo

Para evitar tanto o erro de “tudo vira módulo novo” quanto o erro de “tudo vira workflow parametrizado”, o APP32 deve adotar a seguinte esteira:

```text
1. Modelar o processo em BPMN
2. Analisar necessidades operacionais reveladas pelo fluxo
3. Analisar capacidades já existentes na plataforma
4. Classificar o gap em:
   - núcleo novo
   - capability complementar reutilizável
   - execução externa sem vínculo
   - execução externa com vínculo REST/MCP
   - simples reaproveitamento de capacidade existente
5. Projetar e implementar o que faltar
6. Configurar o BPMS para orquestrar essas capacidades
```

Tese de governança:

> O BPMN descobre a necessidade.  
> A arquitetura classifica a necessidade.  
> A plataforma cria ou reaproveita capacidades.  
> O BPMS orquestra a execução final.


### 3.3. O BPMN deve atuar como orquestrador de capabilities e experiência guiada

A diretriz arquitetural recomendada é que o BPMN não seja apenas um diagrama de fluxo, mas um **runtime operacional real** capaz de:

- iniciar uma **instância de processo** por execução
- manter contexto de tenant, usuário, entidade principal e etapa atual
- decidir se cada step será **automático**, **humano assistido** ou **de integração**
- resolver qual **capability** do APP32 deve ser acionada em cada etapa
- resolver qual **modo de interação** será usado: tela padrão, form inline, modal, drawer, aba guiada ou execução silenciosa
- persistir progresso parcial e permitir retomada de execução

Nesta visão, o BPMN não chama diretamente uma página hardcoded. Ele chama uma capability e o runtime resolve a interface adequada para aquele step e contexto.


### 3.4. Modularização de UI por abas como estratégia de composição

Faz sentido modularizar telas, cadastros e formulários em **abas estruturais**, desde que isso seja tratado como arquitetura de composição e não como personalização ad hoc.

A diretriz recomendada é:

- existir um conjunto de **abas principais do core** para cada entidade ou jornada relevante
- permitir **abas adicionais** vinculadas a capabilities compartilháveis ou customizações controladas
- resolver visibilidade, ordem e obrigatoriedade das abas por tenant, capability e contexto do processo
- manter a regra de negócio nos services/capabilities, nunca na camada visual da aba

As abas, portanto, devem ser entendidas como **slots de composição da experiência** e não como simples divisões estáticas de layout.

---

## 4. Modelo-alvo de arquitetura

### 4.1. Core de Plataforma

Componentes que nunca devem depender do cliente:

- autenticação
- gestão de companies / `company_id`
- usuários, colaboradores, equipes
- RBAC / capabilities
- auditoria
- notificações
- integrações base
- catálogos técnicos compartilhados
- engine de workflow / BPMN
- runtime de instância de processo
- shell padrão de execução guiada de processos
- registry de resolução entre step BPMN, capability e modo de interação
- registry de composição de UI por abas e seções
- surfaces MCP e contratos operacionais

### 4.2. Capacidades Reutilizáveis

Componentes reaproveitáveis entre soluções, ainda que inicialmente surjam em um cliente:

- cadastro mestre
- formulários dinâmicos
- gestão de atributos/variantes
- composição de catálogo
- motor de aprovações
- gestão documental
- contratos recorrentes e avulsos
- faturamento operacional vinculado a contrato (recibos, NFe, NFS-e e derivados)
- dashboards
- automações e gatilhos
- regras de workflow parametrizáveis

Regra importante:

> Uma capability pode nascer por demanda de um único processo, mas deve ser modelada como building block quando houver potencial de reuso.

### 4.3. Configuração por tenant

Camada destinada a adaptar o sistema por empresa sem bifurcar código:

- módulos/capabilities habilitadas
- nomenclaturas
- parâmetros funcionais
- formulários habilitados
- fluxos BPMN selecionados
- integrações ativadas
- limites operacionais
- composição de abas e seções por contexto operacional

### 4.3-A. Composição de UI por abas

A camada de apresentação do APP32 pode adotar um padrão de composição por abas para entidades e fluxos mais ricos, com a seguinte estrutura:

- **abas core**: partes estáveis e transversais da experiência
- **abas capability**: partes habilitadas por módulos/capabilities compartilháveis
- **abas de extensão**: partes adicionais controladas por tenant ou solução específica

Cada aba deve possuir metadados mínimos:

- `tab_key`
- `scope` (`core`, `capability`, `extension`)
- `entity_type`
- `capability_key` quando aplicável
- `visibility_rule`
- `order`
- `interaction_contract`

Esse modelo permite que o mesmo cadastro ou tela base seja ampliado sem bifurcar a experiência inteira.

### 4.4. Runtime BPMN orientado a capability

A camada de workflow do APP32 deve operar com os seguintes conceitos:

- **process definition**: definição do BPMN e suas regras
- **process instance**: execução concreta iniciada manualmente, por rotina ou por evento
- **step execution**: ocorrência de uma etapa específica dentro da instância
- **capability binding**: vínculo entre o step e a capability do APP32
- **interaction mode**: forma de execução do step (`auto`, `form_inline`, `modal`, `drawer`, `review_screen`, `background_service`)
- **entity context**: contrato, cliente, serviço ou entidade principal daquela instância

Essa camada é a ponte entre processo, domínio, UI e automação.

### 4.4. Extensões específicas por cliente

Camada reservada ao que for efetivamente exclusivo:

- regras altamente particulares
- cálculos exclusivos
- integrações proprietárias
- jornadas operacionais únicas
- modelos específicos sem reaplicação imediata

Essas extensões devem permanecer **isoladas, explicitadas e governadas**, e não misturadas ao core por condicionais de cliente.

---

## 5. Classificação das demandas

Toda evolução nova deve ser classificada antes de entrar no código.

Essa classificação deve acontecer explicitamente logo após a leitura do BPMN e da necessidade operacional.

### 5.1. Core

Entra no produto padrão quando:

- é transversal
- afeta vários clientes
- é requisito estrutural da plataforma
- melhora segurança, governança ou escalabilidade

### 5.2. Capability reutilizável

Entra como building block quando:

- pode ser reaproveitada em outros contextos
- o domínio é recorrente
- a lógica pode ser generalizada sem distorcer o caso original

### 5.3. Configuração

Entra como parametrização quando:

- a variação é de fluxo, rótulo, cadastro, visibilidade ou regra selecionável
- o comportamento muda por tenant, mas a base lógica é a mesma

### 5.4. Extensão específica

Entra como solução específica quando:

- a lógica é exclusiva do cliente
- a reaplicação é improvável no curto prazo
- a generalização agora aumentaria custo sem retorno

---

## 6. Leitura dos casos atuais

### 6.1. GanduInvest

**Leitura:** solução vertical específica de tenant.

Diretriz:

- não forçar como módulo padrão do produto
- construir sobre a plataforma APP32
- reaproveitar core, segurança, workflow, auditoria e interfaces base
- tratar como **extensão vertical isolada**

Potencial futuro:

- servir como referência de solução
- alimentar padrões internos
- originar capacidades reutilizáveis parciais no futuro

### 6.2. Ventana

**Leitura:** candidata a originar capacidades de catálogo complexo.

Diretriz:

- implementar a solução atendendo o caso real do cliente
- desenhar a base já pensando em reuso
- separar o que é específico da Ventana do que é padrão de modelagem de catálogo composto

Possíveis capacidades derivadas:

- produto base
- variantes por atributo
- complementos opcionais
- regras de composição comercial/técnica
- listas de materiais/acessórios

### 6.3. Gestão de contratos — Versus e Save Water

**Leitura:** capability compartilhável com forte aderência ao core comercial/operacional.

Diretriz:

- tratar como módulo/capability de plataforma, não como customização isolada
- suportar contratos recorrentes e avulsos
- permitir geração e imputação manual de contratos
- controlar emissão e vínculo operacional de recibos, NFe, NFS-e e artefatos equivalentes
- conectar contratos ao workflow/BPMN, financeiro e cadastro de clientes/serviços

Desdobramentos esperados:

- agenda de recorrência
- status contratual
- vigência, reajuste e renovação
- eventos de faturamento
- trilha de emissão fiscal/documental
- parametrização por tenant para diferenças operacionais entre Versus e Save Water

---

## 7. Princípios inegociáveis

### 7.1. Multi-tenancy obrigatório

Toda leitura e escrita deve respeitar `company_id` em profundidade:

- rota
- service
- query
- integração
- workflow
- surface MCP

### 7.2. Proibido acoplamento por cliente no core

Anti-padrões proibidos:

- `if company_id == X` como regra de negócio recorrente
- arquivos duplicados por cliente no fluxo principal
- rotas paralelas para o mesmo domínio apenas por cliente
- permissões definidas apenas por menu visual

### 7.3. Sem lógica de negócio em rota

Toda variação relevante deve ficar em services, policies, handlers ou adapters adequados.

### 7.4. Capability-first e não tela-first

A governança deve partir de:

- capability
- domínio
- action
- policy
- enablement por tenant

não da tela isolada.

---

## 8. Modelo comercial recomendado

O posicionamento comercial recomendado não é apenas “software 100% customizado”.

O discurso mais sólido é:

> O APP32 é uma plataforma modular e orientada a processos, capaz de se adaptar integralmente à operação do cliente por configuração, workflow e extensões específicas quando necessário.

### 8.1. Receita recomendada

- implantação / setup
- assinatura base da plataforma
- assinatura por capabilities ou pacotes
- serviços profissionais de customização
- integrações e automações premium

### 8.2. Ganho estratégico

Esse modelo permite:

- vender customização sem destruir o produto
- capturar recorrência
- acelerar novos projetos com blueprints internos
- transformar demandas exclusivas em benchmarking para novos casos

---

## 9. Diretriz de engenharia para o APP32

A evolução do sistema deve buscar explicitamente:

1. **catálogo de capabilities**
2. **enablement por empresa**
3. **feature/config flags por tenant**
4. **isolamento entre core e extensões**
5. **uso do BPMN como camada de adaptação operacional**
6. **runtime de instância de processo com retomada e versionamento**
7. **telemetria por capability e por tenant**
8. **contratos claros entre domínio, workflow e UI**
9. **núcleo central de contratos e faturamento operacional como capability compartilhável**
10. **binding explícito entre step BPMN, capability e interaction mode**
11. **composição de UI por abas core, capability e extensão sem bifurcação de tela por cliente**

---

## 10. Estrutura conceitual proposta

### 10.1. Core

- identidade e acesso
- company context
- auditoria
- workflow engine
- runtime de processo
- shell UI guiada de processo
- step resolver
- registry de tabs/seções
- serviços compartilhados

### 10.2. Domain capabilities

- financeiro
- rotina/processos
- projetos
- contratos
- catálogo/produto
- compras
- vendas
- estoque
- IA/automação

### 10.3. Tenant solution layer

- composição de capabilities
- parâmetros do tenant
- BPMNs por operação
- formulários e visibilidade
- bindings de UI por step quando houver variação operacional controlada
- composição e ordenação de abas por tenant e por capability

### 10.4. Client-specific extension layer

- adapters
- integrações proprietárias
- cálculos exclusivos
- regras especiais controladas

---

## 11. Roadmap sugerido

### Fase 1 — definição e governança

- formalizar taxonomia: core, capability, config, extensão
- definir critérios de entrada por tipo de demanda
- nomear as capabilities estratégicas do APP32

### Fase 2 — fundação técnica

- catálogo de capabilities
- enablement por empresa
- policy/capability matrix
- feature/config flags por tenant
- definição do core central de contratos, faturamento operacional e emissão documental

### Fase 3 — workflow-first

- acoplar a customização operacional ao BPMN
- separar fluxo de processo de regra estrutural de domínio
- permitir formulários e estados por tenant
- introduzir instância de processo com persistência parcial, retomada e versionamento
- introduzir binding entre step BPMN, capability e interaction mode
- construir shell padrão de execução guiada para processos
- estruturar composição de telas/cadastros por abas core + capability + extensão

### Fase 4 — casos piloto

- GanduInvest como vertical específica controlada
- Ventana como piloto de capability reutilizável de catálogo complexo

---

## 11-A. Modelo operacional recomendado para execução de processos

Cada processo relevante do APP32 deve ser modelado com um **mapa de atendimento por capability**, respondendo para cada etapa:

- qual necessidade operacional existe
- qual capability do APP32 atende
- se ela pode ser usada como está
- se exige parametrização/customização
- se exige criação nova
- se o step é automático ou humano
- qual modo de interação deve ser usado
- quais abas, blocos ou seções precisam compor a experiência daquela etapa

### Regra decisória por necessidade do processo

- **A)** usar capability existente como está
- **B)** usar capability existente com parametrização, extensão ou ajuste de workflow
- **C)** criar nova capability ou novo módulo quando não houver aderência suficiente

Esse modelo evita criação de módulo no escuro e transforma o BPMN em motor de descoberta e orquestração da plataforma.

## 11-B. Modelo de gestão estratégica por indicadores, processos e projetos

O APP32 deve tratar a gestão estratégica como um ciclo integrado entre **planejamento**, **processos**, **projetos**, **indicadores**, **reuniões de gestão** e **ações corretivas governadas**.

### Classificação dos indicadores

Os indicadores devem ser classificados, no mínimo, em quatro grupos operacionais:

- **Indicadores de planejamento**: medem a aderência da empresa aos objetivos estratégicos, OKRs, metas corporativas, posicionamento e resultados esperados.
- **Indicadores de processos**: medem a saúde da rotina operacional, desempenho de BPMNs, SLAs, gargalos, qualidade, retrabalho, produtividade e maturidade dos processos.
- **Indicadores de projetos**: medem a execução das iniciativas fora da rotina, incluindo prazo, orçamento, avanço, entrega, risco, impacto esperado e benefício capturado.
- **Indicadores de teias de conexões**: medem a qualidade das conexões entre pessoas, áreas, processos, projetos, indicadores, clientes, fornecedores, riscos, sistemas e decisões.

Essa separação preserva a distinção central do APP32:

- **processo/rotina** é o que deve ocorrer de forma recorrente, padronizada e gerenciável por fluxo, POP, dono, SLA e indicador;
- **projeto** é toda iniciativa fora da rotina destinada a criar, corrigir, melhorar, implantar, transformar ou recuperar desempenho.
- **teia de conexões** é a camada transversal que revela se as dependências, alinhamentos e relações que sustentam a execução estão fluindo ou gerando atrito organizacional.

### Indicadores de teias de conexões

As teias de conexões devem funcionar como uma camada diagnóstica transversal. Elas não substituem indicadores de planejamento, processos ou projetos; elas explicam a qualidade das relações que fazem esses três grupos performarem.

A teia pode ser classificada em três estados:

- **Satisfatória**: conexões claras, responsáveis definidos, dependências fluindo, comunicação adequada e baixo atrito entre áreas, processos e projetos.
- **Insatisfatória**: lacunas de governança, atrasos recorrentes, dependências frágeis, comunicação incompleta, dono indefinido ou desalinhamento parcial.
- **Crítica**: ruptura de governança, bloqueio de execução, conflito entre áreas, risco estratégico, perda operacional relevante ou impacto direto no cliente.

Exemplos de sinais de teia insatisfatória ou crítica:

- indicador sem dono claro;
- projeto sem vínculo com indicador ou objetivo estratégico;
- processo crítico sem responsável efetivo;
- reunião sem decisão, encaminhamento ou cobrança;
- dependência entre áreas sem SLA ou acordo de prioridade;
- cliente impactado sem visibilidade gerencial;
- fornecedor, sistema ou pessoa-chave bloqueando execução sem plano de contingência.

Esse grupo permite que o APP32 vá além da leitura do sintoma. Um indicador vermelho pode ser consequência de falha de processo, mas também pode ser consequência de uma teia quebrada: áreas desalinhadas, dependências mal definidas, projeto desconectado da estratégia ou decisões que não chegam à execução.

### Regra para indicador fora do range

Quando um indicador ficar fora do range esperado, o APP32 deve exigir uma resposta gerencial estruturada:

1. identificar o desvio;
2. registrar responsável/dono;
3. analisar causa raiz;
4. vincular a ação corretiva a um projeto existente ou criar um novo projeto;
5. desdobrar a correção em atividades com responsável, prazo e evidência;
6. acompanhar em reunião de gerência;
7. escalar para reunião de diretoria quando o desvio persistir, for crítico ou exigir mudança de prioridade.

Portanto, a regra conceitual não é “todo indicador vermelho cria um projeto novo”.

A regra correta para o APP32 é:

> Todo indicador fora do range deve gerar uma ação corretiva governada, obrigatoriamente vinculada a um projeto existente ou a um novo projeto, com atividades, responsável, prazo, evidência e rito de cobrança.

### Card executivo do indicador

Cada indicador deve possuir uma visão executiva padronizada, suficiente para permitir leitura rápida da situação, cobrança do responsável e rastreabilidade da ação corretiva.

O card executivo do indicador deve conter, no mínimo:

- **semáforo do indicador**: verde, amarelo, vermelho ou azul, calculado conforme range, meta, polaridade e período de medição;
- **responsável pelo indicador**: dono nominal, área/processo relacionado e eventual gestor para escalonamento;
- **causa raiz ou hipótese de causa**: diagnóstico registrado para evitar tratamento apenas do sintoma;
- **projeto associado**: projeto corretivo existente ou novo projeto criado para tratar o desvio, quando aplicável;
- **atividades associadas**: atividades abertas, responsáveis, prazos, dependências e evidências;
- **status do projeto e das atividades**: em dia, atrasado, crítico, bloqueado, concluído ou sem ação definida;
- **próxima cobrança**: reunião, data ou rito em que o responsável deverá prestar contas da evolução.

Quando o indicador estiver dentro do range, o card pode não ter projeto corretivo ativo, mas deve continuar exibindo responsável, última medição, tendência e evidência de acompanhamento.

Essa estrutura cria a cadeia mínima de gestão:

> medição → dono → diagnóstico → projeto/atividade → cobrança → nova medição.

### Painel de Gestão Estratégica no Portal de Processos

O APP32 deve expor uma tela executiva chamada **Painel de Gestão Estratégica**, posicionada abaixo do **Portal de Processos**, na área de **Acesso Rápido**.

Essa tela não deve substituir os cadastros específicos de indicadores, metas, medições, processos ou projetos. Seu papel é ser uma visão executiva de leitura, navegação e acionamento gerencial.

Na tela principal do painel:

- não deve haver menu lateral próprio;
- não deve haver ação genérica de `Novo`;
- não deve haver cadastro de indicador diretamente nessa tela;
- os indicadores devem ser apresentados em quatro grupos de acesso: estratégicos, processos, projetos e teias;
- o clique em cada grupo deve abrir pop-ups em camadas para navegação progressiva;
- as ações executivas permitidas devem ser **Nova reunião** e **Nova atividade/projeto**;
- o período de gestão deve aparecer como contexto/filtro discreto, não como cadastro.

Fluxo de navegação esperado:

> Portal de Processos → Acesso Rápido → Painel de Gestão Estratégica → Grupo de Indicadores → Subgrupo → Indicador → Card Executivo.

Esse posicionamento reforça que a gestão estratégica no APP32 nasce da leitura dos processos, indicadores, projetos e teias que sustentam a execução, sem duplicar os menus operacionais já existentes.

### Encerramento da tese e promoção para SPEC

A tese do **Painel de Gestão Estratégica** está suficientemente madura para sair do nível conceitual do paper e ser promovida para decisão oficial em SPEC.

Decisão de arquitetura:

- o painel será uma visão executiva de gestão estratégica, não um módulo de cadastro;
- o ponto de entrada será o **Portal de Processos**, em **Acesso Rápido**;
- os cadastros de indicadores, metas, medições, projetos e processos permanecem nos menus específicos;
- a tela principal permitirá somente ações executivas coerentes com governança: **Nova reunião** e **Nova atividade/projeto**;
- a implementação deverá respeitar multi-tenancy por `company_id`, leitura operacional MCP First e separação entre rota, service e UI.

Documento oficial derivado: `docs/spec/painel_gestao_estrategica_app32_spec.md`.

### Projeto guarda-chuva e atividade corretiva

Para evitar proliferação de projetos pequenos e desconectados, desvios pontuais podem ser tratados como atividades dentro de um **projeto guarda-chuva**.

Exemplo:

- projeto: `Melhoria dos Indicadores Comerciais`;
- atividade: `Corrigir baixa conversão de propostas`;
- indicador vinculado: `Taxa de conversão`;
- responsável: dono comercial ou gestor definido;
- prazo: data objetiva de correção;
- evidência: alteração de processo, treinamento, nova regra, relatório, experimento ou medição posterior.

Esse modelo mantém a disciplina de execução sem transformar cada alerta em um projeto isolado.

### Cadência de gestão recomendada

O APP32 deve suportar ritos de gestão em camadas:

- **reunião de rotina/processos**: acompanha operação, SLA, desvios e gargalos recorrentes;
- **reunião de projetos**: acompanha atividades, prazos, riscos, dependências e entregáveis;
- **reunião gerencial**: cobra responsáveis por indicadores fora do range e aprova correções;
- **reunião de diretoria**: redefine prioridades, recursos, metas e caminhos quando os desvios forem estruturais ou estratégicos.

Esse desenho conecta o indicador ao comportamento gerencial esperado: medir, diagnosticar, agir, cobrar, aprender e reajustar.

## 12. Decisão recomendada

A recomendação é aprovar o APP32 como:

**plataforma multi-tenant, orientada a processos, com capacidades reutilizáveis e suporte explícito a extensões específicas por cliente**.

### Consequência prática da decisão

- nem toda demanda de cliente vira módulo padrão
- nenhuma demanda específica deve contaminar o core sem classificação
- customização deve ser vendida comercialmente, mas governada tecnicamente
- todo investimento específico deve ser avaliado também como possível blueprint futuro

---

## 13. Conclusão

A estratégia correta para o APP32 não é escolher entre:

- produto padronizado demais
- ou software house pura por cliente

A estratégia correta é construir uma **plataforma evolutiva**, onde:

- o core permanece limpo
- o BPMN absorve adaptação operacional
- capabilities nascem para reuso progressivo
- extensões específicas são permitidas, mas isoladas
- casos exclusivos servem como benchmark e framework interno para novos clientes

Essa abordagem preserva:

- valor comercial
- segurança multi-tenant
- capacidade de manutenção
- escalabilidade de produto
- velocidade futura de implantação

