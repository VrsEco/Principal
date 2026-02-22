import asyncio
import sys
import os

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.intelligence.tools import consult_rules, query_database, get_my_work

# Tenta importar MCP
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

def run_mcp_server():
    if not FastMCP:
        print("ERRO: Biblioteca 'mcp' não encontrada.", file=sys.stderr)
        print("Instale com: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # Cria o servidor MCP
    mcp = FastMCP("GestaoVersus Core System")

    @mcp.tool()
    def consult_business_rules(question: str) -> str:
        """
        Consulta o manual de regras de negócio e procedimentos da empresa (Base de Conhecimento RAG).
        Use isto para dúvidas sobre políticas internas, limites, etc.
        """
        # LangChain tools can be invoked directly
        return consult_rules.invoke(question)

    @mcp.tool()
    def execute_sql_query(query: str) -> str:
        """
        Executa uma consulta SQL no banco de dados.
        Retorna os resultados em JSON.
        """
        return query_database.invoke(query)

    @mcp.tool()
    def list_work_activities(scope: str = 'me', company_ids: str = None) -> str:
        """
        Retorna a lista de tarefas pendentes (Projetos e Processos).
        """
        return get_my_work.invoke({"scope": scope, "company_ids": company_ids})

    # Inicia o servidor
    print("Iniciando MCP Server via STDIO...", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    run_mcp_server()
