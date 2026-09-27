# Guia da Feature: Gestão Financeira — Lançamento Rápido

## Metadados
- `feature_id`: `financeiro_lancamento_rapido`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Lançamento Rápido`
- `rota_app`: `/financial/entries`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Registrar em um único passo um movimento financeiro que já aconteceu (pagamento ou recebimento já efetivado), criando título, lançamento e baixa ao mesmo tempo — sem precisar passar por um agendamento futuro.

## Quando usar
- explicar como registrar rapidamente um pagamento ou recebimento já realizado
- orientar quando usar lançamento rápido em vez de um agendamento — **agendamentos** são para títulos que ainda vão vencer no futuro; **lançamento rápido** é para algo que já aconteceu, já pago ou recebido
- explicar os vínculos obrigatórios (conta bancária) e opcionais (favorecido, plano de contas, centro de resultado)
- explicar como ratear (dividir) um lançamento entre mais de uma combinação de conta contábil e centro de resultado

## Quando não usar
- para um título que ainda vai vencer no futuro — usar a feature `financeiro_agendamentos`
- para conciliar um lançamento já existente com o extrato bancário — usar `financeiro_conciliacao_bancaria`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `bank_account_id`: conta bancária onde o movimento aconteceu
- `entry_type`: pagamento ou recebimento
- valor (`original_amount`) e data (`occurred_on`/`due_date`)

### Opcionais
- `counterparty_id`: favorecido
- `chart_account_id`, `cost_center_id`: conta contábil e centro de resultado
- `allocations`: rateio entre mais de uma combinação de conta/centro de resultado
- `document_number`: número de documento

## Saídas esperadas
- `lista_de_lancamentos`: lançamentos já registrados por lançamento rápido
- `resultado_do_lancamento`: título, lançamento e baixa criados juntos, já conciliados

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Lançamento Rápido** no menu.
2. Escolher a **conta bancária** onde o movimento aconteceu (obrigatória) e o tipo: pagamento ou recebimento.
3. Informar o valor e a data do movimento.
4. Opcionalmente vincular a um favorecido, uma conta contábil e um centro de resultado — ou ratear o valor entre mais de uma combinação.
5. Ao confirmar, o sistema cria **de uma vez** o título, o lançamento e a baixa (liquidação), já como um movimento efetivado — diferente do fluxo de Agendamentos, que separa a criação do título da baixa futura.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada ao lançamento rápido. Via MCP, a IA pode:
- consultar lançamentos já existentes (`list_financial_entries`) para dar contexto sobre movimentos já registrados;
- explicar quando usar lançamento rápido em vez de agendamento, usando este guia;
- **não pode** criar lançamento rápido por MCP — essa ação ainda não é capability canônica remota.

Qualquer evolução futura que exponha lançamento rápido via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; conta bancária é sempre obrigatória (diferente de agendamento, onde é opcional)
- todos os vínculos (favorecido, conta contábil, centro de resultado) devem pertencer à mesma empresa
- quando houver rateio (`allocations`), a soma das partes deve fechar com o valor total do lançamento
- criar um lançamento rápido é mutação financeira sensível e precisa de confirmação humana

## O que nunca expor
- lógica interna de criação simultânea de título, lançamento e baixa
- estrutura de tabelas internas
- nomes de services e métodos internos
- dados financeiros de outra empresa/tenant
