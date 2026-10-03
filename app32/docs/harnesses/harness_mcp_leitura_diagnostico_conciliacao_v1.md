# Harness — Leituras MCP de diagnóstico da conciliação v1

**Status:** validado localmente; não é evidência de produção.
**SPEC:** `docs/spec/mcp_leitura_diagnostico_conciliacao_v1.md`.

## Reprodução
Na raiz Git, executar:

```powershell
python app32/scripts/qa/run_mcp_reconciliation_read_harness.py
```

O runner usa aplicação Flask mínima, doubles em memória, bloqueio de banco e
rede externa. Não carrega a factory real do APP32. O RAG é substituído por double e o
carregamento de `.env` é desativado somente neste processo. O socketpair interno do
asyncio no Windows é permitido, sem liberar conexões arbitrárias.

## Resultado verificado em 03/10/2026
**182 passed in 12.42s**, exit code 0, na branch isolada
`codex/mcp-conciliacao-leitura`, base local de main
`e777d0b7ffaa6c0a3fa9dfc0bfbd6e0a4d4e6aff`.

A primeira coleta nessa base falhou pelo bootstrap de RAG sem chave; após
aprovação, o runner foi isolado de RAG e dotenv e a suíte acima passou.
O resultado anterior (169 testes no checkout original) não substitui esta
evidência. Nenhuma credencial foi fornecida. Alterações preexistentes no
checkout original foram preservadas.

## Cobertura
- empresa 9 e negação antecipada de outros tenants;
- inteiros estritos e IDs inválidos sem consulta;
- lote inexistente, linha de outro lote, baixa ausente e erros propagados;
- contrato com matches confirmed/suggested/rejected e marcador de cancelamento;
- múltiplos matches por linha e preservação dos metadados nos dois sentidos;
- filtro de linhas sem modificar o payload original;
- query de baixa por ID, empresa e soft delete;
- capability explícita analytics/financial.view e policy com negação sem usuário,
  permissão, scope ou tenant autorizado;
- discovery unificado, paridade com manifesto e ausência das novas leituras em
  OAuth user e registrars de outras surfaces;
- nenhuma chamada de mutação ou bootstrap real no serviço de diagnóstico;
- regressões existentes de registrar financeiro, registry, tool policy e RBAC.

## Fora do alcance
Não testa correção financeira, cancelamento real, duplicidade concorrente em
PostgreSQL nem atomicidade do review_match: estes fluxos não foram modificados.
Não acessa ou reexecuta os cinco casos corrigidos e não comprova os três vínculos
pendentes. Integração com banco de teste PostgreSQL e smoke autenticado no
endpoint implantado exigem etapa separada e ambiente oficialmente autorizado.
