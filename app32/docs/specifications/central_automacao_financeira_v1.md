# Central de Automação Financeira — Especificação Funcional v1

## 1. Objetivo

Definir a especificação funcional da **Central de Automação Financeira**, uma camada externa ao módulo Financeiro atual, responsável por:

1. receber entradas automáticas;
2. extrair e estruturar dados financeiros;
3. permitir validação e correção humana em lote;
4. gerar lançamentos e agendamentos no Financeiro oficial;
5. manter rastreabilidade, histórico operacional e exclusão controlada.

A Central **não substitui** o Financeiro atual. Ela opera como uma esteira anterior à efetivação financeira.

---

## 2. Princípios de produto e arquitetura

### 2.1 Princípios funcionais
- a automação deve ser **revisável**;
- a validação humana deve ocorrer de forma **tabular e em lote**;
- o usuário deve trabalhar por **filtro, seleção, correção e validação**, e não por cadastro manual registro a registro;
- o Financeiro oficial deve receber apenas itens já validados.

### 2.2 Princípios arquiteturais
- a Central será um **módulo externo** ao fluxo manual atual do Financeiro;
- o módulo Financeiro existente não deve ser descaracterizado;
- toda leitura e escrita deve respeitar **multi-tenancy com `company_id`**;
- regras de negócio devem permanecer em **service layer**, nunca em rota;
- o acoplamento com o Financeiro oficial deve acontecer por contratos explícitos;
- rastreabilidade entre item importado e item gerado é obrigatória.

---

## 3. Problema de negócio

Hoje, entradas automáticas como planilhas, documentos, prestações de contas e integrações exigem validação antes da criação de lançamentos/agendamentos. A operação precisa de uma camada que permita:

- importar em lote;
- revisar o que foi extraído;
- corrigir dados com produtividade;
- validar apenas o que estiver correto;
- gerar registros financeiros oficiais com segurança;
- consultar histórico e descartar itens indevidos.

---

## 4. Escopo

### 4.1 Dentro do escopo
A Central deve atender entradas como:
- planilhas (`CSV`, `XLSX` e variações compatíveis);
- extratos estruturados e importações financeiras futuras;
- documentos unitários;
- documentos em lote;
- prestação de contas;
- integrações futuras;
- MCP e automações futuras.

### 4.2 Fora do escopo desta versão
Nesta v1, ficam fora do escopo:
- alteração do fluxo manual atual de lançamentos no Financeiro;
- reformulação do módulo oficial de liquidação;
- reformulação do módulo oficial de conciliação;
- automação bancária full API;
- parametrizações avançadas de regras por IA autônoma;
- experiência detalhada de rateio avançado para todos os casos na grade principal.

---

## 5. Resultado esperado

Ao final da esteira, o usuário deve ser capaz de:

1. importar um ou vários itens;
2. visualizar os dados extraídos em uma tabela operacional;
3. corrigir campos inline ou por seleção;
4. marcar itens como validados;
5. gerar apenas os itens validados no Financeiro;
6. consultar depois o histórico do que foi importado, gerado ou excluído.

---

## 6. Jornada funcional consolidada

## 6.1 Etapa 1 — Ingestão
O usuário envia:
- um arquivo;
- vários arquivos;
- uma planilha;
- um documento unitário;
- um lote de documentos.

O sistema:
- registra origem e contexto do lote;
- armazena o arquivo ou documento origem;
- extrai os dados possíveis;
- faz pré-validação básica;
- cria registros temporários de automação.

### Saída da etapa
Todos os registros entram com status:
- **Importada**

## 6.2 Etapa 2 — Validação / Correção Humana
O usuário acessa uma grade única com os registros importados e consegue:
- filtrar;
- editar inline;
- selecionar por `selectbox`;
- abrir detalhe/modal quando necessário;
- visualizar o documento origem;
- selecionar vários itens;
- alterar status em lote;
- validar em lote.

### Saída da etapa
Quando o item estiver apto a ser efetivado:
- **Validada**

## 6.3 Etapa 3 — Geração no Financeiro
O usuário aciona a geração dos registros validados.

O sistema:
- processa somente itens com status **Validada**;
- converte para lançamento ou agendamento conforme as regras de negócio;
- grava vínculo entre item da Central e item financeiro gerado;
- registra evidência de geração e auditoria.

### Saída da etapa
Após sucesso:
- **Gerada**

## 6.4 Etapa 4 — Exclusão controlada
Se o item não deve seguir na esteira, o usuário pode descartá-lo.

Exemplos:
- importação indevida;
- documento irrelevante;
- duplicidade confirmada;
- registro não aproveitável.

### Saída da etapa
- **Excluída**

---

## 7. Status oficiais

A Central terá apenas os seguintes status:

