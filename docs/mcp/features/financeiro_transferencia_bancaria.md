# Guia da Feature: Gestão Financeira — Transferência Bancária

## Metadados
- `feature_id`: `financeiro_transferencia_bancaria`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Movimentos > Transferência Bancária`
- `rota_app`: `/financial/transfers`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Registrar a movimentação de caixa entre duas contas bancárias da própria empresa, sem afetar o resultado financeiro (DRE).

## Quando usar
- explicar como registrar uma transferência entre contas bancárias da mesma empresa
- orientar por que a transferência não entra no resultado (DRE), só no extrato e no caixa
- explicar por que a conta de origem e a de destino precisam ser diferentes
- explicar como editar ou excluir uma transferência já registrada

## Quando não usar
- para pagamento ou recebimento envolvendo terceiros — isso é um lançamento financeiro comum, não uma transferência entre contas próprias
- para explicar conciliação bancária em si (feature própria: `financeiro_conciliacao_bancaria`)
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- `source_bank_account_id`: conta bancária de origem
- `destination_bank_account_id`: conta bancária de destino (deve ser diferente da origem)
- `occurred_on`: data da transferência
- valor da transferência

### Opcionais
- `document_number`: número de documento associado
- observações/metadados

## Saídas esperadas
- `lista_de_transferencias`: transferências já registradas na empresa
- `detalhe_da_transferencia`: o par de lançamentos vinculados (saída na origem, entrada no destino)
- `resultado_da_operacao`: confirmação de criação, atualização ou exclusão

## Como orientar o usuário
1. Acessar **Gestão Financeira > Movimentos > Transferência Bancária** no menu.
2. Selecionar a conta de **origem** e a conta de **destino** — o sistema recusa se forem a mesma conta.
3. Informar o valor, a data e, opcionalmente, um número de documento.
4. Ao confirmar, o sistema cria **dois lançamentos vinculados**: uma saída na conta de origem e uma entrada na conta de destino, agrupados por um identificador comum de transferência.
5. Esses lançamentos aparecem no extrato bancário e no caixa, mas **nunca no DRE** — transferência entre contas próprias não é receita nem despesa.
6. Editar ou excluir uma transferência afeta os dois lançamentos vinculados juntos, nunca só um lado isoladamente.

## Uso por IA / MCP
Hoje esta feature é **operacional apenas no APP** — não há tool MCP dedicada à criação de transferências. Via MCP, a IA pode:
- consultar lançamentos financeiros já existentes (`list_financial_entries`) para dar contexto sobre transferências já realizadas;
- explicar o fluxo de transferência usando este guia, orientando o usuário a executar os passos no APP;
- **não pode** criar, editar ou excluir transferências por MCP — essa ação ainda não é capability canônica remota.

Qualquer evolução futura que exponha transferência via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; as duas contas bancárias devem pertencer à mesma empresa
- conta de origem e conta de destino não podem ser a mesma conta
- toda transferência é automaticamente excluída do DRE e incluída no extrato bancário
- excluir uma transferência sempre remove os dois lançamentos vinculados juntos, nunca um só
- criar, editar ou excluir transferência é mutação financeira sensível e precisa de confirmação humana

## O que nunca expor
- lógica interna de sincronização entre os dois lançamentos vinculados
- estrutura de tabelas internas (lançamentos, grupos de transferência)
- nomes de services e métodos internos
- dados bancários de outra empresa/tenant
