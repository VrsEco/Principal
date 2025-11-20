"""
Database abstraction layer for PEVAPP22
⚠️ APP30: Sistema migrado para PostgreSQL
SQLite está DESATIVADO para forçar uso do PostgreSQL
"""

from .base import DatabaseInterface
from .postgresql_db import PostgreSQLDatabase  # Implementação oficial


def get_database(db_type="postgresql", **kwargs):  # ⚠️ Padrão mudou para PostgreSQL
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
    if db_type == "postgresql":
        return PostgreSQLDatabase(**kwargs)
    else:
        raise ValueError(
            f"❌ Tipo de banco '{db_type}' não suportado!\n"
            f"Use: 'postgresql' (SQLite está desativado)"
        )


# Default database configuration
# ⚠️ APP30: SQLite DESATIVADO - Apenas PostgreSQL
DEFAULT_CONFIG = {
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "bd_app_versus",
        "user": "postgres",
        "password": "*Paraiso1978",
    }
}
