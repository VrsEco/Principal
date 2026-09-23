# Harness — Reconciliação financeira da worktree

Data: 2026-09-23
Branch: codex/financial-drift-reconcile
Base: 2ab1c2b50

## Escopo
Integração seletiva dos serviços financeiros, proteções de interface e testes provenientes de auto-keycloak-provisioning. Não integrar a branch de origem inteira. Preservados os modelos e migrações corrigidos na base.

## Evidências executadas
- 40 testes Python de settlement, guardrails de borderô, renderização inicial e transação: aprovados.
- 20 testes reais PostgreSQL de concorrência, atomicidade, locks e isolamento de empresa: aprovados, sem skips (8,91 s).
- 3 arquivos de testes Node: aprovados; incluem clique duplicado, resposta incerta, readiness e recuperação de falhas.
- git diff --check: sem erros.
- PostgreSQL temporário com dados sintéticos, banco app32_financial_concurrency_lab, exclusivamente loopback. Encerramento confirmado (STOP_EXIT=0).
- Log local: C:\GestaoVersus\app32\backups\financial-lab-922284fdc8474d4295b547be5da76a0c\pytest.log

## Gate de negócio antes da publicação
A alteração permite estornar uma baixa não conciliada de título gerenciado por contrato, sem cancelar o título/contrato. Isso altera a regra anterior que bloqueava esse estorno. Há teste específico. Regra confirmada expressamente pelo usuário em 2026-09-23: permitir estorno de baixa não conciliada, preservando o título e o contrato. A confirmação da regra não implica autorização de commit, push ou deploy.

## Limites
Sem commit, push, merge, deploy ou alteração de dados de produção nesta rodada. Testes selecionados não equivalem à homologação de toda a aplicação. Pendências comerciais/MCP e alterações da worktree raiz não foram descartadas nem incorporadas. Teste funcional OAuth com operacaolp permanece não executado, conforme encerramento solicitado pelo usuário.
