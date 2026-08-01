from pathlib import Path

from flask import Flask
from flask_login import LoginManager, UserMixin


ROOT = Path(__file__).resolve().parents[1]


def test_sapiens_page_exposes_simple_knowledge_experience():
    template = (ROOT / "templates" / "sapiens.html").read_text(encoding="utf-8")

    assert 'id="knowledgeExperience"' in template
    assert 'data-scope="company"' in template
    assert 'data-scope="product"' in template
    assert "Como usar o APP Versus" in template
    assert 'id="knowledgeSources"' in template
    assert 'id="knowledgeFeedbackStatus"' in template
    assert 'data-feedback="correct"' in template
    assert 'data-feedback="partial"' in template
    assert 'data-feedback="wrong"' in template
    assert 'id="knowledgeRefinePanel"' in template
    assert "sapiens_knowledge.js" in template
    assert "sapiens_knowledge.css" in template


def test_sapiens_knowledge_client_uses_structured_tenant_safe_endpoint():
    script = (ROOT / "static" / "js" / "sapiens_knowledge.js").read_text(encoding="utf-8")

    assert "/api/agents/knowledge/answer" in script
    assert "company_id" not in script
    assert "source_types" in script
    assert "safeAppTarget" in script
    assert "knowledge_gap" in script
    assert "AbortController" in script
    assert "OPERATIONAL_TIMEOUT_MS" in script
    assert "fetchWithTimeout('/api/agents/chat'" in script
    assert "renderSafeStructuredText" in script
    assert "appendSafeInlineFormatting" in script
    assert "strong.textContent = match[1]" in script
    assert "/api/agents/knowledge/feedback" in script
    assert "interaction_id" in script
    assert "submitFeedback" in script


def test_knowledge_route_never_accepts_company_id_from_payload():
    routes = (ROOT / "api" / "routes" / "agents.py").read_text(encoding="utf-8")
    route_block = routes.split("def answer_sapiens_knowledge():", 1)[1].split(
        "@agents_bp.route('/api/agents/diagnostics'", 1
    )[0]

    assert "session.get(\"active_company_id\")" in route_block
    assert "data.get(\"company_id\")" not in route_block

    feedback_block = routes.split("def register_sapiens_knowledge_feedback():", 1)[1].split(
        "@agents_bp.route('/api/agents/diagnostics'", 1
    )[0]
    assert "session.get(\"active_company_id\")" in feedback_block
    assert "data.get(\"company_id\")" not in feedback_block


def test_knowledge_endpoint_uses_authenticated_session_company(monkeypatch):
    from api.routes.agents import agents_bp
    from services.knowledge.interaction_service import KnowledgeInteractionService

    captured = {}

    def fake_answer(self, question, **kwargs):
        captured.update(kwargs)
        return {
            "answer": "Resposta segura",
            "claims": [],
            "citations": [],
            "actions": [],
            "warnings": [],
            "trust_signals": [],
        }

    monkeypatch.setattr(KnowledgeInteractionService, "answer", fake_answer)

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test")
    login = LoginManager(app)

    class User(UserMixin):
        id = 7
        employee_id = 8

    @login.user_loader
    def load_user(_user_id):
        return User()

    app.register_blueprint(agents_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "7"
        session["_fresh"] = True
        session["active_company_id"] = 44

    response = client.post(
        "/api/agents/knowledge/answer",
        json={"question": "Qual foi a decisão?", "scope": "company", "company_id": 999},
    )

    assert response.status_code == 200
    assert captured["company_id"] == 44
    assert captured["user_id"] == 7
    assert captured["employee_id"] == 8


def test_knowledge_feedback_endpoint_uses_authenticated_session_company(monkeypatch):
    from api.routes.agents import agents_bp
    from services.knowledge.feedback_service import KnowledgeFeedbackService

    captured = {}

    def fake_register_feedback(self, **kwargs):
        captured.update(kwargs)
        return {"feedback": {"rating": kwargs["rating"]}, "interaction": {"interaction_id": kwargs["interaction_id"]}}

    monkeypatch.setattr(KnowledgeFeedbackService, "register_feedback", fake_register_feedback)

    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test")
    login = LoginManager(app)

    class User(UserMixin):
        id = 7

    @login.user_loader
    def load_user(_user_id):
        return User()

    app.register_blueprint(agents_bp)
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = "7"
        session["_fresh"] = True
        session["active_company_id"] = 44

    response = client.post(
        "/api/agents/knowledge/feedback",
        json={
            "interaction_id": "abc",
            "rating": "partial",
            "reason": "incomplete",
            "company_id": 999,
        },
    )

    assert response.status_code == 200
    assert captured["company_id"] == 44
    assert captured["user_id"] == 7
    assert captured["rating"] == "partial"
