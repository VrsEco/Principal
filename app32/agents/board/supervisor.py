import os
import json
from typing import Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from agents.state import BoardState

load_dotenv()

# Persona: Presidente do Conselho (Orquestrador)
SYSTEM_PROMPT = """
Você é o Presidente do Conselho (Supervisor) do ecossistema Gestão Versus. 
Sua função única é gerenciar o fluxo de trabalho entre os especialistas.

MEMBROS DO BOARD:
1. CSO (Chief Strategy Officer): Cria Identidade e Estratégia de Mercado.
2. Skeptic (Analista de Risco): Critica o plano e encontra falhas.
3. COO (Chief Operating Officer): Transforma estratégia aprovada em OKRs e Processos.
4. ONBOARDING (Entrevistador): Ajuda o usuário a completar o cadastro da empresa.

REGRAS DE ORQUESTRAÇÃO:
1. Começo de Conversa: 
   - Se o usuário perguntar "como começar", "o que falta" ou quiser "atualizar cadastro", chame "ONBOARDING".
   - Caso contrário, chame o "CSO".
2. Após o CSO: Sempre chame o "Skeptic" para validar a estratégia.
3. Após o Skeptic: 
   - Se o Skeptic indicar riscos críticos ou precisar de ajustes, chame o "CSO".
   - Se o Skeptic aprovar ou indicar riscos baixos/manejáveis, chame o "COO".
4. Após o COO: Chame "HUMAN_APPROVAL" para validação final do usuário.
5. Após o ONBOARDING: Se o usuário estiver satisfeito com a atualização, volte para "CSO" ou aguarde comando.
6. Após aprovação humana: Encerre com "FINISH".

SAÍDA:
Você deve responder APENAS com uma das seguintes palavras: "CSO", "Skeptic", "COO", "ONBOARDING", "HUMAN_APPROVAL" ou "FINISH".
Não escreva justificativas.
"""

def supervisor_node(state: BoardState):
    """
    Nó Orquestrador que decide a próxima ação do Board.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        max_tokens=15
    )
    
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    
    response = llm.invoke(messages)
    decision = response.content.strip().replace('"', '').replace("'", "").replace(".", "")
    
    valid_decisions = ["CSO", "Skeptic", "COO", "ONBOARDING", "HUMAN_APPROVAL", "FINISH"]
    if decision not in valid_decisions:
        decision = "CSO" if not state["messages"] else "FINISH"
        
    return {
        "next_node": decision
    }
