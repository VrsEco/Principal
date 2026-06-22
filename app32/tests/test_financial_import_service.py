import hashlib
import os
import sys
from decimal import Decimal


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_import_service as import_module
import services.financial_catalog_service as catalog_module
from services.financial_import_service import FinancialImportService


def test_create_import_batch_computes_file_hash_without_duplicate_keyword(monkeypatch):
    file_bytes = b"historico,valor\nTarifa,10.00\n"
    captured = {}

    class _FakeBatch:
        def __init__(self, **kwargs):
            captured["batch_kwargs"] = kwargs
            self.id = 91
            self.total_rows = 0
            self.valid_rows = 0
            self.error_rows = 0
            self.finished_at = None
            for key, value in kwargs.items():
                setattr(self, key, value)

        def to_dict(self):
            return {
                "id": self.id,
                "company_id": self.company_id,
                "batch_code": self.batch_code,
                "source_type": self.source_type,
                "file_hash": self.file_hash,
                "total_rows": self.total_rows,
                "valid_rows": self.valid_rows,
                "error_rows": self.error_rows,
            }

    class _FakeSession:
        def add(self, obj):
            captured.setdefault("added", []).append(obj)

        def flush(self):
            captured["flushed"] = True

        def commit(self):
            captured["committed"] = True

        def rollback(self):
            captured["rolled_back"] = True

    monkeypatch.setattr(import_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(import_module.FinancialImportService, "_parse_source_rows", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        import_module.FinancialImportService,
        "get_import_batch_deletion_status",
        lambda batch: {"can_delete": True, "confirmed_matches": 0, "created_entries": 0, "blocked_reasons": []},
    )
    monkeypatch.setattr(import_module, "FinancialImportBatch", _FakeBatch)
    monkeypatch.setattr(import_module.db, "session", _FakeSession())

    result, error = FinancialImportService.create_import_batch(
        payload={
            "company_id": 1,
            "batch_code": "REC-TEST-FILEHASH",
            "source_type": "csv",
            "file_name": "extrato.csv",
            "file_hash": "hash-informado-deve-ser-substituido",
            "metadata_json": {"bank_account_id": 7},
        },
        file_bytes=file_bytes,
        allowed_company_ids=[1],
    )

    assert error is None
    assert result["batch"]["file_hash"] == hashlib.sha256(file_bytes).hexdigest()
    assert captured["batch_kwargs"]["file_hash"] == hashlib.sha256(file_bytes).hexdigest()
    assert captured["batch_kwargs"]["status"] == "parsed"
    assert captured["committed"] is True
    assert "rolled_back" not in captured


def test_normalize_row_sanitizes_none_key_in_raw_payload():
    row = FinancialImportService._normalize_row(
        1,
        {
            "historico": "Fornecedor XPTO",
            "valor": "1500,75",
            None: ["coluna-extra", "coluna-extra-2"],
        },
    )

    assert row.raw_payload["__extra_columns__"] == ["coluna-extra", "coluna-extra-2"]
    assert None not in row.raw_payload
    assert row.description == "Fornecedor XPTO"
    assert row.amount == Decimal("1500.75")


def test_parse_csv_bytes_maps_extra_columns_to_string_key():
    rows = FinancialImportService._parse_csv_bytes(b"historico,valor\nFornecedor XPTO,1500,EXTRA\n")

    assert rows == [
        {
            "historico": "Fornecedor XPTO",
            "valor": "1500",
            "__extra_columns__": ["EXTRA"],
        }
    ]


def test_resolve_bank_account_by_code_accepts_numeric_code_without_leading_zeroes(monkeypatch):
    class _Column:
        def __eq__(self, other):
            return ("eq", other)

        def is_(self, other):
            return ("is", other)

    class _FakeAccountQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

        def all(self):
            return [
                type("Account", (), {"id": 3, "code": "003"})(),
                type("Account", (), {"id": 8, "code": "008"})(),
            ]

    class _FakeAccountModel:
        id = _Column()
        company_id = _Column()
        code = _Column()
        deleted_at = _Column()
        query = _FakeAccountQuery()

    monkeypatch.setattr(import_module, "FinancialBankAccount", _FakeAccountModel)

    assert FinancialImportService._resolve_bank_account_id_by_code(1, 8) == 8
    assert FinancialImportService._resolve_bank_account_id_by_code(1, "008") == 8


def test_enrich_reference_payload_does_not_guess_bank_account_when_explicit_code_is_unresolved(monkeypatch):
    class _ForbiddenQuery:
        def filter(self, *args, **kwargs):
            raise AssertionError("não deve consultar sugestão por texto quando há conta_bancaria explícita")

    class _FakeBankAccountModel:
        query = _ForbiddenQuery()

    monkeypatch.setattr(catalog_module, "FinancialBankAccount", _FakeBankAccountModel)

    enriched = catalog_module.FinancialCatalogService.enrich_reference_payload(
        company_id=1,
        payload={"bank_account_code": "008", "counterparty_id": 99},
        description_text="Histórico contém 003 por outro motivo",
        bank_reference="003",
    )

    assert enriched["bank_account_code"] == "008"
    assert "bank_account_id" not in enriched


def test_create_import_batch_blocks_upload_when_ofx_account_does_not_match(monkeypatch):
    monkeypatch.setattr(import_module.FinancialService, "_ensure_company_scope", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        import_module.FinancialImportService,
        "_parse_source_rows",
        lambda *args, **kwargs: [{"date": "20260612", "amount": "100.00", "memo": "Teste"}],
    )

    class _FakeAccountQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return type(
                "Account",
                (),
                {
                    "id": 7,
                    "company_id": 1,
                    "bank_code": "341",
                    "branch_number": "1234",
                    "account_number": "99999",
                    "account_digit": "0",
                },
            )()

    class _FakeAccountModel:
        id = type("C", (), {"__eq__": lambda self, other: ("eq", other)})()
        company_id = type("C", (), {"__eq__": lambda self, other: ("eq", other)})()
        deleted_at = type("C", (), {"is_": lambda self, other: ("is", other)})()
        query = _FakeAccountQuery()

    monkeypatch.setattr(import_module, "FinancialBankAccount", _FakeAccountModel)

    result, error = FinancialImportService.create_import_batch(
        payload={
            "company_id": 1,
            "batch_code": "REC-OFX-001",
            "source_type": "ofx",
            "file_name": "extrato.ofx",
            "metadata_json": {"bank_account_id": 7},
        },
        file_bytes=b"<OFX><BANKACCTFROM><BANKID>341<BRANCHID>1234<ACCTID>12345-6<ACCTTYPE>CHECKING</BANKACCTFROM></OFX>",
        allowed_company_ids=[1],
    )

    assert result is None
    assert error == "O número da conta identificado no arquivo não corresponde à conta bancária selecionada. Selecione a conta correta antes do upload."
