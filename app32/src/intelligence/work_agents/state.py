from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
import operator

class WorkAgentState(TypedDict):
    """
    Estado compartilhado entre os Agentes de Trabalho.
    Armazena o histórico da conversa, o usuário atual e o contexto da empresa.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    next_node: str
    user_id: int
    company_id: int
    context_data: dict  # Dados extras (ex: tabela financeira, ID do processo)
