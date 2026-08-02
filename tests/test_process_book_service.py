from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app32"

for path in (ROOT_DIR, APP_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app32.services.process_book_service import (
    _format_schedule_detail,
    _format_schedule_summary,
)
from app32.services.process_bpmn_service import colorize_bpmn_artifact_svg


def test_format_schedule_detail_specific_date_inverts_iso():
    assert _format_schedule_detail("specific", "2026-05-27", "08:30") == "27/05/2026 às 08:30"


def test_format_schedule_summary_weekly_with_days_and_time():
    assert _format_schedule_summary("weekly", "monday,wednesday", "07:15") == "Semanal · Segunda, Quarta às 07:15"


def test_format_schedule_summary_daily_keeps_time():
    assert _format_schedule_summary("daily", None, "06:00") == "Diária · 06:00"


def test_process_book_cover_omits_obsolete_summary_cards():
    service_source = (APP_DIR / "services" / "process_book_service.py").read_text(encoding="utf-8")
    template_source = (APP_DIR / "templates" / "reports" / "process_book_v2.html").read_text(encoding="utf-8")

    assert '"structuring_label"' not in service_source
    assert '"performance_label"' not in service_source
    assert '"stats"' not in service_source
    assert "first_page.structuring_label" not in template_source
    assert "first_page.performance_label" not in template_source
    assert "first_page.stats" not in template_source


def test_book_snapshot_receives_canonical_artifact_colors_from_bpmn_xml():
    bpmn_xml = """<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
      <bpmn:process id="Process_1">
        <bpmn:dataObjectReference id="Artifact_Check" name="[CHECK]" />
        <bpmn:dataObjectReference id="Artifact_Form" name="[FORM] Cadastro" />
        <bpmn:dataObjectReference id="Artifact_In" name="[DADOS IN]" />
      </bpmn:process>
    </bpmn:definitions>"""
    svg = """<svg xmlns="http://www.w3.org/2000/svg">
      <g class="djs-element" data-element-id="Artifact_Check"><g class="djs-visual"><path style="fill:white;stroke:black" /></g></g>
      <g class="djs-label" data-element-id="Artifact_Check_label"><text>[CHECK]</text></g>
      <g class="djs-element" data-element-id="Artifact_Form"><g class="djs-visual"><path /></g></g>
      <g class="djs-element" data-element-id="Artifact_In"><g class="djs-visual"><path /></g></g>
    </svg>"""

    result = colorize_bpmn_artifact_svg(svg, bpmn_xml)

    assert 'id="app32-artifact-colors"' in result
    assert "app32-artifact-check" in result
    assert "app32-artifact-form" in result
    assert "app32-artifact-data-in" in result
    assert "fill:#ecfdf5!important;stroke:#059669!important" in result
    assert "fill:#f5f3ff!important;stroke:#7c3aed!important" in result
    assert "fill:#ecfeff!important;stroke:#0891b2!important" in result


def test_book_artifact_colorizer_keeps_svg_safe_and_tolerates_invalid_xml():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><g data-element-id="A" /></svg>'

    result = colorize_bpmn_artifact_svg(svg, "<invalid")

    assert "<script" not in result
    assert "app32-artifact-colors" not in result
