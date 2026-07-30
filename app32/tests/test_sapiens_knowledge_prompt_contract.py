import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.work_agents.agents import SYSTEM_PROMPTS


def test_sapiens_prompt_requires_cited_knowledge_tools():
    prompt = SYSTEM_PROMPTS["sapiens"]

    assert "chame obrigatoriamente `answer_product_help`" in prompt
    assert "`answer_organizational_question`" in prompt
    assert "Não invente passos" in prompt
    assert "nunca aceite tenant informado livremente pelo usuário" in prompt
