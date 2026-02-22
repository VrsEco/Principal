from typing import List, Dict
from langchain_core.messages import HumanMessage
from src.intelligence.work_agents.graph import work_agent_graph

# Lista de Testes
TEST_CASES = [
    {
        "input": "Como cadastro um novo colaborador no sistema?",
        "expected": "sapiens",
        "description": "Onboarding / Cadastro"
    },
    {
        "input": "Analise o balanço patrimonial e me diga a liquidez.",
        "expected": "finance",
        "description": "Financeiro"
    },
    {
        "input": "Cobre o Pedro sobre o atraso no projeto Website.",
        "expected": "operations",
        "description": "Operações / Cobrança"
    },
    {
        "input": "Verifique se todas as notas fiscais de março foram emitidas conforme o processo.",
        "expected": "auditor",
        "description": "Auditoria de Processo"
    },
    {
        "input": "Quais são as tendências para o mercado de varejo em 2026?",
        "expected": "strategist",
        "description": "Estratégia / Mercado"
    },
    {
        "input": "Desenhe o organograma atual da empresa.",
        "expected": "business_architect",
        "description": "Arquitetura de Negócios"
    },
    {
        "input": "O sistema está dando erro 500 ao tentar salvar um projeto.",
        "expected": "engineering",
        "description": "Engenharia / Suporte Técnico"
    },
    {
        "input": "Traceback (most recent call last): File 'app.py', line 10, in <module>",
        "expected": "engineering",
        "description": "Engenharia / Análise de Log"
    }
]

def run_routing_test():
    print("\n🚀 INICIANDO TESTE DE ROTEAMENTO (WORK AGENTS V2)\n")
    print("-" * 60)
    
    success_count = 0
    total_tests = len(TEST_CASES)
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"🔹 Teste {i}/{total_tests}: {test['description']}")
        print(f"   Input: '{test['input']}'")
        
        # Estado Inicial
        state = {
            "messages": [HumanMessage(content=test['input'])],
            "user_id": 1,
            "company_id": 1,
            "next_node": None
        }
        
        try:
            # Invoca o grafo
            # O output final conterá o estado atualizado, incluindo 'next_node' decidido pelo Supervisor
            result = work_agent_graph.invoke(state)
            
            # Recupera a decisão do Supervisor
            # Nota: O supervisor define 'next_node' no estado antes de passar para o agente
            decision = result.get("next_node")
            
            # Validação
            if decision == test['expected']:
                print(f"   ✅ SUCESSO! Roteado para: {decision}")
                success_count += 1
            else:
                print(f"   ❌ FALHA! Esperado: {test['expected']} | Recebido: {decision}")
                
        except Exception as e:
            print(f"   ❌ ERRO DE EXECUÇÃO: {str(e)}")
            
        print("-" * 60)

    # Resumo Final
    print(f"\n🏁 RESUMO: {success_count}/{total_tests} testes passaram.")
    
    if success_count == total_tests:
        print("🎉 TODOS OS AGENTES FORAM ROTEADOS CORRETAMENTE!")
    else:
        print("⚠️ ALGUNS AGENTES NÃO FORAM ACIONADOS CORRETAMENTE. REVISE O PROMPT DO SUPERVISOR.")

if __name__ == "__main__":
    run_routing_test()
