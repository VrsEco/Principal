# Guia da Feature: Gestão Comercial — Gestão de Contratos

## Metadados
- `feature_id`: `gestao_comercial_contratos`
- `dominio`: `governance`
- `ramo_menu`: `Gestão Comercial`
- `caminho_menu`: `Gestão Comercial > Gestão de Contratos`
- `rotas_app`: `/contracts`, `/contracts/dashboard`, `/contracts/list`, `/contracts/new`, `/contracts/billing`, `/contracts/billing/review`, `/contracts/billing/done`, `/contracts/invoices`
- `surfaces_permitidas`: `user`, `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Conduzir o ciclo completo de um contrato comercial: cadastro e ciclo de vida (ativar, suspender, encerrar), itens e termos financeiros/fiscais, geração de faturamento, ponte com o financeiro (títulos e retenções) e acompanhamento do status fiscal (NFS-e) até a exportação para emissão externa.

## Quando usar
- explicar como cadastrar um contrato, seus itens e termos financeiros/fiscais
- explicar o ciclo de vida de um contrato: ativar, suspender, encerrar, excluir
- explicar o fluxo de faturamento: **Faturar** (seleção) → **revisão** (ajustes por contrato/item) → confirmação → **Faturamentos Feitos**
- explicar como gerar os títulos financeiros (e retenções) a partir de um faturamento confirmado
- explicar como acompanhar e exportar o status fiscal das notas (workspace de **Notas Fiscais**)
- explicar por que não é possível faturar duas vezes a mesma competência de um contrato

## Quando não usar
- para gerenciar cadastros-base (clientes, PJs emissoras, catálogo) — feature própria: `gestao_comercial_cadastros`
- para tratar o lançamento financeiro em si depois de gerado (ele já é <br>um título comum do módulo Financeiro) — features próprias de Gestão Financeira
- **nunca afirme que o sistema emite nota fiscal eletrônica de verdade** — ver "Uso por IA / MCP"
- fora da surface autorizada

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `contract_id`, `billing_id`, `billing_ids`, `party_id`: identificadores de referência
- `section`: aba do workspace do contrato (cliente, itens, faturamento, financeiro, fiscal, periodicidade, cláusulas, automações, documentos)
- `reason`: motivo obrigatório em ações de ciclo de vida (suspender/encerrar/cancelar)

## Saídas esperadas
- `dashboard_comercial`: visão geral de contratos
- `workspace_do_contrato`: abas do contrato (itens, financeiro, fiscal, cláusulas, automações, documentos)
- `fila_de_faturamento` / `revisao_de_faturamento`: contratos elegíveis e preview antes de confirmar
- `faturamentos_gerados`: faturamentos já confirmados, com status de integração financeira
- `workspace_fiscal`: status de nota fiscal por faturamento, lotes, planilha de exportação

## Como orientar o usuário
1. Acessar **Gestão Comercial > Gestão de Contratos** no menu.
2. Em **Cadastro de Contratos**, criar o contrato, adicionar itens (do catálogo comercial) e definir termos financeiros/fiscais; ativar, suspender ou encerrar sempre exige um motivo registrado (trilha de auditoria).
3. Em **Faturar**, selecionar os contratos elegíveis para o período — isso só abre a revisão, não gera nada ainda.
4. Na revisão, ajustar itens/observações por contrato se necessário e confirmar — aí sim o faturamento é gerado e sai da fila.
5. Em **Faturamentos Feitos**, gerar os títulos financeiros (e retenções: ISS, IR, PIS, COFINS, CSLL, INSS conforme as políticas do contrato) — isso é um clique explícito, o faturamento comercial não lança sozinho no financeiro. Também é aqui que se cancela um faturamento, se necessário (reverte os títulos financeiros vinculados).
6. Em **Notas Fiscais**, acompanhar o status de cada faturamento (pendente/emitida/cancelada), agrupar em lotes, exportar a planilha de integração e marcar manualmente quando a nota foi emitida ou cancelada — ou anexar o arquivo da nota já emitida.

## Uso por IA / MCP
Hoje **não existe nenhuma tool MCP exposta no `mcp-versus`** — mas, assim como os cadastros comerciais, a cobertura de código já é madura: ~15 tools reais em `src/core/mcp_commercial_tools.py` cobrindo contrato (`list/get/create/update/suspend/close/delete_commercial_contract`, `add/update_commercial_contract_item`, `upsert_commercial_contract_financial_terms/fiscal_terms`, `get_commercial_dashboard`), faturamento (`list_commercial_billing_queue`, `build_commercial_billing_review`, `preview_commercial_billing_batch`, `generate_commercial_billing_batch`, `list_commercial_billings_done`, `generate_commercial_financial_titles_for_billing`, `cancel_commercial_billing`) e fiscal (`list_commercial_fiscal_workspace`, `update_commercial_fiscal_entry`, `assign/remove_commercial_fiscal_batch`, `update_commercial_fiscal_status`, `export_commercial_fiscal_integration_spreadsheet`).

Já têm `human_gate=True` no catálogo de capacidades: `update_commercial_offer_contract`, `suspend_commercial_contract`, `close_commercial_contract`, `delete_commercial_contract` (mudança de lifecycle contratual), e `generate_commercial_billing_batch`, `generate_commercial_financial_titles_for_billing`, `cancel_commercial_billing` (operação financeira comercial) — o padrão de gate já está corretamente desenhado no código, só falta a decisão de expor no piloto OAuth.

**Achado crítico para nunca errar ao orientar o usuário: NÃO existe emissão fiscal real de NFS-e.** Não há nenhuma integração com provedor de nota fiscal (prefeitura, SEFAZ, ou serviço terceiro tipo Focus NFe/NFE.io/PlugNotas). O que existe é: (1) exportar uma planilha XLSX com os dados no layout de NFS-e para importar manualmente em algum sistema externo não identificado no código; (2) o usuário emite a nota **fora do APP32**; (3) volta e marca manualmente "emitida" ou "cancelada", ou anexa o arquivo da nota já emitida (o sistema tenta casar o arquivo com um faturamento pendente por heurística simples de nome/conteúdo, não é um parser fiscal robusto). Trate esta feature como controle e rastreio de status fiscal, nunca como emissor de nota fiscal.

## Validações e restrições
- `company_id` obrigatório; nunca aceita `company_id` arbitrário do cliente para autorizar ou persistir
- permissão do recurso `contracts` (`view` no decorator; `create`/`edit` checados no corpo da view)
- **idempotência de faturamento por competência**: cada faturamento nativo tem uma chave baseada em contrato + início/fim da competência; tentar faturar a mesma competência de novo (com faturamento ainda não cancelado) é rejeitado explicitamente
- ações de ciclo de vida (suspender, encerrar, excluir contrato; cancelar faturamento) sempre exigem `reason` e ficam registradas em trilha de auditoria
- cancelar um faturamento reverte em cascata os títulos financeiros e execuções de satélite (retenções) vinculados a ele
- geração de títulos financeiros a partir de um faturamento é sempre uma ação explícita separada — nunca automática

## O que nunca expor
- estrutura de tabelas internas ou nomes de services (`ContractService`, `ContractFinancialService`, `ContractsCatalogService`)
- a hipótese de que o sistema emite NFS-e de verdade — reforce sempre que é controle manual + exportação, não emissão fiscal
- dados de outra empresa/tenant
