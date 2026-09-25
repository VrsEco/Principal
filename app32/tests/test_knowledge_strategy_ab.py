"""Script de avaliação A/B de estratégias: métricas, divergências, abstenção e falhas isoladas.

Sem banco e sem rede: o serviço de conhecimento é substituído por um duplo determinístico.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts import knowledge_strategy_ab as ab  # noqa: E402


def hit(ref, title=None, score=0.5):
    return {"source_ref": ref, "title": title or ref, "score": score}


class FakeService:
    """`table[(pergunta, estratégia)]` = lista de hits; `raises` = pares que levantam erro."""

    def __init__(self, table, raises=()):
        self.table, self.raises, self.calls = table, set(raises), []

    def _respond(self, mode, question, *, company_id, limit, strategy, user_id=None, employee_id=None):
        self.calls.append((mode, question, strategy, company_id, limit))
        if (question, strategy) in self.raises:
            raise RuntimeError("falha simulada")
        hits = self.table.get((question, strategy), [])
        key = "results" if mode == "search" else "citations"
        return {key: hits, "query_plan": {"strategies": ["sql", "full_text"], "fallback_reason": None}}

    def search(self, question, **kw):
        return self._respond("search", question, **kw)

    def answer(self, question, **kw):
        return self._respond("answer", question, **kw)


CASES = [
    {"id": "A", "question": "pergunta a", "expected": ["ref.x"]},
    {"id": "B", "question": "pergunta b", "expected": [ab.ABSTAIN]},
    {"id": "C", "question": "pergunta c", "expected": []},
    {"id": "D", "question": "pergunta d", "expected": ["Título Certo"]},
]
TABLE = {
    ("pergunta a", "full_text"): [hit("ref.x")],
    ("pergunta a", "hybrid"): [hit("ref.y"), hit("ref.x")],
    ("pergunta b", "full_text"): [],
    ("pergunta b", "hybrid"): [],
    ("pergunta c", "full_text"): [hit("ref.c1")],
    ("pergunta c", "hybrid"): [hit("ref.c2")],
    ("pergunta d", "full_text"): [hit("ref.d", "O título certo aqui")],
}


def run(service=None, **overrides):
    service = service or FakeService(TABLE, raises={("pergunta d", "hybrid")})
    options = dict(strategies=["full_text", "hybrid"], company_id=9, limit=5, mode="answer")
    options.update(overrides)
    return service, ab.evaluate(service, CASES, **options)


def test_metrics_per_strategy_count_hit_at_1_topk_mrr_and_abstention():
    _, report = run()
    full, hybrid = report["resumo"]["full_text"], report["resumo"]["hybrid"]
    assert (full["com_esperado"], full["acerto_1"], full["acerto_topk"], full["mrr"]) == (3, 3, 3, 1.0)
    # hybrid: A no 2º lugar, B abstenção correta, D com erro (sem rank)
    assert (hybrid["com_esperado"], hybrid["acerto_1"], hybrid["acerto_topk"]) == (3, 1, 2)
    assert hybrid["mrr"] == round((0.5 + 1 + 0) / 3, 3)
    assert hybrid["erros"] == 1 and full["erros"] == 0
    # só B se abstém; uma pergunta que FALHOU (D no hybrid) conta como erro, não como abstenção
    assert full["abstencoes"] == 1 and hybrid["abstencoes"] == 1


def test_one_failing_question_never_aborts_the_round():
    service, report = run()
    assert len(service.calls) == len(CASES) * 2  # todas as perguntas foram tentadas nas duas estratégias
    erro = next(c for c in report["casos"] if c["id"] == "D")["resultados"]["hybrid"]
    assert erro["error"].startswith("RuntimeError") and erro["hits"] == []


def test_divergences_list_only_cases_whose_top_result_differs():
    _, report = run()
    ids = [d["id"] for d in report["divergencias"]]
    assert ids == ["A", "C", "D"]  # B igual (ambos sem resultado); D difere porque o hybrid falhou
    a = report["divergencias"][0]
    assert a["rank"] == {"full_text": 1, "hybrid": 2} and a["topo"]["hybrid"] == "ref.y"


def test_matches_expected_by_exact_ref_or_case_insensitive_title_fragment():
    assert ab.matches_expected({"source_ref": "rotina.x", "title": "T"}, ["rotina.x"])
    assert ab.matches_expected({"source_ref": "z", "title": "Acessar Lançamento Rápido"}, ["lançamento rápido"])
    assert not ab.matches_expected({"source_ref": "z", "title": "Outro"}, ["lançamento rápido"])


def test_search_mode_reads_results_and_passes_company_limit_and_strategy():
    service, report = run(mode="search", limit=3)
    assert report["mode"] == "search" and report["limit"] == 3
    assert all(call[0] == "search" and call[3] == 9 and call[4] == 3 for call in service.calls)
    assert {call[2] for call in service.calls} == {"full_text", "hybrid"}


def test_render_text_shows_scoreboard_divergences_and_errors():
    _, report = run()
    text = ab.render_text(report)
    assert "empresa 9" in text and "acerto@1" in text
    assert "Divergências no 1º resultado: 3" in text
    assert "esperado: ref.x" in text and "(esperado na posição 2)" in text
    assert "Erros:" in text and "falha simulada" in text


def test_golden_set_file_loads_all_cases_with_expected_refs():
    cases = ab.load_golden_cases(ab.DEFAULT_GOLDEN)
    assert len(cases) >= 5 and all(c["question"] and c["expected"] for c in cases)


def test_question_tsv_parses_comments_blanks_alternatives_and_empty_expected(tmp_path: Path):
    path = tmp_path / "q.tsv"
    path.write_text("# comentário\n\npergunta 1\tA|B\npergunta 2\t\npergunta 3\t-\n", encoding="utf-8")
    cases = ab.load_question_cases(path)
    assert [c["question"] for c in cases] == ["pergunta 1", "pergunta 2", "pergunta 3"]
    assert [c["expected"] for c in cases] == [["A", "B"], [], ["-"]]


def test_starter_question_file_has_tabs_alternatives_and_an_abstention_case():
    cases = ab.load_question_cases(ab.DEFAULT_QUESTIONS)
    assert len(cases) >= 7
    assert cases[0]["expected"] == ["Lançamento Rápido", "Lançar conta a pagar"]
    assert cases[-1]["expected"] == [ab.ABSTAIN]


def test_build_service_refuses_hybrid_without_provider_but_allows_full_text_only(monkeypatch):
    from services.knowledge import openai_embedding_provider as provider_module

    monkeypatch.setattr(provider_module, "build_default_embedding_provider", lambda *a, **k: None)
    service, reason = ab.build_service(["full_text", "hybrid"], factory=lambda: "svc")
    assert service is None and "provedor de embeddings" in reason
    service, reason = ab.build_service(["full_text"], factory=lambda: "svc")
    assert (service, reason) == ("svc", None)


def test_main_exits_5_without_cases(tmp_path: Path):
    missing = str(tmp_path / "nao-existe")
    assert ab.main(["--company-id", "9", "--cases", missing, "--questions", missing]) == ab.EXIT_NO_CASES


def test_collect_cases_merges_golden_and_question_files():
    merged = ab.collect_cases(None, None)
    assert len(merged) == len(ab.load_golden_cases(ab.DEFAULT_GOLDEN)) + len(ab.load_question_cases(ab.DEFAULT_QUESTIONS))
