from __future__ import annotations

from dataclasses import dataclass, asdict
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.sql.sqltypes import String, Text, Unicode, UnicodeText


@dataclass(frozen=True)
class ResidueHit:
    table: str
    column: str
    marker: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def scan_marker_residue(*, company_id: int, markers: list[str]) -> list[ResidueHit]:
    """Procura resíduos textuais de massa E2E em tabelas tenant-safe.

    A varredura é conservadora: só avalia tabelas com coluna `company_id` e
    colunas textuais, usando `LIKE` parametrizado. Isso evita tenant crossing e
    permite validar cleanup sem depender de cada model específico.
    """
    if not markers:
        return []
    if not company_id:
        raise ValueError("company_id obrigatório para auditoria de resíduos E2E.")

    for candidate in (Path.cwd(), Path.cwd() / "app32"):
        candidate_text = str(candidate)
        if candidate.exists() and candidate_text not in sys.path:
            sys.path.insert(0, candidate_text)

    try:
        from app import create_app
        from models import db
    except ModuleNotFoundError:
        from app32.app import create_app
        from app32.models import db

    config_name = "development" if str(os.environ.get("E2E_ENV_NAME") or "").upper() == "DEV_FULL" else "production"
    app = create_app(config_name)
    hits: list[ResidueHit] = []
    with app.app_context():
        bind = db.session.get_bind()
        inspector = inspect(bind)
        preparer = bind.dialect.identifier_preparer
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            column_names = {column["name"] for column in columns}
            if "company_id" not in column_names:
                continue
            text_columns = [
                column["name"]
                for column in columns
                if isinstance(column.get("type"), (String, Text, Unicode, UnicodeText))
            ]
            if not text_columns:
                continue
            quoted_table = preparer.quote(table_name)
            for column_name in text_columns:
                quoted_column = preparer.quote(column_name)
                for marker in markers:
                    stmt = text(
                        f"SELECT COUNT(*) FROM {quoted_table} "
                        f"WHERE company_id = :company_id AND {quoted_column} LIKE :marker"
                    )
                    count = int(
                        db.session.execute(
                            stmt,
                            {"company_id": company_id, "marker": f"%{marker}%"},
                        ).scalar()
                        or 0
                    )
                    if count:
                        hits.append(ResidueHit(table=table_name, column=column_name, marker=marker, count=count))
    return hits
