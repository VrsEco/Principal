from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_guidance_questions_do_not_fall_through_to_operational_workflows():
    script = (ROOT / "static" / "js" / "sapiens_knowledge.js").read_text(encoding="utf-8")

    assert "looksLikeGuidanceQuestion(question)" in script
    assert "activeScope === 'product' || looksLikeGuidanceQuestion(question)" in script


def test_product_scope_includes_curated_manual_and_system_documentation():
    source = (ROOT / "services" / "knowledge" / "interaction_service.py").read_text(
        encoding="utf-8"
    )

    assert 'PRODUCT_SOURCE_TYPES = ("product_help", "system_documentation")' in source
