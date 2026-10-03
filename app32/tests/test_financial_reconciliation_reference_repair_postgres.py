"""Opt-in native PostgreSQL integration: fresh cluster, synthetic identities only.

Requires existing PostgreSQL 14 binaries; never downloads, uses Docker, loads
application config or connects to a pre-existing server. Scalar production model
definitions are extracted by AST; unrelated relationships/FKs are omitted.
"""

import ast
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
from time import perf_counter
from types import ModuleType, SimpleNamespace

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("APP32_REFERENCE_REPAIR_NATIVE_TESTS") != "1",
    reason="Native PostgreSQL integration requires explicit local opt-in",
)
APP = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "reference_repair_pg_isolated",
    APP / "services" / "financial_reconciliation_reference_repair_service.py",
)
REPAIR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPAIR
SPEC.loader.exec_module(REPAIR)
MODEL_NAMES = {
    "account": "FinancialBankAccount",
    "entry": "FinancialEntry",
    "batch": "FinancialImportBatch",
    "row": "FinancialImportRow",
    "match": "FinancialReconciliationMatch",
    "settlement": "FinancialSettlement",
}
TABLE_NAMES = (
    "financial_bank_accounts",
    "financial_entries",
    "financial_import_batches",
    "financial_import_rows",
    "financial_reconciliation_matches",
    "financial_settlements",
)


