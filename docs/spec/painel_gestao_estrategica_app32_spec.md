# SPEC — Painel de Gestão Estratégica APP32

Classe documental: `SPEC`
Status: decisão oficial inicial
Origem conceitual: `docs/paper_plataforma_modular_customizavel_app32.md`
Data: 2026-06-14

## 1. Decisão

O APP32 terá uma tela executiva chamada **Painel de Gestão Estratégica**, posicionada no **Portal de Processos**, dentro da área de **Acesso Rápido**.

Essa tela é uma visão de leitura, navegação e acionamento gerencial. Ela não substitui os cadastros operacionais já existentes.

## 2. Escopo funcional

### 2.1. A tela principal deve exibir

- título: `Painel de Gestão Estratégica`;
- contexto/filtro discreto de período de gestão;
- grupo de indicadores estratégicos;
- grupo de indicadores de processos;
- grupo de indicadores de projetos;
- grupo de indicadores de teias;
- próximas reuniões marcadas.

### 2.2. A tela principal pode acionar

- **Nova reunião**;
- **Nova atividade/projeto**;
- filtros de leitura.

### 2.3. A tela principal não deve acionar

- novo indicador;
- nova meta;
- nova medição;
- novo processo;
- cadastro operacional genérico;
- botão genérico `Novo`.

Cadastros de indicadores, metas, medições, processos e projetos devem permanecer nos seus menus específicos.

## 3. Ponto de entrada

O acesso deve seguir:

> Portal de Processos → Acesso Rápido → Painel de Gestão Estratégica

Não deve haver menu lateral próprio dentro do painel.

## 4. Navegação

A navegação será por pop-ups em camadas, preservando o contexto executivo.

Fluxo esperado:

> Painel de Gestão Estratégica → Grupo de Indicadores → Subgrupo → Indicador → Card Executivo

Exemplo:

> Indicadores Estratégicos → Indicadores Comerciais → Conversão de Propostas → Card Executivo

Cada camada deve manter breadcrumb ou contexto equivalente.

## 5. Grupos de indicadores

### 5.1. Indicadores estratégicos

Medem aderência aos objetivos estratégicos, OKRs, metas corporativas, posicionamento e resultados esperados.

### 5.2. Indicadores de processos

Medem saúde da rotina, desempenho de BPMNs, SLAs, gargalos, qualidade, retrabalho, produtividade e maturidade de processos.

### 5.3. Indicadores de projetos

Medem execução de iniciativas fora da rotina, incluindo prazo, orçamento, avanço, risco, entregáveis, impacto esperado e benefício capturado.

### 5.4. Indicadores de teias

Medem qualidade das conexões entre pessoas, áreas, processos, projetos, indicadores, clientes, fornecedores, riscos, sistemas e decisões.

Estados mínimos:

- satisfatória;
- insatisfatória;
- crítica.

## 6. Card executivo do indicador

Cada indicador aberto em camada final deve apresentar, no mínimo:

- semáforo do indicador;
- responsável;
- objetivo;
- meta e prazo;
- situação atual;
- tendência ou última medição;
- causa raiz ou hipótese;
- projeto associado;
- atividades associadas;
- status do projeto/atividades;
- próxima cobrança/reunião;
- evidências quando existirem.

## 7. Regra para indicador fora do range

Todo indicador fora do range deve gerar uma ação corretiva governada, obrigatoriamente vinculada a:

- projeto existente; ou
- novo projeto corretivo; e
- uma ou mais atividades com responsável, prazo e evidência.

Não é obrigatório criar um projeto novo para cada desvio. Quando adequado, o desvio deve entrar como atividade dentro de projeto guarda-chuva.

## 8. Período de gestão

O período de gestão é filtro/contexto de leitura.

Exemplos:

- mês vigente;
- trimestre;
- ano;
- ciclo estratégico.

O período deve influenciar:

- medições exibidas;
- metas consideradas;
- semáforos;
- reuniões listadas;
- projetos/atividades correlacionados.

## 9. Reuniões

A seção de próximas reuniões deve exibir:

- data e horário;
- tipo da reunião;
- pauta resumida;
- convidados;
- vínculo com indicadores/projetos/teias quando existir;
- acesso ao calendário.

A ação **Nova reunião** deve criar ou abrir fluxo específico de reunião, sem misturar com cadastro de indicadores.

## 10. Nova atividade/projeto

A ação **Nova atividade/projeto** deve ser usada para criar resposta executiva a desvios, teias críticas ou decisões de reunião.

Ela deve respeitar a estrutura atual de projetos e atividades do APP32.

## 11. Guardrails técnicos

- Toda leitura e escrita deve ser tenant-safe com `company_id`.
- Leitura operacional deve seguir MCP First quando aplicável.
- Rotas devem ser finas.
- Regras de negócio devem ficar em service.
- UI deve usar o padrão APP32/workspace: fundo claro, cards claros, bordas suaves e texto escuro.
- Não criar catálogo paralelo de indicadores.
- Não duplicar menus operacionais existentes.

## 12. Fora de escopo inicial

- cadastro completo de indicadores;
- modelagem completa de metas;
- editor de fórmula;
- cadastro completo de processos;
- modelagem BPMN;
- gestão completa de projetos;
- relatórios analíticos avançados;
- automação completa de RCA.

## 13. Critérios de aceite

- O painel aparece em Acesso Rápido do Portal de Processos.
- A tela não possui menu lateral próprio.
- A tela não possui botão genérico `Novo`.
- A tela não oferece cadastro de indicador.
- A tela exibe os quatro grupos de indicadores.
- Cada grupo abre navegação em pop-up/camada.
- A tela exibe próximas reuniões.
- A tela oferece **Nova reunião** e **Nova atividade/projeto**.
- Todas as consultas respeitam `company_id`.
