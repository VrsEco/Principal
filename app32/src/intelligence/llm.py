import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from utils.integration_settings import resolve_ai_runtime_config

load_dotenv()

# Tenta carregar a chave da tela de integrações e mantém fallback legado
runtime = resolve_ai_runtime_config()
api_key = runtime.get("api_key")
default_model = runtime.get("model") or "gpt-4o-mini"

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
    model=default_model,
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
