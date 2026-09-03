"""Cria registro tenant-safe de presença de usuários.

Revision ID: 20260903_1300
Revises: 20260903_1200
Create Date: 2026-09-03 13:00:00
"""

from alembic import op


revision = "20260903_1300"
down_revision = "20260903_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_presence_sessions (
            id BIGSERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            session_hash VARCHAR(64) NOT NULL,
            login_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            last_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            logout_at TIMESTAMP WITHOUT TIME ZONE,
            revoked_at TIMESTAMP WITHOUT TIME ZONE,
            device_type VARCHAR(32),
            browser VARCHAR(64),
            ip_hash VARCHAR(64),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_presence_company_user_session
                UNIQUE (company_id, user_id, session_hash)
        );

        CREATE INDEX IF NOT EXISTS ix_user_presence_company_last_seen
            ON user_presence_sessions(company_id, last_seen_at DESC);
        CREATE INDEX IF NOT EXISTS ix_user_presence_user_company
            ON user_presence_sessions(user_id, company_id);
        CREATE INDEX IF NOT EXISTS ix_user_presence_active_company
            ON user_presence_sessions(company_id, last_seen_at DESC)
            WHERE logout_at IS NULL AND revoked_at IS NULL;
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_presence_sessions")

