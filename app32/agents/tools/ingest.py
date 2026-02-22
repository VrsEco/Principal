import os
import logging
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Caminhos
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docs"))
VECTOR_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../vector_db"))

def ingest_docs():
    """
    Carrega documentos da pasta docs/, divide em chunks e salva no ChromaDB.
    """
    if not os.path.exists(DOCS_DIR):
        logger.error(f"Diretório de documentos não encontrado: {DOCS_DIR}")
        return

    logger.info(f"Iniciando ingestão de documentos de: {DOCS_DIR}")

    # Carregadores (PDF e TXT)
    pdf_loader = DirectoryLoader(DOCS_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader)
    txt_loader = DirectoryLoader(DOCS_DIR, glob="**/*.txt", loader_cls=TextLoader)
    
    docs = []
    try:
        # Carregando PDFs
        pdf_docs = pdf_loader.load()
        docs.extend(pdf_docs)
        logger.info(f"PDFs carregados: {len(pdf_docs)}")
        
        # Carregando TXTs
        txt_docs = txt_loader.load()
        docs.extend(txt_docs)
        logger.info(f"TXTs carregados: {len(txt_docs)}")
    except Exception as e:
        logger.error(f"Erro ao carregar documentos: {e}")
        if not docs:
            return

    if not docs:
        logger.warning(f"Nenhum documento PDF ou TXT encontrado na pasta: {DOCS_DIR}")
        return

    logger.info(f"Total de {len(docs)} documentos carregados.")

    # Divisão de texto (Chunking)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    splits = text_splitter.split_documents(docs)
    logger.info(f"Texto dividido em {len(splits)} chunks.")

    # Embeddings da OpenAI e persistência no ChromaDB
    try:
        # Usando o modelo solicitado pelo usuário (OpenAI)
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Criação e persistência do banco
        logger.info("Gerando embeddings e salvando no ChromaDB...")
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=VECTOR_DB_DIR
        )
        vectorstore.persist()
        logger.info(f"SUCESSO: Base vetorial persistida em: {VECTOR_DB_DIR}")
        
    except Exception as e:
        logger.error(f"Erro crítico na camada de embeddings/vetores: {e}")
        logger.error("Dica: Verifique se 'OPENAI_API_KEY' está no seu .env.")

if __name__ == "__main__":
    ingest_docs()
