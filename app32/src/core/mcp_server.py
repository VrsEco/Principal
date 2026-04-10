import asyncio
import sys
import os
# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.intelligence.tool_catalog import catalog

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

    requested_surface = (os.environ.get("APP32_MCP_SURFACE") or "user").strip().lower()
    if requested_surface in {"user", "admin", "analytics", "ops"}:
        if requested_surface == "user":
            from src.core.mcp_server_user import run_user_mcp_server

            run_user_mcp_server()
            return

        if requested_surface == "analytics":
            from src.core.mcp_server_analytics import run_analytics_mcp_server

            run_analytics_mcp_server()
            return

        if requested_surface == "ops":
            from src.core.mcp_server_ops import run_ops_mcp_server

            run_ops_mcp_server()
            return

        from src.core.mcp_server_admin import run_admin_mcp_server

        run_admin_mcp_server()
        return

    # Cria o servidor MCP
    mcp = FastMCP("GestaoVersus Core System")

    # Registro unificado do catálogo compartilhado entre Sapiens e MCP.
    catalog.register_mcp_tools(mcp)

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

    @mcp.tool()
    def harvest_incentive_module(company_id: int) -> str:
        """
        Dispara a coleta automática de fatos para o módulo de Incentivos (S3).
        Lê processos, projetos e ocorrências do banco e gera fatos para o bônus.
        """
        from app import create_app
        from services.incentive_service import IncentiveService
        from datetime import date
        from models import db
        
        # Cria app para ter context de DB (SQLAlchemy)
        app = create_app()
        
        today = date.today()
        p_start = date(today.year, today.month, 1)
        p_end = today
        
        try:
            with app.app_context():
                results = IncentiveService.harvest_all_modules(company_id, p_start, p_end)
                db.session.commit()
                summary = results.get('summary', {})
                return f"Coleta S3 concluída: Proc={summary.get('processo')}, Proj={summary.get('projeto')}, Ocor={summary.get('ocorrencia')}. Pendentes Manual: {summary.get('manual_pendente')}"
        except Exception as e:
            return f"Erro na coleta: {str(e)}"

    from src.core.mcp_financial_tools import register_financial_mcp_tools

    register_financial_mcp_tools(mcp)

    # Inicia o servidor
    print("Iniciando MCP Server via STDIO (AI-Readable Mode)...", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    run_mcp_server()
