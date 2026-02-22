from datetime import datetime
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
import logging

from src.intelligence.state import AgentState
from src.intelligence.llm import llm_router
from src.intelligence.agents.specialists import fiscal_node, financeiro_node
from src.intelligence.tools import tools
from src.intelligence.memory import get_checkpointer

logger = logging.getLogger(__name__)

# --- Supervisor / Router Logic ---

def router_node(state: AgentState):
    """
    Decide para qual especialista enviar a pergunta ou se deve encerrar.
    """
    messages = state["messages"]
    last_msg = messages[-1].content.lower()
    
    logger.info(f"Router recebeu mensagem: {last_msg}")

    # Lógica de roteamento simples baseada em palavras-chave (pode ser evoluída para LLM Router)
    if "fiscal" in last_msg or "imposto" in last_msg or "cnpj" in last_msg:
        logger.info("Roteando para especialista FISCAL")
        return {"next_node": "fiscal"}
    elif "financeiro" in last_msg or "caixa" in last_msg or "lucro" in last_msg:
        logger.info("Roteando para especialista FINANCEIRO")
        return {"next_node": "financeiro"}
    
    # Para perguntas genéricas, usar o especialista fiscal como padrão
    logger.info("Roteando para especialista FISCAL (padrão)")
    return {"next_node": "fiscal"}

def route_decision(state: AgentState) -> Literal["fiscal", "financeiro"]:
    next_node = state.get("next_node", "fiscal")
    logger.info(f"Route decision: {next_node}")
    if next_node in ["fiscal", "financeiro"]:
        return next_node
    return "fiscal"  # Sempre vai para um especialista, nunca END direto

# --- Graph Construction ---

def create_main_graph():
    workflow = StateGraph(AgentState)

    # Adiciona os Nós
    workflow.add_node("router", router_node)
    workflow.add_node("fiscal", fiscal_node)
    workflow.add_node("financeiro", financeiro_node)
    workflow.add_node("tools", ToolNode(tools))

    # Define as Bordas (Edges)
    workflow.add_edge(START, "router")
    
    # Router sempre vai para fiscal ou financeiro, nunca END direto
    workflow.add_conditional_edges("router", route_decision, {"fiscal": "fiscal", "financeiro": "financeiro"})

    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        logger.info(f"Should continue? Tool calls: {hasattr(last_message, 'tool_calls') and last_message.tool_calls}")
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        return END

    workflow.add_conditional_edges("fiscal", should_continue, ["tools", END])
    workflow.add_conditional_edges("financeiro", should_continue, ["tools", END])
    workflow.add_edge("tools", "router")

    return workflow

# Grafo base sem checkpointer fixo
_workflow = create_main_graph()

def run_agent_interaction(message: str, thread_id: str):
    """
    Executa uma interação com o agente, gerenciando o checkpointer.
    """
    from langchain_core.messages import HumanMessage
    
    with get_checkpointer() as checkpointer:
        app = _workflow.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        
        input_data = {"messages": [HumanMessage(content=message)]}
        result = app.invoke(input_data, config=config)
        
        return result
