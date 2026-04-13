import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.workflow_spec_draft_service import WorkflowSpecDraftService


def test_workflow_spec_draft_service_builds_structured_draft():
    draft = WorkflowSpecDraftService.build_draft(
        {
            "title": "Cadastrar Projeto Guiado",
            "business_domain": "Gestão de Projetos",
            "objective": "Criar projeto com validação dos dados mínimos.",
            "problem_statement": "Hoje o cadastro depende de checagem manual e há inconsistências.",
            "target_users": "Sapiens, PMO",
            "desired_channels": "web, whatsapp",
            "expected_result": "Projeto cadastrado com confirmação final.",
            "user_examples": "Quero cadastrar um novo projeto para o cliente XPTO.",
            "systems_involved": "PostgreSQL, MCP",
            "execution_profile": "action",
            "sensitivity_level": "high",
            "requires_human_confirmation": "yes",
            "source_channel": "ui_workflows_catalog",
        }
    )

    assert draft["suggested_domain_key"] == "gestao_de_projetos"
    assert draft["suggested_action_key"].startswith("gestao_de_projetos.create")
    assert "web" in draft["channels"]
    assert any(item["name"] == "query_database" for item in draft["tools"])
    assert any(item["name"] == "human_gate" for item in draft["permissions"])
