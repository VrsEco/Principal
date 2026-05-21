from __future__ import annotations

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.process_ai_modeler_assistant_service import ProcessAIModelerAssistantService
from services import process_flow_copilot_service as copilot_service


class _QueryStub:
    def __init__(self, item):
        self._item = item

    def filter_by(self, **kwargs):
        return self

    def first(self):
        return self._item


_BPMN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">
  <bpmn:process id="Process_1" isExecutable="false">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_Financeiro" name="Financeiro">
        <bpmn:flowNodeRef>Task_SendCharge</bpmn:flowNodeRef>
      </bpmn:lane>
      <bpmn:lane id="Lane_Operacao" name="Operação">
        <bpmn:flowNodeRef>Task_RegisterDocument</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="StartEvent_1" name="Início">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_SendCharge" name="Enviar cobrança">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:task id="Task_RegisterDocument" name="Registrar documento">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:task>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_SendCharge" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_SendCharge" targetRef="Task_RegisterDocument" />
  </bpmn:process>
</bpmn:definitions>
"""


def test_build_process_flow_copilot_analysis_highlights_automation_candidates(monkeypatch):
    process = SimpleNamespace(id=17, company_id=10, code="PR.01", name="Cobrança")
    diagram = SimpleNamespace(id=9, status="published", version=3, updated_at=None, bpmn_xml=_BPMN_XML)

    monkeypatch.setattr(copilot_service, "Process", SimpleNamespace(query=_QueryStub(process)))
    monkeypatch.setattr(copilot_service, "get_latest_diagram", lambda **kwargs: diagram)
    monkeypatch.setattr(copilot_service, "_load_contracts_map", lambda **kwargs: {})
    monkeypatch.setattr(copilot_service, "_load_pop_map", lambda **kwargs: {})
    monkeypatch.setattr(
        copilot_service,
        "_integrations_by_key",
        lambda: {
            "service_email": {"key": "service_email", "title": "E-mail", "technical_channel": "api", "status": "available", "summary": "Canal e-mail"},
            "service_whatsapp": {"key": "service_whatsapp", "title": "WhatsApp", "technical_channel": "api", "status": "available", "summary": "Canal WhatsApp"},
            "erp_accounting_bridge": {"key": "erp_accounting_bridge", "title": "ERP / Contábil", "technical_channel": "api_mcp", "status": "discovery", "summary": "ERP"},
        },
    )
    monkeypatch.setattr(
        copilot_service.AIAutomationRegistryService,
        "build_registry",
        lambda active_company=None: {"automations": []},
    )

    payload = copilot_service.build_process_flow_copilot_analysis(company_id=10, process_id=17)

    assert payload["summary"]["activities"] == 2
    send_charge = next(item for item in payload["activities"] if item["element_id"] == "Task_SendCharge")
    assert send_charge["lane_name"] == "Financeiro"
    assert send_charge["automation_score"] >= 80
    assert any(candidate["template_key"] == "email_notification_api" for candidate in send_charge["automation_candidates"])
    assert any(candidate["candidate_key"] == "integration:service_whatsapp" for candidate in send_charge["integration_candidates"])
    assert send_charge["human_review_required"] is True


def test_activity_automation_context_returns_selected_activity(monkeypatch):
    monkeypatch.setattr(
        copilot_service,
        "build_process_flow_copilot_analysis",
        lambda **kwargs: {
            "activities": [
                {"element_id": "A1", "element_name": "Registrar documento"},
                {"element_id": "A2", "element_name": "Enviar cobrança"},
            ]
        },
    )

    activity = copilot_service.build_activity_automation_context(company_id=10, process_id=22, bpmn_element_id="A2")

    assert activity["element_name"] == "Enviar cobrança"


def test_process_ai_modeler_assistant_fallback_includes_copilot_candidates(monkeypatch):
    monkeypatch.setattr(
        ProcessAIModelerAssistantService,
        "_resolve_automation_context",
        classmethod(
            lambda cls, payload: {
                "automation_candidates": [
                    {"template_key": "generic_webhook_outbound", "title": "Webhook / API Externa"}
                ],
                "integration_candidates": [
                    {"candidate_key": "integration:erp_accounting_bridge", "title": "ERP / Contábil"}
                ],
            }
        ),
    )

    suggestion = ProcessAIModelerAssistantService._fallback_suggestion(
        {
            "semantic_type": "ai_task",
            "objective": "Sincronizar ERP",
            "current_config": {},
            "next_candidates": [],
            "process_id": 1,
            "company_id": 10,
            "element_id": "Task_1",
        }
    )

    assert suggestion["recommended_template_keys"] == ["generic_webhook_outbound"]
    assert suggestion["integration_candidates"][0]["candidate_key"] == "integration:erp_accounting_bridge"
    assert suggestion["requires_human_review"] is True
