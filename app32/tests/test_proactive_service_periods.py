from datetime import date
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import proactive_service


def test_resolve_summary_period_month():
    start, end, label = proactive_service._resolve_summary_period("month", date(2026, 3, 5))
    assert start == date(2026, 3, 5)
    assert end == date(2026, 3, 31)
    assert "deste mês" in label


def test_resolve_summary_period_next_15_days():
    start, end, label = proactive_service._resolve_summary_period("next_15_days", date(2026, 3, 5))
    assert start == date(2026, 3, 5)
    assert end == date(2026, 3, 19)
    assert "15 dias" in label


def test_parse_custom_period_ddmmyyyy():
    parsed = proactive_service._parse_custom_period("05/03/2026 a 19/03/2026")
    assert parsed == (date(2026, 3, 5), date(2026, 3, 19))


def test_truncate_telegram_message_uses_cta_suffix():
    long_message = "A" * 500
    output = proactive_service._truncate_telegram_message(long_message, max_chars=180)
    assert output.endswith(
        "\n\nRegistros acima da capacidade deste canal, quer que eu te envie por e-mail?"
    )
    assert len(output) <= 180


def test_truncate_telegram_message_keeps_short_message():
    short_message = "Mensagem curta"
    output = proactive_service._truncate_telegram_message(short_message, max_chars=180)
    assert output == short_message


def test_is_affirmative_email_confirmation_variants():
    assert proactive_service._is_affirmative_email_confirmation("sim")
    assert proactive_service._is_affirmative_email_confirmation("Pode enviar por e-mail")
    assert not proactive_service._is_affirmative_email_confirmation("não agora")


def test_infer_date_range_from_summary_text():
    assert proactive_service._infer_date_range_from_summary_text("Sou o Sapiens e trouxe seu resumo da semana (05/03/2026 a 11/03/2026).") == "week"
    assert proactive_service._infer_date_range_from_summary_text("Sou o Sapiens e trouxe seu resumo deste mês (05/03/2026 a 31/03/2026).") == "month"
    assert proactive_service._infer_date_range_from_summary_text("Sou o Sapiens e trouxe seu resumo do período (05/03/2026 a 19/03/2026).") == "05/03/2026 a 19/03/2026"
