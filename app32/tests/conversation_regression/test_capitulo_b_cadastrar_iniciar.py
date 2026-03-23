import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .runner import execute_case, load_chapter_cases


CASES = load_chapter_cases("b_cadastrar_iniciar")


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_capitulo_b_cadastrar_iniciar(monkeypatch, case):
    execute_case(monkeypatch, case)
