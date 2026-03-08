from __future__ import annotations

from typing import List

from .evaluation import WorkflowEvaluationCase


def build_default_workflow_evaluation_cases() -> List[WorkflowEvaluationCase]:
    return [
        WorkflowEvaluationCase(
            domain="summary",
            label="summary_week",
            text="quero o resumo desta semana da equipe",
            expected_action_key="summary.week",
            channel="whatsapp",
        ),
        WorkflowEvaluationCase(
            domain="summary",
            label="summary_month",
            text="me mostra o resumo deste mes",
            expected_action_key="summary.month",
        ),
        WorkflowEvaluationCase(
            domain="summary",
            label="summary_custom",
            text="preciso do resumo de 01/03/2026 a 05/03/2026",
            expected_action_key="summary.custom",
            channel="telegram",
        ),
        WorkflowEvaluationCase(
            domain="my_work",
            label="my_work_open",
            text="quais atividades estao em aberto para mim",
            expected_action_key="my_work.open",
            channel="whatsapp",
        ),
        WorkflowEvaluationCase(
            domain="my_work",
            label="my_work_overdue",
            text="o que esta vencido no meu trabalho",
            expected_action_key="my_work.overdue",
        ),
        WorkflowEvaluationCase(
            domain="my_work",
            label="my_work_completed",
            text="quais atividades foram concluidas no periodo 01/03/2026 a 07/03/2026",
            expected_action_key="my_work.completed_range",
        ),
        WorkflowEvaluationCase(
            domain="collaborator",
            label="collaborator_occupancy",
            text="preciso da ocupacao do colaborador Fabiano nesta semana",
            expected_action_key="collaborator.occupancy",
            channel="whatsapp",
        ),
        WorkflowEvaluationCase(
            domain="project_task",
            label="project_task_create",
            text="quero cadastrar uma nova atividade de projeto",
            expected_action_key="project_task.create",
            channel="whatsapp",
        ),
        WorkflowEvaluationCase(
            domain="project_task",
            label="project_task_complete",
            text="preciso concluir uma atividade de projeto",
            expected_action_key="project_task.complete",
        ),
        WorkflowEvaluationCase(
            domain="process",
            label="process_instance_complete",
            text="quero finalizar uma instancia de processo",
            expected_action_key="process_instance.complete",
        ),
        WorkflowEvaluationCase(
            domain="meeting",
            label="meeting_schedule",
            text="agendar reuniao com a equipe comercial",
            expected_action_key="meeting.schedule",
            channel="telegram",
        ),
        WorkflowEvaluationCase(
            domain="meeting",
            label="meeting_start",
            text="preciso iniciar a reuniao das 14h",
            expected_action_key="meeting.start",
            channel="whatsapp",
        ),
        WorkflowEvaluationCase(
            domain="meeting",
            label="meeting_summarize",
            text="gere um resumo da reuniao de ontem",
            expected_action_key="meeting.summarize",
        ),
        WorkflowEvaluationCase(
            domain="onboarding",
            label="onboarding_status",
            text="qual o status do onboarding dessa empresa",
            expected_action_key="onboarding.status",
        ),
        WorkflowEvaluationCase(
            domain="onboarding",
            label="onboarding_start",
            text="quero iniciar o onboarding assistido",
            expected_action_key="onboarding.start",
        ),
        WorkflowEvaluationCase(
            domain="onboarding",
            label="onboarding_diagnose",
            text="preciso diagnosticar gargalos do funcionamento",
            expected_action_key="onboarding.diagnose",
        ),
        WorkflowEvaluationCase(
            domain="onboarding",
            label="onboarding_go_live",
            text="a empresa esta pronta para operar em producao?",
            expected_action_key="onboarding.go_live_check",
            channel="telegram",
        ),
    ]
