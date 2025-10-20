"""
Database abstraction layer for PEVAPP22
⚠️ APP30: Sistema migrado para PostgreSQL
SQLite está DESATIVADO para forçar uso do PostgreSQL
"""

from .base import DatabaseInterface
from .sqlite_db import SQLiteDatabase  # Mantido apenas para compatibilidade histórica

def get_database(db_type='postgresql', **kwargs):  # ⚠️ Padrão mudou para PostgreSQL
    """
    Factory function to get database instance
    
    ⚠️ IMPORTANTE: APP30 usa APENAS PostgreSQL
    SQLite foi desativado propositalmente
    
    Args:
        db_type (str): Type of database ('postgresql' - sqlite está desativado)
        **kwargs: Database connection parameters
    
    Returns:
        DatabaseInterface: Database instance (PostgreSQL)
    
    Raises:
        RuntimeError: Se tentar usar SQLite
    """
    if db_type == 'sqlite':
        # ⚠️ BLOQUEIO PROPOSITAL - SQLite desativado
        raise RuntimeError(
            "❌ ERRO: Tentativa de usar SQLite BLOQUEADA!\n\n"
            "O APP30 foi completamente migrado para PostgreSQL.\n"
            "SQLite foi desativado propositalmente.\n\n"
            "Este erro indica que algum código está tentando usar SQLite.\n"
            "Verifique o TRACEBACK acima para identificar ONDE.\n\n"
            "CORREÇÃO:\n"
            "  1. Configure .env com DB_TYPE=postgresql\n"
            "  2. Use get_database('postgresql', ...) ao invés de 'sqlite'\n"
            "  3. Ou use config_database.get_db() que já retorna PostgreSQL\n\n"
            "Para emergências (consulta apenas), os arquivos SQLite estão em:\n"
            "  instance/pevapp22.db.DESATIVADO (renomeie para .db temporariamente)\n"
        )
    elif db_type == 'postgresql':
        from .postgresql_db import PostgreSQLDatabase
        return PostgreSQLDatabase(**kwargs)
    else:
        raise ValueError(
            f"❌ Tipo de banco '{db_type}' não suportado!\n"
            f"Use: 'postgresql' (SQLite está desativado)"
        )

# Default database configuration
# ⚠️ APP30: SQLite DESATIVADO - Apenas PostgreSQL
DEFAULT_CONFIG = {
    'sqlite': {
        # ⚠️ DESATIVADO - Não usar
        'db_path': 'instance/pevapp22.db.DESATIVADO'  # Arquivo renomeado propositalmente
    },
    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'database': 'bd_app_versus',
        'user': 'postgres',
        'password': '*Paraiso1978'
    }
}
