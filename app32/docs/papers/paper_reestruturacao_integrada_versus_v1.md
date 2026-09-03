# Paper — Reestruturação Integrada da Versus v1

**Classificação:** Paper  
**Status:** Ciclo 1 concluído para validação humana
**Data-base:** 2026-09-03  
**Empresa:** Versus Gestão Corporativa (`company_id=9`)  
**Projeto de execução recomendado:** `AA.J.15 — Estruturação Versus Gestão Corporativa`  
**Atividade de execução:** `AA.J.15.17 — Reestruturação integrada — mercado, produto e entrega`  

## 1. Propósito

Aplicar a própria Metodologia Versus à Versus para alinhar, em um único sistema:

> público prioritário → dor → oferta → comunicação → venda → processo de entrega → resultado → valor agregado.

Este paper não substitui o Paper do Método Versus nem as SPECs do APP32. Ele registra o diagnóstico inicial da Versus como empresa-cliente de sua própria metodologia e organiza o trabalho que deverá ser executado no APP32.

## 2. Fontes e níveis de evidência

### 2.1 Estado operacional

Leitura tenant-safe realizada via MCP para `company_id=9`:

- perfil e identidade organizacional;
- catálogo, portfólio, clientes e painel comercial;
- arquitetura de processos;
- projetos e planejamentos;
- frentes consultivas de Identidade, Processos, Planejamento Estratégico e Gerenciamento Estratégico.

### 2.2 Documentação canônica e comercial

- `paper_metodo_versus_estruturacao_evolutiva_v1.md`;
- `propostas_comerciais_autovendaveis_versus_paper_v1.md`;
- playbooks de Performance Hub, serviços pontuais e decks;
- propostas comerciais mantidas em `C:/GestaoVersus/app32/Propostas`;
- apresentação comercial de Gestão de Processos da M1;
- site institucional `https://www.gestaoversus.com.br/` e perfil público da empresa no LinkedIn.

### 2.3 Regra de leitura

As conclusões abaixo distinguem:

- **fato canônico:** dado registrado no APP32 ou documento oficial;
- **evidência operacional:** execução, vínculo, medição ou rito registrado;
- **declaração comercial:** promessa presente no site, deck ou proposta;
- **hipótese:** interpretação ainda sujeita a validação humana;
- **gap:** ausência, conflito ou falta de evidência suficiente.

## 3. Diagnóstico executivo

A Versus possui uma metodologia mais madura e uma plataforma mais ampla do que sua arquitetura comercial consegue explicar e vender. O problema principal não é ausência de conhecimento ou de funcionalidades: é falta de uma cadeia canônica que conecte mercado, oferta, operação e valor.

Hoje coexistem quatro linguagens parcialmente divergentes:

1. o Método Versus opera por `Necessidades Urgentes` e `Estruturação Empresarial`;
2. os materiais comerciais apresentam `Serviço Pontual`, `Diagnóstico PME 360`, `Estruturação Empresarial` e `Performance Hub` como uma escada de ofertas;
3. o catálogo comercial do APP32 possui somente um produto cadastrado: `Performance Hub`, sem descrição;
4. o site público concentra quase toda a proposta no `Performance HUB` e não torna clara a entrada por Necessidade Urgente.

### Decisão conceitual recomendada

- **Necessidades Urgentes** e **Estruturação Empresarial** permanecem como os dois trilhos metodológicos.
- **Business Review** permanece como registro do valor agregado, nunca como produto.
- **Serviço Pontual** deve ser tratado como linguagem comercial para uma Necessidade Urgente.
- **Diagnóstico PME 360** deve ser etapa de qualificação/entrada da Fase 00, e não um terceiro trilho metodológico.
- **Performance Hub** deve ser definido como modelo recorrente de sustentação, cadência e acompanhamento da Estruturação Empresarial, e não competir com ela como conceito paralelo.

Essa decisão precisa ser validada antes de reescrever site, propostas ou catálogo.

## 4. Inventário resumido da Versus

### 4.1 Identidade e mercado

