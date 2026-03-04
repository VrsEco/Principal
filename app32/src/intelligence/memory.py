import os
import sys
import logging
from urllib.parse import quote_plus
from contextlib import contextmanager

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except Exception as import_err:
    PostgresSaver = None
    logger.warning("PostgresSaver indisponivel neste ambiente: %s", import_err)


# Fallback sempre disponivel em memoria
memory_checkpointer = MemorySaver()
_postgres_setup_done = False
_postgres_disabled = False
_libpq_warning_logged = False


def _normalize_database_url(database_url: str) -> str:
    if not database_url:
        return database_url
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url[len("postgres://"):]
    if database_url.startswith("postgresql+psycopg2://"):
        return "postgresql://" + database_url[len("postgresql+psycopg2://"):]
    if database_url.startswith("postgresql+psycopg://"):
        return "postgresql://" + database_url[len("postgresql+psycopg://"):]
    return database_url


def _build_postgres_conn_string() -> str:
    # 1) DATABASE_URL padrao (prod/dev)
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DEV_DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
    )
    if database_url:
        return _normalize_database_url(database_url.strip())

    # 2) Variaveis explicitas
    host = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
    db_name = os.getenv("POSTGRES_DB", os.getenv("DB_NAME"))
    user = os.getenv("POSTGRES_USER", os.getenv("DB_USER"))
    password = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", ""))
    port = os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))

    if not (host and db_name and user):
        return ""

    encoded_password = quote_plus(password) if password else ""
    if encoded_password:
        auth = f"{user}:{encoded_password}"
    else:
        auth = user

    return f"postgresql://{auth}@{host}:{port}/{db_name}"


def _libpq_supports_pipeline() -> bool:
    """
    PostgresSaver usa pipeline do psycopg/libpq, que exige libpq >= 14.
    """
    global _libpq_warning_logged
    try:
        import psycopg

        version = psycopg.pq.version()
        if isinstance(version, int) and version < 140000:
            if not _libpq_warning_logged:
                major = version // 10000
                minor = (version % 10000) // 100
                logger.warning(
                    "libpq %s.%s detectado (<14). Desabilitando PostgresSaver e usando MemorySaver.",
                    major,
                    minor,
                )
                _libpq_warning_logged = True
            return False
    except Exception as err:
        logger.debug("Nao foi possivel validar versao do libpq: %s", err)
    return True


@contextmanager
def get_checkpointer():
    """
    Retorna PostgresSaver quando disponivel; fallback para MemorySaver em caso de erro.
    """
    global _postgres_setup_done, _postgres_disabled

    if PostgresSaver is not None and not _postgres_disabled:
        conn_string = _build_postgres_conn_string()
        if conn_string and _libpq_supports_pipeline():
            postgres_cm = None
            try:
                postgres_cm = PostgresSaver.from_conn_string(conn_string)
                checkpointer = postgres_cm.__enter__()
                if not _postgres_setup_done:
                    checkpointer.setup()
                    _postgres_setup_done = True
            except Exception as postgres_err:
                _postgres_disabled = True
                logger.warning("Falha ao inicializar PostgresSaver. Fallback para MemorySaver: %s", postgres_err)
                if postgres_cm is not None:
                    exc_type, exc_val, exc_tb = sys.exc_info()
                    try:
                        postgres_cm.__exit__(exc_type, exc_val, exc_tb)
                    except Exception:
                        pass
            else:
                logger.info("LangGraph PostgresSaver utilizado.")
                try:
                    yield checkpointer
                finally:
                    exc_type, exc_val, exc_tb = sys.exc_info()
                    try:
                        postgres_cm.__exit__(exc_type, exc_val, exc_tb)
                    except Exception as close_err:
                        logger.warning("Erro ao encerrar PostgresSaver: %s", close_err)
                return
        elif conn_string and not _libpq_supports_pipeline():
            _postgres_disabled = True
        else:
            logger.info("Sem string de conexao Postgres para LangGraph. Usando MemorySaver.")

    try:
        logger.info("LangGraph MemorySaver utilizado (persistencia apenas em memoria).")
        yield memory_checkpointer
    except Exception as mem_err:
        logger.error("Erro ao utilizar MemorySaver: %s", mem_err)
        raise
