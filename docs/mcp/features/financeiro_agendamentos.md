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
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada à criação ou gestão de agendamentos. Via MCP, a IA pode:
- consultar lançamentos e catálogos financeiros já existentes (`list_financial_entries`, `list_financial_catalog_items`) para dar contexto sobre títulos já cadastrados;
- explicar o fluxo de agendamento (avulso ou recorrente) usando este guia, orientando o usuário a executar os passos no APP;
- **não pode** criar, editar, pausar, excluir agendamento nem gerar lançamento/baixa por MCP — essas ações ainda não são capability canônica remota.

Qualquer evolução futura que exponha agendamentos via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

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
