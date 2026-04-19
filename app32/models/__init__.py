from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Core Models
from .company import Company
from .user import User
from .role import Role
from .team import Team
from .employee import Employee
from .user_employee_assignment import UserEmployeeAssignment

# Planning & Strategic
from .plan import Plan, PlanParticipant, PlanSectionStatus, PlanDriver, PlanImplantationData
from .indicator import Indicator, IndicatorGroup, IndicatorTree, IndicatorGoal, IndicatorData
from .okr_global import OKRGlobal, KeyResult
from .okr_area import OKRArea, KeyResultArea

# Execution
from .portfolio import Portfolio
from .project import Project, ProjectTask, ProjectTaskDependency, ProjectActivityCollaborator
from .process import ProcessArea, MacroProcess, Process, ProcessRoutine, ProcessStep, ProcessInstance, ProcessInstanceCollaborator
from .routine import Routine, RoutineCollaborator, RoutineJourneyBinding
from .financial import (
    FinancialAccountCategory,
    FinancialAssetAccount,
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialCorrectionIndex,
    FinancialCostCenter,
    FinancialCounterparty,
    FinancialDiscountRule,
    FinancialDomainEnablement,
    FinancialAutomationRule,
    FinancialAutomationExecution,
    FinancialPaymentMethod,
    FinancialSchedule,
    FinancialBordero,
    FinancialBorderoItem,
    FinancialBorderoSettlement,
    FinancialEntry,
    FinancialEntryAllocation,
    FinancialSettlement,
    FinancialSettlementComponent,
    FinancialTitleAdjustment,
    FinancialTitleAdjustmentAllocation,
    FinancialTitleCalculationLog,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
    FinancialClassificationRule,
    FinancialClassificationMemory,
    FinancialClassificationSuggestion,
    FinancialIngestionRecord,
)
from .financial_automation import (
    FinancialAutomationBatch,
    FinancialAutomationDocument,
    FinancialAutomationHistory,
    FinancialAutomationRecord,
)
from .financial_budget import (
    FinancialBudgetCycle,
    FinancialBudgetVersion,
    FinancialBudgetLine,
    FinancialBudgetAmount,
    FinancialBudgetContract,
    FinancialBudgetDocument,
)

# Operations & Governance
from .meeting import Meeting, MeetingAgendaItem
from .note import Note
from .activity_comment import ActivityComment
from .activity_work_log import ActivityWorkLog
from .occurrence import Occurrence
from .cadastro_session import CadastroSession
from .company_performance_settings import CompanyPerformanceSettings
from .project_due_date_change import ProjectTaskDueDateChangeRequest
from .app_compliance_report import AppComplianceReport, AppComplianceReportItem
from .ui_catalog import UiCatalog
from .user_log import UserLog

# AI & Automation
from .ai_agent import AIAgent
from .agent_message import AgentMessage
from .agent_action import AgentAction
from .agent_action_backlog_link import AgentActionBacklogLink
from .agent_menu import AgentMenuOption, AgentMenuSession
from .workflow_gap import WorkflowGapCandidate
from .workflow_usage import WorkflowExecutionLog
from .integration_request import IntegrationRequest
from .ai_capability import (
    AICapability,
    AICapabilityGrant,
    AICapabilityCompanySetting,
    AICapabilityAuditLog,
)
from .work_journey import (
    WorkJourneyBlock,
    WorkJourneyAgenda,
    WorkJourneyAgendaItem,
    WorkJourneyRule,
    WorkJourneyItem,
    WorkJourneyAbsenceRequest,
    WorkJourneyTransferRequest,
)

# Incentive Module (Specific structures)
from .incentive import (
    IncentiveRuleSet, IncentiveRule,
    IncentiveGovernabilityMatrix, IncentiveCalculation,
    IncentiveParticipant
)

__all__ = [
    'db', 'Company', 'User', 'Role', 'Team', 'Employee', 'UserEmployeeAssignment',
    'Plan', 'PlanParticipant', 'PlanSectionStatus', 'PlanDriver', 'PlanImplantationData',
    'Indicator', 'IndicatorGroup', 'IndicatorTree', 'IndicatorGoal', 'IndicatorData',
    'OKRGlobal', 'KeyResult', 'OKRArea', 'KeyResultArea',
    'Portfolio', 'Project', 'ProjectTask', 'ProjectTaskDependency', 'ProjectActivityCollaborator',
    'ProcessArea', 'MacroProcess', 'Process', 'ProcessRoutine', 'ProcessStep', 'ProcessInstance', 'ProcessInstanceCollaborator',
    'Routine', 'RoutineCollaborator', 'RoutineJourneyBinding',
    'FinancialAccountCategory', 'FinancialAssetAccount', 'FinancialBankAccount', 'FinancialChartAccount', 'FinancialCorrectionIndex', 'FinancialCostCenter', 'FinancialCounterparty', 'FinancialDiscountRule', 'FinancialDomainEnablement', 'FinancialAutomationRule', 'FinancialAutomationExecution', 'FinancialPaymentMethod', 'FinancialSchedule', 'FinancialBordero', 'FinancialBorderoItem', 'FinancialBorderoSettlement',
    'FinancialEntry', 'FinancialEntryAllocation', 'FinancialSettlement', 'FinancialSettlementComponent', 'FinancialTitleAdjustment', 'FinancialTitleAdjustmentAllocation', 'FinancialTitleCalculationLog', 'FinancialImportBatch', 'FinancialImportRow', 'FinancialReconciliationMatch', 'FinancialClassificationRule', 'FinancialClassificationMemory', 'FinancialClassificationSuggestion', 'FinancialIngestionRecord',
    'FinancialAutomationBatch', 'FinancialAutomationDocument', 'FinancialAutomationHistory', 'FinancialAutomationRecord',
    'FinancialBudgetCycle', 'FinancialBudgetVersion', 'FinancialBudgetLine', 'FinancialBudgetAmount', 'FinancialBudgetContract', 'FinancialBudgetDocument',
    'Meeting', 'MeetingAgendaItem', 'Note', 'ActivityComment', 'ActivityWorkLog', 'Occurrence', 
    'CadastroSession', 'CompanyPerformanceSettings', 'AppComplianceReport', 'AppComplianceReportItem',
    'ProjectTaskDueDateChangeRequest',
    'UiCatalog', 'UserLog',
    'AIAgent', 'AgentMessage', 'AgentAction', 'AgentActionBacklogLink', 'AgentMenuOption', 'AgentMenuSession',
    'WorkflowGapCandidate', 'WorkflowExecutionLog', 'IntegrationRequest',
    'AICapability', 'AICapabilityGrant', 'AICapabilityCompanySetting', 'AICapabilityAuditLog',
    'WorkJourneyBlock', 'WorkJourneyAgenda', 'WorkJourneyAgendaItem', 'WorkJourneyRule', 'WorkJourneyItem', 'WorkJourneyAbsenceRequest', 'WorkJourneyTransferRequest',
    'IncentiveRuleSet', 'IncentiveRule',
    'IncentiveGovernabilityMatrix', 'IncentiveCalculation',
    'IncentiveParticipant'
]
