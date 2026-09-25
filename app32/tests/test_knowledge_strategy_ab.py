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


def test_load_question_cases_ignores_extra_columns(tmp_path):
    path = tmp_path / "q.tsv"
    path.write_text(
        "# c\ncomo emito nota?\tmanual.a|manual.b\tcorrect\t3\tTitulo\nsem esperado\t\trevisar\n", encoding="utf-8"
    )
    cases = ab.load_question_cases(path)
    assert cases[0]["expected"] == ["manual.a", "manual.b"]
    assert cases[1]["expected"] == []


def _cand(ref, chunk_id, score, source_type="product_help"):
    return {"chunk_id": chunk_id, "source_ref": ref, "title": ref, "source_type": source_type,
            "content": "texto", "source_span": "trecho", "score": score}


REPLAY_DATA = {
    "company_id": 9,
    "limit": 5,
    "casos": [
        {   # FTS acerta; só o vetor traz o vizinho errado (0.80): peso 2 perde, peso 1 não
            "id": "R-1", "question": "lancamento financeiro", "expected": ["lex"],
            "candidatos": {"normalized_question": "lancamento financeiro", "candidate_limit": 30,
                           "answer_source_limit": 5, "fallback_reason": None,
                           "fts": [_cand("lex", 1, 2.0)], "vector": [_cand("viz", 2, 0.80)]},
        },
        {   # FTS vazio; o vetor resgata o certo (0.60): limiar só-vetor 0.65 derruba o resgate
            "id": "R-2", "question": "cadastrar projeto", "expected": ["proj"],
            "candidatos": {"normalized_question": "cadastrar projeto", "candidate_limit": 30,
                           "answer_source_limit": 5, "fallback_reason": None,
                           "fts": [], "vector": [_cand("proj", 3, 0.60)]},
        },
        {"id": "R-3", "question": "falhou", "expected": ["x"], "error": "RuntimeError: falha"},
    ],
}


def test_replay_scores_configs_against_full_text():
    report = ab.replay(REPLAY_DATA, weights=[1.0, 2.0], min_sims=[0.45], solo_mins=[None, 0.65])
    assert report["casos"] == 2 and report["ignorados_por_erro"] == 1
    assert report["full_text"] == {"acerto_1": 1, "abstencoes": 1}
    by_cfg = {(c["peso"], c["solo"]): c for c in report["configs"]}
    assert by_cfg[(1.0, None)]["acerto_1"] == 2 and by_cfg[(1.0, None)]["perdas"] == []
    assert by_cfg[(2.0, None)]["perdas"] == ["R-1"] and by_cfg[(2.0, None)]["ganhos"] == ["R-2"]
    assert by_cfg[(1.0, 0.65)]["ganhos"] == [] and by_cfg[(1.0, 0.65)]["abstencoes"] == 1
    assert "perde: R-1" in ab.render_replay(report)


def test_parse_grid_accepts_off_marker():
    assert ab.parse_grid("1,1.5, 2") == [1.0, 1.5, 2.0]
    assert ab.parse_grid("off,0.55", allow_none=True) == [None, 0.55]


def test_explicit_missing_questions_file_is_an_error(tmp_path, capsys):
    missing = tmp_path / "nao_existe.tsv"
    try:
        ab.collect_cases(None, missing)
    except FileNotFoundError as exc:
        assert "nao_existe.tsv" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("arquivo ausente deveria falhar")
    assert ab.main(["--company-id", "9", "--questions", str(missing)]) == ab.EXIT_NO_CASES
    assert "não encontrado" in capsys.readouterr().err


def test_replay_runs_from_cli_without_app(tmp_path, capsys):
    import json

    path = tmp_path / "cand.json"
    path.write_text(json.dumps(REPLAY_DATA), encoding="utf-8")
    assert ab.main(["--replay", str(path), "--weights", "1,2", "--min-sims", "0.45", "--solo-mins", "off"]) == ab.EXIT_OK
    out = capsys.readouterr().out
    assert "peso 1 lim 0.45 solo off" in out and "perde: R-1" in out


def test_candidates_mode_requires_out():
    import pytest

    with pytest.raises(SystemExit):
        ab.main(["--company-id", "9", "--mode", "candidates"])
