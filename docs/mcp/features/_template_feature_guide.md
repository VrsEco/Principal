# Template de Guia de Feature MCP

> Uso: duplicar este arquivo e adaptar para cada feature.  
> Objetivo: orientar humano e IA sobre **uso operacional** sem expor implementação interna.

## Metadados
- `feature_id`:
- `dominio`:
- `surfaces_permitidas`:
- `sensibilidade`: baixa | media | alta
- `company_id_obrigatorio`: sim

## Objetivo
Descreva em 1 a 3 frases o que a feature entrega para o usuário.

## Quando usar
- Caso 1
- Caso 2
- Caso 3

## Quando não usar
- Limite 1
- Limite 2

## Entradas esperadas
### Obrigatórias
- `company_id`:

### Opcionais
- `campo_opcional`:

## Saídas esperadas
- `saida_1`:
- `saida_2`:

## Como orientar o usuário
Explique como a IA deve descrever a feature ao usuário em linguagem operacional, sem citar implementação interna.

## Passo a passo de uso
1. Confirmar o contexto da operação.
2. Validar se a feature é compatível com a surface.
3. Solicitar ou confirmar entradas mínimas.
4. Executar a consulta/operação permitida.
5. Responder com linguagem clara, objetiva e tenant-safe.

## Exemplos de solicitação
- "Exemplo 1"
- "Exemplo 2"

## Exemplos de resposta
- "Resposta operacional resumida 1"
- "Resposta operacional resumida 2"

## Validações e restrições
- Não prosseguir sem `company_id`.
- Não misturar dados entre tenants.
- Não expor dados fora da surface autorizada.

## Erros comuns
- Entrada insuficiente
- Surface não autorizada
- Recurso não encontrado no tenant

## O que nunca expor
- detalhes de implementação
- tabelas e colunas internas
- regras administrativas profundas
- payloads privilegiados

## Dependências documentais
- catálogo: `C:\GestaoVersus\app32\docs\mcp\catalogo_features.yaml`
- contrato tools: `C:\GestaoVersus\app32\docs\mcp\mcp_tools_contract.json`
