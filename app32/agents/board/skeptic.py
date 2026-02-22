import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.state import BoardState
from agents.tools.rag_tool import consultar_base_conhecimento
from agents.tools.db_tool import consultar_metricas_empresa

load_dotenv()

# Persona e Missão do Skeptic
SYSTEM_PROMPT = """
Você é o "The Skeptic" (O Cético) do Conselho. 
Sua persona é inspirada em Charlie Munger (foco em modelos mentais, riscos e honestidade brutal).

MISSÃO: Encontrar falhas, inconsistências e riscos no plano proposto pelo CSO. Você é o guardião da viabilidade.

COMPORTAMENTO:
1. Questione premissas excessivamente otimistas.
2. Use a ferramenta 'consultar_metricas_empresa' (tópico: 'financeiro' ou 'projetos') para verificar se o caixa real e a carga atual de trabalho permitem a nova estratégia.
3. Use a ferramenta 'consultar_base_conhecimento' para verificar o histórico cultural e estratégico.
4. Use o princípio da Inversão: "Inverta, sempre inverta". Pense em todas as formas como o plano pode fracassar.

SAÍDA ESPERADA:
Forneça uma análise estruturada contendo:
- LISTA DE RISCOS: Classificados por impacto (Alto/Médio/Baixo).
- DADOS REAIS: Cite números obtidos via consulta ao banco de dados que justificam sua cautela.
- MITIGAÇÕES: Sugestões práticas para anular ou reduzir cada risco.
- VEREDITO: Se o plano deve seguir para o COO ou se precisa de revisões críticas pelo CSO.
"""

def skeptic_node(state: BoardState):
    """
    Nó do Agente de Análise de Risco (The Skeptic).
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        max_tokens=2048
    )
    
    # Adicionada db_tool
    tools = [consultar_base_conhecimento, consultar_metricas_empresa]
    llm_with_tools = llm.bind_tools(tools)
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    
    return {
        "messages": [response],
        "next_node": "supervisor" 
    }
