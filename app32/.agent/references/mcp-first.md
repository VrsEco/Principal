# MCP First

## Regra
Antes de assumir estado operacional do sistema, preferir consulta via MCP ou outra fonte viva equivalente.

## Aplicar especialmente em
- diagnóstico de dados
- verificação de schema real
- leitura de saúde do sistema
- workflows e agentes que dependem de estado atual

## Não confundir
MCP First não elimina testes, logs, probes ou validações HTTP. Ele reduz suposição.
