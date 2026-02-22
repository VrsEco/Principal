import os
import sys
import uuid

# Adiciona o diretório raiz ao sys.path para permitir imports dos módulos locais
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage
from agents.graph import board_intelligence

def run_simulation():
    # ID de thread para o checkpointer (representa uma sessão de reunião)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    
    # Input desafiador para provocar o Skeptic
    initial_input = (
        "Quero dobrar o faturamento da empresa em 12 meses expandindo para o "
        "mercado de energia solar, mesmo sem experiência prévia."
    )
    
    print("\n" + "="*50)
    print("🚀 INICIANDO SIMULAÇÃO DO CONSELHO (BOARD)")
    print(f"Input: {initial_input}")
    print("="*50 + "\n")

    input_data = {"messages": [HumanMessage(content=initial_input)]}

    # Loop principal de execução via stream
    finished = False
    while not finished:
        # Executa o grafo até o próximo breakpoint ou fim
        for event in board_intelligence.stream(input_data, config=config, stream_mode="values"):
            # O evento 'values' contém o estado atualizado após cada nó
            if not event:
                continue
                
            messages = event.get("messages", [])
            if messages:
                last_msg = messages[-1]
                # Identifica qual nó acabou de rodar (quem enviou a última mensagem)
                # No LangGraph, podemos ver o histórico de mensagens
                sender = "Sistema"
                if hasattr(last_msg, 'name') and last_msg.name:
                    sender = last_msg.name
                elif "next_node" in event:
                    # Tenta inferir pelo next_node do estado o que acabou de rodar
                    pass

                # Impressão formatada baseada no tipo de mensagem
                if isinstance(last_msg, HumanMessage):
                    continue # Já imprimimos o input inicial
                
                print(f"[{sender or 'Agente'}] enviou uma mensagem...")
                print("-" * 30)
                print(last_msg.content[:500] + "..." if len(last_msg.content) > 500 else last_msg.content)
                print("-" * 30 + "\n")

        # Verifica se o grafo está pausado em um breakpoint
        snapshot = board_intelligence.get_state(config)
        if snapshot.next:
            print("⚠️" + "!"*10 + " ALERTA DE SEGURANÇA " + "!"*10 + "⚠️")
            print(f"SISTEMA PAUSADO AGUARDANDO APROVAÇÃO HUMANA NO NÓ: {snapshot.next}")
            print("Motivo: O COO finalizou o plano e o Supervisor solicitou validação final.")
            
            # Simulação de aprovação humana
            print("\n[Simulando Aprovação Humana...] -> Digitado: 'APROVADO. PROCEDA COM A EXECUÇÃO.'")
            input_data = None # Retoma de onde parou, não envia novo input
            board_intelligence.update_state(
                config, 
                {"messages": [HumanMessage(content="APROVADO. PROCEDA COM A EXECUÇÃO.")]},
                as_node="human_approval"
            )
        else:
            finished = True
            print("✅ SIMULAÇÃO CONCLUÍDA: O Conselho encerrou a sessão.")

if __name__ == "__main__":
    try:
        run_simulation()
    except Exception as e:
        print(f"\n❌ ERRO NA SIMULAÇÃO: {e}")
        print("\nDica: Verifique se suas credenciais Google (Vertex AI) estão ativas no .env.")
