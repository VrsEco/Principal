from pathlib import Path


def test_entry_manage_uses_whole_delete_copy_for_quick_entries():
    template = Path(r"C:\GestaoVersus\app32\app32\templates\modules\financial\entry_manage.html").read_text(encoding="utf-8")

    assert "Excluir lançamento rápido" in template
    assert "remove o lançamento e a baixa juntos" in template
    assert "requiresWholeEntryDelete" in template
