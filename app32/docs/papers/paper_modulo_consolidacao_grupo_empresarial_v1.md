# Paper — Módulo de Consolidação para Grupo Empresarial

Status: em evolução  
Classe: Paper

## 1. Tese

O APP32 deve tratar consolidação de grupo empresarial como uma **camada analítica e configurável acima dos relatórios por empresa**, e não como substituição do multi-tenancy por `company_id`.

A direção proposta é:

- manter a operação transacional segregada por empresa;
- criar um **módulo de consolidação** para relatórios multiempresa;
- permitir **mapeamentos explícitos** entre estruturas equivalentes das empresas do grupo;
- produzir relatórios consolidados com rastreabilidade por empresa de origem.

## 2. Problema

Hoje o sistema já possui sinais de suporte a cenários multiempresa em partes do produto, com uso de `company_ids` em consultas agregadas e filtros operacionais.

Por outro lado, os relatórios gerenciais financeiros permanecem, em sua base arquitetural atual, orientados a **uma empresa por vez**.

Isso gera limitações quando duas ou mais empresas pertencem ao mesmo grupo e a gestão precisa:

- emitir DRE consolidada;
- emitir fluxo de caixa consolidado;
- consolidar razão, títulos e posição financeira;
- comparar grupo e empresas individualmente;
- harmonizar estruturas diferentes entre empresas.

O principal bloqueio não é apenas consultar várias empresas ao mesmo tempo.

O bloqueio real é que, em contexto de grupo:

- contas contábeis equivalentes podem ter IDs diferentes;
- centros de custo equivalentes podem ter códigos e árvores diferentes;
- projetos, processos e contrapartes podem existir com taxonomias não padronizadas;
- algumas linhas exigem inversão de sinal, exclusão ou reclassificação para fins executivos.

Sem uma camada própria de consolidação, o risco é gerar números errados, pouco auditáveis ou frágeis para evolução.

## 3. Princípios da direção proposta

### 3.1. Multi-tenancy continua obrigatório

O runtime transacional continua baseado em `company_id`.

Toda leitura operacional e toda mutação continuam escopadas por empresa, conforme os guardrails oficiais do APP32.

### 3.2. Consolidação é visão, não tenant novo

Grupo empresarial não deve nascer como novo tenant operacional.

Deve nascer como **visão analítica/configurável**, resolvida a partir de:

- um conjunto de empresas autorizadas;
- regras de mapeamento;
- regras de agregação;
- regras de exclusão e reclassificação.

### 3.3. Relatório consolidado precisa ser auditável

Todo valor consolidado deve poder responder:

- de quais empresas veio;
- de quais linhas veio;
- qual regra de mapeamento foi aplicada;
- se houve inversão, exclusão ou consolidação manual.

### 3.4. Configuração vence inferência

Para o financeiro, consolidação não deve depender só de heurística.

O núcleo deve privilegiar:

- mapeamento explícito;
- chave canônica;
- validação de pendências sem mapeamento;
- trilha de auditoria.

## 4. Direção funcional proposta

O produto deve oferecer um **módulo de consolidação** em que o usuário configure grupos empresariais e seus relatórios consolidados.

Exemplo conceitual:

### Grupo 01

- Empresas:
  - Empresa 1
  - Empresa 2
  - Empresa 3

### Consolidação de Plano de Contas

- Conta Consolidadora | Conta da Empresa 1 | Conta da Empresa 2 | Conta da Empresa 3

O mesmo raciocínio pode ser aplicado, quando fizer sentido, para:

- centros de custo;
- projetos;
- processos;
- contrapartes;
- categorias gerenciais;
- naturezas de movimento;
- regras de eliminação intragrupo.

## 5. Camadas do módulo

### 5.1. Cadastro de grupo de consolidação

Responsável por definir:

- nome do grupo;
- empresas participantes;
- empresa líder ou referência visual;
- status de ativação;
- ordem de apresentação.

### 5.2. Catálogo de estruturas consolidadas

Responsável por definir entidades canônicas do grupo, como:

- conta consolidadora;
- centro de custo consolidador;
- categoria consolidada;
- projeto consolidado;
- processo consolidado.

### 5.3. Mapeamento empresa -> estrutura consolidada

Responsável por ligar a estrutura local de cada empresa à estrutura consolidada do grupo.

Exemplo:

- conta consolidada `3.01.001 Receita de Serviços`
- empresa A -> conta local `3.1.01`
- empresa B -> conta local `R-001`
- empresa C -> conta local `301001`

### 5.4. Engine de consolidação

Responsável por:

- buscar dados por `company_ids`;
- normalizar as linhas;
- aplicar mapeamentos;
- agregar valores;
- marcar pendências;
- retornar visão consolidada e visão por origem.

### 5.5. Workspace de auditoria

Responsável por exibir:

- itens não mapeados;
- conflitos de estrutura;
- linhas excluídas;
- linhas reclassificadas;
- diferenças entre consolidado e soma bruta.

## 6. Modelo conceitual inicial

Este paper não congela schema oficial, mas a direção conceitual mínima é:

### 6.1. Grupo

- `consolidation_group`
  - `id`
  - `name`
  - `description`
  - `is_active`

### 6.2. Empresas do grupo

- `consolidation_group_company`
  - `id`
  - `group_id`
  - `company_id`
  - `display_order`
  - `is_primary`

### 6.3. Contas consolidadoras

- `consolidation_chart_account`
  - `id`
  - `group_id`
  - `code`
  - `name`
  - `parent_id`
  - `accepts_posting`

### 6.4. Mapeamento de contas

