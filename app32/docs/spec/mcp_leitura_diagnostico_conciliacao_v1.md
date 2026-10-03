# SPEC — Leitura MCP para diagnóstico de conciliação v1

**Status:** proposta implementada somente no checkout local; não implantada.
**Escopo autorizado:** diagnóstico da empresa 9, sem reparo financeiro.

## Decisão
Criar três leituras dedicadas em `analytics`, sem ampliar o contrato das
ferramentas financeiras legadas ou publicar mutações em `user`:
- `list_financial_reconciliation_batches(company_id)`;
- `get_financial_reconciliation_batch(company_id, batch_id, row_ids=None)`;
- `get_financial_reconciliation_settlement(company_id, settlement_id)`.

## Segurança
- Capability explícita: domínio `finance`, risco baixo, `financial.view`,
  contextos `user` e `company`, scope exclusivo `mcp_analytics`.
- OAuth: scopes `mcp:access` e `mcp:analytics`; principal, grant ativo e RBAC
  continuam revalidados pelo wrapper existente a cada chamada.
- O serviço impõe empresa 9 antes de acessar qualquer repositório. Essa
  restrição adicional não concede acesso: a policy precisa autorizar primeiro.
- IDs são inteiros estritamente positivos; booleanos/coerções não são aceitos.
- Queries e serviços de leitura filtram `company_id` e `deleted_at`.
- Nenhum commit, flush, rollback, associação, geração de baixa ou aprendizado
  de classificação é executado pelas novas leituras.
- Sem novas credenciais, grants, migrações ou configurações de produção.

## Contrato e coleta
A listagem retorna `items`/`count`. O detalhe retorna `batch`, `rows`,
`matches` e `suggestions`, preservando status e metadados persistidos. O filtro
opcional de linhas reduz a resposta, sem modificar o lote. Sugestão de
classificação não é match de conciliação. A baixa retorna `item` com referências
inversas e componentes. Erros retornam `success=false` sem revelar outros tenants.

Coleta futura: resolver o código exato REC-20260918-INTER-CSV-V2; consultar
linhas 9577, 9581, 9584; seguir IDs realmente persistidos e comparar com baixas
esperadas 2752, 2684, 2687. Não inferir destino por valor/data.
Cancelamentos são matches `rejected` com `reconciliation_cancelled=true`.

## Harness local e aceite
Usar doubles em memória, Flask isolado e bloqueio de rede durante os testes;
não criar a aplicação real, não carregar credenciais nem conectar a banco.
Validar empresa 9, negação de outras empresas/IDs inválidos, queries tenant-safe,
referências nos dois sentidos, separação de statuses, filtro de linhas, discovery
e manifesto, negação sem autorização/scopes e ausência na surface OAuth user.
Os cinco casos já corrigidos não são reexecutados: esta entrega só lê.

## Limites
Não corrige `review_match` nem o workspace. Não resolve por si só
ERR_BLOCKED_BY_CLIENT. Não confirma versão ou vínculos de produção.
Implantação, concessão de acesso e reparo de dados exigem planos e aprovações
separados. Antes da implantação, reconciliar endpoint/SHA, grants existentes,
documentação dependente e evidência de smoke autenticado.

## Evidência local — 03/10/2026
- Harness isolado: **182 passed in 12.42s**, exit code 0, base local de main
  `e777d0b7ffaa6c0a3fa9dfc0bfbd6e0a4d4e6aff`.
- Runner: `scripts/qa/run_mcp_reconciliation_read_harness.py`.
- Python 3.11.7 do ambiente local; `.venv` original não tem `pyvenv.cfg`.
- Autoload de plugins desligado somente no harness por incompatibilidade de
  `pytest_flask` com Flask instalado; configuração do APP não foi alterada.
- RAG substituído por double e dotenv desativado no processo após falha de
  coleta e aprovação específica. Nenhuma chave foi fornecida ou necessária.
- Rede externa, PostgreSQL, SQLite e Engine real bloqueados pelo runner.
  Somente o socketpair interno do event loop Windows é permitido.
- O registrar financeiro não inclui estas ferramentas por padrão; o registry
  confiável ativa a opção somente para `analytics`. Testes negativos cobrem
  user, admin, finance, ops e registrar legado, inclusive por nome conhecido.
- Nenhum teste acessou vínculos reais; implantação e validação de produção
  continuam pendentes. Commit e PR foram autorizados separadamente;
  merge, deploy e reparos financeiros não fazem parte desta autorização.
