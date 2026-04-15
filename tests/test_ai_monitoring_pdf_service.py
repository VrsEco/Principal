import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.ai_monitoring_pdf_service import generate_ai_monitoring_report_pdf


def test_generate_ai_monitoring_report_pdf_returns_pdf_bytes():
    panel = {
        "summary": {
            "total": 2,
            "by_source": {
                "human_review": 1,
                "sapiens_workflow": 1,
            },
            "by_status": {
                "success": 1,
                "warning": 1,
            },
        },
        "filters": {
            "source": "all",
            "limit": 12,
        },
        "company_id": 9,
        "events": [
            {
                "created_at": "14/04/2026 10:00",
                "source": "human_review",
                "title": "Revisão manual",
                "actor": "Fabiano",
                "channel": "web",
                "status": "success",
                "description": "Validação manual do evento.",
            },
            {
                "created_at": "14/04/2026 10:05",
                "source": "sapiens_workflow",
                "title": "Workflow Sapiens",
                "actor": "Sapiens",
                "channel": "telegram",
                "status": "warning",
                "description": "Fluxo aguardando confirmação humana.",
            },
        ],
    }

    pdf_bytes = generate_ai_monitoring_report_pdf(
        panel=panel,
        company_name="Empresa Teste",
        generated_by="QA",
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000
