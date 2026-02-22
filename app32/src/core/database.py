import os
import logging
from typing import Tuple, Optional
import psycopg2
from psycopg2 import pool
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseManager:
    """
    Gerencia a conexão com o PostgreSQL.
    Preparado para uso com SQLAlchemy (Body) e LangGraph PostgresSaver (Brain).
    """
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
        self.db_name = os.getenv("POSTGRES_DB", os.getenv("DB_NAME"))
        self.user = os.getenv("POSTGRES_USER", os.getenv("DB_USER"))
        self.password = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD"))
        self.port = os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))
        
        # Se estiver rodando fora de um container (no Windows/Host) e o host for host.docker.internal,
        # mudamos para 127.0.0.1 para permitir conexão com o Postgres instalado no Windows.
        if self.host == "host.docker.internal":
            self.host = "127.0.0.1"
            logger.info("Detectado host.docker.internal em ambiente local. Alterando para 127.0.0.1.")

        # URL de conexão para SQLAlchemy (precisa de quote na senha para caracteres especiais)
        quoted_password = quote_plus(self.password) if self.password else ""
        self.db_url = f"postgresql://{self.user}:{quoted_password}@{self.host}:{self.port}/{self.db_name}"
        
        self._engine = None
        self._session_factory = None
        self._connection_pool = None

    @property
    def engine(self):
        if self._engine is None:
            try:
                self._engine = create_engine(
                    self.db_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    echo=False
                )
                logger.info("SQLAlchemy Engine inicializado com sucesso.")
            except Exception as e:
                logger.error(f"Erro ao inicializar SQLAlchemy Engine: {e}")
                raise e
        return self._engine

    @property
    def session_factory(self):
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    def get_session(self) -> Session:
        """Retorna uma nova sessão do SQLAlchemy."""
        return self.session_factory()

    def get_connection_pool(self):
        """
        Retorna um pool de conexões psycopg2.
        Útil para componentes que precisam de conexão direta ou para o PostgresSaver do LangGraph.
        """
        if self._connection_pool is None:
            try:
                self._connection_pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=20,
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port,
                    database=self.db_name
                )
                logger.info("Psycopg2 Connection Pool inicializado.")
            except Exception as e:
                logger.error(f"Erro ao criar Connection Pool: {e}")
                raise e
        return self._connection_pool

    def health_check(self) -> Tuple[bool, str]:
        """Verifica se o banco de dados está acessível."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "Conexão com PostgreSQL está saudável."
        except Exception as e:
            error_msg = f"Falha no Health Check do banco de dados: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# Instância global para ser importada pelo resto do app
db = DatabaseManager()
