import os
import sys

from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.storage import _query_upload_owner_company_ids, build_upload_file_response


def _build_app(tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    return app


def test_build_upload_file_response_serves_local_file(tmp_path):
    app = _build_app(tmp_path)
    target = tmp_path / "pop" / "imagem.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"local-image")

    with app.test_request_context():
        response = build_upload_file_response("pop/imagem.png")

    assert response.status_code == 200
    response.direct_passthrough = False
    assert response.get_data() == b"local-image"


def test_build_upload_file_response_falls_back_to_gcs(monkeypatch, tmp_path):
    app = _build_app(tmp_path)

    monkeypatch.setattr("utils.storage.get_gcs_config", lambda: "bucket-test")
    monkeypatch.setattr(
        "utils.storage.download_from_gcs",
        lambda path: {"bytes": b"gcs-image", "content_type": "image/png"} if path == "pop/imagem.png" else None,
    )

    with app.test_request_context():
        response = build_upload_file_response("pop/imagem.png")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    response.direct_passthrough = False
    assert response.get_data() == b"gcs-image"


def test_query_upload_owner_company_ids_includes_financial_automation_documents(monkeypatch):
    captured = {}

    class _Result:
        @staticmethod
        def scalars():
            return [10]

    def _fake_execute(query, params):
        captured["sql"] = str(query)
        captured["params"] = params
        return _Result()

    monkeypatch.setattr("utils.storage.db.session.execute", _fake_execute)

    company_ids = _query_upload_owner_company_ids("financial/automation/10/derived/arquivo_preview.webp")

    assert company_ids == {10}
    assert "financial_automation_documents" in captured["sql"]
