"""Agenda, Fase 3: blocos da pessoa (validacao, avisos de sobreposicao, escopo por usuario, auditoria)."""
from __future__ import annotations

import json
import os
import sys
from datetime import time
from types import SimpleNamespace

import pytest
from flask import Flask

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import PersonWorkBlock, UserLog, db
from services import person_work_block_service as svc
from services.person_work_block_service import PersonBlockError, overlap_warnings, union_minutes, validate_payload


@pytest.fixture()
def ctx(monkeypatch):
    import itertools

    import models.user_log as user_log_module

    counter = itertools.count(1)
    # O UserLog reserva o id pela sequência do PostgreSQL; no SQLite do teste usamos um contador.
    monkeypatch.setattr(user_log_module, "_allocate_user_log_id", lambda connection: next(counter))
    app = Flask(__name__)
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite://", SQLALCHEMY_TRACK_MODIFICATIONS=False, TESTING=True)
    db.init_app(app)
    with app.app_context():
        db.metadata.create_all(bind=db.engine, tables=[PersonWorkBlock.__table__, UserLog.__table__])
        yield app


def _p(**kw):
    base = {"name": "Foco", "start": "08:00", "end": "10:00", "mode": "operational", "weekdays": [0, 1, 2]}
    base.update(kw)
    return base


def test_validacao_dos_campos():
    ok = validate_payload(_p(weekdays=[2, 0, 0], preferred_item_types=["project_task", "xx"]))
    assert ok["weekdays_json"] == [0, 2] and ok["preferred_item_types"] == ["project_task"]
    assert ok["start_time"] == time(8, 0) and ok["block_mode"] == "operational"
    for bad in (
        _p(name=" "), _p(name="x" * 161), _p(start="25:00"), _p(end="08:00"), _p(start="10:00", end="09:00"),
        _p(mode="outro"), _p(weekdays=[]), _p(weekdays=[7]), _p(weekdays=["a"]), _p(start=None),
    ):
        with pytest.raises(PersonBlockError):
            validate_payload(bad)


def test_uniao_de_intervalos_nao_conta_hora_duas_vezes():
    assert union_minutes([(480, 600), (540, 660)]) == 180  # 8-10 e 9-11 = 3 h
    assert union_minutes([(480, 600), (600, 660)]) == 180  # encostados
    assert union_minutes([(480, 540), (600, 660)]) == 120  # separados
    assert union_minutes([(480, 720), (500, 520)]) == 240  # contido
    assert union_minutes([]) == 0 and union_minutes([(10, 10)]) == 0


def _blk(i, start, end, days, active=True):
    return SimpleNamespace(id=i, name=f"B{i}", start_time=time(*start), end_time=time(*end), weekdays_json=days, is_active=active)


def test_avisos_de_sobreposicao_so_avisam():
    blocks = [_blk(1, (8, 0), (10, 0), [0, 1]), _blk(2, (9, 0), (11, 0), [1, 2]), _blk(3, (10, 0), (12, 0), [1]),
              _blk(4, (9, 0), (10, 0), [0, 1], active=False)]
    warns = overlap_warnings(blocks)
    pairs = {(w["a"]["id"], w["b"]["id"]) for w in warns}
    assert pairs == {(1, 2), (2, 3)}  # 1 e 3 só encostam; o inativo não conta
    assert warns[0]["weekdays"] == [1]


def test_crud_isolado_por_usuario_com_auditoria(ctx):
    created = svc.create_block(1, _p())
    block_id = created["block"]["id"]
    with pytest.raises(PersonBlockError):
        svc.update_block(2, block_id, _p(name="Invasão"))  # outro usuário não enxerga
    with pytest.raises(PersonBlockError):
        svc.delete_block(2, block_id)
    assert svc.list_blocks(2)["blocks"] == []

    svc.update_block(1, block_id, {"name": "Foco profundo", "end": "11:00"})
    block = PersonWorkBlock.query.get(block_id)
    assert block.name == "Foco profundo" and block.end_time == time(11, 0) and block.start_time == time(8, 0)

    svc.delete_block(1, block_id)
    assert PersonWorkBlock.query.count() == 0
    logs = UserLog.query.filter_by(entity_type="person_work_block").order_by(UserLog.id).all()
    assert [l.action for l in logs] == ["create", "update", "delete"]
    update = logs[1]
    assert json.loads(update.old_values)["name"] == "Foco" and json.loads(update.new_values)["name"] == "Foco profundo"


def test_sobreposicao_gera_aviso_e_nao_impede(ctx):
    svc.create_block(1, _p(name="A", start="08:00", end="10:00"))
    result = svc.create_block(1, _p(name="B", start="09:00", end="11:00"))
    assert result["block"]["id"] and len(result["warnings"]) == 1
    assert len(svc.list_blocks(1)["blocks"]) == 2


def test_reordenar_e_reverter(ctx):
    ids = [svc.create_block(1, _p(name=n))["block"]["id"] for n in ("A", "B", "C")]
    out = svc.reorder_blocks(1, list(reversed(ids)))
    assert [b["name"] for b in out["blocks"]] == ["C", "B", "A"]
    with pytest.raises(PersonBlockError):
        svc.reorder_blocks(1, ids[:2])  # faltam blocos
    assert svc.has_blocks(1) and not svc.has_blocks(2) and not svc.has_blocks(None)
    assert svc.delete_all_blocks(1) == {"removed": 3}
    assert not svc.has_blocks(1)


def test_limite_de_blocos(ctx, monkeypatch):
    monkeypatch.setattr(svc, "MAX_BLOCKS_PER_USER", 2)
    svc.create_block(1, _p(name="A"))
    svc.create_block(1, _p(name="B"))
    with pytest.raises(PersonBlockError, match="Limite"):
        svc.create_block(1, _p(name="C"))
