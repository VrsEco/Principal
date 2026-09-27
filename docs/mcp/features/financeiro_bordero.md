# Guia da Feature: Gestão Financeira — Borderô

## Metadados
- `feature_id`: `financeiro_bordero`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Borderô`
- `rota_app`: `/financial/borderos`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Agrupar vários títulos financeiros (todos a pagar, ou todos a receber) num único lote — o borderô — para revisar, processar e dar baixa em conjunto.

## Quando usar
- explicar como criar um borderô agrupando títulos a pagar ou a receber
- orientar por que não é possível misturar títulos a pagar e a receber no mesmo borderô
- explicar como adicionar ou remover itens de um borderô ainda aberto
- explicar como dar baixa (liquidar) os itens de um borderô
- orientar que um título só pode estar vinculado a um borderô aberto por vez
- explicar como editar ou excluir um borderô

## Quando não usar
- para executar criação, edição ou baixa de borderô em nome do usuário sem confirmação humana — é mutação financeira sensível
- para explicar a conciliação bancária em si (tem feature própria: `financeiro_conciliacao_bancaria`) — se o borderô nascer a partir de uma linha de extrato, mencione a ligação mas oriente pelo fluxo de conciliação naquela feature
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `bordero_type`: tipo do borderô — `a_pagar` ou `a_receber` (não podem se misturar no mesmo borderô)

### Opcionais
- `items`: lista de títulos financeiros (`financial_schedule_id`) a incluir
- `name`, `description`, `notes`
- `created_date`

## Saídas esperadas
- `lista_de_borderos`: borderôs da empresa, com código, tipo, status e valor total
- `detalhe_do_bordero`: itens vinculados, valores, status de cada um
- `resultado_da_baixa`: liquidações (settlements) geradas ao dar baixa nos itens

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Borderô** no menu.
2. Criar um novo borderô escolhendo o tipo: **a pagar** ou **a receber** — os dois tipos nunca podem estar no mesmo borderô.
3. Adicionar títulos financeiros já lançados e com saldo em aberto — títulos em rascunho, cancelados ou apenas previstos não podem entrar.
4. Cada título só pode estar vinculado a **um borderô aberto por vez**; o sistema bloqueia a duplicidade automaticamente.
5. Revisar o valor total consolidado do borderô antes de confirmar a criação.
6. Quando o pagamento ou recebimento for efetivado, dar baixa nos itens do borderô — isso gera as liquidações (settlements) vinculadas a cada título.
7. Um borderô aberto pode ser editado (nome, itens) ou excluído; um borderô já com baixas precisa de cuidado extra, pois excluir desfaz as liquidações vinculadas.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada à criação ou gestão de borderô. Via MCP, a IA pode:
- consultar lançamentos e status financeiros já existentes (`list_financial_entries`, `list_financial_catalog_items`) para dar contexto antes ou depois de um borderô;
- explicar o fluxo de borderô usando este guia, orientando o usuário a executar os passos no APP;
- **não pode** criar, editar, excluir ou dar baixa em borderô por MCP — essas ações ainda não são capability canônica remota.

Qualquer evolução futura que exponha borderô via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; título de outra empresa nunca pode entrar num borderô
- não é permitido misturar títulos a pagar e a receber no mesmo borderô
- só título financeiro operacional com saldo em aberto entra num borderô (rascunho, cancelado ou previsto são recusados)
- um título só pode estar em um borderô aberto por vez — tentativa de duplicidade é bloqueada
- toda baixa de borderô é mutação financeira sensível e precisa de confirmação humana

## O que nunca expor
- lógica interna de alocação de valores entre itens do borderô
- estrutura de tabelas internas (borderô, itens, liquidações)
- nomes de services e métodos internos
- dados financeiros de outra empresa/tenant
