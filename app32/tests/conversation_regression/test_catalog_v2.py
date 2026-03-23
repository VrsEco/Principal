import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from .reporting import build_catalog_report
from .runner import load_catalog


def test_catalog_v2_gera_relatorio_consolidado_por_capitulo():
    report = build_catalog_report(load_catalog())

    assert report["total_chapters"] == 4
    assert report["total_cases"] >= 13
    assert report["chapters"]["a_consultar"]["types"]["parsing"] >= 3
    assert report["chapters"]["a_consultar"]["failure_classes"]["parsing"] >= 3
    assert report["chapters"]["b_cadastrar_iniciar"]["types"]["multiturn"] >= 1
    assert report["chapters"]["b_cadastrar_iniciar"]["failure_classes"]["multi_turn"] >= 1
    assert report["chapters"]["c_encerrar"]["types"]["routing"] >= 2
    assert report["chapters"]["d_analisar"]["types"]["parsing"] >= 2