### 7.1 Importada
Registro criado na Central e disponível para revisão.

### 7.2 Validada
Registro revisado e apto para gerar lançamento/agendamento.

### 7.3 Gerada
Registro já convertido em item oficial do Financeiro.

### 7.4 Excluída
Registro descartado da esteira e não elegível para geração.

---

## 8. Regra central de negócio

A revisão do item deve partir da pergunta operacional:

## “O item já foi pago/recebido ou está em aberto?”

Opções:
- **já pago / já recebido**
- **em aberto**

### Tradução sistêmica esperada
- **já pago / já recebido** → registro com liquidação informada, quando aplicável;
- **em aberto** → item pendente de pagamento/recebimento, conforme as regras do Financeiro oficial.

A Central trabalha com linguagem operacional para o usuário e traduz isso para a estrutura interna do Financeiro.

---

## 9. Boundary com o Financeiro oficial

### 9.1 O que fica na Central
- ingestão;
- armazenamento de origem;
- extração;
- preview tabular;
- validação humana;
- correção;
- histórico da automação;
- geração;
- exclusão controlada.

### 9.2 O que continua no Financeiro oficial
- manutenção oficial de lançamentos e agendamentos;
- liquidação oficial;
- conciliação oficial;
- dashboard e relatórios;
- consultas gerenciais oficiais.

### 9.3 Regra de acoplamento
A Central prepara e valida.
O Financeiro oficial executa e controla o ciclo oficial dos registros financeiros.

---

## 10. Tela principal

## 10.1 Conceito
A tela principal da Central será uma **grade operacional de validação**.

Ela é o ponto principal de produtividade do módulo.

## 10.2 Objetivo
Permitir revisão de muitos registros sem exigir abertura de formulários completos para cada item.

---

## 11. Colunas recomendadas da grade — MVP

A tabela principal deverá iniciar com as seguintes colunas:

- seleção;
- status;
- origem;
- data da importação;
- tipo do item (`pagar` / `receber`);
- situação do item (`já pago/recebido` / `em aberto`);
- descrição;
- favorecido / cliente;
- valor;
- competência;
- vencimento;
- conta bancária;
- plano de contas;
- centro de resultado;
- projeto / processo;
- indicador de confiança da extração;
- ação de visualizar origem;
- ação de editar detalhe.

---

## 12. Edição dos registros

## 12.1 Edição inline
A maioria dos casos deve ser resolvida diretamente na grade.

Campos elegíveis para edição inline:
- descrição;
- tipo do item;
- situação do item;
- valor;
- competência;
- vencimento;
- favorecido / cliente;
- conta bancária;
- plano de contas;
- centro de resultado;
- projeto / processo;
- status.

## 12.2 Edição por seleção
Campos de catálogo devem priorizar `selectbox`:
- favorecido;
- conta bancária;
- plano de contas;
- centro de resultado;
- projeto / processo.

## 12.3 Edição avançada
Para casos especiais, a Central poderá abrir:
- modal;
- painel lateral;
- linha expandida.

Essa abertura deve ser usada apenas quando a edição inline não for suficiente.

---

## 13. Casos especiais

Na v1, a grade principal deve priorizar simplicidade.

### Diretriz
Resolver aproximadamente **95% dos casos** na tabela principal.

### Casos que podem ir para detalhe avançado
- múltiplas liquidações;
- rateio por centro de resultado;
- rateio por projeto/processo;
- múltiplos vínculos operacionais;
- observações extensas;
- conferência detalhada do documento origem.

### Decisão de produto
Não poluir a tela principal com estruturas raras que comprometam a produtividade do caso comum.

---

## 14. Visualização da origem

Cada linha deverá possuir ação de:

## **Visualizar origem**

Ao acionar, o sistema deve abrir um pop-up ou modal com:
- PDF;
- imagem;
- documento;
- texto extraído;
- preview estruturado da planilha;
- payload importado, quando fizer sentido.

### Objetivo
Permitir conferência rápida sem tirar o usuário da grade de validação.

---

## 15. Filtros obrigatórios

A tela deve permitir filtros por:
- status;
- data de importação;
- origem;
- tipo do item;
- favorecido;
- valor;
- período de competência;
- período de vencimento;
- lote;
- usuário importador;
- registros já gerados;
- registros excluídos.

### Observação
A Central deve servir tanto para tratamento de itens novos quanto para consulta histórica.

---

## 16. Ações em lote

A grade deve suportar pelo menos:
- marcar múltiplos itens como **Validada**;
- marcar múltiplos itens como **Excluída**;
- atualizar campo comum em múltiplos registros;
- gerar todos os itens **Validados** selecionados ou filtrados.

### Justificativa
Sem ação em lote, a solução perde grande parte do ganho operacional esperado.

