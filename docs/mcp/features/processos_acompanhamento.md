# Guia da Feature: Acompanhamento de Processos

## Metadados
- `feature_id`: `processos_acompanhamento`
- `dominio`: `processes`
- `surfaces_permitidas`: `user`, `admin`, `ops`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Permitir consulta do andamento de processos, responsáveis e próximos passos, com linguagem operacional e sem expor lógica interna.

## Quando usar
- consultar status de um processo
- identificar próximos passos
- orientar acompanhamento operacional

## Quando não usar
- ações fora da surface autorizada
- operações de administração sensível sem confirmação humana

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `processo_id`
- `periodo`
- `responsavel_id`

## Saídas esperadas
- `status_do_processo`
- `proximos_passos`
- `responsaveis`

## Como orientar o usuário
Explique quais filtros podem ser usados e responda de forma objetiva sobre estágio atual, pendências e próximos movimentos operacionais.

## Validações e restrições
- `company_id` obrigatório
- sem cruzamento entre tenants
- respeitar a surface atual

## O que nunca expor
- fluxos internos de decisão
- nomes de services
- estruturas internas de persistência
