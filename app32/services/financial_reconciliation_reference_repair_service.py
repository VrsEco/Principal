"""Explicit, internal repair of existing reconciliation references; no public surface.

Importing this module never loads the application, environment, models or database.
The caller supplies an authorized repository and an approved dry-run snapshot.
"""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from uuid import uuid4

AUDIT_KEY = "reconciliation_reference_repair_audit"
MATCH_KEYS = ("financial_settlement_id",)
SETTLEMENT_KEYS = ("import_batch_id", "import_row_id", "reconciliation_match_id")


class RepairConflict(ValueError):
    """No repair is committed when identity, snapshot or references conflict."""


@dataclass(frozen=True)
class RepairPair:
    row_id: int
    match_id: int
    entry_id: int
    settlement_id: int


@dataclass(frozen=True)
class RepairPlan:
    company_id: int
    bank_account_id: int
    batch_id: int
    batch_code: str
    pairs: tuple[RepairPair, ...]


# Configuration only. Never automatically applied or used as a default argument.
INTER_REFERENCE_REPAIR_PLAN = RepairPlan(
    9,
    1,
    84,
    "REC-20260918-INTER-CSV-V2",
    (
        RepairPair(9577, 538, 2673, 2752),
        RepairPair(9581, 539, 2615, 2684),
        RepairPair(9584, 540, 2618, 2687),
    ),
)


def _canonical(value):
    if is_dataclass(value):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise RepairConflict("Unsupported snapshot value")


def _hash(value):
    data = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _state(record):
    table = getattr(record, "__table__", None)
    names = (
        [column.name for column in table.columns] if table is not None else vars(record)
    )
    return {name: getattr(record, name) for name in names if not name.startswith("_")}


def _snapshot(records):
    # Values outside this allowlist are hashed, never emitted into the receipt.
    fields = (
        "id",
        "company_id",
        "bank_account_id",
        "financial_entry_id",
        "import_batch_id",
        "import_row_id",
        "matched_entry_id",
        "match_status",
        "settlement_status",
        "reconciliation_status",
        "updated_at",
        "deleted_at",
        "batch_code",
        "movement_nature",
        "amount",
        "matched_amount",
        "original_amount",
        "principal_amount",
        "net_amount",
        "gross_amount",
        "interest_amount",
        "penalty_amount",
        "discount_amount",
        "fee_amount",
        "other_adjustments_amount",
        "occurred_on",
        "matched_date",
        "settlement_date",
        "due_date",
        "competence_date",
    )
    return [
        {
            "kind": kind,
            "id": record.id,
            "fingerprint": _hash(_state(record)),
            "identity": _canonical(
                {
                    name: getattr(record, name)
                    for name in fields
                    if hasattr(record, name)
                }
            ),
        }
        for kind, record in records
    ]


def _before_fields(match, settlement):
    def keys(record, selected):
        metadata = record.metadata_json or {}
        return {
            key: {"present": key in metadata, "value": deepcopy(metadata.get(key))}
            for key in selected
        }

    return {
        "match": keys(match, MATCH_KEYS),
        "settlement": keys(settlement, SETTLEMENT_KEYS),
        "reconciliation_status": settlement.reconciliation_status,
    }


def _restore_metadata(record, fields):
    metadata = deepcopy(record.metadata_json or {})
    for key, previous in fields.items():
        if previous["present"]:
            metadata[key] = previous["value"]
        else:
            metadata.pop(key, None)
    record.metadata_json = metadata


def _existing_reference(metadata, key):
    """Detect legacy numeric-string links without accepting malformed identities."""
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise RepairConflict("Invalid metadata")
    value = metadata.get(key)
    if value is None:
        return None
    if type(value) not in (int, str):
        raise RepairConflict("Invalid existing reconciliation reference")
    try:
        identity = int(value)
    except ValueError as error:
        raise RepairConflict("Invalid existing reconciliation reference") from error
    if identity <= 0:
        raise RepairConflict("Invalid existing reconciliation reference")
    return identity


