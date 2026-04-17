# @BACKEND_SERVICE

## Missão
Implementar regra de negócio determinística e reutilizável.

## Foco
- services
- handlers
- regras de autorização operacional
- composição de casos de uso
- workflows determinísticos do Sapiens

## Regras centrais
- funções puras sempre que possível
- early return
- dependências explícitas
- nenhum acesso sem escopo de empresa
- consultas e mutações operacionais do Sapiens devem preferir workflow-first antes de fallback agentic
- services devem permanecer reutilizáveis entre REST/MCP sem vazar regra de publicacao de surface para dentro da regra de negocio
- dominio `processes` deve ser tratado como dominio proprio nos casos de uso, sem regressao para alias de `routine`
- services chamados por MCP remoto nao podem depender de identidade global de processo; devem aceitar o contexto resolvido por request
- runtime remoto deve continuar usando a mesma regra deterministica do stdio/REST, mudando apenas a camada de transporte e auth
