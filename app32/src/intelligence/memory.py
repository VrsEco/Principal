import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

from contextlib import contextmanager

# Usaremos MemorySaver enquanto houver incompatibilidade de libpq no ambiente local
memory_checkpointer = MemorySaver()

@contextmanager
def get_checkpointer():
    """
    Retorna o MemorySaver para persistência de estado do LangGraph (Em memória).
    Nota: Em produção ou com libpq atualizada, deve-se usar PostgresSaver.
    """
    try:
        logger.info("LangGraph MemorySaver utilizado (Sincronização em memória).")
        yield memory_checkpointer
    except Exception as e:
        logger.error(f"Erro ao utilizar o checkpointer em memória: {e}")
        raise e
