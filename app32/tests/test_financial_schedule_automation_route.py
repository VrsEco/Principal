from pathlib import Path


def test_financial_schedule_automation_route_exists():
    source = Path(r"C:\GestaoVersus\app32\app32\api\routes\financial.py").read_text(encoding="utf-8")

    assert '@financial_bp.route("/financial/schedules/<int:schedule_id>/automations", methods=["POST"])' in source
    assert "FinancialLocalAutomationService.create_schedule_automation" in source
