from services.macro_process_sipoc_report_service import _serialize_report_sipoc


def test_report_payload_preserves_all_lanes_and_boundaries():
    payload = _serialize_report_sipoc({
        "version": 3,
        "start_boundary": "Gatilho",
        "end_boundary": "Entrega",
        "items": {"supplier": [{"title": "Fornecedor", "description": None}]},
    })

    assert payload["version"] == 3
    assert payload["boundaries"] == [("Início", "Gatilho"), ("Fim", "Entrega")]
    assert [lane["key"] for lane in payload["lanes"]] == ["supplier", "input", "process", "output", "customer"]
    assert payload["lanes"][0]["items"][0]["title"] == "Fornecedor"
    assert payload["lanes"][1]["items"][0]["title"] == "Não informado."