- missão, visão, propósito, valores e quatro pilares estão registrados;
- o ICP atual é apenas `PMEs brasileiras`, amplo demais para orientar mídia, oferta, qualificação ou priorização;
- as duas propostas de valor refletem corretamente os trilhos metodológicos;
- propostas de valor, diferenciais, competências, políticas e stakeholders ainda carregam itens de origem `ia_inferido`, embora apareçam como confirmados;
- o perfil empresarial está incompleto: descrição, porte, cobertura e experiência não estão preenchidos no objeto canônico da empresa;
- não há indicadores corporativos estruturados na identidade.

### 4.2 Arquitetura comercial

- 1 produto/serviço cadastrado: `Performance Hub`;
- 0 itens de estrutura do catálogo;
- 1 carteira: `Clientes Versus Mensais`;
- 5 clientes comerciais, todos com contrato ativo;
- o APP32 não materializa hoje a arquitetura de oferta descrita nos materiais comerciais;
- não há, no cadastro do produto, promessa, ICP, entregáveis, método de entrada, critérios de aceite ou processos responsáveis pela entrega.

### 4.3 Processos e capacidade de entrega

- 3 áreas, 12 macroprocessos e 47 processos;
- 45 de 47 processos possuem dono/responsável;
- 21 de 47 possuem evidência de modelagem;
- 17 rotinas e 4 passos cadastrados;
- 1 contrato de execução de atividade;
- 1 checklist e nenhuma agenda de processo;
- ainda não existe vínculo canônico único entre processo, projeto de implantação, treinamento, estabilização por três ciclos e auditoria.

### 4.4 Planejamento e gerenciamento estratégico

- existem planejamentos em modos legados (`implantation` e `evolucao`) apesar da decisão canônica por Planejamento de Crescimento;
- a frente reconhece 2 planos de crescimento, nenhum ativo;
- há 1 OKR global e 1 OKR de área, porém nenhum projeto ou processo vinculado à estratégia;
- existem 2 indicadores ativos, apenas 1 com responsável, nenhum com meta e nenhum com medição;
- não há reunião gerencial estratégica registrada;
- o sistema ainda não comprova ciclos recorrentes de decisão, ação e aprendizado.

### 4.5 APP32, MCP e agentes

O APP32 possui cobertura funcional extensa — 785 rotas no boot validado — com módulos de processos, projetos, indicadores, planejamento, reuniões, contratos, comercial, financeiro, auditoria, incentivos, jornadas, canais, agentes e cockpit consultivo.

A capacidade técnica é suficiente para conduzir a reestruturação. O gap não é criar mais módulos; é configurar e usar os objetos existentes em uma cadeia de gestão coerente, expondo ao mercado somente as capacidades que tenham processo e evidência de entrega.

## 5. Matriz dos quatro pilares

| Pilar | Força atual | Discrepância principal | Decisão de evolução |
|---|---|---|---|
| Forma de Trabalho | Método incremental, orientado a restrição, projeto, indicador, follow-up e gate | Linguagem comercial cria mais ofertas/conceitos do que os dois trilhos canônicos | Normalizar a arquitetura de oferta e associar cada pacote a uma etapa do método |
| Ferramenta | APP32 cobre os domínios necessários e o MCP permite leitura/escrita governada | Catálogo comercial, planos, vínculos e indicadores não representam a promessa pública | Materializar produto → processo → projeto → indicador → Business Review |
| Agentes | Squad Cliente, Squad Versus e Engenharia possuem papéis e governança | Ainda não há evidência recorrente de uso dos agentes na qualificação, entrega e validação comercial | Definir instruções por etapa, entregável, gate e limite de decisão |
| Orquestração | Cockpit, protocolos, MCP, handoffs e gates já existem | Estratégia, processos, projetos, reuniões e valor ainda aparecem como leituras separadas | Criar workflow ponta a ponta da demanda ao valor agregado, sem duplicar objetos |

## 6. Congruências

1. A mensagem pública “gestão funcionando, não documentos” é aderente ao método baseado em evidência operacional.
2. A promessa de clareza, organização, previsibilidade e menor improviso está coerente com a Fase 00 e com o motor indicador → projeto → follow-up.
3. O APP32 já possui os componentes necessários para entregar e provar a proposta: processos, projetos, indicadores, reuniões, auditoria e Business Review.
4. O modelo híbrido de consultor, cliente, squads e IA é compatível com PMEs e com a formação progressiva de capacidades internas.
5. A cadeia de processos da Versus contém Desenvolvimento de Produtos, Desenvolvimento de Mercados, Marketing, Vendas, Relacionamento e Operações, permitindo lastrear a correção comercial na operação real.

