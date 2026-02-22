import logging
from langgraph.checkpoint.postgres import PostgresSaver
from src.core.database import db

logger = logging.getLogger(__name__)

from contextlib import contextmanager

@contextmanager
def get_checkpointer():
    """
    Inicializa e retorna o PostgresSaver para persistência de estado do LangGraph.
    Utiliza uma conexão síncrona com o PostgreSQL.
    """
    try:
        db_url = db.db_url
        with PostgresSaver.from_conn_string(db_url) as checkpointer:
            # Garante que as tabelas existam
            checkpointer.setup()
            logger.info("LangGraph PostgresSaver inicializado com sucesso via conn_string.")
            yield checkpointer
    except Exception as e:
        logger.error(f"Erro ao inicializar o checkpointer: {e}")
        raise e
