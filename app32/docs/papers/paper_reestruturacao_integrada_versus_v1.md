# Paper — Reestruturação Integrada da Versus v1

**Classificação:** Paper  
**Status:** Diagnóstico inicial para validação  
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

## 12. Próxima decisão humana

Antes de alterar publicidade, catálogo ou produto, a direção da Versus precisa validar:

1. se a arquitetura-alvo dos dois trilhos e dos componentes subordinados está correta;
2. quais segmentos devem compor o ICP prioritário;
3. se Performance Hub é o nome do modelo recorrente ou o nome comercial da própria Estruturação Empresarial;
4. quais resultados e cases podem ser publicados com evidência e autorização.

Após essa validação, o trabalho deve continuar no `AA.J.15`, começando pelo processo `Desenvolvimento de Mercados` e conectado aos processos `Desenvolvimento de Produtos`, `Gerir Marketing Digital`, `Gerir Vendas` e `Gerir Operações Próprias`.
