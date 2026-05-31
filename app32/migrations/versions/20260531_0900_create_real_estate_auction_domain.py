"""create real estate auction domain

Revision ID: 20260531_0900
Revises: 20260526_1700
Create Date: 2026-05-31 09:00:00
"""

from alembic import op


revision = "20260531_0900"
down_revision = "20260526_1700"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.real_estate_auction_properties (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            code VARCHAR(50) NOT NULL,
            nickname VARCHAR(255),
            address VARCHAR(255) NOT NULL,
            district VARCHAR(120),
            city VARCHAR(120),
            state VARCHAR(2),
            zip_code VARCHAR(20),
            property_type VARCHAR(80),
            auxiliary_filter VARCHAR(10),
            sale_modality VARCHAR(120),
            land_area NUMERIC(14, 2),
            private_area NUMERIC(14, 2),
            built_area NUMERIC(14, 2),
            registry_number VARCHAR(120),
            registry_office VARCHAR(120),
            court_district VARCHAR(120),
            bank VARCHAR(120),
            occupied BOOLEAN NOT NULL DEFAULT TRUE,
            status VARCHAR(40) NOT NULL DEFAULT 'in_analysis',
            triage_status VARCHAR(40) NOT NULL DEFAULT 'pending',
            triage_reason_code VARCHAR(80),
            triage_reason_label VARCHAR(160),
            triage_notes TEXT,
            appraisal_value NUMERIC(14, 2),
            estimated_quick_sale_value NUMERIC(14, 2),
            estimated_normal_sale_value NUMERIC(14, 2),
            recommended_max_bid NUMERIC(14, 2),
            auctioneer VARCHAR(120),
            auction_url TEXT,
            notice_url TEXT,
            buyer_name VARCHAR(255),
            broker_name VARCHAR(255),
            closed_sale_value NUMERIC(14, 2),
            auction_won_at TIMESTAMP WITHOUT TIME ZONE,
            available_for_sale_at TIMESTAMP WITHOUT TIME ZONE,
            sold_at TIMESTAMP WITHOUT TIME ZONE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            updated_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMP WITHOUT TIME ZONE,
            CONSTRAINT uq_re_auction_properties_company_code UNIQUE(company_id, code),
            CONSTRAINT uq_re_auction_properties_company_id UNIQUE(company_id, id),
            CONSTRAINT ck_re_auction_properties_status CHECK (
                status IN ('draft', 'in_analysis', 'awaiting_auction', 'won', 'lost', 'discarded', 'available_for_sale', 'sold')
            ),
            CONSTRAINT ck_re_auction_properties_triage_status CHECK (
                triage_status IN ('pending', 'awaiting_auction', 'auction_won', 'auction_lost', 'discarded')
            )
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_company_status ON public.real_estate_auction_properties(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_company_triage ON public.real_estate_auction_properties(company_id, triage_status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_company_city_state ON public.real_estate_auction_properties(company_id, city, state);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_company_id ON public.real_estate_auction_properties(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_city ON public.real_estate_auction_properties(city);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_state ON public.real_estate_auction_properties(state);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_bank ON public.real_estate_auction_properties(bank);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_occupied ON public.real_estate_auction_properties(occupied);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_status ON public.real_estate_auction_properties(status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_triage_status ON public.real_estate_auction_properties(triage_status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_auxiliary_filter ON public.real_estate_auction_properties(auxiliary_filter);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_created_by_user_id ON public.real_estate_auction_properties(created_by_user_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_properties_updated_by_user_id ON public.real_estate_auction_properties(updated_by_user_id);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_events (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            property_id INTEGER NOT NULL,
            auction_type VARCHAR(40),
            auction_datetime TIMESTAMP WITHOUT TIME ZONE,
            minimum_bid NUMERIC(14, 2),
            modality VARCHAR(120),
            auctioneer VARCHAR(120),
            winning_bid NUMERIC(14, 2),
            result VARCHAR(60) NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_re_auction_events_company_property
                FOREIGN KEY(company_id, property_id)
                REFERENCES public.real_estate_auction_properties(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_company_datetime ON public.real_estate_auction_events(company_id, auction_datetime);
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_company_property ON public.real_estate_auction_events(company_id, property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_company_id ON public.real_estate_auction_events(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_property_id ON public.real_estate_auction_events(property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_auction_datetime ON public.real_estate_auction_events(auction_datetime);
        CREATE INDEX IF NOT EXISTS ix_re_auction_events_result ON public.real_estate_auction_events(result);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_financial_sheets (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            property_id INTEGER NOT NULL,
            winning_bid NUMERIC(14, 2) NOT NULL DEFAULT 0,
            auctioneer_commission_percent NUMERIC(7, 4) NOT NULL DEFAULT 5,
            other_acquisition_costs NUMERIC(14, 2) NOT NULL DEFAULT 0,
            transfer_tax_percent NUMERIC(7, 4) NOT NULL DEFAULT 0,
            transfer_tax_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            registry_cost_percent NUMERIC(7, 4) NOT NULL DEFAULT 0,
            registry_cost_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            eviction_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
            renovation_budget NUMERIC(14, 2) NOT NULL DEFAULT 0,
            cleaning_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
            overdue_property_tax NUMERIC(14, 2) NOT NULL DEFAULT 0,
            future_property_tax NUMERIC(14, 2) NOT NULL DEFAULT 0,
            overdue_condo_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            future_condo_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            legal_fees NUMERIC(14, 2) NOT NULL DEFAULT 0,
            contingency_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            capital_cost_months INTEGER NOT NULL DEFAULT 0,
            capital_cost_percent NUMERIC(7, 4) NOT NULL DEFAULT 0,
            minimum_profit_percent NUMERIC(7, 4) NOT NULL DEFAULT 0,
            minimum_profit_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            projected_sale_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            broker_commission_percent NUMERIC(7, 4) NOT NULL DEFAULT 5,
            sale_tax_percent NUMERIC(7, 4) NOT NULL DEFAULT 0,
            operational_expenses NUMERIC(14, 2) NOT NULL DEFAULT 0,
            last_calculation_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_re_auction_financial_sheets_company_property UNIQUE(company_id, property_id),
            CONSTRAINT fk_re_auction_financial_sheets_company_property
                FOREIGN KEY(company_id, property_id)
                REFERENCES public.real_estate_auction_properties(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_financial_sheets_company_property ON public.real_estate_auction_financial_sheets(company_id, property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_financial_sheets_company_id ON public.real_estate_auction_financial_sheets(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_financial_sheets_property_id ON public.real_estate_auction_financial_sheets(property_id);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_due_diligence (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            property_id INTEGER NOT NULL,
            condo_fee_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            building_age INTEGER,
            building_description TEXT,
            property_description TEXT,
            region_square_meter_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
            resident_contacted BOOLEAN NOT NULL DEFAULT FALSE,
            resident_report TEXT,
            manager_contacted BOOLEAN NOT NULL DEFAULT FALSE,
            manager_report TEXT,
            other_debts NUMERIC(14, 2) NOT NULL DEFAULT 0,
            internal_notes TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_re_auction_due_diligence_company_property UNIQUE(company_id, property_id),
            CONSTRAINT fk_re_auction_due_diligence_company_property
                FOREIGN KEY(company_id, property_id)
                REFERENCES public.real_estate_auction_properties(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_due_diligence_company_property ON public.real_estate_auction_due_diligence(company_id, property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_due_diligence_company_id ON public.real_estate_auction_due_diligence(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_due_diligence_property_id ON public.real_estate_auction_due_diligence(property_id);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_attachments (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            property_id INTEGER NOT NULL,
            category VARCHAR(30) NOT NULL DEFAULT 'other',
            original_filename VARCHAR(255),
            stored_filename VARCHAR(255),
            storage_path VARCHAR(1024) NOT NULL,
            mime_type VARCHAR(255),
            size_bytes INTEGER NOT NULL DEFAULT 0,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_re_auction_attachments_category CHECK (
                category IN ('photo', 'notice', 'registry', 'report', 'other')
            ),
            CONSTRAINT fk_re_auction_attachments_company_property
                FOREIGN KEY(company_id, property_id)
                REFERENCES public.real_estate_auction_properties(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_company_property ON public.real_estate_auction_attachments(company_id, property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_company_category ON public.real_estate_auction_attachments(company_id, category);
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_company_id ON public.real_estate_auction_attachments(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_property_id ON public.real_estate_auction_attachments(property_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_category ON public.real_estate_auction_attachments(category);
        CREATE INDEX IF NOT EXISTS ix_re_auction_attachments_created_by_user_id ON public.real_estate_auction_attachments(created_by_user_id);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_sources (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            name VARCHAR(160) NOT NULL,
            domain VARCHAR(255) NOT NULL,
            base_url VARCHAR(1024) NOT NULL,
            link_pattern VARCHAR(255),
            listing_selector VARCHAR(255),
            active BOOLEAN NOT NULL DEFAULT TRUE,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_re_auction_sources_company_base_url UNIQUE(company_id, base_url),
            CONSTRAINT uq_re_auction_sources_company_id UNIQUE(company_id, id)
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_sources_company_active ON public.real_estate_auction_sources(company_id, active);
        CREATE INDEX IF NOT EXISTS ix_re_auction_sources_company_id ON public.real_estate_auction_sources(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_sources_domain ON public.real_estate_auction_sources(domain);
        CREATE INDEX IF NOT EXISTS ix_re_auction_sources_active ON public.real_estate_auction_sources(active);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_import_jobs (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            source_id INTEGER NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMP WITHOUT TIME ZONE,
            total_found INTEGER NOT NULL DEFAULT 0,
            total_imported INTEGER NOT NULL DEFAULT 0,
            total_duplicated INTEGER NOT NULL DEFAULT 0,
            total_error INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            CONSTRAINT uq_re_auction_import_jobs_company_id UNIQUE(company_id, id),
            CONSTRAINT ck_re_auction_import_jobs_status CHECK (
                status IN ('pending', 'running', 'imported', 'duplicated', 'error', 'completed', 'cancelled')
            ),
            CONSTRAINT fk_re_auction_import_jobs_company_source
                FOREIGN KEY(company_id, source_id)
                REFERENCES public.real_estate_auction_sources(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_jobs_company_status ON public.real_estate_auction_import_jobs(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_jobs_company_source ON public.real_estate_auction_import_jobs(company_id, source_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_jobs_company_id ON public.real_estate_auction_import_jobs(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_jobs_source_id ON public.real_estate_auction_import_jobs(source_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_jobs_status ON public.real_estate_auction_import_jobs(status);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_import_job_items (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            job_id INTEGER NOT NULL,
            url VARCHAR(1024) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            error_message TEXT,
            fingerprint VARCHAR(128) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_re_auction_import_items_company_job_fp UNIQUE(company_id, job_id, fingerprint),
            CONSTRAINT ck_re_auction_import_items_status CHECK (
                status IN ('pending', 'running', 'imported', 'duplicated', 'error', 'completed', 'cancelled')
            ),
            CONSTRAINT fk_re_auction_import_items_company_job
                FOREIGN KEY(company_id, job_id)
                REFERENCES public.real_estate_auction_import_jobs(company_id, id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_items_company_job ON public.real_estate_auction_import_job_items(company_id, job_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_items_company_status ON public.real_estate_auction_import_job_items(company_id, status);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_items_company_id ON public.real_estate_auction_import_job_items(company_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_items_job_id ON public.real_estate_auction_import_job_items(job_id);
        CREATE INDEX IF NOT EXISTS ix_re_auction_import_items_status ON public.real_estate_auction_import_job_items(status);

        CREATE TABLE IF NOT EXISTS public.real_estate_auction_tenant_settings (
            id SERIAL PRIMARY KEY,
            company_id INTEGER NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
            module_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            display_name VARCHAR(160) NOT NULL DEFAULT 'Leilões Imobiliários',
            code_prefix VARCHAR(20),
            settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_re_auction_tenant_settings_company UNIQUE(company_id)
        );
        CREATE INDEX IF NOT EXISTS ix_re_auction_tenant_settings_enabled ON public.real_estate_auction_tenant_settings(company_id, module_enabled);
        CREATE INDEX IF NOT EXISTS ix_re_auction_tenant_settings_company_id ON public.real_estate_auction_tenant_settings(company_id);
        """
    )


def downgrade():
    op.execute(
        """
        DROP INDEX IF EXISTS public.ix_re_auction_tenant_settings_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_tenant_settings_enabled;
        DROP TABLE IF EXISTS public.real_estate_auction_tenant_settings;

        DROP INDEX IF EXISTS public.ix_re_auction_import_items_status;
        DROP INDEX IF EXISTS public.ix_re_auction_import_items_job_id;
        DROP INDEX IF EXISTS public.ix_re_auction_import_items_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_import_items_company_status;
        DROP INDEX IF EXISTS public.ix_re_auction_import_items_company_job;
        DROP TABLE IF EXISTS public.real_estate_auction_import_job_items;

        DROP INDEX IF EXISTS public.ix_re_auction_import_jobs_status;
        DROP INDEX IF EXISTS public.ix_re_auction_import_jobs_source_id;
        DROP INDEX IF EXISTS public.ix_re_auction_import_jobs_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_import_jobs_company_source;
        DROP INDEX IF EXISTS public.ix_re_auction_import_jobs_company_status;
        DROP TABLE IF EXISTS public.real_estate_auction_import_jobs;

        DROP INDEX IF EXISTS public.ix_re_auction_sources_active;
        DROP INDEX IF EXISTS public.ix_re_auction_sources_domain;
        DROP INDEX IF EXISTS public.ix_re_auction_sources_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_sources_company_active;
        DROP TABLE IF EXISTS public.real_estate_auction_sources;

        DROP INDEX IF EXISTS public.ix_re_auction_attachments_created_by_user_id;
        DROP INDEX IF EXISTS public.ix_re_auction_attachments_category;
        DROP INDEX IF EXISTS public.ix_re_auction_attachments_property_id;
        DROP INDEX IF EXISTS public.ix_re_auction_attachments_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_attachments_company_category;
        DROP INDEX IF EXISTS public.ix_re_auction_attachments_company_property;
        DROP TABLE IF EXISTS public.real_estate_auction_attachments;

        DROP INDEX IF EXISTS public.ix_re_auction_due_diligence_property_id;
        DROP INDEX IF EXISTS public.ix_re_auction_due_diligence_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_due_diligence_company_property;
        DROP TABLE IF EXISTS public.real_estate_auction_due_diligence;

        DROP INDEX IF EXISTS public.ix_re_auction_financial_sheets_property_id;
        DROP INDEX IF EXISTS public.ix_re_auction_financial_sheets_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_financial_sheets_company_property;
        DROP TABLE IF EXISTS public.real_estate_auction_financial_sheets;

        DROP INDEX IF EXISTS public.ix_re_auction_events_result;
        DROP INDEX IF EXISTS public.ix_re_auction_events_auction_datetime;
        DROP INDEX IF EXISTS public.ix_re_auction_events_property_id;
        DROP INDEX IF EXISTS public.ix_re_auction_events_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_events_company_property;
        DROP INDEX IF EXISTS public.ix_re_auction_events_company_datetime;
        DROP TABLE IF EXISTS public.real_estate_auction_events;

        DROP INDEX IF EXISTS public.ix_re_auction_properties_updated_by_user_id;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_created_by_user_id;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_auxiliary_filter;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_triage_status;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_status;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_occupied;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_bank;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_state;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_city;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_company_id;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_company_city_state;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_company_triage;
        DROP INDEX IF EXISTS public.ix_re_auction_properties_company_status;
        DROP TABLE IF EXISTS public.real_estate_auction_properties;
        """
    )
