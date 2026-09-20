"""Launch loopback-only portable PostgreSQL and run the isolated P0 tests.

No Windows service, application DATABASE_URL, real identities or production data.
Binary directory must be explicitly provided. Cluster is stopped in finally.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument(
        "--full-chain",
        action="store_true",
        help="Also run the complete Flask-Migrate chain in a second synthetic database.",
    )
    parser.add_argument(
        "--deployment-replay",
        action="store_true",
        help="Replay only the P0 head from its production predecessor revision.",
    )
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[2]
    binaries = args.pg_bin.resolve()
    for name in ("initdb.exe", "pg_ctl.exe", "postgres.exe"):
        if not (binaries / name).is_file():
            parser.error(f"missing binary: {name}")
    workspace = package / "tmp" / "audit_p0_pg_lab" / ("run_" + uuid.uuid4().hex)
    workspace.mkdir(parents=True)
    cluster = workspace / "cluster"
    password_file = workspace / "password.tmp"
    password = secrets.token_urlsafe(32)
    password_file.write_text(password, encoding="utf-8")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["PYTHONPATH"] = str(package)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    result_code = 1
    contract_suite_code = None
    full_chain_code = None
    full_chain_head = None
    deployment_replay_code = None
    deployment_replay_head = None
    started = False
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    def run(command, *, cwd=None, child_env=None, **kwargs):
        must_succeed = kwargs.pop("check", False)
        log = workspace / ("command_" + uuid.uuid4().hex + ".log")
        # pg_ctl's background child can retain pipe handles on Windows. Files
        # avoid communicate() waiting for the server's lifetime.
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=cwd or package.parent, env=child_env or env,
                                    creationflags=flags, stdout=stream,
                                    stderr=subprocess.STDOUT, **kwargs)
        output = log.read_text(encoding="utf-8", errors="replace").replace(password, "[REDACTED]")
        log.write_text(output, encoding="utf-8")
        # Windows consoles often default to cp1252 while application startup
        # emits emoji. Keep the evidence UTF-8 without making the harness fail.
        sys.stdout.buffer.write(output.encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
        if must_succeed:
            result.check_returncode()
        return result
    try:
        run([str(binaries / "initdb.exe"), "-D", str(cluster), "-U", "audit_p0",
             "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C",
             "--pwfile", str(password_file)], check=True, timeout=90)
        password_file.unlink()
        run([str(binaries / "pg_ctl.exe"), "-D", str(cluster), "-l", str(workspace / "postgres.log"),
             "-o", f"-h 127.0.0.1 -p {port} -c max_connections=20", "-w", "start"], check=True, timeout=60)
        started = True
        import psycopg2
        conn = psycopg2.connect(host="127.0.0.1", port=port, user="audit_p0", password=password,
                               dbname="postgres", connect_timeout=5)
        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("CREATE DATABASE app32_audit_p0_test")
        finally:
            conn.close()
        env["APP32_AUDIT_P0_TEST_URL"] = (
            f"postgresql+psycopg2://audit_p0:{password}@127.0.0.1:{port}/app32_audit_p0_test"
        )
        result = run([sys.executable, "-m", "pytest",
                      "app32/tests/test_audit_p0_postgresql_integration.py", "-q"], timeout=120)
        contract_suite_code = result.returncode
        result_code = contract_suite_code

        if args.full_chain and contract_suite_code == 0:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="audit_p0",
                password=password,
                dbname="postgres",
                connect_timeout=5,
            )
            try:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute("CREATE DATABASE app32_audit_p0_chain")
            finally:
                conn.close()

            chain_url = (
                f"postgresql+psycopg2://audit_p0:{password}"
                f"@127.0.0.1:{port}/app32_audit_p0_chain"
            )
            chain_env = env.copy()
            chain_env.update(
                {
                    "DATABASE_URL": chain_url,
                    "DEV_DATABASE_URL": chain_url,
                    "FLASK_CONFIG": "development",
                    "APP_BOOTSTRAP_DB_SCHEMA": "0",
                    "APP_BOOTSTRAP_RUNTIME_SERVICES": "0",
                    "TELEGRAM_SETUP_WEBHOOK": "0",
                    "USAGE_TELEMETRY_ENABLED": "0",
                }
            )
            chain = run(
                [sys.executable, "-m", "flask", "--app", "app:create_app", "db", "upgrade"],
                cwd=package,
                child_env=chain_env,
                timeout=600,
            )
            full_chain_code = chain.returncode
            result_code = full_chain_code
            if full_chain_code == 0:
                conn = psycopg2.connect(
                    host="127.0.0.1",
                    port=port,
                    user="audit_p0",
                    password=password,
                    dbname="app32_audit_p0_chain",
                    connect_timeout=5,
                )
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version_num FROM alembic_version")
                        heads = sorted(row[0] for row in cursor.fetchall())
                        full_chain_head = ",".join(heads)
                        if heads != ["20260916_1000"]:
                            raise RuntimeError(f"unexpected Alembic heads: {heads}")
                        cursor.execute(
                            """
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'ai_mcp_audit_events'
                            """
                        )
                        columns = {row[0] for row in cursor.fetchall()}
                        required = {
                            "company_id", "principal_id", "auth_method", "client_id",
                            "surface", "token_scopes", "policy_allowed", "policy_reason",
                            "approval_request_id", "payload_digest",
                        }
                        missing = sorted(required - columns)
                        if missing:
                            raise RuntimeError(f"missing audit v2 columns: {missing}")
                finally:
                    conn.close()

        if args.deployment_replay and contract_suite_code == 0:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="audit_p0",
                password=password,
                dbname="postgres",
                connect_timeout=5,
            )
            try:
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute("CREATE DATABASE app32_audit_p0_replay")
            finally:
                conn.close()

            conn = psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="audit_p0",
                password=password,
                dbname="app32_audit_p0_replay",
                connect_timeout=5,
            )
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "CREATE TABLE alembic_version "
                        "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )
                    cursor.execute(
                        "INSERT INTO alembic_version(version_num) VALUES (%s)",
                        ("20260913_1500",),
                    )
                conn.commit()
            finally:
                conn.close()

            replay_url = (
                f"postgresql+psycopg2://audit_p0:{password}"
                f"@127.0.0.1:{port}/app32_audit_p0_replay"
            )
            replay_env = env.copy()
            replay_env.update(
                {
                    "DATABASE_URL": replay_url,
                    "DEV_DATABASE_URL": replay_url,
                    "FLASK_CONFIG": "development",
                    "APP_BOOTSTRAP_DB_SCHEMA": "0",
                    "APP_BOOTSTRAP_RUNTIME_SERVICES": "0",
                    "TELEGRAM_SETUP_WEBHOOK": "0",
                    "USAGE_TELEMETRY_ENABLED": "0",
                }
            )
            replay = run(
                [sys.executable, "-m", "flask", "--app", "app:create_app", "db", "upgrade"],
                cwd=package,
                child_env=replay_env,
                timeout=300,
            )
            deployment_replay_code = replay.returncode
            if deployment_replay_code == 0:
                conn = psycopg2.connect(
                    host="127.0.0.1",
                    port=port,
                    user="audit_p0",
                    password=password,
                    dbname="app32_audit_p0_replay",
                    connect_timeout=5,
                )
                try:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT version_num FROM alembic_version")
                        heads = sorted(row[0] for row in cursor.fetchall())
                        deployment_replay_head = ",".join(heads)
                        if heads != ["20260916_1000"]:
                            deployment_replay_code = 2
                        cursor.execute(
                            """
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'ai_mcp_audit_events'
                            """
                        )
                        columns = {row[0] for row in cursor.fetchall()}
                        required = {
                            "company_id", "principal_id", "auth_method", "client_id",
                            "surface", "token_scopes", "policy_allowed", "policy_reason",
                            "approval_request_id", "payload_digest",
                        }
                        if required - columns:
                            deployment_replay_code = 3
                finally:
                    conn.close()

        gate_codes = [contract_suite_code]
        if args.full_chain:
            gate_codes.append(full_chain_code)
        if args.deployment_replay:
            gate_codes.append(deployment_replay_code)
        result_code = 0 if all(code == 0 for code in gate_codes) else 1
    finally:
        env.pop("APP32_AUDIT_P0_TEST_URL", None)
        if password_file.exists():
            password_file.unlink()
        if started or (cluster / "postmaster.pid").exists():
            run([str(binaries / "pg_ctl.exe"), "-D", str(cluster), "-m", "fast", "-w", "stop"],
                check=True, timeout=60)
        with socket.socket() as probe:
            probe.settimeout(1)
            stopped = probe.connect_ex(("127.0.0.1", port)) != 0
        report = {
            "suite_exit_code": result_code,
            "contract_suite_exit_code": contract_suite_code,
            "full_chain_requested": args.full_chain,
            "full_chain_exit_code": full_chain_code,
            "full_chain_head": full_chain_head,
            "deployment_replay_requested": args.deployment_replay,
            "deployment_replay_exit_code": deployment_replay_code,
            "deployment_replay_head": deployment_replay_head,
            "listener_stopped": stopped,
            "data": "synthetic_only",
            "production_access": False,
        }
        (workspace / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    raise SystemExit(result_code)


if __name__ == "__main__":
    main()
