"""Módulos de domínio das tools do Sapiens/MCP."""

from .work_ops import get_my_work
from .strategy_ops import get_plan_diagnostics, list_plans, update_plan_section
from .analytics_ops import (
    get_plan_diagnostics_read_model,
    get_projects_execution_risk_read_model,
    get_team_workload_read_model,
)
from .system_ops import consult_rules, escalate_technical_issue, query_database
from .company_ops import list_my_companies, update_company_status
from .user_ops import (
    get_user_summary,
    list_system_users,
    register_system_user,
    update_user_contacts,
)
from .process_ops import (
    create_macro_process,
    create_process,
    create_process_area,
    list_process_hierarchy,
)
from .meeting_ops import (
    finish_meeting,
    log_meeting_discussion,
    schedule_meeting,
    send_meeting_minutes,
    start_meeting,
)
from .task_ops import (
    create_project_task,
    get_tasks_today,
    list_team_workload,
    complete_task,
    log_work_hours,
    request_deadline_extension,
    squad_create_intervention,
    squad_finish_intervention,
    squad_update_intervention,
)

__all__ = [
    "get_my_work",
    "get_plan_diagnostics",
    "get_plan_diagnostics_read_model",
    "list_plans",
    "update_plan_section",
    "get_projects_execution_risk_read_model",
    "get_team_workload_read_model",
    "consult_rules",
    "escalate_technical_issue",
    "query_database",
    "list_my_companies",
    "update_company_status",
    "get_user_summary",
    "list_system_users",
    "register_system_user",
    "update_user_contacts",
    "create_macro_process",
    "create_process",
    "create_process_area",
    "list_process_hierarchy",
    "finish_meeting",
    "log_meeting_discussion",
    "schedule_meeting",
    "send_meeting_minutes",
    "start_meeting",
    "create_project_task",
    "get_tasks_today",
    "list_team_workload",
    "complete_task",
    "log_work_hours",
    "request_deadline_extension",
    "squad_create_intervention",
    "squad_finish_intervention",
    "squad_update_intervention",
]