## 7. Incongruências e riscos

### P0 — arquitetura de mercado e produto

1. **ICP genérico:** `PMEs brasileiras` não permite escolher setor, porte, maturidade, dor, decisor, capacidade de investimento ou canal.
2. **Produto sem contrato de valor:** o único item do catálogo é Performance Hub, sem descrição e sem conexão explícita aos entregáveis e processos.
3. **Taxonomia comercial paralela:** Serviço Pontual, Diagnóstico PME 360, Estruturação e Performance Hub podem parecer quatro produtos independentes.
4. **Promessa maior que a evidência:** a Visão afirma ser o serviço que mais entrega resultados no Brasil, sem critério comparativo ou indicador que permita comprová-la.

### P1 — publicidade e prova

5. O site concentra a comunicação no Performance Hub e não oferece rota clara para a dor urgente.
6. O site promete “mapeamento completo” enquanto o método prioriza recorte, velocidade e valor antes da completude.
7. Há variação entre “mais de duas décadas”, “15+ anos” e “mais de 15 anos de prática”. A referência precisa ser única e comprovável.
8. Expressões como “eliminar gargalos”, “metodologia validada” e “resultados reais” exigem critérios e provas autorizadas.
9. A prova social existe, mas ainda não está convertida em casos comparáveis com contexto, intervenção, resultado e valor agregado.

### P1 — execução e entrega

10. Menos da metade dos processos possui evidência de modelagem.
11. Não há cadeia operacional completa e mensurável ligando aquisição, proposta, contrato, implantação, execução, estabilização e Business Review.
12. O APP32 não evidencia ainda a capacidade disponível por consultor, cliente, processo e projeto para proteger prazo e qualidade da entrega.

### P2 — gestão e aprendizado

13. Indicadores sem metas, medições e reuniões impedem provar a promessa de gestão baseada em fatos.
14. Planejamento sem vínculo com processo e projeto não direciona produto, publicidade nem capacidade.
15. A maturidade da Identidade aparece como 100%, mas a frente permanece em `draft`, há colaboradores sem cargo e falta validação de coerência. O número mede cobertura, não maturidade plena.
16. Não há leitura MCP específica do Business Review no inventário comercial, dificultando fechar automaticamente a cadeia promessa → resultado → valor.

## 8. Arquitetura-alvo da oferta

### 8.1 Trilhos metodológicos

| Trilho | Gatilho | Objeto de execução | Saída |
|---|---|---|---|
| Necessidade Urgente | dor concentrada e prioridade imediata | projeto ou programa de projetos | dor tratada, aprendizado e Business Review |
| Estruturação Empresarial | necessidade de capacidade gerencial duradoura | programa faseado com gates | identidade, processos, planejamento e gestão funcionando |

### 8.2 Componentes comerciais subordinados

- `Serviço Pontual`: forma comercial da Necessidade Urgente;
- `Diagnóstico PME 360`: mecanismo de qualificação e priorização da Fase 00;
- `Performance Hub`: modelo de sustentação recorrente da execução, cadência e evolução;
- `Business Review`: evidência do valor agregado em qualquer trabalho concluído.

## 9. Fluxo operacional alvo

1. captar demanda e origem;
2. identificar empresa, decisor, dor, urgência e aderência ao ICP;
3. classificar como Necessidade Urgente ou Estruturação Empresarial;
4. selecionar pacote, escopo e proposta adequados;
5. vincular produto, contrato e processos de entrega;
6. abrir projeto/programa, responsáveis, capacidade e indicadores;
7. executar com consultor, cliente e squads conforme protocolo;
8. validar entregáveis e estabilização;
9. registrar Business Review com necessidade, solução, resultado e valor agregado;
10. retroalimentar ICP, proposta, publicidade, produto, processo e planejamento.

## 10. Backlog recomendado

### Ciclo 1 — verdade comercial

