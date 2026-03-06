"""fix activity work log trigger and constraint

Revision ID: 6c9b3e8f4a21
Revises: d2ea9f5a3870
Create Date: 2026-03-06 19:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "6c9b3e8f4a21"
down_revision = "d2ea9f5a3870"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'activity_work_logs'
            ) THEN
                ALTER TABLE public.activity_work_logs
                    DROP CONSTRAINT IF EXISTS activity_work_logs_activity_type_check;

                ALTER TABLE public.activity_work_logs
                    ADD CONSTRAINT activity_work_logs_activity_type_check
                    CHECK (
                        activity_type::text = ANY (
                            ARRAY['project'::character varying, 'process'::character varying, 'process_instance'::character varying]::text[]
                        )
                    );
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sync_activity_worked_hours(
            p_activity_type text,
            p_activity_id integer
        ) RETURNS void
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            total_hours numeric := 0;
            has_project_tasks boolean := false;
            has_project_task_summary boolean := false;
            has_process_instances boolean := false;
            has_company_projects_worked_hours boolean := false;
        BEGIN
            IF p_activity_type IS NULL OR p_activity_id IS NULL THEN
                RETURN;
            END IF;

            SELECT COALESCE(SUM(hours_worked), 0)
              INTO total_hours
              FROM public.activity_work_logs
             WHERE activity_type = p_activity_type
               AND activity_id = p_activity_id;

            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'project_tasks'
                   AND column_name = 'worked_hours'
            ) INTO has_project_tasks;

            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'project_task_hours_summary'
                   AND column_name = 'total_worked_hours'
            ) INTO has_project_task_summary;

            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'process_instances'
                   AND column_name = 'worked_hours'
            ) INTO has_process_instances;

            SELECT EXISTS (
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'company_projects'
                   AND column_name = 'worked_hours'
            ) INTO has_company_projects_worked_hours;

            IF p_activity_type = 'project' THEN
                IF has_project_tasks THEN
                    UPDATE public.project_tasks
                       SET worked_hours = total_hours,
                           updated_at = NOW()
                     WHERE id = p_activity_id;
                ELSIF has_company_projects_worked_hours THEN
                    UPDATE public.company_projects
                       SET worked_hours = total_hours,
                           updated_at = NOW()
                     WHERE id = p_activity_id;
                END IF;

                IF has_project_task_summary THEN
                    UPDATE public.project_task_hours_summary
                       SET total_worked_hours = total_hours,
                           updated_at = NOW()
                     WHERE task_id = p_activity_id;
                END IF;
            ELSIF p_activity_type IN ('process', 'process_instance') THEN
                IF has_process_instances THEN
                    UPDATE public.process_instances
                       SET worked_hours = total_hours,
                           actual_hours = total_hours::real,
                           updated_at = NOW()
                     WHERE id = p_activity_id;
                END IF;
            END IF;
        END;
        $function$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.update_activity_worked_hours()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                PERFORM public.sync_activity_worked_hours(OLD.activity_type, OLD.activity_id);
            END IF;

            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                PERFORM public.sync_activity_worked_hours(NEW.activity_type, NEW.activity_id);
            END IF;

            RETURN COALESCE(NEW, OLD);
        END;
        $function$;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trigger_update_worked_hours ON public.activity_work_logs;")
    op.execute(
        """
        CREATE TRIGGER trigger_update_worked_hours
        AFTER INSERT OR UPDATE OR DELETE ON public.activity_work_logs
        FOR EACH ROW
        EXECUTE FUNCTION public.update_activity_worked_hours();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trigger_update_worked_hours ON public.activity_work_logs;")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.update_activity_worked_hours()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            IF NEW.activity_type = 'project' THEN
                UPDATE public.company_projects
                   SET worked_hours = (
                        SELECT COALESCE(SUM(hours_worked), 0)
                          FROM public.activity_work_logs
                         WHERE activity_type = 'project'
                           AND activity_id = NEW.activity_id
                   )
                 WHERE id = NEW.activity_id;
            ELSIF NEW.activity_type = 'process' THEN
                UPDATE public.process_instances
                   SET actual_hours = (
                        SELECT COALESCE(SUM(hours_worked), 0)
                          FROM public.activity_work_logs
                         WHERE activity_type = 'process'
                           AND activity_id = NEW.activity_id
                   )
                 WHERE id = NEW.activity_id;
            END IF;

            RETURN NEW;
        END;
        $function$;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trigger_update_worked_hours
        AFTER INSERT ON public.activity_work_logs
        FOR EACH ROW
        EXECUTE FUNCTION public.update_activity_worked_hours();
        """
    )

    op.execute("DROP FUNCTION IF EXISTS public.sync_activity_worked_hours(text, integer);")

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'activity_work_logs'
            ) THEN
                ALTER TABLE public.activity_work_logs
                    DROP CONSTRAINT IF EXISTS activity_work_logs_activity_type_check;

                ALTER TABLE public.activity_work_logs
                    ADD CONSTRAINT activity_work_logs_activity_type_check
                    CHECK (
                        activity_type::text = ANY (
                            ARRAY['project'::character varying, 'process'::character varying]::text[]
                        )
                    );
            END IF;
        END
        $$;
        """
    )
