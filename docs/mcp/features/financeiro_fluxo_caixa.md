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

## Quando não usar
- em `surface=user`
- para mutações financeiras
- para expor dados sensíveis sem contexto autorizado

## Entradas esperadas
### Obrigatórias
- `company_id`

### Opcionais
- `periodo`
- `conta`
- `centro_resultado`

## Saídas esperadas
- `resumo_financeiro`
- `entradas`
- `saidas`
- `saldo`

## Como orientar o usuário
Explique a feature como consulta financeira controlada. Se a surface não permitir, responder com bloqueio claro e orientar o canal adequado.

## Validações e restrições
- `company_id` obrigatório
- acesso restrito a `admin` e `analytics`
- nunca expor mutação financeira em surface `user`

## O que nunca expor
- regras internas de cálculo
- payloads administrativos sensíveis
- estruturas de banco e trilhas internas
