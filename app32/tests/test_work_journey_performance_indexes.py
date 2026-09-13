from pathlib import Path


def test_work_journey_query_indexes_cover_recurring_tenant_filters():
    root = Path(__file__).resolve().parents[1]
    model = (root / 'models' / 'work_journey.py').read_text(encoding='utf-8')
    migration = (root / 'migrations' / 'versions' / '20260913_1000_add_work_journey_query_indexes.py').read_text(encoding='utf-8')

    expected = (
        'ix_work_journey_blocks_company_employee_active',
        'ix_work_journey_rules_company_employee_active',
        'ix_work_journey_items_company_employee_due',
        'ix_work_journey_items_company_employee_occurrence',
    )
    for name in expected:
        assert name in model
        assert name in migration
    assert 'down_revision = "20260912_1700"' in migration
