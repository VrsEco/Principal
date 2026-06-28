from __future__ import annotations

from app32.tests.e2e.load.processes_functional_harness import execute_processes_functional_probe
from app32.tests.e2e.test_http_session_contract import _settings


def test_processes_functional_harness_validates_actions(monkeypatch):
    class _Response:
        def __init__(self, *, status_code=200, headers=None, text="", url="http://localhost:5002"):
            self.status_code = status_code
            self.headers = headers or {}
            self.text = text
            self.url = url
            self.ok = status_code < 400

        def raise_for_status(self):
            return None

    class _FakeHTTP:
        def login(self): return {"success": True}
        def select_company(self): return {"success": True}
        def request_json(self, method, path, *, json_payload=None, operation):
            if path.startswith("/api/companies/9/processes"):
                return [{"id": 518, "code": "M1.C.1.1.1"}]
            if path.endswith("/bpmn-diagram"):
                return {"id": 77, "status": "draft", "bpmn_xml": "<xml />", "svg_snapshot": "<svg />"}
            if "/api/companies/9/process-portal/processes/518" in path:
                return {"ok": True, "data": {"stats": {"resource_count": 2}, "resources": {"links": [{"id": 1}], "grouped": {"people": []}}}}
            if "/api/companies/9/process-portal/strategic-management" in path:
                return {"ok": True, "data": {"audience": "client", "structuring_trail": {"phases": []}, "groups": [{"key": "team_efficiency"}]}}
            return {"id": 518, "company_id": 9, "name": "Processo"}
        def request(self, method, path, *, json_payload=None):
            if "/process-portal/processes/518" in path:
                return _Response(headers={"Content-Type": "text/html"}, text="Estrutura/Recursos Processo Recursos", url="http://localhost:5002" + path)
            if "/process-portal/strategic-management" in path:
                return _Response(headers={"Content-Type": "text/html"}, text="Painel Gestão Estratégica smpLayerStack smpMobileActionsToggle", url="http://localhost:5002" + path)
            return _Response(headers={"Content-Type": "text/html"}, text="<div class='bpmn-modeler-shell'>Salvar rascunho</div>", url="http://localhost:5002/processes/518/bpmn-modeler")
        def assert_not_login_redirect(self, response, *, operation): return None
        _json_or_raise = lambda self, response, operation: {"id": 77, "status": "draft"}

    monkeypatch.setattr(
        "app32.tests.e2e.load.processes_functional_harness.AuthenticatedHTTPSession.create",
        lambda _settings: _FakeHTTP(),
    )
    settings = _settings()
    results = execute_processes_functional_probe(settings=settings)
    assert len(results) >= 9
    assert any(result.check_name == "processes.portal_detail_resources_contract" for result in results)
    assert any(result.check_name == "processes.strategic_management_api_client" for result in results)
    assert all(result.success for result in results)