def scalar_models():
    """Use actual columns/defaults/checks without importing the application graph."""
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.orm import declarative_base

    base = declarative_base()
    db = SimpleNamespace(
        Model=base,
        **{
            name: getattr(sa, name)
            for name in (
                "Column",
                "Integer",
                "String",
                "Text",
                "Date",
                "DateTime",
                "Numeric",
                "Boolean",
                "CheckConstraint",
                "UniqueConstraint",
                "Index",
                "Float",
                "JSON",
            )
        },
    )
    source = APP / "models" / "financial.py"
    parsed = ast.parse(source.read_text(encoding="utf-8-sig"))
    constants = {}
    for node in parsed.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass

    class StripForeignKeys(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            node.args = [
                arg
                for arg in node.args
                if not (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and arg.func.attr == "ForeignKey"
                )
            ]
            return node

    definitions = []
    for node in parsed.body:
        if isinstance(node, ast.ClassDef) and node.name in MODEL_NAMES.values():
            node = deepcopy(node)
            node.body = [
                item
                for item in node.body
                if isinstance(item, ast.Assign)
                and (
                    any(
                        isinstance(target, ast.Name)
                        and target.id in {"__tablename__", "__table_args__"}
                        for target in item.targets
                    )
                    or isinstance(item.value, ast.Call)
                    and isinstance(item.value.func, ast.Attribute)
                    and item.value.func.attr == "Column"
                )
            ]
            definitions.append(StripForeignKeys().visit(node))
    module = ast.Module(body=definitions, type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {**constants, "db": db, "JSONB": JSONB, "datetime": datetime}
    exec(compile(module, str(source), "exec"), namespace)
    isolated = ModuleType("models.financial")
    for name in MODEL_NAMES.values():
        setattr(isolated, name, namespace[name])
    return base, isolated, {kind: namespace[name] for kind, name in MODEL_NAMES.items()}


@pytest.fixture(scope="session")
def isolated_postgres():
    import psycopg2
    from sqlalchemy import create_engine

    binaries = Path(r"C:\Program Files\PostgreSQL\14\bin")
    for name in ("initdb.exe", "pg_ctl.exe", "postgres.exe"):
        if not (binaries / name).is_file():
            pytest.fail(
                f"Required existing binary unavailable: {name}; no installation attempted"
            )
    root = Path(tempfile.mkdtemp(prefix="app32-reference-repair-pg-")).resolve()
    data = root / "cluster"
    log = root / "server.log"
    passfile = root / "empty.synthetic.pgpass"
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    start_attempted = False
    engine = None
    timings = {}
    command_number = 0
    environment_patch = pytest.MonkeyPatch()

    def run(arguments, *, allowed_returncodes=(0,)):
        nonlocal command_number
        command_number += 1
        stdout_path = root / f"command-{command_number}.stdout.log"
        stderr_path = root / f"command-{command_number}.stderr.log"
        # pg_ctl starts a child that may inherit stdout/stderr. PIPE would keep
        # communicate() waiting for the running postmaster on Windows.
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            try:
                result = subprocess.run(
                    arguments,
                    stdout=stdout,
                    stderr=stderr,
                    text=True,
                    timeout=40,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except subprocess.TimeoutExpired:
                pytest.fail(
                    f"Ephemeral PostgreSQL command timed out; evidence directory: {root}"
                )
        if result.returncode not in allowed_returncodes:
            output = stdout_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            errors = stderr_path.read_text(encoding="utf-8", errors="replace")[-4000:]
            pytest.fail(
                f"Ephemeral PostgreSQL command failed ({result.returncode}): {output}\n{errors}"
            )
        return result

    def owned_pidfile():
        pid_path = data / "postmaster.pid"
        if not pid_path.exists():
            return None
        lines = pid_path.read_text().splitlines()
        assert len(lines) >= 4, f"Incomplete pidfile; preserve cluster: {data}"
        assert (
            Path(lines[1]).resolve() == data.resolve()
        ), f"Pidfile directory mismatch; preserve cluster: {data}"
        assert int(lines[3]) == port, f"Pidfile port mismatch; preserve cluster: {data}"
        pid = int(lines[0])
        assert pid > 0, f"Invalid postmaster PID; preserve cluster: {data}"
        return pid

    try:
        # Never inherit libpq/service/password/options settings from the host.
        # Select variables by name; saved values are never logged or used to connect.
        for name in tuple(os.environ):
            if name.upper().startswith("PG"):
                environment_patch.delenv(name, raising=False)
        assert not any(name.upper().startswith("PG") for name in os.environ)
        passfile.write_text("", encoding="utf-8")
        began = perf_counter()
        run(
            [
                str(binaries / "initdb.exe"),
                "-D",
                str(data),
                "-U",
                "repair_synthetic",
                "-A",
                "trust",
                "--no-locale",
                "-E",
                "UTF8",
            ]
        )
        timings["init_seconds"] = perf_counter() - began
        print(
            f"native_pg_init data_directory={data} init_seconds={timings['init_seconds']:.6f}"
        )
        start_attempted = True
        run(
            [
                str(binaries / "pg_ctl.exe"),
                "-D",
                str(data),
                "-l",
                str(log),
                "-w",
                "-t",
                "20",
                "-o",
                f"-h 127.0.0.1 -p {port} -c shared_buffers=16MB -c max_connections=12 "
                "-c statement_timeout=5000",
                "start",
            ]
        )

        def connect():
            return psycopg2.connect(
                host="127.0.0.1",
                port=port,
                user="repair_synthetic",
                dbname="postgres",
                password="synthetic-unused",
                passfile=str(passfile),
                sslmode="disable",
                gssencmode="disable",
                connect_timeout=3,
                application_name="app32_synthetic_reference_repair_tests",
            )

        connection = connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SHOW data_directory")
                assert (
                    Path(cursor.fetchone()[0]).resolve() == data.resolve()
                ), "Cluster identity mismatch"
                cursor.execute(
                    "SELECT host(inet_server_addr()), inet_server_port(), version()"
                )
                host, actual_port, version = cursor.fetchone()
                assert host == "127.0.0.1" and actual_port == port
                assert "PostgreSQL 14" in version
                postmaster_pid = owned_pidfile()
                assert postmaster_pid is not None
                print(
                    f"native_pg_identity data_directory={data} host={host} port={actual_port} "
                    f"postmaster_pid={postmaster_pid}"
                )
                cursor.execute(
                    "CREATE TABLE app32_synthetic_cluster_marker (label text PRIMARY KEY)"
                )
                cursor.execute(
                    "INSERT INTO app32_synthetic_cluster_marker VALUES ('fresh-synthetic-only')"
                )
            connection.commit()
        finally:
            connection.close()
        engine = create_engine(
            "postgresql+psycopg2://", creator=connect, pool_size=3, max_overflow=3
        )
        base, module, models = scalar_models()
        with pytest.MonkeyPatch.context() as patch:
            patch.setitem(sys.modules, "models.financial", module)
            base.metadata.create_all(engine)
            yield engine, models, timings
    finally:
        try:
            # Only the randomly generated cluster under the OS temp root is removable.
            expected_parent = Path(tempfile.gettempdir()).resolve()
            assert root.parent == expected_parent and root.name.startswith(
                "app32-reference-repair-pg-"
            )
            assert data.resolve().parent == root
            try:
                if engine is not None:
                    engine.dispose()
            finally:
                if start_attempted:
                    # Startup may have failed after spawning postgres: never rely on
                    # pg_ctl start returning successfully to decide whether to stop.
                    pid = owned_pidfile()
                    status = run(
                        [str(binaries / "pg_ctl.exe"), "-D", str(data), "status"],
                        allowed_returncodes=(0, 3),
                    )
                    if status.returncode == 0 or pid is not None:
                        assert (
                            pid is not None
                        ), f"Running cluster lacks verified pidfile; preserve: {data}"
                        began = perf_counter()
                        run(
                            [
                                str(binaries / "pg_ctl.exe"),
                                "-D",
                                str(data),
                                "-w",
                                "-t",
                                "20",
                                "-m",
                                "fast",
                                "stop",
                            ]
                        )
                        print(
                            f"native_pg_shutdown data_directory={data} postmaster_pid={pid} "
                            f"shutdown_seconds={perf_counter() - began:.6f}"
                        )
                    stopped = run(
                        [str(binaries / "pg_ctl.exe"), "-D", str(data), "status"],
                        allowed_returncodes=(3,),
                    )
                    print(
                        f"native_pg_shutdown_verified data_directory={data} status={stopped.returncode}"
                    )
            assert not (
                data / "postmaster.pid"
            ).exists(), "Cluster still running; refuse cleanup"
            shutil.rmtree(root)
            assert not root.exists(), f"Temporary cluster was not removed: {root}"
            print(f"native_pg_removed root={root}")
        finally:
            environment_patch.undo()


@pytest.fixture
def fixture(isolated_postgres):
    from sqlalchemy.orm import sessionmaker

    engine, models, timings = isolated_postgres
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    plan = REPAIR.RepairPlan(
        77,
        20,
        30,
        "SYNTHETIC-ONLY",
        tuple(
            REPAIR.RepairPair(101 + index, 201 + index, 301 + index, 401 + index)
            for index in range(3)
        ),
    )
    with factory.begin() as session:
        for kind in ("match", "settlement", "row", "entry", "batch", "account"):
            session.query(models[kind]).delete()
        session.add(
            models["account"](
                id=20,
                company_id=77,
                code="SYNTH",
                name="Synthetic bank",
                bank_code="000",
            )
        )
        session.add(
            models["batch"](
                id=30,
                company_id=77,
                batch_code=plan.batch_code,
                source_type="csv",
                status="processed",
            )
        )
        for index, pair in enumerate(plan.pairs):
            amount = Decimal("123.45") + index
            session.add(
                models["entry"](
                    id=pair.entry_id,
                    company_id=77,
                    entry_code=f"SYN-{index}",
                    entry_type="transfer",
                    movement_nature="debit",
                    origin_type="manual",
                    original_amount=amount,
                    competence_date=date(2026, 1, 1),
                    description="Synthetic only",
                    status="settled",
                )
            )
            session.add(
                models["row"](
                    id=pair.row_id,
                    company_id=77,
                    import_batch_id=30,
                    row_number=index + 1,
                    amount=amount,
                    occurred_on=date(2026, 1, 2),
                    movement_nature="debit",
                    matched_entry_id=pair.entry_id,
                    normalized_payload={"bank_account_id": 20},
                )
            )
            session.add(
                models["match"](
                    id=pair.match_id,
                    company_id=77,
                    import_batch_id=30,
                    import_row_id=pair.row_id,
                    financial_entry_id=pair.entry_id,
                    match_status="confirmed",
                    matched_amount=amount,
                    metadata_json={
                        "keep": index,
                        "private_nested": {
                            "marker": "SYNTHETIC-PRIVATE-NOT-IN-RECEIPT",
                            "values": [None, True],
                        },
                        **({"financial_settlement_id": None} if index == 0 else {}),
                    },
                )
            )
            session.add(
                models["settlement"](
                    id=pair.settlement_id,
                    company_id=77,
                    financial_entry_id=pair.entry_id,
                    settlement_code=f"SYN-BX-{index}",
                    settlement_type="manual",
                    settlement_status="posted",
                    settlement_date=date(2026, 1, 1),
                    bank_account_id=20,
                    principal_amount=amount,
                    net_amount=amount,
                    gross_amount=amount,
                    reconciliation_status="pending",
                    metadata_json={
                        "keep": index,
                        "private_nested": {"values": [None, {"keep": True}]},
                        **({"import_batch_id": None} if index == 0 else {}),
                    },
                )
            )
    repository = REPAIR.PostgresReferenceRepairRepository(engine)
    service = REPAIR.FinancialReconciliationReferenceRepairService(repository)
    return plan, service, repository, factory, models, timings


def preview(plan, service):
    return service.dry_run(plan, allowed_company_ids=(77,))


def apply(plan, service, approved):
    return service.apply(
        plan,
        allowed_company_ids=(77,),
        actor_user_id=55,
        financial_edit_authorized=True,
        approved_snapshot=approved,
    )


def recover(plan, service, receipt):
    return service.recover(
        plan,
        allowed_company_ids=(77,),
        actor_user_id=55,
        financial_edit_authorized=True,
        receipt=receipt,
    )


def persisted(factory, models):
    with factory() as session:
        return {
            kind: [
                deepcopy(REPAIR._state(item))
                for item in session.query(model).order_by(model.id)
            ]
            for kind, model in models.items()
        }


def assert_table_locks_released(factory):
    """A different transaction must acquire all six writer modes immediately."""
    from sqlalchemy import text

    with factory.begin() as observer:
        observer.execute(
            text(f"LOCK TABLE {', '.join(TABLE_NAMES)} IN ROW EXCLUSIVE MODE NOWAIT")
        )


def insert_copy(session, model, source_id, new_id, **overrides):
    source = session.get(model, source_id)
    fields = deepcopy(REPAIR._state(source))
    fields.update(id=new_id, **overrides)
    session.add(model(**fields))
    session.flush()


def add_string_dependency(factory, models, plan, kind):
    pair = plan.pairs[0]
    with factory.begin() as session:
        if kind == "match":
            insert_copy(session, models["row"], pair.row_id, 999, row_number=999)
            insert_copy(
                session,
                models["match"],
                pair.match_id,
                999,
                import_row_id=999,
                metadata_json={"financial_settlement_id": str(pair.settlement_id)},
            )
        else:
            insert_copy(
                session,
                models["settlement"],
                pair.settlement_id,
                999,
                settlement_code="SYN-DEPENDENCY-999",
                metadata_json={
                    "import_row_id": str(pair.row_id),
                    "reconciliation_match_id": str(pair.match_id),
                },
            )


def remove_string_dependency(factory, models, kind):
    with factory.begin() as session:
        session.query(models[kind]).filter(
            models[kind].id == 999, models[kind].company_id == 77
        ).delete()
        if kind == "match":
            session.query(models["row"]).filter(
                models["row"].id == 999, models["row"].company_id == 77
            ).delete()


def test_pg_apply_idempotence_recovery_and_preservation(fixture):
    plan, service, repository, factory, models, timings = fixture
    original = persisted(factory, models)
    approved = preview(plan, service)
    began = perf_counter()
    receipt = apply(plan, service, approved)
    timings["apply_seconds"] = perf_counter() - began
    after = persisted(factory, models)
    assert receipt["changed"] and len(receipt["changes"]) == 3
    assert preview(plan, service)["snapshot"] == receipt["after"]
    assert "SYNTHETIC-PRIVATE-NOT-IN-RECEIPT" not in str(receipt)
    assert_table_locks_released(factory)
    assert apply(plan, service, approved)["changed"] is False
    assert persisted(factory, models) == after
    for index, pair in enumerate(plan.pairs):
        match, settlement = after["match"][index], after["settlement"][index]
        assert match["metadata_json"]["financial_settlement_id"] == pair.settlement_id
        assert settlement["metadata_json"]["reconciliation_match_id"] == pair.match_id
        assert (
            settlement["reconciliation_status"] == "reconciled"
            and settlement["import_batch_id"] is None
        )
        for kind in ("match", "settlement"):
            ignored = {"updated_at", "metadata_json", "reconciliation_status"}
            assert {
                key: value
                for key, value in after[kind][index].items()
                if key not in ignored
            } == {
                key: value
                for key, value in original[kind][index].items()
                if key not in ignored
            }
        assert {
            key: value
            for key, value in match["metadata_json"].items()
            if key not in {"financial_settlement_id", REPAIR.AUDIT_KEY}
        } == {
            key: value
            for key, value in original["match"][index]["metadata_json"].items()
            if key != "financial_settlement_id"
        }
        assert {
            key: value
            for key, value in settlement["metadata_json"].items()
            if key not in REPAIR.SETTLEMENT_KEYS
        } == {
            key: value
            for key, value in original["settlement"][index]["metadata_json"].items()
            if key not in REPAIR.SETTLEMENT_KEYS
        }
    assert recover(plan, service, receipt)["recovered"]
    restored = persisted(factory, models)
    assert_table_locks_released(factory)
    for index, item in enumerate(restored["settlement"]):
        assert (
            item["reconciliation_status"]
            == original["settlement"][index]["reconciliation_status"]
        )
        assert item["metadata_json"] == original["settlement"][index]["metadata_json"]
        metadata = restored["match"][index]["metadata_json"]
        assert {
            key: value for key, value in metadata.items() if key != REPAIR.AUDIT_KEY
        } == original["match"][index]["metadata_json"]
        assert [event["action"] for event in metadata[REPAIR.AUDIT_KEY]] == [
            "apply",
            "recover",
        ]
    for kind in ("account", "batch", "entry", "row"):
        assert original[kind] == restored[kind]
    with pytest.raises(REPAIR.RepairConflict, match="State changed"):
        recover(plan, service, receipt)
    assert persisted(factory, models) == restored
    assert_table_locks_released(factory)
    print(f"native_pg_apply_seconds={timings['apply_seconds']:.6f}")


def test_pg_constraint_failure_at_flush_rolls_back_all_pairs(fixture):
    from sqlalchemy import event
    from sqlalchemy.exc import IntegrityError

    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    original = persisted(factory, models)
    seen_pairs = []

    def violate_constraint(session, context, instances):
        changed_matches = sorted(
            item.id for item in session.dirty if isinstance(item, models["match"])
        )
        changed_settlements = sorted(
            item.id for item in session.dirty if isinstance(item, models["settlement"])
        )
        assert changed_matches == [pair.match_id for pair in plan.pairs]
        assert changed_settlements == [pair.settlement_id for pair in plan.pairs]
        seen_pairs.extend(changed_settlements)
        for item in session.dirty:
            if (
                isinstance(item, models["settlement"])
                and item.id == plan.pairs[-1].settlement_id
            ):
                assert (
                    item.metadata_json["reconciliation_match_id"]
                    == plan.pairs[-1].match_id
                )
                item.reconciliation_status = "invalid-test-status"

    event.listen(repository.factory, "before_flush", violate_constraint)
    try:
        with pytest.raises(IntegrityError):
            apply(plan, service, approved)
    finally:
        event.remove(repository.factory, "before_flush", violate_constraint)
    assert seen_pairs == [pair.settlement_id for pair in plan.pairs]
    assert persisted(factory, models) == original
    assert repository.session is None
    assert_table_locks_released(factory)


def test_pg_stale_snapshot_and_recovery_concurrent_change(fixture):
    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    with factory.begin() as session:
        entry = session.get(models["entry"], plan.pairs[0].entry_id)
        entry.description = "Concurrent synthetic update"
    stale_state = persisted(factory, models)
    with pytest.raises(REPAIR.RepairConflict, match="State changed"):
        apply(plan, service, approved)
    assert persisted(factory, models) == stale_state
    assert_table_locks_released(factory)
    receipt = apply(plan, service, preview(plan, service))
    with factory.begin() as session:
        session.get(models["entry"], plan.pairs[0].entry_id).description = (
            "Later concurrent change"
        )
    changed_state = persisted(factory, models)
    with pytest.raises(REPAIR.RepairConflict, match="State changed"):
        recover(plan, service, receipt)
    assert persisted(factory, models) == changed_state
    assert_table_locks_released(factory)


@pytest.mark.parametrize(
    "kind,field",
    [
        ("account", "name"),
        ("entry", "description"),
        ("batch", "notes"),
        ("row", "description"),
        ("match", "match_reason"),
        ("settlement", "notes"),
    ],
)
def test_pg_legacy_writer_causes_immediate_nowait_failure(fixture, kind, field):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    original = persisted(factory, models)
    identity = original[kind][0]["id"]
    table = models[kind].__tablename__
    with factory() as writer:
        with writer.begin():
            writer.execute(
                text(
                    f"UPDATE {table} SET {field}='Uncommitted synthetic writer' "
                    "WHERE id=:identity AND company_id=77"
                ),
                {"identity": identity},
            )
            began = perf_counter()
            with pytest.raises(OperationalError) as error:
                apply(plan, service, approved)
            elapsed = perf_counter() - began
            assert error.value.orig.pgcode == "55P03" and elapsed < 2
            assert repository.session is None
            # A conflict in the last table must release already-acquired locks
            # in the first five even while the original writer remains open.
            assert_table_locks_released(factory)
            print(f"native_pg_nowait table={table} rejection_seconds={elapsed:.6f}")
            writer.rollback()
    assert persisted(factory, models) == original
    assert_table_locks_released(factory)


@pytest.mark.parametrize("finalization", ["commit", "rollback"])
def test_pg_lock_blocks_other_tenant_writer_but_allows_reads(fixture, finalization):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    original = persisted(factory, models)

    class SyntheticRollback(Exception):
        pass

    began_transaction = perf_counter()
    try:
        with repository.transaction(write=True):
            repair_pid = repository.session.execute(
                text("SELECT pg_backend_pid()")
            ).scalar()
            with factory() as observer:
                assert (
                    observer.execute(text("SELECT pg_backend_pid()")).scalar()
                    != repair_pid
                )
                locks = (
                    observer.execute(
                        text(
                            "SELECT c.relname FROM pg_locks AS l JOIN pg_class AS c ON c.oid=l.relation "
                            "WHERE l.pid=:pid AND l.mode='ShareRowExclusiveLock' AND l.granted"
                        ),
                        {"pid": repair_pid},
                    )
                    .scalars()
                    .all()
                )
                assert set(locks) == set(TABLE_NAMES) and len(locks) == 6
                for kind, model in models.items():
                    expected = 1 if kind in {"account", "batch"} else 3
                    assert (
                        observer.execute(
                            text(f"SELECT count(*) FROM {model.__tablename__}")
                        ).scalar()
                        == expected
                    )

            for kind, source_id, overrides in (
                (
                    "match",
                    plan.pairs[0].match_id,
                    {"import_row_id": plan.pairs[0].row_id},
                ),
                (
                    "settlement",
                    plan.pairs[0].settlement_id,
                    {"settlement_code": "BLOCKED-SYN-999"},
                ),
                (
                    "batch",
                    plan.batch_id,
                    {"company_id": 88, "batch_code": "OTHER-SYNTHETIC"},
                ),
            ):
                with factory() as writer:
                    writer.execute(text("SET LOCAL lock_timeout='150ms'"))
                    began = perf_counter()
                    with pytest.raises(OperationalError) as error:
                        insert_copy(writer, models[kind], source_id, 999, **overrides)
                    elapsed = perf_counter() - began
                    assert error.value.orig.pgcode == "55P03" and elapsed < 2
                    print(
                        f"native_pg_insert_blocked table={models[kind].__tablename__} "
                        f"company_id={overrides.get('company_id', 77)} seconds={elapsed:.6f}"
                    )
                    writer.rollback()

            other_repository = REPAIR.PostgresReferenceRepairRepository(
                factory.kw["bind"]
            )
            other_service = REPAIR.FinancialReconciliationReferenceRepairService(
                other_repository
            )
            began = perf_counter()
            with pytest.raises(OperationalError) as error:
                apply(plan, other_service, approved)
            elapsed = perf_counter() - began
            assert error.value.orig.pgcode == "55P03" and elapsed < 2
            assert other_repository.session is None
            print(f"native_pg_other_repair_nowait_seconds={elapsed:.6f}")
            if finalization == "rollback":
                raise SyntheticRollback()
    except SyntheticRollback:
        assert finalization == "rollback"
    assert repository.session is None
    held_seconds = perf_counter() - began_transaction
    assert_table_locks_released(factory)
    assert persisted(factory, models) == original
    with factory() as observer:
        remaining = observer.execute(
            text(
                "SELECT count(*) FROM pg_locks WHERE pid=:pid AND mode='ShareRowExclusiveLock' AND granted"
            ),
            {"pid": repair_pid},
        ).scalar()
        assert remaining == 0
    print(
        f"native_pg_six_table_locks_released finalization={finalization} held_seconds={held_seconds:.6f}"
    )


@pytest.mark.parametrize("kind", ["match", "settlement"])
def test_pg_new_dependency_blocks_recovery(fixture, kind):
    plan, service, repository, factory, models, _ = fixture
    expected = "another active match" if kind == "match" else "Another settlement"
    approved = preview(plan, service)
    add_string_dependency(factory, models, plan, kind)
    before_failed_apply = persisted(factory, models)
    with pytest.raises(REPAIR.RepairConflict, match=expected):
        apply(plan, service, approved)
    assert persisted(factory, models) == before_failed_apply
    assert_table_locks_released(factory)
    remove_string_dependency(factory, models, kind)
    receipt = apply(plan, service, preview(plan, service))
    add_string_dependency(factory, models, plan, kind)
    before_failed_recovery = persisted(factory, models)
    with pytest.raises(REPAIR.RepairConflict, match=expected):
        recover(plan, service, receipt)
    assert persisted(factory, models) == before_failed_recovery
    assert_table_locks_released(factory)


@pytest.mark.parametrize("kind", ["match", "settlement"])
@pytest.mark.parametrize("row_lock", ["UPDATE", "KEY SHARE"])
def test_pg_existing_row_lock_causes_nowait_and_releases_all_tables(
    fixture, kind, row_lock
):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    original = persisted(factory, models)
    identity = getattr(plan.pairs[0], f"{kind}_id")
    table = models[kind].__tablename__
    with factory.begin() as locker:
        locker.execute(
            text(
                f"SELECT id FROM {table} WHERE id=:identity AND company_id=77 FOR {row_lock}"
            ),
            {"identity": identity},
        )
        began = perf_counter()
        with pytest.raises(OperationalError) as error:
            apply(plan, service, approved)
        elapsed = perf_counter() - began
        assert error.value.orig.pgcode == "55P03" and elapsed < 2
        assert repository.session is None
        assert_table_locks_released(factory)
        assert preview(plan, service) == approved
        print(
            f"native_pg_row_nowait table={table} row_lock={row_lock} rejection_seconds={elapsed:.6f}"
        )
    assert persisted(factory, models) == original
    assert_table_locks_released(factory)


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("identity", "Relationship differs"),
        ("tenant", "authorized company"),
        ("account", "Bank account differs"),
        ("amount", "amounts must agree exactly"),
    ],
)
def test_pg_real_identity_tenant_account_and_amount_conflicts_do_not_write(
    fixture, mutation, expected
):
    plan, service, repository, factory, models, _ = fixture
    approved = preview(plan, service)
    pair = plan.pairs[0]
    with factory.begin() as session:
        if mutation == "identity":
            session.get(models["match"], pair.match_id).financial_entry_id = plan.pairs[
                1
            ].entry_id
        elif mutation == "tenant":
            session.get(models["match"], pair.match_id).company_id = 88
        elif mutation == "account":
            insert_copy(
                session,
                models["account"],
                plan.bank_account_id,
                21,
                code="OTHER-SYNTHETIC-ACCOUNT",
            )
            session.get(models["settlement"], pair.settlement_id).bank_account_id = 21
        else:
            session.get(models["settlement"], pair.settlement_id).net_amount = Decimal(
                "999"
            )
    before = persisted(factory, models)
    with pytest.raises(REPAIR.RepairConflict, match=expected):
        preview(plan, service)
    with pytest.raises(REPAIR.RepairConflict, match=expected):
        apply(plan, service, approved)
    assert persisted(factory, models) == before
    assert repository.session is None
    assert_table_locks_released(factory)
