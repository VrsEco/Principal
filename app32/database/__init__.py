"""
Database abstraction layer for PEVAPP22
⚠️ APP30: Sistema migrado para PostgreSQL
SQLite está DESATIVADO para forçar uso do PostgreSQL
"""

from .base import DatabaseInterface
from .postgresql_db import PostgreSQLDatabase  # Implementação oficial


def get_database(db_type="postgresql", **kwargs):
    """
    Factory function to get database instance
    """
    # Simply return PostgreSQL implementation as it is the only supported one
    return PostgreSQLDatabase(**kwargs)


# Default database configuration
DEFAULT_CONFIG = {
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "bd_app_versus",
        "user": "postgres",
        "password": "*Paraiso1978",
    }
}

# Alias for compatibility
get_db = get_database
