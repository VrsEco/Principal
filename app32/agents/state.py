from typing import TypedDict, Annotated, List, Union, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class BoardState(TypedDict):
    """
    Estado compartilhado entre os membros do Conselho (Board).
    """
    # Histórico de mensagens da sessão (acumulativo)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Controle de fluxo: Próximo agente a ser chamado
    next_node: str
    
    # Artefatos estruturados produzidos pelos agentes
    strategic_plan: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    operational_kpis: List[Dict[str, Any]]
    
    # Flag para aprovação humana (Human-in-the-Loop)
    approved_by_human: bool
    
    # Contexto recuperado do Shared RAG que pode ser passado implicitamente
    shared_context: str