---

## 17. Regras de geração

## 17.1 Pré-condição
Somente itens com status **Validada** podem ser gerados.

## 17.2 Comportamento esperado
Na geração, o sistema deve:
- validar `company_id` e escopo de acesso;
- validar integridade mínima dos campos obrigatórios;
- criar lançamento ou agendamento conforme as regras do Financeiro oficial;
- registrar vínculo entre a Central e o item gerado;
- impedir geração duplicada do mesmo item, salvo fluxo explícito de reprocessamento permitido.

## 17.3 Saídas da geração
Ao final, o sistema deve registrar:
- identificador do item gerado;
- tipo gerado (`lancamento` / `agendamento`);
- data e usuário da geração;
- status final do item da Central = **Gerada**.

---

## 18. Regras de exclusão controlada

Itens podem ser marcados como **Excluída** quando forem descartados antes da geração.

### Regras mínimas
- a exclusão deve ser auditável;
- itens já gerados não devem ser simplesmente marcados como excluídos sem tratamento apropriado;
- a ação deve respeitar permissão do usuário e escopo da empresa.

---

## 19. Histórico e rastreabilidade

A Central deve permitir consulta posterior de:
- lote de origem;
- usuário que importou;
- data de importação;
- status atual;
- documento origem;
- dados corrigidos;
- data de validação;
- usuário que validou;
- data de geração;
- usuário que gerou;
- vínculo com item financeiro criado.

Rastreabilidade entre origem e resultado final é requisito obrigatório.

---

## 20. Prestação de contas dentro da mesma esteira

A prestação de contas deve seguir a mesma sistemática da Central.

### Exemplos de uso
- subir 20 documentos de uma vez;
- subir 1 documento agora e outro depois;
- consolidar tudo na mesma grade de revisão.

### Regra funcional
Independentemente da origem, todos os registros devem convergir para a mesma lógica:
- importação;
- extração;
- revisão;
- validação;
- geração.

---

## 21. Modelo conceitual mínimo

Sem detalhar implementação final, a Central deverá trabalhar conceitualmente com:
- lote de automação;
- registro de automação;
- arquivo ou documento origem;
- resultado da extração;
- histórico de validação;
- vínculo com lançamento/agendamento gerado.

---

## 22. API e serviços — diretriz de desenho

### 22.1 Backend API
A solução deverá expor contratos específicos para:
- criar lote de ingestão;
- listar registros importados;
- editar registro da Central;
- alterar status em lote;
- visualizar metadados da origem;
- gerar itens validados;
- consultar histórico.

### 22.2 Service layer
Toda regra de:
- extração;
- normalização;
- validação;
- geração;
- rastreabilidade;
- descarte controlado;

...deve ficar em serviços específicos da Central, sem deslocar regra de negócio para rotas.

### 22.3 Integração com Financeiro oficial
A geração deve reutilizar os contratos e serviços oficiais do Financeiro sempre que possível, preservando consistência funcional.

---

## 23. Segurança e multi-tenancy

### Regras obrigatórias
- todo registro da Central deve carregar `company_id`;
- filtros e leituras devem respeitar escopo de empresa;
- geração só pode ocorrer dentro do escopo autorizado;
- visualização do documento origem deve respeitar permissão e tenant;
- a consulta histórica não pode vazar dados entre empresas.

---

## 24. Fora de escopo técnico imediato

Mesmo sendo desejáveis no futuro, não entram como obrigação da v1:
- engine avançada de score por IA;
- OCR multimodal completo para todas as origens;
- conciliação automática full bank API;
- workflows complexos de reversão pós-liquidação;
- tela principal com experiência de rateio avançado para todos os casos.

---

## 25. Critérios de aceite — v1

A v1 será considerada funcionalmente aceita quando for possível:

1. importar um ou vários itens para a Central;
2. visualizar os registros em uma grade operacional única;
3. corrigir os principais campos na própria grade;
4. filtrar por status, origem e datas;
5. visualizar o documento origem por linha;
6. marcar um ou vários registros como **Validada**;
7. marcar um ou vários registros como **Excluída**;
8. gerar somente os registros **Validados**;
9. registrar vínculo entre o item importado e o item financeiro gerado;
10. consultar posteriormente o histórico dos registros importados, gerados e excluídos;
11. garantir escopo por `company_id` em toda a jornada.

---

## 26. Resumo executivo

## Nome proposto
**Central de Automação Financeira**

## Fluxo padrão
**Importada → Validada → Gerada / Excluída**

## Papel no produto
A Central atua como camada externa de automação e revisão antes do Financeiro oficial.

## Benefício principal
Aumentar produtividade e segurança operacional sem alterar o fluxo manual robusto já existente no Financeiro.
