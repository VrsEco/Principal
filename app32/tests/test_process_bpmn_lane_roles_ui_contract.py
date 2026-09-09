from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bpmn_modeler_exposes_process_scoped_role_selector_for_lanes():
    template = (ROOT / "templates/modules/processes/bpmn_modeler.html").read_text(encoding="utf-8")
    script = (ROOT / "static/js/process_bpmn_modeler.js").read_text(encoding="utf-8")
    app_source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert 'id="bpmnLaneRoleDialog"' in template
    assert 'id="bpmnLaneRoleSelect"' in template
    assert 'data-lane-role-save' in template
    assert 'data-action="lane-role"' in template
    assert "function openLaneRoleDialog(lane)" in script
    assert "lane_role_bindings: Object.fromEntries(laneRoleBindings)" in script
    assert "/api/processes/${processId}/bpmn-lane-roles" in script
    assert "'bpmn:Lane'" in script
    assert "ProcessBpmnLaneRoleCatalogResource" in app_source
    assert "'/api/processes/<int:process_id>/bpmn-lane-roles'" in app_source
