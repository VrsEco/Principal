# Guia da Feature: Gestão Financeira — Cadastros

## Metadados
- `feature_id`: `financeiro_cadastros`
- `dominio`: `finance`
- `ramo_menu`: `Gestão Financeira`
- `caminho_menu`: `Gestão Financeira > Cadastros`
- `rotas_app`: `/financial/catalogs/counterparties`, `/financial/catalogs/bank-accounts`, `/financial/catalogs/chart-accounts`, `/financial/catalogs/cost-centers`, `/financial/catalogs/payment-methods`, `/financial/catalogs/correction-indexes`, `/financial/catalogs/discount-rules`, `/financial/catalogs/account-categories`, `/financial/catalogs/asset-accounts`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Gerenciar os cadastros básicos usados por todo o módulo financeiro: favorecidos, contas bancárias, plano de contas, centros de resultado, formas financeiras, correções, descontos, categorias de conta e contas patrimoniais.

## Quando usar
- explicar como cadastrar um favorecido (cliente, fornecedor ou outra contraparte)
- explicar como cadastrar uma conta bancária
- explicar como organizar o plano de contas e os centros de resultado, que são hierárquicos (podem ter item pai)
- explicar cadastros de apoio: formas financeiras (formas de pagamento), correções (índices), descontos, categorias de conta, contas patrimoniais
- orientar por que esses cadastros são pré-requisito para lançamentos, agendamentos, borderô, orçamento e conciliação

## Quando não usar
- para operar um lançamento ou movimento em si — isso é uma das features de Movimentos (`financeiro_agendamentos`, `financeiro_lancamento_rapido`, etc.)
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant
- tipo de cadastro (favorecido, conta bancária, plano de contas, centro de resultado, forma financeira, correção, desconto, categoria de conta ou conta patrimonial)

### Opcionais
- item pai (`parent_id`), para hierarquia em plano de contas e centro de resultado
- dados específicos de cada cadastro (ex: dados bancários da conta, papel do favorecido como cliente/fornecedor)

## Saídas esperadas
- `lista_do_cadastro`: itens cadastrados de um tipo específico
- `detalhe_do_item`: dados completos de um item do cadastro
- `resultado_da_operacao`: confirmação de criação, atualização ou exclusão

## Como orientar o usuário
1. Acessar **Gestão Financeira > Cadastros** no menu e escolher o tipo de cadastro desejado.
2. Plano de contas e centro de resultado são hierárquicos — organizar a estrutura (item pai/filho) antes de usar em lançamentos evita retrabalho depois.
3. Preencher os dados específicos do cadastro escolhido.
4. Lembrar que esses cadastros alimentam todas as demais features financeiras — sem um favorecido, conta bancária ou plano de contas cadastrado, não é possível lançar, agendar ou conciliar.
5. Editar ou excluir um item já em uso exige atenção: o sistema valida os vínculos existentes antes de permitir a exclusão.

## Uso por IA / MCP
Esta feature já é parcialmente consultável via MCP hoje:
- `list_financial_catalog_items` já permite à IA **listar** (leitura) os itens de cada tipo de cadastro na empresa.

O que **ainda não é capability remota**: criar, editar ou excluir um item de cadastro — essas ações continuam operacionais apenas no APP.

Qualquer evolução futura que exponha mutação de cadastros via MCP deve seguir o mesmo padrão de mutação sensível já usado em `create_financial_settlement` (gate humano obrigatório).

## Validações e restrições
- `company_id` obrigatório; um cadastro nunca pode ser vinculado a item de outra empresa
- hierarquias (plano de contas, centro de resultado) não podem formar ciclo — o sistema valida isso na criação/edição
- item de cadastro já em uso (referenciado por lançamento, agendamento, etc.) não pode ser excluído livremente
- criar, editar ou excluir cadastro é mutação sensível e, dependendo do tipo, pode exigir confirmação humana

## O que nunca expor
- identificadores técnicos internos de tipo de cadastro
- estrutura de tabelas internas
- lógica de geração automática de código
- dados financeiros de outra empresa/tenant
