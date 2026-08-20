from datetime import datetime
from types import SimpleNamespace

from services.process_artifact_pdf_service import generate_process_artifact_pdf_bytes


def test_generates_pdf_for_completed_check_result():
    artifact = SimpleNamespace(
        id=91,
        company_id=10,
        process_instance_id=749,
        artifact_key="check-entrevista",
        artifact_type="check",
        artifact_version=1,
        completed_at=datetime(2026, 8, 20, 14, 30),
        definition_snapshot_json={
            "name": "Checklist de entrevista",
            "configuration_json": {
                "items": [{"id": "fit", "label": "Perfil aderente", "required": True}]
            },
        },
        output_json={"answers": {"fit": {"status": "accepted", "comment": "Aprovado"}}},
        evidence_json={"fit": {"name": "entrevista.pdf"}},
        activity_execution=SimpleNamespace(
            bpmn_element_name="Fazer entrevista",
            bpmn_element_id="task_7",
        ),
    )
    instance = SimpleNamespace(id=749, instance_code="M1.545-749")

    pdf = generate_process_artifact_pdf_bytes(artifact, instance=instance)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
