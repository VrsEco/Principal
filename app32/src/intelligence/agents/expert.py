from langchain_core.messages import SystemMessage
from src.intelligence.llm import model_with_tools

def expert_node(state):
    """
    Nó do Agente Especialista.
    Analisa a demanda, consulta regras e banco de dados se necessário, e gera a resposta técnica.
    """
    messages = state["messages"]
    
    # Prompt do Sistema para guiar o comportamento do especialista
    system_prompt = (
        "Você é um Especialista Sênior do sistema Gestão Versus. "
        "Sua missão é fornecer respostas precisas sobre gestão financeira, contábil e de processos. "
        "DIRETRIZ OBRIGATÓRIA: Antes de responder qualquer dúvida técnica ou processual, "
        "SEMPRE VERIFIQUE AS REGRAS utilizando a ferramenta 'consult_rules'. "
        "Baseie suas decisões e respostas estritamente no conhecimento recuperado e nos dados do banco ('query_database')."
    )
    
    # Injeta a System Message no início
    full_messages = [SystemMessage(content=system_prompt)] + messages
    
    # Invoca o modelo
    response = model_with_tools.invoke(full_messages)
    
    # Retorna o progresso (a mensagem gerada pelo LLM, que pode conter tool_calls)
    return {"messages": [response]}
