# Multi-tenancy Checklist

Use este checklist em qualquer bug funcional com empresa/tenant envolvido.

## Comparações obrigatórias
- `active_company_id` da sessão
- `company_id` da request
- `company_id` do registro carregado
- empresas vinculadas ao usuário
- permissões do usuário naquela empresa

## Perguntas obrigatórias
1. O usuário tem acesso à empresa?
2. O objeto pertence à empresa informada?
3. A rota usa `company_id` de query, body, sessão ou URL?
4. O backend aplica filtro explícito por tenant?
5. O frontend está enviando o tenant correto?

## Sinais clássicos
- usuário vê item mas não consegue editar/concluir
- lista vem de uma empresa e ação tenta outra
- sessão troca de empresa no meio do fluxo
- consulta por id sem filtro de `company_id`

## Regra do projeto
Nunca confiar apenas no ID do objeto. Toda consulta relevante deve respeitar `company_id`.
