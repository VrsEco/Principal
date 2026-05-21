def test_company_collaborator_modal_binds_weekly_hours_to_real_payload():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "templates/modules/companies/company_form_v2.html").read_text(encoding="utf-8")

    assert 'id="emp-weekly-hours"' in source
    assert 'placeholder="40:00"' in source
    assert "window.App32InputFormatters.formatValueByType('hours-decimal', emp.weekly_hours ?? '')" in source
    assert "weekly_hours: weeklyHoursValue === ''" in source
    assert "window.App32InputFormatters.normalizeForSubmit(weeklyHoursInput)" in source
    assert "document.getElementById('emp-weekly-hours').value = ''" in source
