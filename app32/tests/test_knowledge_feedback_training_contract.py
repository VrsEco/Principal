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
