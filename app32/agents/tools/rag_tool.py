import os
import logging
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

logger = logging.getLogger(__name__)

# Diretório onde o banco ChromaDB está persistido
VECTOR_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../vector_db"))

@tool
def consultar_base_conhecimento(query: str) -> str:
    """
    Essencial para qualquer decisão estratégica. Busca dados sobre a identidade da empresa 
    (missão/visão), histórico financeiro e regras de negócio. 
    Input: uma string com a pergunta ou tópico para busca na base vetorial.
    """
    try:
        # Verificação de existência do banco
        if not os.path.exists(VECTOR_DB_DIR) or not os.listdir(VECTOR_DB_DIR):
            return (
                "AVISO: A base de conhecimento (Vector DB) está vazia ou não foi inicializada. "
                "Por favor, execute o script 'agents/tools/ingest.py' após adicionar documentos na pasta 'docs/'."
            )

        # Inicializa embeddings (deve ser o mesmo modelo usado na ingestão)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Carrega o banco existente
        vectorstore = Chroma(
            persist_directory=VECTOR_DB_DIR, 
            embedding_function=embeddings
        )
        
        # Realiza a busca por similaridade
        # Retornamos os 4 documentos mais relevantes para dar contexto suficiente ao agente
        docs = vectorstore.similarity_search(query, k=4)
        
        if not docs:
            return "Nenhuma informação relevante encontrada na base de conhecimento para a consulta fornecida."

        # Formata os resultados para o agente
        context_parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'desconhecido')
            content = doc.page_content.replace('\n', ' ')
            context_parts.append(f"[Trecho {i} - Fonte: {source}]: {content}")

        formatted_context = "\n\n".join(context_parts)
        
        logger.info(f"Busca RAG realizada para: '{query}' - {len(docs)} resultados encontrados.")
        return formatted_context

    except Exception as e:
        error_msg = f"Erro técnico ao consultar a base de conhecimento: {str(e)}"
        logger.error(error_msg)
        return error_msg
