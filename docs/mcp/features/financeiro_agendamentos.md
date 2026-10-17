# Guia da Feature: Gestão Financeira — Agendamentos

## Metadados
- `feature_id`: `financeiro_agendamentos`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Agendamentos`
- `rota_app`: `/financial/schedules`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Cadastrar e gerenciar títulos financeiros — a pagar ou a receber, avulsos ou recorrentes — que geram lançamentos e podem se vincular a favorecidos, contas, processos e rotinas.

## Quando usar
- explicar como criar um título financeiro (a pagar ou a receber)
- orientar como configurar um título recorrente, que gera lançamentos automaticamente ao longo do tempo
- explicar como pausar ou reativar um agendamento
- explicar como gerar o lançamento (ou já a liquidação direta) a partir de um título vencido
- explicar como vincular um título a favorecido, conta bancária, plano de contas, centro de resultado, processo ou rotina
- explicar como anexar comprovantes a um título

## Quando não usar
- para conciliação bancária isolada (feature própria: `financeiro_conciliacao_bancaria`)
- para orçamento matricial em si (feature própria: `financeiro_orcamento_matricial`) — embora um título possa nascer de uma linha de orçamento
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `entry_type`: tipo do título — a pagar ou a receber
- `movement_nature`: natureza do movimento (deve ser compatível com `entry_type`)
- valor e data de vencimento

### Opcionais
- `bank_account_id`, `counterparty_id` (favorecido), `chart_account_id`, `cost_center_id`
- `activity_id`, `process_instance_id`, `routine_id`: vínculo com processo/rotina/atividade
- frequência de recorrência
- `allocations`: rateio entre contas/centros de resultado
- anexos (comprovantes/documentos)

## Saídas esperadas
- `lista_de_agendamentos`: títulos financeiros da empresa, com status e próximos vencimentos
- `detalhe_do_agendamento`: vínculos, histórico e recorrência de um título
- `lancamento_gerado`: lançamento criado a partir do agendamento
- `resultado_da_baixa`: liquidação registrada a partir de um título

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Agendamentos** no menu.
2. Criar um novo título, escolhendo o tipo: **a pagar** ou **a receber** — a natureza do movimento precisa ser compatível com o tipo escolhido.
3. Vincular o título a favorecido, conta bancária, plano de contas e centro de resultado; quando fizer sentido, vincular também a um processo/instância ou rotina.
4. Se for um título recorrente, configurar a frequência — o sistema materializa os lançamentos futuros automaticamente conforme a regra definida.
5. Pausar um agendamento (toggle) interrompe a geração de novos lançamentos sem apagar o histórico já gerado.
6. Quando o título vencer, gerar o lançamento correspondente ou já registrar a liquidação diretamente a partir do agendamento.
7. É possível anexar comprovantes e documentos ao título.
8. Excluir um agendamento que já tem baixas ativas exige atenção — normalmente exige tratar as baixas antes.

## Uso por IA / MCP
Regra do produto: **toda conta a pagar ou a receber é um agendamento** (Títulos Financeiros). Nunca crie conta a pagar/receber por `create_financial_entry`: a tool recusa `payable` e `receivable`.

Tools disponíveis:
- `create_financial_schedule_secure(company_id, payload, idempotency_key)`: cria o agendamento (avulso com `frequency: "one_time"` ou recorrente). **Exige aprovação humana** (gate) no APP32: a primeira chamada devolve o número da solicitação; após a aprovação, repita exatamente a mesma chamada. Repetir com a mesma `idempotency_key` devolve o mesmo agendamento, sem duplicar.
- `list_financial_schedules`, `update_financial_schedule`, `toggle_financial_schedule`, `generate_due_financial_schedules`: consulta e gestão.
- `delete_financial_entry(company_id, entry_id)`: exclusão lógica de lançamento criado por conector MCP, sem baixa, conciliação, borderô ou agendamento vinculado. Exige aprovação humana. Para desfazer um agendamento, use `toggle_financial_schedule` com status `cancelled`.

Campos aceitos no `payload` (o `company_id` do payload, se informado, deve coincidir com o da chamada):
- obrigatórios: `name`, `description`, `entry_type` (`payable`/`receivable`), `movement_nature` (`debit` para pagar, `credit` para receber), `start_date`, `first_due_date`, `template_amount`
- recorrência: `frequency` (`one_time`, `weekly`, `monthly`, `yearly`), `interval_value`, `day_of_month`, `end_date`
- `status`: use `active` para o título valer; o padrão é `draft`
- `competence_date` (padrão: `start_date`; `first_due_date` não pode ser anterior à competência), `document_number_prefix`, `memo`
- vínculos: `counterparty_id` (favorecido), `bank_account_id`, `chart_account_id`, `cost_center_id`, `activity_id`, `process_instance_id`, `routine_id`
- `allocations`: rateio; cada item com `allocation_type` (`percentage` ou `amount`), `percentage` ou `allocated_amount`, `chart_account_id` e `cost_center_id`; a soma deve fechar 100% (ou o valor do título)
- `schedule_code` é opcional: se omitido, o sistema gera `AG-000001`, `AG-000002` e assim por diante

Exemplo (título a pagar avulso, rateio de 100%), argumentos da tool:

```json
{
  "company_id": 16,
  "idempotency_key": "sefaz-ba-paf-128984-2026-09",
  "payload": {
    "name": "SEFAZ-BA Transação Tributária - PAF 128984.0120/24-9",
    "description": "SEFAZ-BA Transação Tributária - PAF 128984.0120/24-9",
    "entry_type": "payable",
    "movement_nature": "debit",
    "frequency": "one_time",
    "status": "active",
    "start_date": "2026-09-30",
    "competence_date": "2026-09-30",
    "first_due_date": "2026-09-30",
    "template_amount": 2635.95,
    "counterparty_id": 223,
    "allocations": [
      {"allocation_type": "percentage", "percentage": 100, "chart_account_id": 805, "cost_center_id": 67}
    ]
  }
}
```

O agendamento aparece em **Financeiro > Títulos Financeiros** e no relatório de títulos, no vencimento informado. A tela de Títulos abre com o filtro de vencimento do mês corrente (agora indicado em destaque); para ver títulos de outros meses, ajuste ou limpe o filtro.

## Validações e restrições
- `company_id` obrigatório; `movement_nature` deve ser compatível com `entry_type`
- todos os vínculos (conta bancária, favorecido, plano de contas, centro de resultado, processo, rotina) devem pertencer à mesma empresa
- título com baixa ativa não pode ser excluído livremente
- criar, editar, excluir agendamento e gerar lançamento/baixa são mutações financeiras sensíveis e precisam de confirmação humana

## O que nunca expor
- lógica interna de materialização de recorrência
- estrutura de tabelas internas (agendamentos, alocações, anexos)
- nomes de services e métodos internos
- dados financeiros de outra empresa/tenant
