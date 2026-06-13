# Harness — Central de Testes E2E

## Classe
Harness

## Papel
Operar a camada supervisionada da suíte E2E dentro do app32.

## Entradas aceitas
- `suite_id`
- `environment`

## Restrições
- somente suítes do catálogo oficial
- `DEV_FULL` para jornadas destrutivas
- `PROD_SAFE` para smoke e relatórios não destrutivos

## Saídas
- `meta.json` por execução supervisionada
- `stdout.log`
- `stderr.log`
- artefatos normais da suíte em `app32/tests/e2e/outputs`

## Localizações canônicas
- service: `C:\GestaoVersus\app32\app32\tests\e2e\core\e2e_supervised_execution_service.py`
- central web: `C:\GestaoVersus\app32\app32\templates\modules\operations\e2e_center.html`
- catálogo: `C:\GestaoVersus\app32\app32\tests\e2e\catalog\suite_catalog.py`

## Cobertura funcional atualizada
- Financeiro: valida lista/API de títulos, contrato `summary.counterparty_name`, aba local `Automações`, workspace de `Transferência Bancária` e catálogo tenant-safe de contas bancárias.
- Contratos/fiscal: valida fila de notas fiscais, filtro por `issuer_legal_entity_id` e painel de ações em lote.
- As novas rotas permanecem `PROD_SAFE` quando são somente leitura e exigem `company_id` explícito; mutações financeiras como `POST /api/financial/transfers` ficam fora do smoke seguro.