- `consolidation_chart_mapping`
  - `id`
  - `group_id`
  - `consolidated_account_id`
  - `source_company_id`
  - `source_chart_account_id` ou `source_chart_account_code`
  - `sign_rule`
  - `mapping_type`
  - `notes`

### 6.5. Perfis de relatório consolidado

- `consolidation_report_profile`
  - `id`
  - `group_id`
  - `report_type`
  - `name`
  - `default_filters_json`
  - `show_company_breakdown`
  - `show_unmapped_items`
  - `show_eliminations`

## 7. Regras de consolidação

### 7.1. Chave canônica acima de ID local

Consolidação não deve usar somente ID interno das entidades locais.

Deve privilegiar:

- código;
- chave canônica;
- ou mapeamento explícito.

### 7.2. Estados mínimos de mapeamento

Cada linha consolidável deve poder ser classificada como:

- `mapped`
- `unmapped`
- `mapped_with_sign_inversion`
- `excluded`
- `reclassified`

### 7.3. Linha não mapeada não pode sumir

Se uma linha não estiver mapeada, ela não deve desaparecer silenciosamente.

Ela deve:

- aparecer em auditoria;
- poder bloquear fechamento consolidado, se o perfil exigir;
- ou entrar em bucket de pendência explícita.

### 7.4. Consolidação deve preservar drill-down

Todo total consolidado deve poder abrir detalhamento por:

- empresa;
- conta local;
- lançamento/título de origem;
- regra aplicada.

## 8. Tipos de relatório prioritários

A primeira onda de consolidação deve priorizar relatórios que têm maior valor executivo e estrutura mais previsível.

### Onda 1

- DRE consolidada
- fluxo de caixa consolidado
- relatório de títulos financeiros consolidado

### Onda 2

- razão consolidado
- extrato gerencial consolidado
- capital circulante líquido consolidado

### Onda 3

- relatórios operacionais consolidados por projeto/processo
- dashboards executivos de grupo
- análise comparativa grupo x empresa

## 9. Boundaries arquiteturais

### 9.1. Rota fina

As rotas não devem carregar regra de consolidação.

Devem apenas:

- validar entrada;
- resolver contexto autorizado;
- delegar ao service.

### 9.2. Service dedicado

A regra deve nascer em service próprio, algo na linha de:

- `consolidation_group_service`
- `consolidated_report_service`

### 9.3. Reuso dos builders atuais com camada intermediária

Sempre que possível, a evolução deve reaproveitar componentes atuais de leitura e montagem de relatório, mas com uma camada intermediária que:

- consulte múltiplas empresas;
- normalize payloads;
- aplique mapeamento consolidado.

### 9.4. Sem tenant crossing implícito

Mesmo em modo consolidado, o sistema só pode usar empresas:

- explicitamente selecionadas;
- pertencentes ao grupo;
- permitidas ao usuário.

## 10. Permissão e segurança

Relatório consolidado de grupo deve respeitar:

- vínculo do usuário com as empresas;
- papel administrativo ou executivo quando exigido;
- escopo explícito do grupo.

O sistema não deve permitir:

- consolidar empresa fora do grupo;
- consolidar empresa fora do escopo permitido ao usuário;
- usar configuração de grupo para burlar segregação multi-tenant.

## 11. UX proposta

O usuário deve conseguir:

- selecionar um grupo empresarial;
- escolher um perfil de relatório consolidado;
- definir período;
- alternar entre:
  - consolidado;
  - por empresa;
  - auditoria do mapeamento.

Filtros importantes:

- grupo
- empresas incluídas
- período
- perfil do relatório
- exibir não mapeados
- exibir eliminações
- detalhar por empresa

## 12. Benefícios esperados

- visão executiva real do grupo;
- menor dependência de montagem manual em planilhas;
- redução de erro operacional;
- melhor auditabilidade;
- base para governança financeira corporativa;
- evolução futura para dashboards consolidados, orçamento consolidado e análise intragrupo.

## 13. Riscos e cuidados

### 13.1. Risco de virar tenant paralelo

Se o grupo empresarial for tratado como nova empresa operacional, a arquitetura tende a quebrar segregação e gerar acoplamento indevido.

### 13.2. Risco de consolidar sem harmonização

Se empresas tiverem planos de contas muito diferentes e não houver mapeamento confiável, o consolidado pode induzir erro gerencial.

### 13.3. Risco de esconder pendência

Linhas não mapeadas ou eliminadas não podem ser invisíveis.

### 13.4. Risco de performance

Relatórios multiempresa exigirão atenção a:

- índices por `company_id`, datas e chaves de filtro;
- pré-agregação futura;
- paginação e drill-down sob demanda;
- eventual materialização analítica em etapas posteriores.

## 14. Fases sugeridas

### Fase 1 — Consolidação configurada por grupo

- cadastro de grupo
- vínculo empresa-grupo
- mapa de plano de contas
- DRE consolidada
- fluxo de caixa consolidado
- auditoria de não mapeados

### Fase 2 — Ampliação gerencial

- títulos financeiros consolidados
- razão consolidado
- perfis salvos de relatório
- subtotal por empresa

### Fase 3 — Consolidação corporativa ampliada

- centros de custo consolidados
- projetos/processos consolidados
- regras de eliminação intragrupo
- dashboards executivos

## 15. Decisão conceitual deste paper

Este paper sustenta a seguinte direção:

> O APP32 deve introduzir um módulo de consolidação de grupo empresarial baseado em configuração, mapeamento explícito e engine analítica multiempresa, preservando o multi-tenancy operacional por `company_id`.

Ainda não é uma SPEC.

É a tese de evolução recomendada para amadurecer a arquitetura antes de congelar:

- schema oficial;
- contratos de API;
- telas;
- regras definitivas por relatório.

