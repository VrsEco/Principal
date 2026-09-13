from pathlib import Path


def test_portfolio_list_batches_tenant_scoped_project_counts():
    root = Path(__file__).resolve().parents[1]
    source = (root / "api" / "routes" / "portfolios.py").read_text(encoding="utf-8")

    assert "Project.company_id == company_id" in source
    assert ".group_by(Project.portfolio_id)" in source
    assert ".outerjoin(project_counts" in source
    assert "joinedload(Portfolio.responsible)" in source
    assert "portfolio.to_dict()" in source
    assert "to_dict(include_project_count=True) for p in portfolios" not in source


def test_meetings_workspace_avoids_project_and_task_stats_n_plus_one():
    root = Path(__file__).resolve().parents[1]
    source = (root / "api" / "routes" / "meetings.py").read_text(encoding="utf-8")

    assert "joinedload(Meeting.project)" in source
    assert '"id": project.id, "name": project.name, "code": project.code' in source
    assert "projects_data = [p.to_dict() for p in projects]" not in source


def test_p5_indexes_match_tenant_scoped_workspace_queries():
    root = Path(__file__).resolve().parents[1]
    project_model = (root / "models" / "project.py").read_text(encoding="utf-8")
    meeting_model = (root / "models" / "meeting.py").read_text(encoding="utf-8")
    migration = (
        root / "migrations" / "versions" / "20260913_1100_add_workspace_query_indexes.py"
    ).read_text(encoding="utf-8")

    for name in ("ix_projects_company_portfolio_id", "ix_meetings_company_created_at"):
        assert name in migration
    assert "ix_projects_company_portfolio_id" in project_model
    assert "ix_meetings_company_created_at" in meeting_model
    assert 'down_revision = "20260913_1000"' in migration
