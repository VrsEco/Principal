import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from agents.state import BoardState
from agents.tools.db_tool import atualizar_perfil_empresa, consultar_metricas_empresa

load_dotenv()

# Persona e Missão do Onboarding Interviewer
SYSTEM_PROMPT = """
Você é o "Especialista de Onboarding" do ecossistema Gestão Versus.

SUA MISSÃO: Garantir que o cadastro da empresa esteja completo para que os outros agentes (CSO, Skeptic, COO) possam trabalhar com precisão.

LOGICA DE GAPS (Raciocínio):
1. Quando o usuário tiver um desejo (ex: "Quero dobrar o faturamento"), você deve verificar se os dados necessários existem.
2. Se o foco for ESTRATÉGICO -> Verifique se 'mission', 'vision', 'values' estão preenchidos.
3. Se o foco for FINANCEIRO/OPERACIONAL -> Verifique se 'segment' (indústria) e métricas básicas estão preenchidas.

COMPORTAMENTO:
- Seja acolhedor e consultivo. 
- Explique POR QUE a informação é importante (ex: "Para o Skeptic analisar seu risco, ele precisa saber seu segmento").
- Não peça tudo de uma vez. Faça uma entrevista passo a passo.
- Sempre que receber uma resposta, use a ferramenta 'atualizar_perfil_empresa' para salvar os dados imediatamente.

FLUXO:
1. Analise o que o usuário quer e o que falta (Use 'consultar_metricas_empresa' para ver o contexto atual se necessário).
2. Proponha o preenchimento: "Para te ajudar com X, vi que faltam A e B. Vamos preencher?"
3. Entreviste: "Qual a missão da sua empresa?"
4. Salve: Use 'atualizar_perfil_empresa(field_name="mission", value="...", company_id=...)'.
"""

def onboarding_interviewer_node(state: BoardState):
    """
    Nó do Agente de Onboarding (Entrevistador).
    """
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2048
    )
    
    tools = [atualizar_perfil_empresa, consultar_metricas_empresa]
    llm_with_tools = llm.bind_tools(tools)
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    response = llm_with_tools.invoke(messages)
    
    # Se o agente terminou de entrevistar um campo ou o cadastro está OK, 
    # o Supervisor decidirá se volta para o fluxo estratégico ou encerra.
    return {
        "messages": [response],
        "next_node": "supervisor" 
    }
