import hashlib
import os
import sys
from decimal import Decimal


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import services.financial_import_service as import_module
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
