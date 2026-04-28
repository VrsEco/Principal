import hashlib
import os
import sys


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
