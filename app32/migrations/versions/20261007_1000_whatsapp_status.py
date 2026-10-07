"""Status-only private acervo, schedules and durable ledger (PostgreSQL).

Revision ID: 20261007_1000
Revises: 20261002_1000
"""
from alembic import op

revision = '20261007_1000'
down_revision = '20261002_1000'
branch_labels = None
depends_on = None

DDL = '''
CREATE TABLE whatsapp_status_accounts (
 company_id integer PRIMARY KEY REFERENCES companies(id),
 integration_id varchar(120) NOT NULL,
 allow_global boolean NOT NULL DEFAULT false,
 expected_phone varchar(20) NOT NULL,
 verified_at timestamptz,
 status_tested_at timestamptz,
 enabled boolean NOT NULL DEFAULT false
);
CREATE TABLE whatsapp_status_arts (
 id serial PRIMARY KEY,
 company_id integer NOT NULL REFERENCES companies(id),
 project_id integer NOT NULL REFERENCES projects(id),
 kit_code varchar(40) NOT NULL,
 kit_size integer NOT NULL CHECK (kit_size BETWEEN 1 AND 12),
 code varchar(40) NOT NULL,
 version integer NOT NULL CHECK (version > 0),
 position integer NOT NULL CHECK (position BETWEEN 1 AND 12),
 private_path varchar(255) NOT NULL,
 sha256 varchar(64) NOT NULL,
 mime varchar(20) NOT NULL CHECK (mime IN ('image/png','image/jpeg')),
 approved_by integer NOT NULL REFERENCES users(id),
 approved_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
 revoked_at timestamptz,
 UNIQUE(company_id,id), UNIQUE(company_id,kit_code,version,position), UNIQUE(company_id,code,version)
);
CREATE INDEX ix_whatsapp_status_arts_company_id ON whatsapp_status_arts(company_id);
CREATE TABLE whatsapp_status_schedules (
 id serial PRIMARY KEY,
 company_id integer NOT NULL REFERENCES companies(id),
 name varchar(80) NOT NULL,
 timezone varchar(40) NOT NULL DEFAULT 'America/Bahia' CHECK (timezone='America/Bahia'),
 hour integer NOT NULL DEFAULT 8 CHECK (hour BETWEEN 0 AND 23),
 minute integer NOT NULL DEFAULT 30 CHECK (minute BETWEEN 0 AND 59),
 weekly_arts json NOT NULL,
 active boolean NOT NULL DEFAULT false,
 revision integer NOT NULL DEFAULT 1,
 created_by integer NOT NULL REFERENCES users(id),
 principal_id integer NOT NULL REFERENCES identity_principals(id),
 review_due timestamptz NOT NULL,
 last_run_date date,
 last_result varchar(40),
 UNIQUE(company_id,id), UNIQUE(company_id,name)
);
CREATE INDEX ix_whatsapp_status_schedules_company_id ON whatsapp_status_schedules(company_id);
CREATE TABLE whatsapp_status_batches (
 id serial PRIMARY KEY,
 company_id integer NOT NULL REFERENCES companies(id),
 command_key varchar(100) NOT NULL,
 payload_digest varchar(64) NOT NULL,
 art_ids json NOT NULL,
 created_by integer NOT NULL REFERENCES users(id),
 principal_id integer NOT NULL REFERENCES identity_principals(id),
 schedule_id integer,
 status varchar(20) NOT NULL DEFAULT 'queued',
 created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(company_id,id), UNIQUE(company_id,command_key),
 FOREIGN KEY(company_id,schedule_id) REFERENCES whatsapp_status_schedules(company_id,id)
);
CREATE INDEX ix_whatsapp_status_batches_company_id ON whatsapp_status_batches(company_id);
CREATE TABLE whatsapp_status_publications (
 id serial PRIMARY KEY,
 company_id integer NOT NULL REFERENCES companies(id),
 art_id integer NOT NULL,
 batch_id integer NOT NULL,
 sha256 varchar(64) NOT NULL,
 local_date date NOT NULL,
 status varchar(20) NOT NULL CHECK (status IN ('sending','accepted','failed','unknown')),
 result_code varchar(40),
 provider_message_id varchar(120),
 started_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at timestamptz,
 mobile_confirmed_at timestamptz,
 mobile_confirmed_by integer REFERENCES users(id),
 UNIQUE(company_id,sha256,local_date),
 FOREIGN KEY(company_id,art_id) REFERENCES whatsapp_status_arts(company_id,id),
 FOREIGN KEY(company_id,batch_id) REFERENCES whatsapp_status_batches(company_id,id)
);
CREATE INDEX ix_whatsapp_status_publications_company_id ON whatsapp_status_publications(company_id);
'''


def upgrade():
    if op.get_bind().dialect.name != 'postgresql':
        raise RuntimeError('whatsapp_status requires PostgreSQL')
    op.execute(DDL)


def downgrade():
    # Operational publication evidence must never be silently destroyed.
    raise RuntimeError('Status ledger downgrade requires an approved preservation/migration plan')
