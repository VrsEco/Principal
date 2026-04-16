# Gestão Versus — AI Readable

Resumo mínimo para agentes externos.

## Regras centrais
1. Multi-tenancy com `company_id` é obrigatório.
2. O projeto oficial usa Python + Flask + PostgreSQL.
3. Preferir MCP para validar estado operacional antes de assumir dados.
4. Não colocar lógica de negócio em rotas.

## MCP
- comando base: `C:\GestaoVersus\.venv\Scripts\python.exe C:\GestaoVersus\app32\src\core\mcp_server.py`

## Estrutura de governança interna
- `C:\GestaoVersus\app32\app32\.agent\skills\gestao_versus_core\SKILL.md`
- `C:\GestaoVersus\app32\app32\.agent\router\orchestrator.md`
- `C:\GestaoVersus\app32\app32\.agent\references\mcp-first.md`
