from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Core Models
from .company import Company
from .user import User
from .user_mcp_token import UserMcpToken
from .instruction_registry import InstructionRegistryEntry, InstructionRegistryAuditLog
from .role import Role
from .team import Team
from .employee import Employee
from .user_employee_assignment import UserEmployeeAssignment

# Planning & Strategic
from .plan import Plan, PlanParticipant, PlanSectionStatus, PlanDriver, PlanImplantationData
from .indicator import Indicator, IndicatorEntityLink, IndicatorGroup, IndicatorTree, IndicatorGoal, IndicatorData
from .okr_global import OKRGlobal, KeyResult
from .okr_area import OKRArea, KeyResultArea

# Execution
from .portfolio import Portfolio
from .project import Project, ProjectTask, ProjectTaskDependency, ProjectActivityCollaborator
from .process import ProcessArea, MacroProcess, Process, ProcessBpmnDiagram, ProcessBpmsAnalysis, ProcessSipocSnapshot, ProcessSipocItem, ProcessSipocRegulatoryItem, MacroProcessSipocSnapshot, MacroProcessSipocItem, MacroProcessSipocRegulatoryItem, ProcessRoutine, ProcessStep, ProcessInstance, ProcessInstanceCollaborator, ProcessInstanceExecution, ProcessActivityExecutionContract
from .process_resource import ResourceCatalog, ProcessResourceLink
from .process_portal import ProcessPortalPublication, ProcessPortalPublicationGrant
from .strategy_alignment import (
    IndicatorLineOfSight,
    OrganizationalIdentity,
    ProcessStrategicAlignmentLink,
    ProcessStrategyProfile,
    StrategyMaturationItem,
)
from .routine import Routine, RoutineCollaborator, RoutineJourneyBinding
from .financial import (
    FinancialAccountCategory,
    FinancialAssetAccount,
    FinancialBankAccount,
    FinancialChartAccount,
    FinancialCorrectionIndex,
    FinancialCostCenter,
    FinancialCustomerPortfolio,
    FinancialCounterparty,
    FinancialDiscountRule,
    FinancialDomainEnablement,
    FinancialManualDomain,
    FinancialAutomationRule,
    FinancialAutomationExecution,
    FinancialPaymentMethod,
    FinancialSchedule,
    FinancialSatellitePolicy,
    FinancialScheduleLink,
    FinancialSatelliteExecution,
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
from .contracts import (
    Contract,
    ContractCatalogItem,
    ContractBillingItem,
    ContractNativeBilling,
    ContractNativeBillingItem,
    ContractClause,
    ContractDocument,
    ContractEvent,
    ContractFinancialTerm,
    ContractFiscalTerm,
    ContractItem,
    ContractNote,
    ContractParty,
    ContractingLegalEntity,
    ContractRetention,
    ContractTrigger,
)
from .automation import (
    AutomationRegistry,
    AutomationRule,
    AutomationExecution,
    AutomationBpmsLink,
)
from .real_estate_auction import (
    RealEstateAuctionAttachment,
    RealEstateAuctionDueDiligence,
    RealEstateAuctionEvent,
    RealEstateAuctionFinancialSheet,
    RealEstateAuctionImportJob,
    RealEstateAuctionImportJobItem,
    RealEstateAuctionProperty,
    RealEstateAuctionSource,
    RealEstateAuctionTenantSettings,
)

from .internal_audit import (
    AuditArea,
    AuditAuditor,
    AuditChecklist,
    AuditChecklistItem,
    AuditExecution,
    AuditExecutionItem,
    AuditEvidenceLink,
    AuditFinding,
    AuditFollowUp,
    AuditPoint,
    AuditReport,
    AuditSchedule,
    AuditWorkpaper,
)

# Operations & Governance
from .meeting import Meeting, MeetingAgendaItem
from .note import Note
from .activity_comment import ActivityComment
from .activity_work_log import ActivityWorkLog
from .occurrence import Occurrence
from .cadastro_session import CadastroSession
from .company_performance_settings import CompanyPerformanceSettings
from .company_role_permission_preset import CompanyRolePermissionPreset
from .project_due_date_change import ProjectTaskDueDateChangeRequest
from .app_compliance_report import AppComplianceReport, AppComplianceReportItem
from .ui_catalog import UiCatalog
from .user_log import UserLog
from .urgent_business_review import (
    BusinessReviewRecord,
    StructuralLearningLink,
    UrgentNeedOverlay,
)
from .consultive_assisted_analysis import (
    AssistedAnalysis,
    AssistedAnalysisDecision,
    AssistedAnalysisValidation,
)
from .consultive_protocol import ConsultiveProtocol

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
    WorkCalendarEvent,
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
    'db', 'Company', 'User', 'UserMcpToken', 'Role', 'Team', 'Employee', 'UserEmployeeAssignment',
    'InstructionRegistryEntry', 'InstructionRegistryAuditLog',
    'Plan', 'PlanParticipant', 'PlanSectionStatus', 'PlanDriver', 'PlanImplantationData',
    'Indicator', 'IndicatorEntityLink', 'IndicatorGroup', 'IndicatorTree', 'IndicatorGoal', 'IndicatorData',
    'OKRGlobal', 'KeyResult', 'OKRArea', 'KeyResultArea',
    'Portfolio', 'Project', 'ProjectTask', 'ProjectTaskDependency', 'ProjectActivityCollaborator',
    'ProcessArea', 'MacroProcess', 'Process', 'ProcessBpmnDiagram', 'ProcessBpmsAnalysis', 'ProcessSipocSnapshot', 'ProcessSipocItem', 'ProcessSipocRegulatoryItem', 'MacroProcessSipocSnapshot', 'MacroProcessSipocItem', 'MacroProcessSipocRegulatoryItem', 'ProcessRoutine', 'ProcessStep', 'ProcessInstance', 'ProcessInstanceCollaborator', 'ProcessInstanceExecution', 'ProcessActivityExecutionContract', 'ResourceCatalog', 'ProcessResourceLink', 'ProcessPortalPublication', 'ProcessPortalPublicationGrant',
    'OrganizationalIdentity', 'ProcessStrategyProfile', 'ProcessStrategicAlignmentLink', 'IndicatorLineOfSight', 'StrategyMaturationItem',
    'Routine', 'RoutineCollaborator', 'RoutineJourneyBinding',
    'FinancialAccountCategory', 'FinancialAssetAccount', 'FinancialBankAccount', 'FinancialChartAccount', 'FinancialCorrectionIndex', 'FinancialCostCenter', 'FinancialCustomerPortfolio', 'FinancialCounterparty', 'FinancialDiscountRule', 'FinancialDomainEnablement', 'FinancialManualDomain', 'FinancialAutomationRule', 'FinancialAutomationExecution', 'FinancialPaymentMethod', 'FinancialSchedule', 'FinancialSatellitePolicy', 'FinancialScheduleLink', 'FinancialSatelliteExecution', 'FinancialBordero', 'FinancialBorderoItem', 'FinancialBorderoSettlement',
    'FinancialEntry', 'FinancialEntryAllocation', 'FinancialSettlement', 'FinancialSettlementComponent', 'FinancialTitleAdjustment', 'FinancialTitleAdjustmentAllocation', 'FinancialTitleCalculationLog', 'FinancialImportBatch', 'FinancialImportRow', 'FinancialReconciliationMatch', 'FinancialClassificationRule', 'FinancialClassificationMemory', 'FinancialClassificationSuggestion', 'FinancialIngestionRecord',
    'FinancialAutomationBatch', 'FinancialAutomationDocument', 'FinancialAutomationHistory', 'FinancialAutomationRecord',
    'FinancialBudgetCycle', 'FinancialBudgetVersion', 'FinancialBudgetLine', 'FinancialBudgetAmount', 'FinancialBudgetContract', 'FinancialBudgetDocument',
    'AutomationRegistry', 'AutomationRule', 'AutomationExecution', 'AutomationBpmsLink',
    'AuditArea', 'AuditAuditor', 'AuditChecklist', 'AuditChecklistItem', 'AuditSchedule', 'AuditExecution', 'AuditExecutionItem', 'AuditPoint', 'AuditWorkpaper', 'AuditFinding', 'AuditEvidenceLink', 'AuditReport', 'AuditFollowUp',
    'RealEstateAuctionProperty', 'RealEstateAuctionEvent', 'RealEstateAuctionFinancialSheet', 'RealEstateAuctionDueDiligence', 'RealEstateAuctionAttachment', 'RealEstateAuctionSource', 'RealEstateAuctionImportJob', 'RealEstateAuctionImportJobItem', 'RealEstateAuctionTenantSettings',
    'Contract', 'ContractCatalogItem', 'ContractParty', 'ContractingLegalEntity', 'ContractItem', 'ContractBillingItem', 'ContractNativeBilling', 'ContractNativeBillingItem', 'ContractFinancialTerm', 'ContractFiscalTerm', 'ContractRetention', 'ContractTrigger', 'ContractDocument', 'ContractClause', 'ContractNote', 'ContractEvent',
    'Meeting', 'MeetingAgendaItem', 'Note', 'ActivityComment', 'ActivityWorkLog', 'Occurrence', 
    'CadastroSession', 'CompanyPerformanceSettings', 'CompanyRolePermissionPreset', 'AppComplianceReport', 'AppComplianceReportItem',
    'ProjectTaskDueDateChangeRequest',
    'UiCatalog', 'UserLog',
    'UrgentNeedOverlay', 'BusinessReviewRecord', 'StructuralLearningLink',
    'AssistedAnalysis', 'AssistedAnalysisValidation', 'AssistedAnalysisDecision',
    'ConsultiveProtocol',
    'AIAgent', 'AgentMessage', 'AgentAction', 'AgentActionBacklogLink', 'AgentMenuOption', 'AgentMenuSession',
    'WorkflowGapCandidate', 'WorkflowExecutionLog', 'IntegrationRequest',
    'AICapability', 'AICapabilityGrant', 'AICapabilityCompanySetting', 'AICapabilityAuditLog',
    'WorkJourneyBlock', 'WorkJourneyAgenda', 'WorkJourneyAgendaItem', 'WorkCalendarEvent', 'WorkJourneyRule', 'WorkJourneyItem', 'WorkJourneyAbsenceRequest', 'WorkJourneyTransferRequest',
    'IncentiveRuleSet', 'IncentiveRule',
    'IncentiveGovernabilityMatrix', 'IncentiveCalculation',
    'IncentiveParticipant'
]
