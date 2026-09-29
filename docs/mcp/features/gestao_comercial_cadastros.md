# Guia da Feature: Gestão Comercial — Cadastros

## Metadados
- `feature_id`: `gestao_comercial_cadastros`
- `dominio`: `governance`
- `ramo_menu`: `Gestão Comercial`
- `caminho_menu`: `Gestão Comercial > Cadastros`
- `rotas_app`: `/contracts/customers/portfolio`, `/contracts/customers`, `/contracts/parties`, `/contracts/legal-entities`, `/contracts/catalogs/items`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Manter os cadastros-base usados pela Gestão de Contratos: carteira de clientes, clientes, pessoas jurídicas emissoras (PJs) e o catálogo de produtos/serviços (grupo, sub-grupo e item), incluindo os dados fiscais de cada item.

## Quando usar
- explicar como organizar carteiras de clientes (estrutura em árvore)
- explicar que a lista de "Clientes" aqui é só uma visão filtrada do cadastro de favorecidos do módulo Financeiro — não é onde se cria um cliente novo
- explicar como cadastrar uma PJ emissora e suas alíquotas de ISS vigentes/futuras
- explicar a estrutura fixa de 3 níveis do catálogo comercial: Grupo → Sub-Grupo → Item
- explicar os campos fiscais de um item de catálogo (código de serviço, NBS, NCM, CFOP, alíquotas de ISS/IBS/CBS)

## Quando não usar
- para criar ou reclassificar um cliente/favorecido (Cliente vs Fornecedor) — isso só é feito no cadastro de favorecidos do módulo Financeiro
- para gerenciar o contrato em si, faturamento ou notas fiscais — feature própria: `gestao_comercial_contratos`
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `portfolio_id`, `counterparty_id`, `legal_entity_id`, `catalog_item_id`: identificadores para consulta/edição
- `catalog_view`: `structure` (Grupo/Sub-Grupo) ou `items` (Item)

## Saídas esperadas
- `carteiras_de_clientes`: árvore de carteiras
- `lista_de_clientes`: favorecidos marcados como cliente (`is_customer=True`)
- `pjs_emissoras`: pessoas jurídicas emissoras e suas regras de ISS
- `catalogo_comercial`: grupos, sub-grupos e itens com metadados fiscais

## Como orientar o usuário
1. Acessar **Gestão Comercial > Cadastros** no menu.
2. Em **Carteira de Clientes**, organizar a árvore — só os nós "analíticos" (folha) podem ser vinculados a um cliente; nós com filhos são apenas agrupadores.
3. Em **Clientes**, consultar a lista — para criar um cliente novo ou trocar a classificação Cliente/Fornecedor, o caminho é o cadastro de favorecidos do módulo Financeiro, não esta tela.
4. Em **PJs Emissoras**, cadastrar a pessoa jurídica que vai emitir as notas fiscais dos contratos — o código é gerado automaticamente em sequência, e cada PJ carrega seu próprio histórico de alíquota de ISS.
5. Em **Grupo de Produtos/Serviços** e **Produtos/Serviços** (mesma tela, filtrada por `catalog_view`), montar a hierarquia: um Item só pode existir dentro de um Sub-Grupo, nunca direto sob um Grupo.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP exposta no `mcp-versus`** para este domínio — mas, diferente da maioria das outras áreas mapeadas nesta iniciativa, **a cobertura de código já é madura**: ~15 tools reais em `src/core/mcp_commercial_tools.py` (`list/create/update/toggle_commercial_customer_portfolio`, `list_commercial_customers`, `update_commercial_customer`, `list/create/update_commercial_issuer`, `list/create/update/toggle_commercial_catalog_structure_item`, `list/create/update/toggle_commercial_products_services`, `get_commercial_product_service_readiness`), já rodando nas surfaces internas (`sapiens`, `admin`) e compartilhando 100% da lógica de negócio com a interface web (mesmos métodos de `ContractService`/`ContractsCatalogService`/`FinancialCatalogService`).

**Achado importante:** existe um mecanismo de "oferta comercial padronizada" por item de catálogo (`commercial_contract_v1`, campo `commercial_contract_enforced`, tool `get_commercial_product_service_readiness`) que calcula se um item está "pronto" para ativação comercial — mas o levantamento não encontrou onde esse dado é efetivamente consumido no fluxo de contrato/faturamento hoje. Trate como um mecanismo em construção; não afirme ao usuário que ele já controla algo no fluxo de venda.

## Validações e restrições
- `company_id` obrigatório; toda leitura e escrita é restrita à empresa ativa (nunca aceita `company_id` arbitrário do cliente)
- permissão do recurso `contracts` (`view` para leitura; `create`/`edit` checados no corpo da view antes de qualquer escrita)
- catálogo comercial tem hierarquia travada em exatamente 3 níveis (Grupo, Sub-Grupo, Item) — tentar um 4º nível é rejeitado
- item de catálogo exige um Sub-Grupo como pai; não pode ser criado direto sob um Grupo
- exclusão/toggle de item de catálogo tem `risk=HIGH` e fica restrito aos scopes admin

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`ContractService`, `ContractsCatalogService`, `FinancialCatalogService`)
- que "Clientes" e "Carteira de Clientes" aqui são o mesmo cadastro de favorecidos do Financeiro, filtrado — mas nunca prometa que dá para criar/reclassificar cliente por aqui
- dados de outra empresa/tenant
