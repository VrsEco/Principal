# Guia da Feature: Gestão Financeira — Conciliação Bancária

## Metadados
- `feature_id`: `financeiro_conciliacao_bancaria`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Conciliação Bancária`
- `rota_app`: `/financial/reconciliation`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Ajudar o usuário a conciliar lançamentos bancários importados (extrato) com títulos e lançamentos já cadastrados no sistema (ledger), confirmando pagamentos e recebimentos reais e mantendo o caixa como fonte de verdade.

## Quando usar
- explicar como importar e revisar um extrato bancário para conciliação
- orientar como interpretar as sugestões automáticas de correspondência (auto-match) entre extrato e sistema
- explicar como confirmar, ajustar manualmente ou recusar uma sugestão de correspondência
- explicar como liquidar um título em aberto diretamente a partir de uma linha do extrato
- explicar como agrupar várias linhas do extrato num borderô e reconciliar em lote
- orientar como cancelar uma conciliação feita por engano

## Quando não usar
- para executar a conciliação em nome do usuário sem confirmação humana — é mutação financeira sensível
- para explicar fluxo de caixa executivo, orçamento matricial ou outros módulos de "Gestão Financeira > Movimentos" — cada um tem seu próprio feature
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `bank_account_id`: conta bancária cujo extrato está sendo conciliado

### Opcionais
- `batch_id`: lote de extrato importado
- `search_query`, `amount_filter`, `movement_nature`: filtros de busca na tela
- intervalo de datas (`data_inicio`, `data_fim`)

## Saídas esperadas
- `linhas_do_extrato`: linhas do extrato bancário importado (staging), com status de conciliação
- `titulos_em_aberto`: títulos/lançamentos do sistema ainda não conciliados
- `sugestoes_de_match`: correspondências sugeridas automaticamente entre extrato e sistema, com nível de confiança
- `resultado_da_conciliacao`: status final de cada linha (conciliada, pendente, cancelada)

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Conciliação Bancária** no menu.
2. Selecionar a conta bancária e o lote de extrato já importado.
3. O sistema sugere automaticamente correspondências entre linhas do extrato e títulos do sistema, com uma pontuação de confiança.
4. Para cada sugestão, o usuário pode: confirmar a correspondência sugerida, ajustar manualmente quando o sistema não acertar sozinho, ou liquidar diretamente um título em aberto a partir da linha do extrato.
5. Quando várias linhas pertencem ao mesmo pagamento agrupado (ex: um borderô bancário), usar a opção de reconciliar em grupo.
6. Se algo for conciliado por engano, é possível cancelar a conciliação de uma linha específica ou de um lote inteiro — o lançamento original não é apagado, só desfaz o vínculo.

Explique sempre em dois lados: **extrato** (o que o banco informou) e **sistema** (o que já está lançado) — o objetivo da conciliação é fechar os dois lados um a um.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada ao motor de correspondência (matching) em si. Via MCP, a IA pode:
- consultar lançamentos e status financeiros já existentes (`list_financial_entries`, `list_financial_catalog_items`) para dar contexto antes ou depois da conciliação;
- explicar o fluxo de conciliação usando este guia, orientando o usuário a executar os passos no APP;
- **não pode** disparar auto-match, confirmar correspondência ou liquidar título por MCP — essas ações ainda não são capability canônica remota.

Qualquer evolução futura que exponha conciliação via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; nunca cruzar contas bancárias ou lançamentos entre empresas
- toda liquidação ou conciliação sugerida pela IA precisa de confirmação humana antes de ser efetivada no APP
- ajuste de valor por índice de correção (juros/multa) segue a mesma trilha de auditoria dos lançamentos normais
- cancelar uma conciliação preserva o histórico de auditoria; não apaga o lançamento original

## O que nunca expor
- lógica interna do algoritmo de pontuação (scoring) de correspondência
- estrutura de tabelas internas (linhas de importação, matches, etc.)
- nomes de services e métodos internos
- dados bancários de outra empresa/tenant
