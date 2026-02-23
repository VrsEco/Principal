import asyncio
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.intelligence.tools import consult_rules, query_database, get_my_work

from src.intelligence.tools import tools as system_tools

# Tenta importar MCP
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

def run_mcp_server():
    if not FastMCP:
        print("ERRO: Biblioteca 'mcp' não encontrada.", file=sys.stderr)
        print("Instale com: pip install mcp fastmcp", file=sys.stderr)
        sys.exit(1)

    # Cria o servidor MCP
    mcp = FastMCP("GestaoVersus Core System")

    # Registro dinâmico de ferramentas do LangGraph/Intelligence
    # Isso garante que tanto o Agente interno quanto Agentes externos (MCP)
    # usem exatamente a mesma lógica de negócio (Regra do Espelhamento).
    for tool in system_tools:
        # FastMCP usa introspecção da função Python (assinatura e docstring)
        # Vamos passar a função original (tool.func) para gerar o Schema exato
        if hasattr(tool, 'func'):
            mcp.tool(name=tool.name, description=tool.description)(tool.func)
        else:
            # Caso não tenha func, fallback
            def make_wrapper(t):
                @mcp.tool(name=t.name, description=t.description)
                def mcp_tool_wrapper(*args, **kwargs):
                    return t.invoke(kwargs if kwargs else args[0] if args else {})
                return mcp_tool_wrapper
            make_wrapper(tool)


    # Ferramentas Adicionais de Diagnóstico de Sistema
    @mcp.tool()
    def get_system_health() -> str:
        """Verifica a saúde do banco de dados e do servidor."""
        from src.core.database import db
        status, msg = db.health_check()
        return f"Database: {'OK' if status else 'ERROR'} - {msg}"

    @mcp.tool()
    def get_database_schema() -> str:
        """Retorna uma lista de todas as tabelas do banco de dados (Visão Geral)."""
        from src.core.database import db
        from sqlalchemy import text
        try:
            with db.engine.connect() as connection:
                query = text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                result = connection.execute(query)
                tables = [row[0] for row in result]
                return f"Tabelas ativas: {', '.join(tables)}"
        except Exception as e:
            return f"Erro ao ler schema: {str(e)}"

    # Inicia o servidor
    print("Iniciando MCP Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    run_mcp_server()
