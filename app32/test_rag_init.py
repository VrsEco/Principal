
import os
import sys

# Adiciona o caminho do projeto ao sys.path
sys.path.insert(0, os.getcwd())

try:
    from src.intelligence.rag import knowledge_base
    print("✅ KnowledgeBase carregada com sucesso.")
    if knowledge_base.vector_store:
        print("✅ Vector Store inicializado.")
    else:
        print("❌ Vector Store é None.")
except Exception as e:
    print(f"❌ Erro crítico ao carregar KnowledgeBase: {str(e)}")
    import traceback
    traceback.print_exc()
