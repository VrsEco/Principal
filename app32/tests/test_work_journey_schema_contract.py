from pydantic import ValidationError

from schemas.work_journey import WorkJourneyManualTaskCreateSchema


def test_manual_task_create_schema_rejects_occurrence_date_as_read_only():
    try:
        WorkJourneyManualTaskCreateSchema.model_validate(
            {
                "employee_id": 88,
                "title": "Tarefa smoke",
                "due_date": "2026-05-16",
                "occurrence_date": "2026-05-16",
            }
        )
    except ValidationError as exc:
        message = str(exc)
        assert "occurrence_date é um campo somente-leitura" in message
        assert "Use due_date" in message
    else:  # pragma: no cover
        raise AssertionError("Era esperado erro de validação para occurrence_date em criação.")
