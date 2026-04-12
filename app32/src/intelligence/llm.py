import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Tenta carregar a chave de várias fontes
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")

if not api_key:
    try:
        from config import Config
        api_key = getattr(Config, "AI_API_KEY", None)
    except (ImportError, Exception):
        pass

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key

# Instância para roteamento e tarefas simples (Rápida e Barata)
llm_router = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=api_key
)

# Instância para raciocínio complexo, análise de negócios e fiscal (Especialista)
llm_expert = ChatOpenAI(
    model="gpt-4o",
    temperature=0.2,
    api_key=api_key
)

from src.intelligence.tool_catalog import tools
model_with_tools = llm_expert.bind_tools(tools)
