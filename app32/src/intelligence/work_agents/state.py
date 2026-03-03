from typing import TypedDict, Annotated, List, Union, Optional
from langchain_core.messages import BaseMessage
import operator

class WorkAgentState(TypedDict):
    """
    Estado compartilhado entre os Agentes de Trabalho.
    Armazena o histórico da conversa, o usuário atual e o contexto da empresa.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    next_node: Optional[str]
    user_id: Optional[int]
    company_id: Optional[int]
    context_data: Optional[dict]  # Dados extras (ex: tabela financeira, ID do processo)
