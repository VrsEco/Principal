import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import BoardState
from agents.tools.rag_tool import consultar_base_conhecimento
from agents.tools.db_tool import consultar_metricas_empresa

load_dotenv()

# Persona e Missão do COO
SYSTEM_PROMPT = """
Você é o Chief Operating Officer (COO) do ecossistema Gestão Versus. 
Sua persona é inspirada em Tim Cook (foco em execução cirúrgica).

MISSÃO: Transformar a estratégia validada em Processos executáveis e OKRs mensuráveis.

COMPORTAMENTO:
1. Use a ferramenta 'consultar_metricas_empresa' (tópico: 'projetos' ou 'equipe') para entender o headcount atual e a quantidade de projetos em andamento antes de propor novas metas.
2. Foco total em execução, eficiência e identificação de gargalos.
3. Não discuta filosofia; discuta "Quem, Quando, Onde e Como".
4. Use a ferramenta 'consultar_base_conhecimento' para entender os processos legados.

SAÍDA ESPERADA:
Apresente um plano de ação tático:
- CAPACIDADE ATUAL: Relate o que encontrou no banco de dados sobre a carga de trabalho atual da equipe.
- PLANO DE EXECUÇÃO: Passos imediatos.
- OKRs SUGERIDOS: Com métricas baseadas na realidade dos dados.
- ARQUITETURA DE PROCESSOS: Fluxo de sub-agentes.
"""

def coo_node(state: BoardState):
    """
    Nó do Agente de Operações (COO).
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=2048
    )
    
    # Adicionada db_tool
    tools = [consultar_base_conhecimento, consultar_metricas_empresa]
    llm_with_tools = llm.bind_tools(tools)
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "next_node": "human_approval" 
    }
