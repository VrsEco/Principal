import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _read_template(name: str) -> str:
    return (BASE_DIR / "templates" / "modules" / "incentives" / name).read_text(encoding="utf-8")


def test_dashboard_has_plan_action_buttons():
    content = _read_template("dashboard.html")

    assert 'title="Abrir plano"' in content
    assert 'title="Editar plano"' in content
    assert 'title="Excluir plano"' in content
    assert "deletePlanFromDashboard" in content


def test_plan_manage_has_edit_and_delete_actions_for_plan_participants_and_rules():
    content = _read_template("plan_manage.html")

    assert "Editar Plano" in content
    assert "Excluir Plano" in content
    assert "Editar participante" in content
    assert "Excluir participante" in content
    assert "Excluir Vetor" in content
    assert "editVetorCard" in content


def test_indicator_list_keeps_edit_and_delete_actions():
    content = _read_template("indicator_list.html")

    assert 'title="Editar"' in content
    assert "deleteIndicator" in content
    assert "fa-trash" in content
    assert "soft delete" in content


def test_closings_list_keeps_action_column_for_historical_records():
    content = _read_template("closings_list.html")

    assert "Ações" in content
    assert "Ver" in content
    assert "Excluir" in content
    assert "deleteClosing" in content


def test_closing_view_exposes_protected_edit_flow():
    content = _read_template("closing.html")

    assert "Modo protegido de edição" in content
    assert "saveProtectedClosingEdit" in content
    assert "deleteCurrentClosing" in content
