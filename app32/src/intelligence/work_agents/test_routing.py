from typing import List
from langchain_core.messages import HumanMessage
from src.intelligence.work_agents.graph import work_agent_graph

# Casos de Teste (Mock de Usuário Real)
TEST_CASES = [
    {
        "input": "Como cadastro um novo cliente no sistema?",
        "expected": "sapiens",
        "desc": "Onboarding/Dúvida de Uso"
    },
    {
        "input": "Qual a previsão de fluxo de caixa para o próximo trimestre?",
        "expected": "finance",
        "desc": "Análise Financeira"
    },
    {
        "input": "Verifique se a compra #123 seguiu o processo de 3 cotações.",
        "expected": "auditor",
        "desc": "Auditoria de Processo"
    },
    {
        "input": "Cobre o João sobre o atraso no projeto de Marketing.",
        "expected": "operations",
        "desc": "Cobrança/Operações"
    },
    {
        "input": "Analise o mercado de tecnologia no Brasil e sugira tendências.",
        "expected": "strategist",
        "desc": "Estratégia/Mercado"
    },
    {
        "input": "Desenhe o fluxograma do processo de vendas atual.",
        "expected": "business_architect",
        "desc": "Arquitetura de Negócios"
    }
]

def run_tests():
    print("🚀 INICIANDO TESTE DE ROTEAMENTO - WORK AGENTS V2\n")
    success_count = 0
    
    for case in TEST_CASES:
        print(f"🔹 Testando: '{case['input']}'")
        
        # Simula o estado inicial
        initial_state = {
            "messages": [HumanMessage(content=case['input'])],
            "user_id": 1,
            "company_id": 1
        }
        
        try:
            # Executa o grafo (apenas o primeiro passo para ver a decisão do supervisor)
            # Como o supervisor é o primeiro nó, podemos inspecionar a saída dele
            # Mas o grafo executa até o fim ou até uma interrupção. 
            # Vamos rodar e verificar quais nós foram visitados no caminho.
            
            # Nota: Em um teste real unitário, poderíamos mockar o LLM. 
            # Aqui, estamos testando a integração real com o OpenAI.
            
            output = work_agent_graph.invoke(initial_state)
            
            # A decisão do supervisor fica salva em 'next_node' no estado (se o supervisor retornar isso)
            # Ou podemos inferir pelo último nó que executou antes do 'end'
            # No nosso grafo, o supervisor define 'next_node'.
            
            decision = output.get("next_node")
            
            if decision == case['expected']:
                print(f"✅ SUCESSO! Roteado para: {decision}")
                success_count += 1
            else:
                print(f"❌ FALHA! Esperado: {case['expected']}, Recebido: {decision}")
                
        except Exception as e:
            print(f"❌ ERRO DE EXECUÇÃO: {e}")
            
        print("-" * 50)

    print(f"\n🏁 RESUMO: {success_count}/{len(TEST_CASES)} testes passaram.")

if __name__ == "__main__":
    run_tests()
