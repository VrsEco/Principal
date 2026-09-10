import pytest

from scripts.qa.create_alembic_reconciliation_clone import maintenance_url


def test_maintenance_url_keeps_connection_details_without_database() -> None:
    admin_url, source_database = maintenance_url("postgresql://user:secret@localhost:5432/app32_oauth_hml")

    assert admin_url == "postgresql://user:secret@localhost:5432/postgres"
    assert source_database == "app32_oauth_hml"


def test_clone_rejects_invalid_target_before_database_connection() -> None:
    from scripts.qa.create_alembic_reconciliation_clone import create_clone

    with pytest.raises(ValueError, match="app32_oauth_r04"):
        create_clone(source_url="postgresql://user:secret@localhost/app32_oauth_hml", target_database="app32")
