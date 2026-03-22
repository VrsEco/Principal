import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.intelligence.workflows.handlers import (
    CompanyAccessExecutionHandler,
    CompanyAccessExecutionRequest,
)


class _Company:
    def __init__(self, company_id, client_code, name, is_active=True):
        self.id = company_id
        self.client_code = client_code
        self.name = name
        self.is_active = is_active


def test_company_access_handler_formats_accessible_companies():
    captured = {}

    def fake_loader(user_id):
        captured["user_id"] = user_id
        return [
            _Company(9, "AA", "Versus Gestao Corporativa"),
            _Company(7, "AU", "Gandu Investimentos e Participacoes"),
        ]

    def fake_formatter(**kwargs):
        captured["formatter"] = kwargs
        return "Atualmente, voce possui acesso a 2 empresa(s) ativa(s)."

    handler = CompanyAccessExecutionHandler(
        load_accessible_companies_for_user=fake_loader,
        format_report=fake_formatter,
    )

    result = handler.execute(
        CompanyAccessExecutionRequest(
            payload={},
            active_company_id=1,
            user_id=3,
            channel="whatsapp",
        )
    )

    assert captured["user_id"] == 3
    assert len(captured["formatter"]["companies"]) == 2
    assert captured["formatter"]["channel"] == "whatsapp"
    assert result.response_text == "Atualmente, voce possui acesso a 2 empresa(s) ativa(s)."


def test_company_access_handler_returns_empty_message_when_user_has_no_companies():
    handler = CompanyAccessExecutionHandler(
        load_accessible_companies_for_user=lambda user_id: [],
        format_report=lambda **kwargs: "unexpected",
    )

    result = handler.execute(
        CompanyAccessExecutionRequest(
            payload={},
            active_company_id=None,
            user_id=10,
            channel="web",
        )
    )

    assert result.response_text == "Nenhuma empresa vinculada ao seu usuário."
