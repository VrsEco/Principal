import pytest

from src.core.mcp_prevalidation import prevalidate

MESSAGE = "Conta a pagar/receber deve ser criada como agendamento. Use create_financial_schedule_secure."


@pytest.mark.parametrize("entry_type", ["payable", "receivable", " Payable "])
def test_create_financial_entry_prevalidation_blocks_titles_before_approval(entry_type):
    error = prevalidate("create_financial_entry", {"company_id": 16, "payload": {"entry_type": entry_type}})

    assert error == MESSAGE
