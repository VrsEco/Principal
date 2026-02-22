import sys
import os

# Adiciona a raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.intelligence.rag import knowledge_base

def seed():
    print("Populando base de conhecimento com regras de exemplo...")
    
    regras = [
        "Notas fiscais acima de R$ 10.000 precisam de aprovação de dois diretores.",
        "O sistema não aceita XMLs sem o campo 'xMotivo' preenchido em casos de rejeição.",
        "Pagamentos agendados para sábado devem ser movidos para a segunda-feira seguinte.",
        "Para erros de conexão com a SEFAZ, o sistema deve tentar novamente 3 vezes antes de falhar."
    ]
    
    metadatas = [
        {"category": "financeiro", "rule_id": 1},
        {"category": "fiscal", "rule_id": 2},
        {"category": "financeiro", "rule_id": 3},
        {"category": "infra", "rule_id": 4}
    ]
    
    success = knowledge_base.add_documents(regras, metadatas)
    
    if success:
        print("Base de conhecimento populada com sucesso!")
    else:
        print("Erro ao popular base de conhecimento.")

if __name__ == "__main__":
    seed()
