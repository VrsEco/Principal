import os
import logging
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
os.environ.setdefault("CHROMA_ANONYMIZED_TELEMETRY", "FALSE")

load_dotenv()

# Tenta carregar a chave de várias fontes possíveis
logger = logging.getLogger(__name__)
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")

if not api_key:
    # Se não encontrar, tenta carregar do config legado caso esteja disponível
    try:
        from config import Config
        api_key = Config.AI_API_KEY
    except ImportError:
        pass

if api_key:
    # Define como variável de ambiente para componentes internos do LangChain/OpenAI
    os.environ["OPENAI_API_KEY"] = api_key
else:
    logger.warning("ALERTA: Nenhuma chave OpenAI (OPENAI_API_KEY ou AI_API_KEY) foi encontrada no ambiente.")

class KnowledgeBase:
    """
    Interface para o Vector Store (ChromaDB) com OpenAI Embeddings.
    Implementa a infraestrutura de RAG para o Gestão Versus v2.0.
    """
    def __init__(self, persist_directory="./data/chroma_db", collection_name="gestao_versus_rules"):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Garante que o diretório de dados exista
        os.makedirs(os.path.dirname(self.persist_directory), exist_ok=True)
        
        # Modelo text-embedding-3-small conforme especificação
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            # Se api_key for None aqui, o LangChain levantará o erro que vimos
            api_key=api_key
        )
        
        try:
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
        except Exception as e:
            logger.error(f"Erro ao carregar o Chroma DB (provável corrupção): {e}")
            logger.info("Tentando recriar o banco de dados vetorial do zero...")
            import shutil
            if os.path.exists(self.persist_directory):
                try:
                    shutil.rmtree(self.persist_directory)
                except Exception as ex:
                    logger.warning(f"Aviso ao deletar diretório do Chroma: {ex}")
            
            try:
                self.vector_store = Chroma(
                    collection_name=self.collection_name,
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory
                )
                logger.info("Chroma DB recriado com sucesso.")
            except Exception as critical_error:
                logger.error(f"Falha CRÍTICA ao recriar Chroma DB: {critical_error}")
                self.vector_store = None
            
        logger.info(f"KnowledgeBase inicializada (ChromaDB: {self.persist_directory})")

    def add_documents(self, texts: list[str], metadatas: list[dict] = None):
        """
        Adiciona novos documentos (regras/conhecimento) à coleção.
        """
        if not self.vector_store:
            logger.error("Chroma DB não está disponível.")
            return False
        try:
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Adicionados {len(texts)} documentos à KnowledgeBase.")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar documentos: {e}")
            return False

    def search(self, query: str, k=3):
        """
        Busca os k documentos mais similares à query.
        """
        if not self.vector_store:
            logger.error("Chroma DB não está disponível.")
            return []
        try:
            # Verifica se há documentos na coleção (aproximado)
            # No LangChain Chroma, similarity_search retorna lista vazia se não houver nada
            results = self.vector_store.similarity_search(query, k=k)
            
            if not results:
                logger.warning("Nenhum resultado encontrado. A coleção pode estar vazia.")
                return []
            
            return results
        except Exception as e:
            logger.error(f"Erro na busca RAG: {e}")
            return []

# Singleton para uso no app
knowledge_base = KnowledgeBase()