class FinancialReconciliationReferenceRepairService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _authorize(
        plan, allowed_company_ids, actor_user_id=None, financial_edit_authorized=False
    ):
        ids = (plan.company_id, plan.bank_account_id, plan.batch_id)
        if any(type(value) is not int or value <= 0 for value in ids):
            raise RepairConflict("Invalid tenant, account or batch")
        if plan.company_id not in allowed_company_ids:
            raise RepairConflict("Company outside authorized scope")
        if (
            not isinstance(plan.batch_code, str)
            or not plan.batch_code
            or not 1 <= len(plan.pairs) <= 3
        ):
            raise RepairConflict("An explicit bounded plan is required")
        for field in ("row_id", "match_id", "entry_id", "settlement_id"):
            values = [getattr(pair, field) for pair in plan.pairs]
            if any(type(value) is not int or value <= 0 for value in values) or len(
                set(values)
            ) != len(values):
                raise RepairConflict("Invalid or duplicate repair identities")
        if actor_user_id is not None and (
            type(actor_user_id) is not int or actor_user_id <= 0
        ):
            raise RepairConflict("Invalid authenticated actor")
        if actor_user_id is not None and financial_edit_authorized is not True:
            raise RepairConflict("Financial edit authorization is required")

    def _load(self, plan):
        repo = self.repository
        batch = repo.get("batch", plan.batch_id, plan.company_id)
        account = repo.get("account", plan.bank_account_id, plan.company_id)
        if batch.batch_code != plan.batch_code:
            raise RepairConflict("Batch code changed")
        if getattr(batch, "status", None) == "cancelled":
            raise RepairConflict("Cancelled import batch")
        batch_account = (getattr(batch, "metadata_json", None) or {}).get(
            "bank_account_id"
        )
        if batch_account is not None and (
            type(batch_account) is not int or batch_account != plan.bank_account_id
        ):
            raise RepairConflict("Batch account differs from the plan")
        records = [("batch", batch), ("account", account)]
        loaded = []
        active_matches = repo.active_matches(plan.company_id)
        active_settlements = repo.active_settlements(plan.company_id)
        for pair in plan.pairs:
            row, match, entry, settlement = [
                repo.get(kind, identity, plan.company_id)
                for kind, identity in (
                    ("row", pair.row_id),
                    ("match", pair.match_id),
                    ("entry", pair.entry_id),
                    ("settlement", pair.settlement_id),
                )
            ]
            records.extend(
                zip(
                    ("row", "match", "entry", "settlement"),
                    (row, match, entry, settlement),
                )
            )
            if (
                row.import_batch_id != plan.batch_id
                or match.import_batch_id != plan.batch_id
                or match.import_row_id != row.id
                or match.financial_entry_id != entry.id
                or settlement.financial_entry_id != entry.id
                or row.matched_entry_id != entry.id
                or row.created_entry_id
            ):
                raise RepairConflict("Relationship differs from the approved pair")
            if (
                match.match_status != "confirmed"
                or settlement.settlement_status != "posted"
            ):
                raise RepairConflict("Expected confirmed match and posted settlement")
            if getattr(entry, "status", None) == "cancelled":
                raise RepairConflict("Cancelled financial entry")
            normalized = row.normalized_payload or {}
            if (
                normalized.get("bank_account_id") != plan.bank_account_id
                or settlement.bank_account_id != plan.bank_account_id
            ):
                raise RepairConflict("Bank account differs from the plan")
            if (
                row.movement_nature not in {"credit", "debit"}
                or row.movement_nature != entry.movement_nature
            ):
                raise RepairConflict("Movement nature differs")
            amount = Decimal(str(row.amount))
            comparable = next(
                (
                    Decimal(str(getattr(settlement, name) or 0))
                    for name in ("net_amount", "gross_amount", "principal_amount")
                    if Decimal(str(getattr(settlement, name) or 0)) > 0
                ),
                Decimal("0"),
            )
            if (
                not amount.is_finite()
                or not comparable.is_finite()
                or amount <= 0
                or amount != comparable
            ):
                raise RepairConflict("Bank and settlement amounts must agree exactly")
            if (
                match.matched_amount is None
                or Decimal(str(match.matched_amount)) != amount
            ):
                raise RepairConflict("Confirmed match amount differs")
            if not settlement.settlement_date or not row.occurred_on:
                raise RepairConflict("Missing financial dates")
            if (
                len(
                    [
                        item
                        for item in active_matches
                        if item.import_row_id == row.id
                        and item.match_status == "confirmed"
                    ]
                )
                != 1
            ):
                raise RepairConflict("Bank row has another confirmed match")
            for other in active_matches:
                if (
                    other.id != match.id
                    and other.match_status != "rejected"
                    and (
                        _existing_reference(
                            other.metadata_json, "financial_settlement_id"
                        )
                        == settlement.id
                    )
                ):
                    raise RepairConflict(
                        "Settlement is referenced by another active match"
                    )
            for other in active_settlements:
                if other.id != settlement.id and (
                    _existing_reference(other.metadata_json, "reconciliation_match_id")
                    == match.id
                    or _existing_reference(other.metadata_json, "import_row_id")
                    == row.id
                    or other.external_reference == f"reconciliation-match:{match.id}"
                ):
                    raise RepairConflict(
                        "Another settlement references the row or match"
                    )
            expected = {
                "import_batch_id": plan.batch_id,
                "import_row_id": row.id,
                "reconciliation_match_id": match.id,
            }
            if settlement.import_batch_id not in (None, plan.batch_id):
                raise RepairConflict("Settlement column refers to another batch")
            if settlement.reconciliation_status not in {"pending", "reconciled"}:
                raise RepairConflict("Settlement reconciliation status conflicts")
            for record, wanted in (
                (match, {"financial_settlement_id": settlement.id}),
                (settlement, expected),
            ):
                metadata = record.metadata_json or {}
                if not isinstance(metadata, dict):
                    raise RepairConflict("Invalid metadata")
                for key, value in wanted.items():
                    if (
                        key in metadata
                        and metadata[key] is not None
                        and (type(metadata[key]) is not int or metadata[key] != value)
                    ):
                        raise RepairConflict("Conflicting reconciliation reference")
                if metadata.get("bordero_settlement_id") or metadata.get(
                    "reconciliation_cancelled"
                ):
                    raise RepairConflict(
                        "Bordero or cancelled reconciliation requires separate review"
                    )
            audit = (match.metadata_json or {}).get(AUDIT_KEY, [])
            if not isinstance(audit, list):
                raise RepairConflict("Invalid repair audit history")
            loaded.append((pair, match, settlement, expected))
        return records, loaded

    def dry_run(self, plan, *, allowed_company_ids):
        """Return an approval snapshot without changing financial records."""
        self._authorize(plan, allowed_company_ids)
        with self.repository.transaction(write=False):
            records, loaded = self._load(plan)
            return {
                "plan_fingerprint": _hash(asdict(plan)),
                "snapshot": _snapshot(records),
                "pairs": [asdict(pair) for pair, _, _, _ in loaded],
                "writes": False,
                "proposed": [
                    {
                        "match_id": match.id,
                        "match_metadata": {"financial_settlement_id": settlement.id},
                        "settlement_id": settlement.id,
                        "settlement_metadata": expected,
                        "reconciliation_status": "reconciled",
                    }
                    for _, match, settlement, expected in loaded
                ],
            }

    def apply(
        self,
        plan,
        *,
        allowed_company_ids,
        actor_user_id,
        financial_edit_authorized,
        approved_snapshot,
    ):
        """Complete references atomically, rejecting stale approvals and conflicts."""
        self._authorize(
            plan, allowed_company_ids, actor_user_id, financial_edit_authorized
        )
        if actor_user_id is None:
            raise RepairConflict("An authenticated actor is required")
        with self.repository.transaction(write=True):
            records, loaded = self._load(plan)
            before = _snapshot(records)
            if approved_snapshot.get("plan_fingerprint") != _hash(asdict(plan)):
                raise RepairConflict("Approved plan differs")
            complete = all(
                (match.metadata_json or {}).get("financial_settlement_id")
                == settlement.id
                and all(
                    (settlement.metadata_json or {}).get(key) == value
                    for key, value in expected.items()
                )
                and settlement.reconciliation_status == "reconciled"
                for _, match, settlement, expected in loaded
            )
            if complete:
                return {"changed": False, "after": before}
            if approved_snapshot.get("snapshot") != before:
                raise RepairConflict(
                    "State changed after dry-run; review a new snapshot"
                )
            operation_id = str(uuid4())
            changes = []
            for pair, match, settlement, expected in loaded:
                original = _before_fields(match, settlement)
                audit_event = {
                    "operation_id": operation_id,
                    "action": "apply",
                    "actor_user_id": actor_user_id,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "pair": asdict(pair),
                    "before_fields": original,
                }
                metadata = deepcopy(match.metadata_json or {})
                metadata["financial_settlement_id"] = settlement.id
                metadata[AUDIT_KEY] = [*metadata.get(AUDIT_KEY, []), audit_event]
                match.metadata_json = metadata
                settlement.metadata_json = {
                    **deepcopy(settlement.metadata_json or {}),
                    **expected,
                }
                settlement.reconciliation_status = "reconciled"
                changes.append({"pair": asdict(pair), "before_fields": original})
            self.repository.flush()
            return {
                "changed": True,
                "operation_id": operation_id,
                "plan_fingerprint": _hash(asdict(plan)),
                "before": before,
                "after": _snapshot(records),
                "changes": changes,
            }

    def recover(
        self,
        plan,
        *,
        allowed_company_ids,
        actor_user_id,
        financial_edit_authorized,
        receipt,
    ):
        """Restore only audited reference fields when the post-repair state matches."""
        self._authorize(
            plan, allowed_company_ids, actor_user_id, financial_edit_authorized
        )
        if actor_user_id is None or receipt.get("plan_fingerprint") != _hash(
            asdict(plan)
        ):
            raise RepairConflict("Invalid recovery authority or receipt")
        with self.repository.transaction(write=True):
            records, loaded = self._load(plan)
            if _snapshot(records) != receipt.get("after"):
                raise RepairConflict(
                    "State changed since repair; recovery requires review"
                )
            changes = receipt.get("changes", [])
            if len(changes) != len(loaded):
                raise RepairConflict("Incomplete recovery receipt")
            # Validate all persisted audit evidence before touching any record.
            for change, (pair, match, _, _) in zip(changes, loaded):
                events = (match.metadata_json or {}).get(AUDIT_KEY, [])
                event = next(
                    (
                        item
                        for item in events
                        if item.get("operation_id") == receipt.get("operation_id")
                        and item.get("action") == "apply"
                    ),
                    None,
                )
                if (
                    event is None
                    or change.get("pair") != asdict(pair)
                    or event.get("pair") != asdict(pair)
                    or event.get("before_fields") != change.get("before_fields")
                ):
                    raise RepairConflict(
                        "Recovery receipt differs from persisted audit"
                    )
            for change, (_, match, settlement, _) in zip(changes, loaded):
                original = change["before_fields"]
                _restore_metadata(match, original["match"])
                _restore_metadata(settlement, original["settlement"])
                settlement.reconciliation_status = original["reconciliation_status"]
                metadata = deepcopy(match.metadata_json)
                metadata[AUDIT_KEY].append(
                    {
                        "operation_id": receipt["operation_id"],
                        "action": "recover",
                        "actor_user_id": actor_user_id,
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                match.metadata_json = metadata
            self.repository.flush()
            return {
                "recovered": True,
                "operation_id": receipt["operation_id"],
                "after": _snapshot(records),
            }


class PostgresReferenceRepairRepository:
    """Dedicated transaction; caller supplies an existing authorized PostgreSQL engine.

    Coarse NOWAIT table locks cover legacy writers that do not take advisory locks.
    Never instantiate with an unknown engine or during unit tests.
    """

    def __init__(self, engine):
        if engine.dialect.name != "postgresql":
            raise RepairConflict(
                "An explicitly authorized PostgreSQL engine is required"
            )
        from sqlalchemy.orm import sessionmaker
        from models.financial import (
            FinancialBankAccount,
            FinancialEntry,
            FinancialImportBatch,
            FinancialImportRow,
            FinancialReconciliationMatch,
            FinancialSettlement,
        )

        self.factory = sessionmaker(bind=engine, expire_on_commit=False)
        self.models = dict(
            zip(
                ("account", "entry", "batch", "row", "match", "settlement"),
                (
                    FinancialBankAccount,
                    FinancialEntry,
                    FinancialImportBatch,
                    FinancialImportRow,
                    FinancialReconciliationMatch,
                    FinancialSettlement,
                ),
            )
        )
        self.session = None
        self.write_transaction = False

    @contextmanager
    def transaction(self, *, write):
        """Hold all repair locks until a single commit or a complete rollback."""
        if self.session is not None:
            raise RepairConflict("Nested repair transaction is forbidden")
        from sqlalchemy import text

        with self.factory() as session:
            self.session = session
            self.write_transaction = write
            try:
                with session.begin():
                    if write:
                        session.execute(
                            text(
                                "LOCK TABLE financial_bank_accounts, financial_entries, financial_import_batches, "
                                "financial_import_rows, financial_reconciliation_matches, financial_settlements "
                                "IN SHARE ROW EXCLUSIVE MODE NOWAIT"
                            )
                        )
                    else:
                        session.execute(
                            text(
                                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                            )
                        )
                    yield
            finally:
                self.session = None
                self.write_transaction = False

    def get(self, kind, identity, company_id):
        """Load an active tenant-scoped target, locking its row NOWAIT for writes."""
        model = self.models[kind]
        query = self.session.query(model).filter(
            model.id == identity,
            model.company_id == company_id,
            model.deleted_at.is_(None),
        )
        # ROW SHARE from a pre-existing SELECT FOR UPDATE is compatible with our
        # table locks. Acquire target row locks NOWAIT too, before any mutation.
        if self.write_transaction:
            query = query.with_for_update(nowait=True)
        record = query.one_or_none()
        if record is None:
            raise RepairConflict("Record missing from authorized company")
        return record

    def active_matches(self, company_id):
        """Load same-tenant active matches for dependency checks."""
        model = self.models["match"]
        return (
            self.session.query(model)
            .filter(model.company_id == company_id, model.deleted_at.is_(None))
            .all()
        )

    def active_settlements(self, company_id):
        """Load same-tenant active, non-cancelled settlements for dependency checks."""
        model = self.models["settlement"]
        return (
            self.session.query(model)
            .filter(
                model.company_id == company_id,
                model.deleted_at.is_(None),
                model.settlement_status != "cancelled",
            )
            .all()
        )

    def flush(self):
        """Persist pending ORM changes within the dedicated repair transaction."""
        self.session.flush()
