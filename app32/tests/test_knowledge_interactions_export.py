"""Exportação de perguntas reais: agrupamento, esperado só quando confirmado, saída compatível com o A/B."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import knowledge_interactions_export as exp  # noqa: E402
from scripts import knowledge_strategy_ab as ab  # noqa: E402


def row(question, rating="unrated", refs=(("manual.x", "Titulo X"),)):
    return {
        "question": question,
        "normalized_question": question.lower(),
        "rating_status": rating,
        "citations": [{"source_ref": r, "title": t} for r, t in refs],
    }


def test_expected_only_when_confirmed_and_dedup():
    rows = [
        row("Como emito nota fiscal?"),
        row("como emito nota fiscal?", rating="correct"),
        row("Onde vejo o DRE?", rating="wrong", refs=(("manual.y", "DRE"),)),
        row("oi"),
    ]
    out = exp.build_candidates(rows)
    by_q = {c["question"].lower(): c for c in out}
    assert by_q["como emito nota fiscal?"]["count"] == 2
    assert by_q["como emito nota fiscal?"]["expected"] == "manual.x"
    assert by_q["onde vejo o dre?"]["expected"] == "" and by_q["onde vejo o dre?"]["rating"] == "wrong"
    assert by_q["onde vejo o dre?"]["cited"] == ["manual.y"]
    assert len(out) == 2  # "oi" descartada


def test_rendered_tsv_loads_in_ab(tmp_path):
    path = tmp_path / "q.tsv"
    path.write_text(exp.render_tsv(exp.build_candidates([row("Como emito nota fiscal?", "correct")])), encoding="utf-8")
    cases = ab.load_question_cases(path)
    assert cases == [{"id": "Q-001", "question": "Como emito nota fiscal?", "expected": ["manual.x"]}]
