from src.intelligence import rag


def test_rag_load_failure_never_deletes_persisted_knowledge(monkeypatch, tmp_path):
    sentinel = tmp_path / "knowledge-must-survive.txt"
    sentinel.write_text("preservar", encoding="utf-8")

    class FailingChroma:
        def __init__(self, **_kwargs):
            raise RuntimeError("indisponível")

    monkeypatch.setattr(rag, "OpenAIEmbeddings", lambda **_kwargs: object())
    monkeypatch.setattr(rag, "Chroma", FailingChroma)

    knowledge_base = rag.KnowledgeBase(persist_directory=str(tmp_path))

    assert knowledge_base.vector_store is None
    assert sentinel.read_text(encoding="utf-8") == "preservar"
