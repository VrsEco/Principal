from services.block_signal_service import compute_block_signals, fmt_minutes, signal_for


def _b(bid, start, end, mode="operational", name=None):
    return {"id": bid, "name": name or f"B{bid}", "mode": mode, "start_minutes": start, "end_minutes": end}


def test_spec_example_8_1_acima_e_livre():
    blocks = [_b(1, 7 * 60 + 30, 10 * 60), _b(2, 10 * 60, 12 * 60)]
    items = [{"block_id": 2, "estimated_minutes": 120}]
    events = [{"start_minutes": 10 * 60, "duration_minutes": 90}]
    out = compute_block_signals(blocks, items, events)
    first, second = out["blocks"]
    assert first["signal"] == {"state": "free", "minutes": 150, "label": "Livre 2h30"}
    assert second["signal"]["state"] == "over"
    assert second["signal"]["label"] == "Acima 1h30"


def test_spec_example_8_1_mover_deixa_os_dois_livres_30min():
    blocks = [_b(1, 7 * 60 + 30, 10 * 60), _b(2, 10 * 60, 12 * 60)]
    items = [{"block_id": 1, "estimated_minutes": 120}]
    events = [{"start_minutes": 10 * 60, "duration_minutes": 90}]
    out = compute_block_signals(blocks, items, events)
    assert [b["signal"]["label"] for b in out["blocks"]] == ["Livre 30min", "Livre 30min"]


def test_limites_exatos():
    assert signal_for(120, 90)["state"] == "free"  # exatamente 30 min livres
    assert signal_for(120, 91)["state"] == "full"  # 29 min livres
    assert signal_for(120, 120)["label"] == "Completo"  # consumo igual a capacidade
    assert signal_for(120, 121)["label"] == "Acima 1min"
    assert signal_for(120, 90, idle_threshold=45)["state"] == "full"


def test_concluidos_nao_consomem_e_sem_estimativa_fica_fora():
    blocks = [_b(1, 480, 600)]
    items = [
        {"block_id": 1, "estimated_minutes": 60, "completed": True},
        {"block_id": 1, "estimated_minutes": 0},
        {"block_id": 1, "estimated_minutes": None},
        {"block_id": None, "estimated_minutes": 0},
        {"block_id": 1, "estimated_minutes": 30},
    ]
    out = compute_block_signals(blocks, items, [])
    block = out["blocks"][0]
    assert block["consumed_minutes"] == 30
    assert block["without_estimate"] == 2
    assert block["item_count"] == 3
    assert out["unassigned_without_estimate"] == 1


def test_evento_que_cruza_dois_blocos_conta_so_no_que_comeca():
    blocks = [_b(1, 480, 600), _b(2, 600, 720)]
    out = compute_block_signals(blocks, [], [{"start_minutes": 570, "duration_minutes": 90}])
    assert out["blocks"][0]["consumed_minutes"] == 90
    assert out["blocks"][1]["consumed_minutes"] == 0


def test_evento_fora_de_qualquer_bloco_nao_consome():
    out = compute_block_signals([_b(1, 480, 600)], [], [{"start_minutes": 700, "duration_minutes": 60}])
    assert out["blocks"][0]["consumed_minutes"] == 0


def test_bloco_reservado_e_buffer_nao_recebem_sinal_nem_capacidade():
    blocks = [_b(1, 480, 600), _b(2, 600, 660, mode="reserved_full"), _b(3, 660, 720, mode="buffer")]
    out = compute_block_signals(blocks, [{"block_id": 2, "estimated_minutes": 30}], [])
    assert out["blocks"][1]["signal"]["state"] == "none"
    assert out["blocks"][2]["signal"]["state"] == "none"
    assert out["day"]["capacity_minutes"] == 120


def test_dia_sem_bloco_operacional_mostra_sem_expediente():
    out = compute_block_signals([], [], [])
    assert out["day"]["label"] == "Sem expediente"
    out = compute_block_signals([_b(1, 480, 600, mode="buffer")], [], [])
    assert out["day"]["label"] == "Sem expediente"


def test_nunca_bloqueia_mesmo_muito_acima():
    out = compute_block_signals([_b(1, 480, 540)], [{"block_id": 1, "estimated_minutes": 600}], [])
    assert out["blocks"][0]["signal"]["state"] == "over"
    assert out["day"]["state"] == "over"


def test_fmt_minutes():
    assert [fmt_minutes(m) for m in (0, 30, 60, 90, 150)] == ["0min", "30min", "1h", "1h30", "2h30"]
