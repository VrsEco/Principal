# Running the project hours SQL migration on Cloud SQL

The new API surface depends on the `project_activities` and `project_activity_collaborators` tables plus the supporting triggers that keep `worked_hours` in sync. The `scripts/gcloud/project_hours_migration.sql` file contains the full DDL/trigger batch that can be executed directly in the Cloud SQL shell. Because `gcloud sql connect` opens an interactive `psql` session, it is safer to upload the script through `\i` instead of shell redirection, which otherwise can emit the `pq: syntax error at or near "-"` message if the `psql` prompt interprets the first characters literally.

## Steps
1. Make sure you have the latest code in this repository and that you already created a production backup.
2. From Cloud Shell (or any authorized environment with the repository files), run the Cloud SQL connector:
   ```bash
   gcloud sql connect YOUR_INSTANCE_NAME --user=postgres --database=gestaopev
   ```
3. Once you are in the `psql` prompt, load the prepared SQL:
   ```sql
   \i scripts/gcloud/project_hours_migration.sql
   ```
4. The script wraps the statements in `BEGIN`/`COMMIT`, so it can be safely re-run and it guards against already existing objects.
5. After the schema is updated, proceed with the usual code deployment flow: commit/push the remaining changes and deploy the service via your existing Cloud Run/App Engine steps.

Open `scripts/gcloud/project_hours_migration.sql` if you want to inspect every statement before running it.
