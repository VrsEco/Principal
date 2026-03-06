"""
Models package for APP32.
Contains SQLAlchemy models for database tables.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models here for Alembic auto-detection
# Core Models
from .company import Company
from .user import User
from .role import Role
from .team import Team
from .employee import Employee
from .user_employee_assignment import UserEmployeeAssignment

# Planning Models
from .plan import Plan, PlanParticipant, PlanSectionStatus, PlanDriver, PlanImplantationData

# Strategy & Indicators
from .indicator import Indicator, IndicatorGroup, IndicatorGoal, IndicatorData
from .okr_global import OKRGlobal, KeyResult
from .okr_area import OKRArea, KeyResultArea

# Execution Models
from .portfolio import Portfolio
from .project import Project, ProjectTask, ProjectActivityCollaborator
from .process import ProcessArea, MacroProcess, Process, ProcessRoutine, ProcessStep, ProcessInstance, ProcessInstanceCollaborator
from .routine import Routine, RoutineCollaborator

# Operations
from .meeting import Meeting, MeetingAgendaItem
from .note import Note
from .activity_work_log import ActivityWorkLog
from .occurrence import Occurrence
from .company_performance_settings import CompanyPerformanceSettings

# AI & Agents
from .ai_agent import AIAgent
from .agent_message import AgentMessage
from .agent_action import AgentAction
from .agent_menu import AgentMenuOption, AgentMenuSession

__all__ = [
    'db', 'Company', 'User', 'Role', 'Team', 'Employee', 'UserEmployeeAssignment',
    'Plan', 'PlanParticipant', 'PlanSectionStatus', 'PlanDriver', 'PlanImplantationData',
    'Indicator', 'IndicatorGroup', 'IndicatorGoal', 'IndicatorData',
    'OKRGlobal', 'KeyResult', 'OKRArea', 'KeyResultArea',
    'Portfolio', 'Project', 'ProjectTask', 'ProjectActivityCollaborator',
    'ProcessArea', 'MacroProcess', 'Process', 'ProcessRoutine', 'ProcessStep', 'ProcessInstance', 'ProcessInstanceCollaborator',
    'Routine', 'RoutineCollaborator',
    'Meeting', 'MeetingAgendaItem', 'Note', 'ActivityWorkLog', 'Occurrence', 'CompanyPerformanceSettings',
    'AIAgent', 'AgentMessage', 'AgentAction', 'AgentMenuOption', 'AgentMenuSession'
]
