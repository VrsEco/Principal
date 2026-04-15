from pathlib import Path


def test_operations_audit_ui_declares_expected_contracts():
    template = Path("templates/modules/operations/audit.html").read_text(encoding="utf-8")
    script = Path("static/js/operations_audit.js").read_text(encoding="utf-8")
    css = Path("static/css/operations_audit.css").read_text(encoding="utf-8")

    assert "data-company-id" in template
    assert "opsAuditSource" in template
    assert "opsAuditEventsList" in template
    assert "opsAuditApprovalsList" in template
    assert "/api/operations/audit" in script
    assert "ai_mcp_runtime" in script
    assert "human_review" in script
    assert "sapiens_workflow" in script
    assert "agent_action" in script
    assert ".ops-audit-page" in css
    assert ".ops-audit-summary-grid" in css
