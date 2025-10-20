"""
Database configuration for PEVAPP22
⚠️ APP30: Sistema migrado para PostgreSQL
SQLite está DESATIVADO propositalmente
"""

import os
from database import get_database, DEFAULT_CONFIG

class DatabaseConfig:
    """
    Database configuration manager
    
    ⚠️ APP30: SQLite DESATIVADO
    Sistema usa APENAS PostgreSQL
    """
    
    def __init__(self):
        self.db_type = os.environ.get('DB_TYPE', 'postgresql')  # Padrão: PostgreSQL
        
        # ⚠️ BLOQUEIO: Se tentar usar SQLite, gerar erro claro
        if self.db_type == 'sqlite':
            raise RuntimeError(
                "❌ ERRO: SQLite está DESATIVADO no APP30!\n\n"
                "O arquivo .env está configurado com DB_TYPE=sqlite\n"
                "mas o sistema foi migrado para PostgreSQL.\n\n"
                "CORREÇÃO NECESSÁRIA:\n"
                "  1. Edite o arquivo .env\n"
                "  2. Mude: DB_TYPE=sqlite\n"
                "     Para: DB_TYPE=postgresql\n"
                "  3. Verifique DATABASE_URL aponta para postgresql://...\n"
                "  4. Reinicie a aplicação\n\n"
                "SQLite foi desativado propositalmente para garantir\n"
                "que todo o sistema use PostgreSQL.\n"
            )
        
        self.config = self._get_config()
    
    def _get_config(self):
        """Get database configuration based on environment"""
        if self.db_type == 'sqlite':
            # ⚠️ Este código nunca deve ser executado (bloqueio no __init__)
            raise RuntimeError("SQLite está desativado!")
        elif self.db_type == 'postgresql':
            return {
                'host': os.environ.get('POSTGRES_HOST', 'localhost'),
                'port': int(os.environ.get('POSTGRES_PORT', 5432)),
                'database': os.environ.get('POSTGRES_DB', 'bd_app_versus'),
                'user': os.environ.get('POSTGRES_USER', 'postgres'),
                'password': os.environ.get('POSTGRES_PASSWORD', '*Paraiso1978')  # Senha atualizada
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_database_instance(self):
        """Get database instance based on configuration"""
        return get_database(self.db_type, **self.config)
    
    def print_config(self):
        """Print current database configuration"""
        print(f"Database Configuration:")
        print(f"   Type: {self.db_type}")
        print(f"   Config: {self.config}")
        
        if self.db_type == 'sqlite':
            print(f"   File: {self.config['db_path']}")
        elif self.db_type == 'postgresql':
            print(f"   Host: {self.config['host']}:{self.config['port']}")
            print(f"   Database: {self.config['database']}")
            print(f"   User: {self.config['user']}")

# Global database configuration
db_config = DatabaseConfig()

def get_db():
    """Get database instance"""
    return db_config.get_database_instance()

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
    print(f"✅ Found {len(companies)} companies in database")
    
    # Example: Switch to PostgreSQL
    # postgres_db = switch_database('postgresql', 
    #                               host='localhost', 
    #                               port=5432, 
    #                               database='pevapp22', 
    #                               user='postgres', 
    #                               password='password')
