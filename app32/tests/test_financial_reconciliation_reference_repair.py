"""Synthetic in-memory repository only: no app, models, engine or credentials."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date
from decimal import Decimal
import ast
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


# Load just the dependency-free service, avoiding application/package bootstrap.
PATH = Path(__file__).parents[1] / "services" / "financial_reconciliation_reference_repair_service.py"
SPEC = importlib.util.spec_from_file_location("reference_repair_isolated", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
Service = MODULE.FinancialReconciliationReferenceRepairService
Conflict = MODULE.RepairConflict


class MemoryRepository:
    def __init__(self, plan):
        self.data = {}
        self.transactions = []
        self.fail_flush = False
        self.on_begin = None

        def put(kind, identity, **fields):
            self.data[kind, identity] = SimpleNamespace(
                id=identity, company_id=plan.company_id, deleted_at=None, updated_at="synthetic-v1", **fields)

        put("batch", plan.batch_id, batch_code=plan.batch_code)
        put("account", plan.bank_account_id)
        for index, pair in enumerate(plan.pairs):
            amount = Decimal("123.45") + index
            put("row", pair.row_id, import_batch_id=plan.batch_id, matched_entry_id=pair.entry_id,
                created_entry_id=None, movement_nature="debit", amount=amount,
                occurred_on=date(2026, 1, 2), normalized_payload={"bank_account_id": plan.bank_account_id})
            put("match", pair.match_id, import_batch_id=plan.batch_id, import_row_id=pair.row_id,
                financial_entry_id=pair.entry_id, match_status="confirmed", matched_amount=amount,
                metadata_json={"preserved": {"nested": True}})
            put("entry", pair.entry_id, movement_nature="debit", original_amount=amount,
                metadata_json={"transfer_group_id": "synthetic-transfer"})
            put("settlement", pair.settlement_id, financial_entry_id=pair.entry_id,
                bank_account_id=plan.bank_account_id, settlement_status="posted", settlement_date=date(2026, 1, 1),
                net_amount=amount, gross_amount=amount, principal_amount=amount, import_batch_id=None,
                reconciliation_status="pending", external_reference="synthetic-existing-payment",
                metadata_json={"preserved": {"nested": True}})
        # Represents previously repaired cases and the other transfer ends, outside this delivery.
        for identity in range(8000, 8007):
            put("entry", identity, movement_nature="credit", metadata_json={"keep": identity})

    @contextmanager
    def transaction(self, *, write):
        self.transactions.append(write)
        if self.on_begin:
            self.on_begin()
        before = deepcopy(self.data)
        try:
            yield
        except Exception:
            self.data = before
            raise
        if not write:
            assert self.data.keys() == before.keys()
            assert all(vars(value) == vars(before[key]) for key, value in self.data.items())

    def get(self, kind, identity, company_id):
        record = self.data.get((kind, identity))
        if record is None or record.company_id != company_id or record.deleted_at is not None:
            raise Conflict("Record missing from authorized company")
        return record

    def active_matches(self, company_id):
        return [value for (kind, _), value in self.data.items()
                if kind == "match" and value.company_id == company_id and value.deleted_at is None]

    def active_settlements(self, company_id):
        return [value for (kind, _), value in self.data.items()
                if kind == "settlement" and value.company_id == company_id and value.deleted_at is None
                and value.settlement_status != "cancelled"]

    def flush(self):
        if self.fail_flush:
            raise RuntimeError("synthetic persistence failure")
        for kind, value in self.data.items():
            if kind[0] in {"match", "settlement"}:
                value.updated_at = "synthetic-v2"


@pytest.fixture
def fixture():
    plan = MODULE.RepairPlan(77, 20, 30, "SYNTHETIC-ONLY", tuple(
        MODULE.RepairPair(101 + index, 201 + index, 301 + index, 401 + index) for index in range(3)))
    repo = MemoryRepository(plan)
    service = Service(repo)
    return plan, repo, service


def preview(plan, service):
    return service.dry_run(plan, allowed_company_ids=(77,))


def apply(plan, service, approved):
    return service.apply(plan, allowed_company_ids=(77,), actor_user_id=55,
                         financial_edit_authorized=True, approved_snapshot=approved)


def recover(plan, service, receipt):
    return service.recover(plan, allowed_company_ids=(77,), actor_user_id=55,
                           financial_edit_authorized=True, receipt=receipt)


def test_target_configuration_is_inert_and_fixtures_use_other_identities(fixture):
    plan, repo, service = fixture
    assert plan.company_id != MODULE.INTER_REFERENCE_REPAIR_PLAN.company_id
    before = deepcopy(repo.data)
    result = preview(plan, service)
    assert result["writes"] is False and repo.transactions == [False]
    assert all(vars(value) == vars(before[key]) for key, value in repo.data.items())
    assert "synthetic-existing-payment" not in str(result)
    result["pairs"][0]["row_id"] = 999
    assert plan.pairs[0].row_id == 101


def test_apply_bidirectional_references_preserves_finances_and_unrelated_records(fixture):
    plan, repo, service = fixture
    before = deepcopy(repo.data)
    receipt = apply(plan, service, preview(plan, service))
    assert receipt["changed"] and len(repo.data) == len(before)
    assert repo.transactions == [False, True]
    for pair in plan.pairs:
        match = repo.data["match", pair.match_id]
        settlement = repo.data["settlement", pair.settlement_id]
        assert match.metadata_json["financial_settlement_id"] == pair.settlement_id
        assert settlement.metadata_json["import_row_id"] == pair.row_id
        assert settlement.metadata_json["reconciliation_match_id"] == pair.match_id
        assert settlement.metadata_json["import_batch_id"] == plan.batch_id
        assert settlement.reconciliation_status == "reconciled" and settlement.import_batch_id is None
        assert match.metadata_json["preserved"] == settlement.metadata_json["preserved"] == {"nested": True}
        for kind, identity in (("match", pair.match_id), ("settlement", pair.settlement_id)):
            current = vars(repo.data[kind, identity])
            original = vars(before[kind, identity])
            assert {key: value for key, value in current.items() if key not in {"metadata_json", "updated_at", "reconciliation_status"}} == {
                key: value for key, value in original.items() if key not in {"metadata_json", "updated_at", "reconciliation_status"}}
    for key, value in before.items():
        if key[0] not in {"match", "settlement"}:
            assert vars(repo.data[key]) == vars(value)
    # Three bank rows / three links already existed; this repair never creates matches.
    assert sum(item.match_status == "confirmed" for item in repo.active_matches(77)) == 3


def test_idempotent_retry_does_not_flush_or_append_audit(fixture):
    plan, repo, service = fixture
    approved = preview(plan, service)
    apply(plan, service, approved)
    before = deepcopy(repo.data)
    repo.fail_flush = True
    assert apply(plan, service, preview(plan, service))["changed"] is False
    assert all(vars(value) == vars(before[key]) for key, value in repo.data.items())


@pytest.mark.parametrize("mutation", ["references", "date", "metadata", "amount"])
def test_complete_repair_still_rejects_stale_approval(fixture, mutation):
    plan, repo, service = fixture
    initial = preview(plan, service)
    apply(plan, service, initial)
    approved = initial if mutation == "references" else preview(plan, service)
    pair = plan.pairs[0]
    if mutation == "date":
        repo.data["settlement", pair.settlement_id].settlement_date = date(2026, 1, 3)
    elif mutation == "metadata":
        repo.data["entry", pair.entry_id].metadata_json["later"] = True
    elif mutation == "amount":
        repo.data["row", pair.row_id].amount = Decimal("999.00")
        repo.data["match", pair.match_id].matched_amount = Decimal("999.00")
        for name in ("net_amount", "gross_amount", "principal_amount"):
            setattr(repo.data["settlement", pair.settlement_id], name, Decimal("999.00"))
    before = deepcopy(repo.data)
    with pytest.raises(Conflict, match="State changed"):
        apply(plan, service, approved)
    assert all(vars(value) == vars(before[key]) for key, value in repo.data.items())


@pytest.mark.parametrize("reference", ["reconciliation-match:999", "reconciliation-match:",
                                       "reconciliation-match:malformed", "reconciliation-match:0201"])
def test_target_external_reconciliation_reference_conflicts_without_writes(fixture, reference):
    plan, repo, service = fixture
    repo.data["settlement", plan.pairs[0].settlement_id].external_reference = reference
    before = deepcopy(repo.data)
    with pytest.raises(Conflict, match="External reconciliation reference"):
        preview(plan, service)
    assert all(vars(value) == vars(before[key]) for key, value in repo.data.items())


def test_matching_external_reconciliation_reference_is_preserved(fixture):
    plan, repo, service = fixture
    pair = plan.pairs[0]
    expected = f"reconciliation-match:{pair.match_id}"
    repo.data["settlement", pair.settlement_id].external_reference = expected
    apply(plan, service, preview(plan, service))
    assert repo.data["settlement", pair.settlement_id].external_reference == expected


@pytest.mark.parametrize("kind,field,value", [
    ("match", "company_id", 88), ("match", "financial_entry_id", 999),
    ("match", "match_status", "suggested"), ("settlement", "settlement_status", "cancelled"),
    ("settlement", "bank_account_id", 999), ("settlement", "net_amount", Decimal("999")),
    ("row", "matched_entry_id", 999), ("row", "created_entry_id", 999),
    ("entry", "movement_nature", "credit"), ("row", "import_batch_id", 999),
    ("settlement", "reconciliation_status", "rejected"), ("match", "deleted_at", "deleted"),
    ("entry", "status", "cancelled"),
])
def test_runtime_invariants_fail_without_writes(fixture, kind, field, value):
    plan, repo, service = fixture
    pair = plan.pairs[0]
    identity = getattr(pair, {"match": "match_id", "row": "row_id", "entry": "entry_id", "settlement": "settlement_id"}[kind])
    setattr(repo.data[kind, identity], field, value)
    before = deepcopy(repo.data)
    with pytest.raises(Conflict):
        preview(plan, service)
    assert all(vars(item) == vars(before[key]) for key, item in repo.data.items())


@pytest.mark.parametrize("kind,key,value", [
    ("match", "financial_settlement_id", 999), ("settlement", "import_row_id", 999),
    ("settlement", "reconciliation_match_id", 999), ("settlement", "import_batch_id", 999),
    ("settlement", "bordero_settlement_id", 999), ("match", "reconciliation_cancelled", True),
])
def test_conflicting_metadata_fails(fixture, kind, key, value):
    plan, repo, service = fixture
    pair = plan.pairs[0]
    identity = pair.match_id if kind == "match" else pair.settlement_id
    repo.data[kind, identity].metadata_json[key] = value
    with pytest.raises(Conflict):
        preview(plan, service)


def test_duplicate_confirmed_match_and_other_settlement_link_fail(fixture):
    plan, repo, service = fixture
    other = deepcopy(repo.data["match", plan.pairs[0].match_id])
    other.id = 999
    repo.data["match", 999] = other
    with pytest.raises(Conflict):
        preview(plan, service)
    del repo.data["match", 999]
    other = deepcopy(repo.data["settlement", plan.pairs[0].settlement_id])
    other.id = 999
    other.metadata_json["reconciliation_match_id"] = plan.pairs[0].match_id
    repo.data["settlement", 999] = other
    with pytest.raises(Conflict):
        preview(plan, service)


def test_stale_dry_run_detects_change_at_transaction_start(fixture):
    plan, repo, service = fixture
    approved = preview(plan, service)
    repo.on_begin = lambda: setattr(repo.data["entry", plan.pairs[0].entry_id], "updated_at", "concurrent")
    with pytest.raises(Conflict, match="State changed"):
        apply(plan, service, approved)
    assert repo.data["settlement", plan.pairs[0].settlement_id].reconciliation_status == "pending"


def test_persistence_failure_rolls_back_all_three_pairs(fixture):
    plan, repo, service = fixture
    approved = preview(plan, service)
    before = deepcopy(repo.data)
    repo.fail_flush = True
    with pytest.raises(RuntimeError):
        apply(plan, service, approved)
    assert all(vars(value) == vars(before[key]) for key, value in repo.data.items())


def test_recovery_restores_missing_and_null_keys_and_keeps_audit(fixture):
    plan, repo, service = fixture
    repo.data["match", plan.pairs[0].match_id].metadata_json["financial_settlement_id"] = None
    receipt = apply(plan, service, preview(plan, service))
    assert recover(plan, service, receipt)["recovered"]
    for index, pair in enumerate(plan.pairs):
        match = repo.data["match", pair.match_id]
        settlement = repo.data["settlement", pair.settlement_id]
        if index == 0:
            assert match.metadata_json["financial_settlement_id"] is None
        else:
            assert "financial_settlement_id" not in match.metadata_json
        assert settlement.metadata_json == {"preserved": {"nested": True}}
        assert settlement.reconciliation_status == "pending"
        assert [item["action"] for item in match.metadata_json[MODULE.AUDIT_KEY]] == ["apply", "recover"]


def test_recovery_blocks_concurrent_change_and_forged_receipt(fixture):
    plan, repo, service = fixture
    receipt = apply(plan, service, preview(plan, service))
    forged = deepcopy(receipt)
    forged["changes"][0]["before_fields"]["reconciliation_status"] = "rejected"
    with pytest.raises(Conflict, match="persisted audit"):
        recover(plan, service, forged)
    repo.data["entry", plan.pairs[0].entry_id].updated_at = "concurrent"
    with pytest.raises(Conflict, match="State changed"):
        recover(plan, service, receipt)


def test_recovery_blocks_new_match_dependency(fixture):
    plan, repo, service = fixture
    receipt = apply(plan, service, preview(plan, service))
    other = deepcopy(repo.data["match", plan.pairs[1].match_id])
    other.id, other.import_row_id = 999, 999
    other.metadata_json["financial_settlement_id"] = plan.pairs[0].settlement_id
    repo.data["match", 999] = other
    with pytest.raises(Conflict, match="another active match"):
        recover(plan, service, receipt)


@pytest.mark.parametrize("operation", ["apply", "recover"])
@pytest.mark.parametrize("kind,key,field", [
    ("match", "financial_settlement_id", "settlement_id"),
    ("settlement", "reconciliation_match_id", "match_id"),
    ("settlement", "import_row_id", "row_id"),
])
def test_legacy_string_dependency_blocks_apply_and_recovery(fixture, operation, kind, key, field):
    plan, repo, service = fixture
    approved = preview(plan, service)
    receipt = apply(plan, service, approved) if operation == "recover" else None
    pair = plan.pairs[0]
    identity = pair.match_id if kind == "match" else pair.settlement_id
    other = deepcopy(repo.data[kind, identity])
    other.id = 999
    other.metadata_json = {key: str(getattr(pair, field))}
    if kind == "match":
        other.import_row_id = 999
    repo.data[kind, other.id] = other
    before = deepcopy(repo.data)
    with pytest.raises(Conflict, match="another active match|Another settlement"):
        if operation == "apply":
            apply(plan, service, approved)
        else:
            recover(plan, service, receipt)
    assert all(vars(item) == vars(before[identity]) for identity, item in repo.data.items())


@pytest.mark.parametrize("value", [True, False, 0, -1, 401.0, "malformed", [], {}])
def test_malformed_existing_dependency_fails_closed_without_writes(fixture, value):
    plan, repo, service = fixture
    approved = preview(plan, service)
    other = deepcopy(repo.data["match", plan.pairs[0].match_id])
    other.id, other.import_row_id = 999, 999
    other.metadata_json = {"financial_settlement_id": value}
    repo.data["match", other.id] = other
    before = deepcopy(repo.data)
    with pytest.raises(Conflict, match="Invalid existing reconciliation reference"):
        apply(plan, service, approved)
    assert all(vars(item) == vars(before[identity]) for identity, item in repo.data.items())


def test_scope_and_edit_authority_checked_before_repository_access(fixture):
    plan, repo, service = fixture
    with pytest.raises(Conflict):
        service.dry_run(plan, allowed_company_ids=(88,))
    with pytest.raises(Conflict):
        service.apply(plan, allowed_company_ids=(77,), actor_user_id=55,
                      financial_edit_authorized=False, approved_snapshot={})
    with pytest.raises(Conflict):
        service.apply(plan, allowed_company_ids=(77,), actor_user_id=None,
                      financial_edit_authorized=True, approved_snapshot={})
    assert repo.transactions == []


def test_snapshot_exposes_reviewable_finances_but_hashes_private_metadata(fixture):
    plan, repo, service = fixture
    repo.data["match", plan.pairs[0].match_id].metadata_json["private_fixture_marker"] = "DO-NOT-EMIT"
    snapshot = preview(plan, service)
    assert "DO-NOT-EMIT" not in str(snapshot)
    settled = next(item for item in snapshot["snapshot"] if item["kind"] == "settlement")
    assert settled["identity"]["net_amount"] == "123.45"
    assert settled["identity"]["settlement_date"] == "2026-01-01"
    assert len(settled["fingerprint"]) == 64


def test_invalid_plan_and_changed_plan_are_rejected(fixture):
    plan, repo, service = fixture
    bad_plan = MODULE.RepairPlan(77, 20, 30, "SYNTHETIC-ONLY", (plan.pairs[0], plan.pairs[0]))
    with pytest.raises(Conflict, match="duplicate"):
        preview(bad_plan, service)
    approved = preview(plan, service)
    approved["plan_fingerprint"] = "different"
    with pytest.raises(Conflict, match="Approved plan"):
        apply(plan, service, approved)


def test_failure_during_third_pair_restores_earlier_pair_updates(fixture, monkeypatch):
    plan, repo, service = fixture
    approved = preview(plan, service)
    original_data = deepcopy(repo.data)
    original_before_fields = MODULE._before_fields
    calls = []

    def fail_third(match, settlement):
        calls.append(match.id)
        if len(calls) == 3:
            raise RuntimeError("third synthetic pair failed")
        return original_before_fields(match, settlement)

    monkeypatch.setattr(MODULE, "_before_fields", fail_third)
    with pytest.raises(RuntimeError, match="third synthetic pair"):
        apply(plan, service, approved)
    assert len(calls) == 3
    assert all(vars(value) == vars(original_data[key]) for key, value in repo.data.items())


def test_non_postgres_adapter_rejected_before_imports():
    engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    with pytest.raises(Conflict, match="PostgreSQL"):
        MODULE.PostgresReferenceRepairRepository(engine)


def test_partial_compatible_references_and_nulls_are_completed(fixture):
    plan, repo, service = fixture
    first = plan.pairs[0]
    repo.data["match", first.match_id].metadata_json["financial_settlement_id"] = first.settlement_id
    repo.data["settlement", first.settlement_id].metadata_json["import_row_id"] = first.row_id
    repo.data["settlement", first.settlement_id].metadata_json["import_batch_id"] = None
    receipt = apply(plan, service, preview(plan, service))
    assert receipt["changed"]
    assert repo.data["settlement", first.settlement_id].metadata_json["import_batch_id"] == plan.batch_id


def test_dry_run_checks_code_batch_account_dates_and_amount_of_match(fixture):
    plan, repo, service = fixture
    mutations = [
        (("batch", plan.batch_id), "batch_code", "OTHER"),
        (("batch", plan.batch_id), "metadata_json", {"bank_account_id": 999}),
        (("batch", plan.batch_id), "status", "cancelled"),
        (("settlement", plan.pairs[0].settlement_id), "settlement_date", None),
        (("match", plan.pairs[0].match_id), "matched_amount", Decimal("1")),
    ]
    for key, name, value in mutations:
        original = deepcopy(repo.data)
        setattr(repo.data[key], name, value)
        with pytest.raises(Conflict):
            preview(plan, service)
        repo.data = original


def test_actual_workspace_serializers_show_links_without_increasing_confirmed_count(fixture):
    plan, repo, service = fixture
    source = PATH.with_name("financial_reconciliation_workspace_service.py")
    tree = ast.parse(source.read_text(encoding="utf-8-sig"))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                 and node.name == "FinancialReconciliationWorkspaceService")
    selected = {"_build_row_match_snapshot", "_serialize_system_settlement"}
    functions = [deepcopy(node) for node in owner.body if isinstance(node, ast.FunctionDef) and node.name in selected]
    for function in functions:
        function.decorator_list = []
    parsed = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
                             *functions], type_ignores=[])
    ast.fix_missing_locations(parsed)
    helpers = SimpleNamespace(
        _settlement_reconciliation_amount=lambda settlement: settlement.net_amount,
        _entry_remaining_amount=lambda entry: Decimal("0"),
        _counterparty_name=lambda company, identity: None, _chart_account_label=lambda company, identity: None)
    namespace = {"Decimal": Decimal, "FinancialReconciliationWorkspaceService": helpers,
                 "FinancialService": SimpleNamespace(serialize_entry=lambda entry, **kwargs: {})}
    exec(compile(parsed, str(source), "exec"), namespace)

    def view():
        bank_count, linked, reconciled = 0, 0, 0
        for pair in plan.pairs:
            match = repo.data["match", pair.match_id]
            row_snapshot = namespace["_build_row_match_snapshot"]([SimpleNamespace(to_dict=lambda: vars(match))])
            bank_count += row_snapshot["confirmed_count"]
            assert row_snapshot["match_mode"] == "1:1"
            settlement = repo.data["settlement", pair.settlement_id]
            entry = repo.data["entry", pair.entry_id]
            entry.counterparty_id = entry.chart_account_id = None
            settlement.settlement_code = "SYNTHETIC"
            settlement.notes = "SYNTHETIC"
            ids = [pair.row_id] if match.metadata_json.get("financial_settlement_id") == pair.settlement_id else []
            projected = namespace["_serialize_system_settlement"](settlement, entry, linked_row_ids=ids)
            linked += projected["linked_rows_count"]
            reconciled += projected["is_reconciled"]
            assert projected["match_mode"] == ("1:1" if ids else "unmatched")
        return bank_count, linked, reconciled

    assert view() == (3, 0, 0)
    apply(plan, service, preview(plan, service))
    assert view() == (3, 3, 3)


@pytest.mark.parametrize("write", [False, True])
def test_postgres_get_scopes_identity_and_locks_target_rows_only_for_writes(write):
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Query, declarative_base

    base = declarative_base()

    class Account(base):
        __tablename__ = "synthetic_accounts"
        id = sa.Column(sa.Integer, primary_key=True)
        company_id = sa.Column(sa.Integer, nullable=False)
        deleted_at = sa.Column(sa.DateTime)

    statements = []
    record = SimpleNamespace(id=20, company_id=77, deleted_at=None)

    class CapturedQuery:
        def __init__(self):
            self.query = Query(Account)

        def filter(self, *conditions):
            self.query = self.query.filter(*conditions)
            return self

        def with_for_update(self, **options):
            self.query = self.query.with_for_update(**options)
            return self

        def one_or_none(self):
            statements.append(str(self.query.statement.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})))
            return record

    repository = object.__new__(MODULE.PostgresReferenceRepairRepository)
    repository.models = {"account": Account}
    repository.session = SimpleNamespace(query=lambda model: CapturedQuery())
    repository.write_transaction = write
    assert repository.get("account", 20, 77) is record
    assert "id = 20" in statements[0] and "company_id = 77" in statements[0]
    assert "deleted_at IS NULL" in statements[0]
    assert ("FOR UPDATE NOWAIT" in statements[0]) is write


def test_postgres_adapter_transaction_contract_with_doubles_only(monkeypatch):
    from types import ModuleType

    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            calls.append("close")

        @contextmanager
        def begin(self):
            calls.append("begin")
            try:
                yield
            except Exception:
                calls.append("rollback")
                raise
            calls.append("commit")

        def execute(self, statement):
            calls.append(str(statement))

    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy.text = lambda statement: statement
    orm = ModuleType("sqlalchemy.orm")
    orm.sessionmaker = lambda **kwargs: Session
    models = ModuleType("models.financial")
    for name in ("FinancialBankAccount", "FinancialEntry", "FinancialImportBatch", "FinancialImportRow",
                 "FinancialReconciliationMatch", "FinancialSettlement"):
        setattr(models, name, object)
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)
    monkeypatch.setitem(sys.modules, "sqlalchemy.orm", orm)
    monkeypatch.setitem(sys.modules, "models.financial", models)
    repo = MODULE.PostgresReferenceRepairRepository(SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))
    with repo.transaction(write=False):
        assert "REPEATABLE READ READ ONLY" in calls[-1]
        assert repo.write_transaction is False
    with pytest.raises(RuntimeError):
        with repo.transaction(write=True):
            assert "SHARE ROW EXCLUSIVE MODE NOWAIT" in calls[-1]
            assert repo.write_transaction is True
            raise RuntimeError("synthetic failure")
    assert "rollback" in calls and repo.session is None and repo.write_transaction is False
    with repo.transaction(write=True):
        with pytest.raises(Conflict, match="Nested"):
            with repo.transaction(write=True):
                pass
    assert calls.count("commit") == 2
