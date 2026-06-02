from datetime import date

from schemas.project import project_schema
from models.project import Project


def test_project_schema_exposes_deadline_field_from_synonym(monkeypatch):
    monkeypatch.setattr(Project, "company_code", property(lambda self: "AA"))

    project = Project(
        id=17,
        company_id=3,
        name="Projeto com prazo",
        end_date=date(2026, 6, 30),
    )

    payload = project_schema.dump(project)

    assert payload["deadline"] == "2026-06-30"
    assert payload["end_date"] == "2026-06-30"
