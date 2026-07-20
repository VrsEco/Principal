from __future__ import annotations

from pathlib import Path


def test_classification_migration_preserves_and_reclassifies_only_the_known_technical_record():
    source = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260720_0900_classify_consultive_assisted_analyses.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "20260719_1030"' in source
    assert "ADD COLUMN IF NOT EXISTS analysis_type" in source
    assert "ADD COLUMN IF NOT EXISTS journey_eligible" in source
    assert "WHERE id = 7" in source
    assert "AND company_id = 9" in source
    assert "technical_test_not_methodological" in source
