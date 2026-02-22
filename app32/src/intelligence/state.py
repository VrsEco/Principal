from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """
    Define o estado do agente para a orquestração do LangGraph.
    Utiliza add_messages para permitir o acúmulo de histórico de mensagens.
    """
    # Lista de mensagens com suporte a histórico (append-only)
    messages: Annotated[List, add_messages]
    
    # Próximo nó a ser executado (usado por roteadores)
    next_node: str
    
    # Captura de erros durante a execução de ferramentas ou nós
    errors: List[str]
