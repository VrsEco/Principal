"""create_user_mcp_tokens

Revision ID: 20260507_1100
Revises: 20260504_1700, 20260506_0900
Create Date: 2026-05-07 11:00:00.000000
"""

from alembic import op


revision = "20260507_1100"
down_revision = ("20260504_1700", "20260506_0900")
branch_labels = None
depends_on = None


def upgrade():
    # Idempotente por desenho: alguns ambientes legados criaram esta tabela via
    # bootstrap/modelo antes da revisão Alembic ser registrada em alembic_version.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.user_mcp_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES public.users(id),
            token_hash VARCHAR(128) NOT NULL,
            token_prefix VARCHAR(24) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_by_user_id INTEGER REFERENCES public.users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            last_used_at TIMESTAMP WITHOUT TIME ZONE,
            revoked_at TIMESTAMP WITHOUT TIME ZONE,
            last_client_name VARCHAR(120),
            last_surface VARCHAR(32),
            last_company_id INTEGER REFERENCES public.companies(id),
            notice_d3_sent_at TIMESTAMP WITHOUT TIME ZONE,
            notice_d0_sent_at TIMESTAMP WITHOUT TIME ZONE,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        );

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'user_mcp_tokens_token_hash_key'
            ) THEN
                ALTER TABLE public.user_mcp_tokens
                    ADD CONSTRAINT user_mcp_tokens_token_hash_key UNIQUE(token_hash);
            END IF;
        END $$;

        CREATE INDEX IF NOT EXISTS ix_user_mcp_tokens_expires_at
            ON public.user_mcp_tokens(expires_at);
        CREATE INDEX IF NOT EXISTS ix_user_mcp_tokens_status
            ON public.user_mcp_tokens(status);
        CREATE INDEX IF NOT EXISTS ix_user_mcp_tokens_token_hash
            ON public.user_mcp_tokens(token_hash);
        CREATE INDEX IF NOT EXISTS ix_user_mcp_tokens_user_id
            ON public.user_mcp_tokens(user_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_user_mcp_tokens_user_id;
        DROP INDEX IF EXISTS public.ix_user_mcp_tokens_token_hash;
        DROP INDEX IF EXISTS public.ix_user_mcp_tokens_status;
        DROP INDEX IF EXISTS public.ix_user_mcp_tokens_expires_at;
        DROP TABLE IF EXISTS public.user_mcp_tokens;
        """
    )
