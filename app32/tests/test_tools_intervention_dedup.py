from types import SimpleNamespace


def test_squad_create_intervention_reuses_open_bug_card(monkeypatch):
    from src.intelligence import tools as tools_module
    from models import project as project_module
    from models import employee as employee_module
    from models import user as user_module
    from services import whatsapp_service as whatsapp_module

    class _Col:
        def __eq__(self, other):
            return ("eq", other)

        def __ne__(self, other):
            return ("ne", other)

        def __ge__(self, other):
            return ("ge", other)

        def desc(self):
            return self

    class _Query:
        def __init__(self, first_result):
            self._first_result = first_result

        def filter_by(self, **_kwargs):
            return self

        def filter(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

        def first(self):
            return self._first_result

    existing_task = SimpleNamespace(
        id=264,
        notes="Descrição do Erro:\nstack antiga",
        how="Contexto do erro e logs para análise investigativa.",
        due_date=None,
        updated_at=None,
    )
    fake_project = SimpleNamespace(id=31, company_id=1)

    fake_project_task = type(
        "FakeProjectTask",
        (),
        {
            "project_id": _Col(),
            "what": _Col(),
            "stage": _Col(),
            "updated_at": _Col(),
            "id": _Col(),
            "created_at": _Col(),
            "query": _Query(existing_task),
        },
    )
    fake_project_cls = type("FakeProject", (), {"query": _Query(fake_project)})
    fake_employee_cls = type("FakeEmployee", (), {"company_id": _Col(), "name": _Col(), "user_id": _Col(), "query": _Query(None)})
    fake_user_cls = type("FakeUser", (), {"id": _Col(), "name": _Col()})

    commits = []
    fake_db = SimpleNamespace(session=SimpleNamespace(commit=lambda: commits.append("commit")))

    monkeypatch.setattr(project_module, "Project", fake_project_cls)
    monkeypatch.setattr(project_module, "ProjectTask", fake_project_task)
    monkeypatch.setattr(employee_module, "Employee", fake_employee_cls)
    monkeypatch.setattr(user_module, "User", fake_user_cls)
    monkeypatch.setattr(whatsapp_module, "whatsapp_service", SimpleNamespace(send_message=lambda *_args, **_kwargs: None))
    monkeypatch.setattr(tools_module, "db", fake_db)

    result = tools_module.squad_create_intervention.func(
        title="[BUG] Inconsistência Detectada Automagicamente",
        due_date="2026-03-18",
        how="Contexto do erro e logs para análise investigativa.",
        notes="Descrição do Erro:\nstack nova",
        assignee_name="Agente Sapiens",
    )

    assert "[REINCIDÊNCIA]" in result
    assert "264" in result
    assert "[RECORRÊNCIA AUTOMÁTICA -" in existing_task.notes
    assert "stack nova" in existing_task.notes
    assert commits == ["commit"]


def test_escalate_technical_issue_generates_specific_title(monkeypatch):
    from src.intelligence import tools as tools_module

    captured = {}

    monkeypatch.setattr(
        tools_module,
        "squad_create_intervention",
        SimpleNamespace(
            invoke=lambda payload: captured.setdefault("payload", dict(payload)) or "ok"
        ),
    )

    tools_module.escalate_technical_issue.func(
        error_description="This transaction is closed; IllegalStateChangeError ao concluir tarefas.",
        context="Tentativa de concluir as atividades com IDs 24 e 323.",
    )

    assert captured["payload"]["title"] == "[BUG][SQLALCHEMY_TX] Transacao fechada ao concluir atividade"
