import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.tool_catalog import tools


def test_sapiens_langchain_catalog_exposes_knowledge_tools():
    names = {tool.name for tool in tools}

    assert {
        "answer_product_help",
        "search_organizational_knowledge",
        "answer_organizational_question",
    }.issubset(names)