- validar segmentos prioritários e critérios de exclusão do ICP;
- definir a arquitetura oficial de oferta e a relação entre os cinco termos comerciais atuais;
- completar o perfil institucional canônico;
- normalizar experiência, promessas e provas públicas.

**Gate:** cada oferta possui público, dor, decisor, promessa, escopo, entregáveis, limites e prova mínima.

### Ciclo 2 — contrato operacional do produto

- estruturar o catálogo comercial no APP32;
- vincular cada oferta aos processos responsáveis;
- definir critérios de aceite, handover, indicadores e Business Review;
- mapear capacidade e dependências do cliente.

**Gate:** nenhuma proposta é enviada sem existir caminho operacional executável e responsável.

### Ciclo 3 — publicidade orientada por evidência

- reescrever site e decks por ICP/dor, sem abrir a metodologia proprietária;
- criar biblioteca de cases no formato necessidade → solução → resultado → valor;
- definir campanhas, canais, CTA e qualificação por oferta;
- conectar origem da demanda ao funil comercial no APP32.

**Gate:** cada promessa publicitária aponta para produto, processo, evidência e próximo passo reais.

### Ciclo 4 — gestão e aprendizado

- ativar indicadores comerciais, operacionais, satisfação, recompra e rentabilidade;
- instalar reunião periódica de produto/mercado e de entrega;
- conectar planejamento, processos, projetos e indicadores;
- usar Business Reviews para revisar ICP, publicidade e produto.

**Gate:** três ciclos consecutivos de revisão com decisão, ação e aprendizado registrados.

## 11. Indicadores mínimos

### Mercado e publicidade

- leads por ICP, dor, oferta e canal;
- taxa de qualificação e desqualificação;
- custo por oportunidade qualificada;
- conversão por oferta e motivo de perda.

### Produto e venda

- ciclo de venda;
- aderência entre proposta e contrato;
- margem prevista por produto;
- percentual de propostas com prova e critérios de aceite.

### Execução e entrega

- prazo, esforço, retrabalho e margem realizada;
- entregáveis aceitos;
- processos implantados e estabilizados;
- satisfação e recompra.

### Valor e aprendizado

- Business Reviews concluídos;
- valor agregado único e recorrente;
- aprendizados convertidos em processo, produto ou publicidade;
- recorrência de gaps por causa.

## 12. Gate de evolução

Publicidade, catálogo, produto e propostas não devem ser alterados antes da validação humana do ICP e da arquitetura de oferta. O Ciclo 1, registrado a seguir, aprofunda esse gate e apresenta as decisões para a direção da Versus.

Após a validação, o trabalho deverá continuar no `AA.J.15`, começando pelo processo `Desenvolvimento de Mercados` e conectado aos processos `Desenvolvimento de Produtos`, `Gerir Marketing Digital`, `Gerir Vendas` e `Gerir Operações Próprias`.

## 13. Ciclo 1 — ICP e arquitetura de oferta

### 13.1 Evidência interna

A base comercial atual demonstra recorrência, mas ainda não demonstra segmentação:

- 5 clientes e 5 contratos mensais ativos;
- todos os contratos possuem `Performance Hub` como único item;
- faixa mensal observada entre R$ 3 mil e R$ 6 mil, com total mensal de R$ 21 mil;
- 1 produto no catálogo, sem descrição, escopo, entregáveis ou critérios de aceite;
- os clientes atendidos pertencem a setores diferentes, portanto a amostra atual não comprova especialização setorial;
- o cadastro não contém atributos suficientes para comparar porte, maturidade, dor de entrada, ciclo de venda, margem, resultado ou valor agregado por perfil.

**Leitura:** a Versus já possui uma base recorrente, porém ainda vende e registra um único nome comercial para trabalhos que podem ter gatilhos, escopos e resultados distintos. A base atual é evidência de operação; não é, sozinha, evidência de ICP.

### 13.2 Evidência externa e implicações

