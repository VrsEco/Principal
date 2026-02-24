from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY")

try:
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
    res = llm.invoke("Hello")
    print(f"Success: {res.content}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
