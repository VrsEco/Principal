import sys
import os

# Adiciona a raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.intelligence.rag import knowledge_base

def test_retrieval():
    print("Iniciando Teste de Recuperação RAG...")
    
    # Pergunta especificada
    query = "Quantas tentativas para erro na SEFAZ?"
    print(f"Pergunta: '{query}'")
    
    # Realiza a busca
    results = knowledge_base.search(query, k=1)
    
    if results:
        content = results[0].page_content
        print(f"\nResultado Recuperado: '{content}'")
        
        if "3 vezes" in content and "SEFAZ" in content:
            print("\nSUCESSO: A informação correta foi recuperada da base de conhecimento!")
        else:
            print("\nAVISO: O resultado recuperado pode não ser o mais preciso.")
    else:
        print("\nFALHA: Nenhum documento recuperado. Tente rodar o seed_knowledge.py primeiro.")

if __name__ == "__main__":
    # Verifica se o banco existe (buscando algo genérico)
    check = knowledge_base.search("teste", k=1)
    if not check:
        print("Banco vazio ou inexistente. Rodando seed automático...")
        from src.intelligence.seed_knowledge import seed
        seed()
    
    test_retrieval()