- O IBGE diferencia empresas de alto crescimento por trajetória mensurável e pessoal ocupado, reforçando que “PME” isoladamente não descreve estágio nem necessidade gerencial. Fonte: [Demografia das Empresas e Estatísticas de Empreendedorismo](https://www.ibge.gov.br/estatisticas/economicas/servicos/22649-demografia-das-empresas-e-estatisticas-de-empreendedorismo.html).
- O IBGC recomenda governança gradual e adequada à realidade das PMEs, nas quais proprietário e gestor frequentemente são a mesma pessoa. Isso é aderente à condução Versus com implantação progressiva, sem burocracia excessiva. Fonte: [Governança corporativa em PMEs exige modelos sob medida](https://www3.ibgc.org.br/blog/estudo-governanca-pmes).
- O Sebrae trata planejamento, processos e indicadores como partes conectadas da gestão e destaca a necessidade de acompanhamento sistemático da execução. Isso valida a proposta integrada da Versus, mas também mostra que esses elementos, isoladamente, não são diferenciais exclusivos. Fontes: [Gestão empresarial](https://sebrae.com.br/sites/PortalSebrae/ufs/ms/sebraeaz/prepare-se-sobre-gestao-empresarial%2C6621a8c0a1c5c710VgnVCM100000d701210aRCRD), [Gestão por indicadores](https://sebrae.com.br/sites/PortalSebrae/artigos/gestao-por-indicadores%2Cc269a48dcd616810VgnVCM1000001b00320aRCRD) e [Organização de processos](https://meuatendimento.sebrae.com.br/sites/PortalSebrae/sebraeaz/organize-os-processos-da-sua-empresa-e-atinja-as-suas-metas%2C640c08cd17c90710aRCRD).
- A Endeavor mostra que o desafio predominante muda conforme a maturidade: estrutura organizacional, crescimento e refinamento do modelo de negócio não devem receber a mesma abordagem. Fonte: [Endeavor Outliers 2026](https://endeavor.org.br/2026-endeavor-outliers/).
- A Falconi organiza sua comunicação por problema e domínio de resultado — estratégia, operações, gastos e digital — e apresenta casos com resultado mensurável. A Versus pode adotar essa clareza sem copiar sua arquitetura ou mirar o mesmo porte de cliente. Fonte: [Falconi](https://falconi.com/).
- O G4 explicita programas diferentes para fases e necessidades distintas e usa uma triagem curta para orientar o cliente. A referência útil é a clareza de entrada; o modelo educacional não deve ser confundido com a consultoria assistida e implantadora da Versus. Fonte: [G4 Business](https://g4business.com/).

**Conclusão externa:** o mercado já promete planejamento, processos, indicadores, educação e resultado. O diferencial potencial da Versus não é possuir esses componentes, mas conectá-los em uma implantação assistida, dentro do APP32, com consultor, cliente, squads, IA, gates, estabilização e registro do valor agregado. Essa diferenciação ainda precisa ser comprovada por casos e indicadores.

### 13.3 ICP proposto para validação

O ICP deve combinar características da empresa, situação de compra e condições de execução. Setor e faturamento, sozinhos, não bastam.

#### Núcleo comum obrigatório

Empresa brasileira de pequeno ou médio porte que:

1. possua operação real, equipe e processos interdependentes;
2. tenha sócio, diretor ou gestor com poder de patrocinar mudanças;
3. enfrente perda relevante por improviso, falta de clareza, baixa previsibilidade ou crescimento desorganizado;
4. aceite disponibilizar pessoas, dados e tempo para implantação;
5. queira capacidade gerencial funcionando, e não apenas relatório ou aconselhamento;
6. tenha condição econômica compatível com o escopo, a duração e a intensidade do trabalho.

#### Perfil A — dor urgente

- **Gatilho:** risco, perda, autuação, ruptura, atraso crítico, falha financeira, comercial ou operacional.
- **Busca:** resposta rápida e responsável para uma dor delimitada.
- **Entrada comercial:** Necessidade Urgente, executada por projeto ou programa.
- **Expansão possível:** o aprendizado pode originar Estruturação Empresarial, sem venda forçada e sem automatismo.

#### Perfil B — estruturação para crescer ou recuperar controle

- **Gatilho:** dependência excessiva do dono, crescimento sem organização, baixa delegação, processos informais, estratégia sem execução ou gestão sem indicadores confiáveis.
- **Busca:** estruturar capacidades duradouras e tornar a gestão executável pela empresa.
- **Entrada comercial:** Fase 00 da Estruturação Empresarial, com diagnóstico e priorização.
- **Sustentação possível:** Performance Hub como cadência recorrente de execução, acompanhamento e evolução.

#### Prioridade inicial recomendada

Priorizar empresas lideradas diretamente por sócios ou diretores, com complexidade suficiente para exigir coordenação entre áreas, mas ainda sem estrutura gerencial madura. Não restringir por setor nesta etapa, porque a base atual é multissetorial e ainda pequena. O recorte setorial deverá resultar de evidência de conversão, margem, velocidade de entrega, recompra e valor agregado.

#### Critérios de exclusão ou despriorização

- ausência de patrocinador com poder de decisão;
- busca exclusiva por documento, palestra ou opinião sem implantação;
- indisponibilidade de dados, responsáveis ou agenda mínima do cliente;
- expectativa de terceirizar integralmente a gestão para a Versus;
- necessidade técnica regulada fora da competência da Versus sem parceiro habilitado;
- urgência sem capacidade mínima de decisão ou execução;
- incompatibilidade econômica com o esforço necessário;
- conduta contrária à ética, à transparência ou aos limites metodológicos.

### 13.4 Arquitetura canônica de oferta proposta

| Camada | Nome | Função | Modelo comercial | Relação com a metodologia |
|---|---|---|---|---|
| Qualificação | Diagnóstico inicial / Fase 00 | compreender contexto, dor, prontidão e prioridade | etapa de entrada, gratuita ou remunerada conforme profundidade | não é um terceiro trilho |
| Oferta 1 | Necessidade Urgente | resolver uma dor específica e relevante | projeto ou programa com escopo, prazo, responsável e critério de aceite | primeiro trilho metodológico |
| Oferta 2 | Estruturação Empresarial | construir ou amadurecer capacidades permanentes | programa faseado, com gates e projetos de implantação | segundo trilho metodológico |
| Sustentação | Performance Hub | manter cadência, acompanhamento, squads, APP32 e evolução | contrato recorrente, com capacidade e ritos definidos | modelo operacional que sustenta principalmente a Estruturação Empresarial |
| Evidência | Business Review | registrar necessidade, solução, resultado e valor agregado | obrigatório na entrega; não comercializado isoladamente | fecha o ciclo de valor e aprendizado |

#### Recomendação sobre o Performance Hub

Manter `Performance Hub` como nome do **modelo recorrente de sustentação e operação assistida**, e não como sinônimo da metodologia inteira. Assim:

- o cliente entende primeiro qual problema será resolvido;
- a Versus preserva os dois trilhos canônicos;
- o contrato recorrente define capacidade, cadência, ferramentas e governança;
- projetos de Necessidade Urgente podem existir dentro ou fora do Hub, conforme contratação;
- a Estruturação Empresarial pode usar o Hub como veículo recorrente de execução;
- o APP32 deixa de registrar todos os contratos como se fossem um produto indistinto.

### 13.5 Informações mínimas por oferta no APP32

Cada item comercial deverá conter:

- ICP e situação de compra;
- dor e resultado esperado;
- patrocinador e participantes necessários;
- escopo, exclusões e premissas;
- entregáveis e critérios de aceite;
- processo responsável pela venda, implantação e entrega;
- capacidade Versus e capacidade exigida do cliente;
- preço ou regra de formação, periodicidade e margem-alvo;
- indicadores de execução e resultado;
- regra de encerramento, continuidade e Business Review;
- evidências e cases autorizados para comunicação.

### 13.6 Decisões humanas para fechar o Ciclo 1

A direção deverá confirmar ou ajustar:

1. o núcleo comum do ICP e os dois perfis por situação de compra;
2. a decisão de não especializar por setor antes de medir a base;
3. os critérios de exclusão e despriorização;
4. `Performance Hub` como sustentação recorrente, não como terceiro trilho nem nome da metodologia inteira;
5. se o diagnóstico da Fase 00 poderá ser gratuito, remunerado ou possuir duas profundidades;
6. quais clientes e resultados podem formar a primeira biblioteca de provas.

Somente após esse gate o conteúdo deverá migrar de Paper para SPEC e ser materializado no catálogo, nos processos comerciais, nas propostas e no site.
