# Guia da Feature: Fluxo de Caixa

## Metadados
- `feature_id`: `financeiro_fluxo_caixa`
- `dominio`: `finance`
- `surfaces_permitidas`: `admin`, `analytics`
- `sensibilidade`: `alta`
- `company_id_obrigatorio`: `sim`

## Objetivo
Permitir visão operacional e executiva do fluxo de caixa conforme perfil autorizado, com foco em leitura controlada e tenant-safe.

## Quando usar
- consultar saldo e movimentações
- obter resumo financeiro do período
- analisar entradas e saídas autorizadas
- simular reparo de movimentos ausentes no Extrato Bancário (`preview_financial_bank_statement_repair`)
- criar transferência bancária entre contas do tenant, somente em surface administrativa (`create_financial_bank_transfer`)
- aplicar reparo/backfill de extrato somente após preview e confirmação explícita (`apply_financial_bank_statement_repair`)

## Quando não usar
- em `surface=user`
- para mutações financeiras fora de `surface=admin`
- para expor dados sensíveis sem contexto autorizado
- para aplicar reparo de extrato sem preview prévio e confirmação humana

## Entradas esperadas
### Obrigatórias
- `company_id`

### Opcionais
- `periodo`
- `conta`
- `centro_resultado`
- `payload` para transferência bancária administrativa
- `confirmed=true` para aplicação de reparo de extrato

## Saídas esperadas
- `resumo_financeiro`
- `entradas`
- `saidas`
- `saldo`
- `transfer_group_id`
- `reconciliation_bank_accounts`
- `transfer_settlements`

## Como orientar o usuário
Explique a feature como consulta financeira controlada. Para transferência ou reparo de extrato, orientar primeiro a revisão humana do impacto; se a surface não permitir, responder com bloqueio claro e direcionar para `admin`.

## Validações e restrições
- `company_id` obrigatório
- acesso restrito a `admin` e `analytics`
- nunca expor mutação financeira em surface `user`
- `preview_financial_bank_statement_repair` é leitura/simulação e pode operar em `admin` ou `analytics`
- `create_financial_bank_transfer` e `apply_financial_bank_statement_repair` são mutações financeiras e ficam restritas a `admin`
- `apply_financial_bank_statement_repair` exige `confirmed=true`

## O que nunca expor
- regras internas de cálculo
- payloads administrativos sensíveis
- estruturas de banco e trilhas internas
