# Guia da Feature: Gestão Financeira — Relatórios

## Metadados
- `feature_id`: `financeiro_relatorios`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Relatórios`
- `rotas_app`: `/financial`, `/financial/dashboard`, `/financial/reports/agendamento`, `/financial/reports/extrato-bancario`, `/financial/reports/dossie-extrato-bancario`, `/financial/reports/demonstrativo-resultados`, `/financial/reports/demonstrativo-resultados-02`, `/financial/reports/fluxo-caixa`, `/financial/reports/razao`, `/financial/reports/capital-circulante-liquido`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Consultar a posição financeira da empresa pelo dashboard executivo e por relatórios especializados: títulos, extrato bancário, demonstrações de resultado, fluxo de caixa, razão e capital circulante líquido.

## Quando usar
- explicar como interpretar o **Dashboard** (Visão) financeiro
- orientar qual relatório usar conforme a necessidade — veja a lista abaixo
- explicar os filtros disponíveis em cada relatório (período, conta bancária, conta contábil, centro de resultado, projeto)

## Quando não usar
- para operar ou lançar um movimento — isso é uma das features de Movimentos
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- tipo de relatório

### Opcionais
- período (a maioria dos relatórios aceita filtro de data)
- `bank_account_id`, `chart_account_id` (múltiplo), `cost_center_id` (múltiplo), projeto — conforme o relatório escolhido

## Saídas esperadas
- `relatorio_gerado`: dados formatados conforme o tipo de relatório escolhido

## Como orientar o usuário
1. Acessar **Gestão Financeira > Relatórios** no menu — o **Dashboard (Visão)** é a página inicial, com indicadores executivos consolidados.
2. Escolher o relatório certo conforme a necessidade:
   - **Relatório de Agendamento** (Relatório de Títulos Financeiros): mapa operacional dos títulos, com saldos, baixas e vínculo com borderô.
   - **Extrato Bancário**: extrato gerencial das baixas por conta, com saldo inicial, entradas, saídas e saldo final.
   - **Dossiê do Extrato Bancário**: pacote documental com extrato bancário, DRE por liquidação e comprovantes anexados.
   - **Demonstrativo de Resultados** (01): DRE contábil de período único, com apuração por competência, vencimento ou baixa.
   - **Demonstrativos de Resultados 02**: DRE contábil hierárquica, com as três visões (competência, vencimento, baixa) lado a lado.
   - **Fluxo de Caixa**: saldo diário, realizado, projeções em aberto e saldo acumulado do período.
   - **Razão**: histórico de lançamentos por conta contábil, com baixa vinculada e saldo acumulado.
   - **Capital Circulante Líquido**: composição de disponibilidades, recebíveis, exigibilidades e folga financeira.
3. Aplicar os filtros disponíveis em cada relatório — período é comum à maioria; alguns aceitam múltiplas contas contábeis, centros de resultado ou projetos ao mesmo tempo.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP que gere os relatórios formatados. Via MCP, a IA pode:
- consultar lançamentos e catálogos já existentes (`list_financial_entries`, `list_financial_catalog_items`) para responder perguntas pontuais sobre posição financeira;
- explicar qual relatório usar para cada necessidade, usando este guia.

A IA **não pode** gerar os relatórios formatados (com layout, totalizações e exportação) por MCP — essas visões continuam exclusivas do APP.

## Validações e restrições
- `company_id` obrigatório em qualquer relatório
- relatórios respeitam RBAC e surface — alguns dados sensíveis não aparecem quando a chamada vem de `surface=user`
- filtros de conta/centro de resultado só retornam dados da mesma empresa

## O que nunca expor
- lógica interna de cálculo de cada relatório
- nomes de services e identificadores técnicos internos (slugs de relatório)
- dados financeiros de outra empresa/tenant
