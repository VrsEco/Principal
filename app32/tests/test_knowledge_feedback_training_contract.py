from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_feedback_service_uses_supervised_simple_rating_and_tenant_guard():
    service = (ROOT / "services" / "knowledge" / "feedback_service.py").read_text(
        encoding="utf-8"
    )

    assert 'VALID_RATINGS = {"correct", "partial", "wrong"}' in service
    assert '"wrong_subject"' in service
    assert '"too_technical"' in service
    assert "same_user" in service
    assert "interaction.company_id is not None" in service
    assert "interaction.company_id != company_id" in service
    assert "and not same_user" in service
    assert "rating_status = normalized_rating" in service


def test_training_robot_creates_reviewable_proposals_without_auto_apply():
    service = (
        ROOT / "services" / "knowledge" / "training_robot_service.py"
    ).read_text(encoding="utf-8")

    assert "NEGATIVE_RATINGS" in service
    assert '"partial"' in service
    assert '"wrong"' in service
    assert "pending_review" in service
    assert '"apply_automatically": False' in service
    assert "KnowledgeTrainingProposal" in service
    assert "_existing_pending" in service


def test_training_review_service_is_tenant_scoped_and_human_reviewed():
    service = (
        ROOT / "services" / "knowledge" / "training_review_service.py"
    ).read_text(encoding="utf-8")

    assert "KnowledgeTrainingReviewService" in service
    assert "company_id: int | None" in service
    assert "KnowledgeInteraction.company_id == int(company_id)" in service
    assert "KnowledgeTrainingProposal," in service
    assert "model.company_id == int(company_id)" in service
    assert 'VALID_DECISIONS = {"approved", "rejected"}' in service
    assert "proposal.status = normalized_decision" in service
    assert '"reviewed_by_user_id"' in service


def test_training_routes_use_session_company_and_never_payload_company_id():
    routes = (ROOT / "api" / "routes" / "agents.py").read_text(encoding="utf-8")
    route_block = routes.split("def sapiens_knowledge_training_overview():", 1)[1].split(
        "@agents_bp.route('/api/agents/diagnostics'", 1
    )[0]

    assert "session.get(\"active_company_id\")" in route_block
    assert "KnowledgeTrainingReviewService" in route_block
    assert "data.get(\"company_id\")" not in route_block
    assert "Sem permissão para curadoria do Sapiens" in route_block
    assert "Sem permissão para treinar o Sapiens" in route_block
    assert "Sem permissão para revisar propostas do Sapiens" in route_block
