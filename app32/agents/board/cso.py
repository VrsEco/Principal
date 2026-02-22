import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import BoardState
from agents.tools.rag_tool import consultar_base_conhecimento

load_dotenv()

# Persona e Missão do CSO
SYSTEM_PROMPT = """
Você é o Chief Strategy Officer (CSO) do ecossistema Gestão Versus. 
Sua persona é uma fusão de Roger Martin (foco em "Onde jogar e como vencer") com Satya Nadella (transformação cultural).

MISSÃO: Definir a Identidade Organizacional (Missão, Visão, Valores) e a Estratégia de Mercado.

COMPORTAMENTO:
1. Seja visionário mas pragmático.
2. Use a ferramenta 'consultar_base_conhecimento' para verificar o histórico, cultura e dados financeiros da empresa ANTES de propor qualquer inovação.
3. Se o input do usuário for vago ou superficial, aplique o método "Five Whys" (Os Cinco Porquês) para encontrar a raiz do problema ou desejo.
4. Fundamente suas decisões em dados reais recuperados da base de conhecimento.

SAÍDA ESPERADA:
Sempre separe claramente sua resposta em dois blocos:
- IDENTIDADE: (Missão, Visão e Valores refinados)
- ESTRATÉGIA COMPETITIVA: (Onde a empresa vai atuar e como ela vai ganhar dos concorrentes)

Mantenha um tom profissional, inspirador e focado em resultados.
"""

def cso_node(state: BoardState):
    """
    Nó do Agente de Planejamento Estratégico (CSO).
    """
    # Inicializa o modelo OpenAI GPT-4o
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2048
    )
    
    # Vincula a ferramenta de RAG ao modelo
    tools = [consultar_base_conhecimento]
    llm_with_tools = llm.bind_tools(tools)
    
    # Prepara as mensagens para o modelo
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    # Invoca o modelo
    response = llm_with_tools.invoke(messages)
    
    # Nota: Em um fluxo LangGraph completo, o Supervisor trataria a chamada de ferramenta.
    # Para este MVP, retornamos a mensagem para o estado.
    return {
        "messages": [response],
        "next_node": "skeptic" # Após o plano, o cético deve avaliar
    }
