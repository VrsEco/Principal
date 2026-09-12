from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "20260912_1700_password_reset_tokens.py"
)


def test_password_reset_migration_declares_current_merge_head_and_additive_schema():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    assert 'revision = "20260912_1700"' in source
    assert 'down_revision = ("20260910_1000", "20260911_1830")' in source
    assert 'op.add_column(\n        "users",' in source
    assert '"auth_session_version"' in source
    assert 'op.create_table(\n        "password_reset_tokens"' in source
    assert 'sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")' in source
    assert 'sa.UniqueConstraint("token_hash")' in source


def test_password_reset_migration_creates_and_reverses_indexes_in_dependency_order():
    source = MIGRATION_PATH.read_text(encoding="utf-8")

    for index_name in (
        "ix_password_reset_tokens_user_id",
        "ix_password_reset_tokens_token_hash",
        "ix_password_reset_tokens_expires_at",
        "ix_password_reset_tokens_used_at",
    ):
        assert f'op.create_index("{index_name}"' in source
        assert f'op.drop_index("{index_name}"' in source

    assert source.index('op.drop_table("password_reset_tokens")') < source.index('op.drop_column("users", "auth_session_version")')
