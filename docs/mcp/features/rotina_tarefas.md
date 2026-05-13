# Guia da Feature: Tarefas da Rotina

## Metadados
- `feature_id`: `rotina_tarefas`
- `dominio`: `routine`
- `surfaces_permitidas`: `user`, `admin`
- `sensibilidade`: `media`
- `company_id_obrigatorio`: `sim`

## Objetivo
Permitir consulta e orientação operacional sobre tarefas da rotina, com foco em listar pendências, status e próximos passos sem expor regras internas do backend.

## Quando usar
- listar tarefas do dia
- verificar andamento de tarefas
- orientar o usuário sobre o que precisa ser executado

## Quando não usar
- ações administrativas privilegiadas fora da surface permitida
- mutações sensíveis sem confirmação explícita

## Entradas esperadas
### Obrigatórias
- `company_id`: escopo do tenant

### Opcionais
- `data_referencia`: data-base da consulta
- `responsavel_id`: filtro por responsável
- `status`: filtro operacional

## Saídas esperadas
- `lista_de_tarefas`: tarefas encontradas
- `status`: situação das tarefas
- `resumo_operacional`: visão consolidada

## Como orientar o usuário
Explique a feature como um recurso para acompanhamento da rotina. Oriente quais filtros podem ser informados e deixe claro quando a resposta é geral ou filtrada.

## Passo a passo de uso
1. Confirmar tenant ativo.
2. Identificar se o usuário quer visão geral ou filtrada.
3. Coletar filtros opcionais relevantes.
4. Executar a consulta permitida.
5. Responder com resumo e próximos passos operacionais.

## Exemplos de solicitação
- "Quais são minhas tarefas de hoje?"
- "Liste as tarefas em aberto do responsável 42."
- "Como está a rotina operacional desta semana?"

## Exemplos de resposta
- "Encontrei 12 tarefas para hoje, sendo 4 pendentes, 6 em andamento e 2 concluídas."
- "Há 3 tarefas críticas em aberto para o responsável informado."

## Validações e restrições
- `company_id` é obrigatório.
- Não retornar dados de outro tenant.
- Em `surface=user`, limitar a visão ao escopo autorizado.

## Erros comuns
- ausência de tenant ativo
- filtros incompatíveis
- consulta sem permissão para a surface atual

## O que nunca expor
- nomes de serviços internos
- queries
- estrutura de banco
- lógica de priorização interna
