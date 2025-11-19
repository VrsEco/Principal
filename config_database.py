"""
Database configuration for PEVAPP22
âš ï¸ APP30: Sistema migrado para PostgreSQL
SQLite estÃ¡ DESATIVADO propositalmente
"""

import logging
import os
from database import get_database, DEFAULT_CONFIG
from utils.env_helpers import normalize_docker_host

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """
    Database configuration manager
    
    âš ï¸ APP30: SQLite DESATIVADO
    Sistema usa APENAS PostgreSQL
    """
    
    def __init__(self):
        self.db_type = os.environ.get('DB_TYPE', 'postgresql')  # PadrÃ£o: PostgreSQL
        
        # âš ï¸ BLOQUEIO: Se tentar usar SQLite, gerar erro claro
        if self.db_type == 'sqlite':
            raise RuntimeError(
                "âŒ ERRO: SQLite estÃ¡ DESATIVADO no APP30!\n\n"
                "O arquivo .env estÃ¡ configurado com DB_TYPE=sqlite\n"
                "mas o sistema foi migrado para PostgreSQL.\n\n"
                "CORREÃ‡ÃƒO NECESSÃRIA:\n"
                "  1. Edite o arquivo .env\n"
                "  2. Mude: DB_TYPE=sqlite\n"
                "     Para: DB_TYPE=postgresql\n"
                "  3. Verifique DATABASE_URL aponta para postgresql://...\n"
                "  4. Reinicie a aplicaÃ§Ã£o\n\n"
                "SQLite foi desativado propositalmente para garantir\n"
                "que todo o sistema use PostgreSQL.\n"
            )
        
        self.config = self._get_config()
    
    def _get_config(self):
        """Get database configuration based on environment"""
        if self.db_type == 'sqlite':
            # âš ï¸ Este cÃ³digo nunca deve ser executado (bloqueio no __init__)
            raise RuntimeError("SQLite estÃ¡ desativado!")
        elif self.db_type == 'postgresql':
            host = normalize_docker_host(os.environ.get('POSTGRES_HOST', 'localhost'))
            return {
                'host': host,
                'port': int(os.environ.get('POSTGRES_PORT', 5432)),
                'database': os.environ.get('POSTGRES_DB', 'bd_app_versus'),
                'user': os.environ.get('POSTGRES_USER', 'postgres'),
                # Nunca mantenha senhas em cÃ³digo: exigir variÃ¡vel de ambiente ou emitir erro claro
                'password': os.environ.get('POSTGRES_PASSWORD') or '',
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_database_instance(self):
        """Get database instance based on configuration"""
        return get_database(self.db_type, **self.config)
    
    def print_config(self):
        """Print current database configuration"""
        logger.info("Database Configuration:")
        logger.info("   Type: %s", self.db_type)
        logger.info("   Config: %s", self.config)
        
        if self.db_type == 'sqlite':
            logger.info("   File: %s", self.config['db_path'])
        elif self.db_type == 'postgresql':
            logger.info("   Host: %s:%s", self.config['host'], self.config['port'])
            logger.info("   Database: %s", self.config['database'])
            logger.info("   User: %s", self.config['user'])

# Global database configuration
db_config = DatabaseConfig()

_DB_INITIALIZED = False

def get_db():
    """Get database instance"""
    global _DB_INITIALIZED
    db_instance = db_config.get_database_instance()
    if not _DB_INITIALIZED:
        init_fn = getattr(db_instance, "init_database", None)
        if callable(init_fn):
            try:
                init_fn()
                _DB_INITIALIZED = True
            except Exception as exc:
                logger.warning("[DB INIT] Aviso: falha ao executar init_database(): %s", exc)
    return db_instance

def switch_database(db_type: str, **kwargs):
    """Switch database type"""
    global db_config
    db_config.db_type = db_type
    db_config.config = kwargs
    return db_config.get_database_instance()

# Example usage:
if __name__ == "__main__":
    # Print current configuration
    db_config.print_config()
    
    # Get database instance
    db = get_db()
    
    # Test connection
    companies = db.get_companies()
    logger.info("Found %s companies in database", len(companies))
    

