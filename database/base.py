"""
Base database interface
Defines the contract that all database implementations must follow
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class DatabaseInterface(ABC):
    """Abstract base class for database operations"""
    
    @abstractmethod
    def init_database(self) -> bool:
        """Initialize database and create tables"""
        pass
    
    @abstractmethod
    def seed_data(self) -> bool:
        """Seed database with initial data"""
        pass
    
    # Company operations
    @abstractmethod
    def get_companies(self) -> List[Dict[str, Any]]:
        """Get all companies"""
        pass
    
    @abstractmethod
    def get_company(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        pass
    
    @abstractmethod
    def delete_company(self, company_id: int) -> bool:
        """Delete company by ID"""
        pass
    
    # Plan operations
    @abstractmethod
    def get_plans_by_company(self, company_id: int) -> List[Dict[str, Any]]:
        """Get plans for a company"""
        pass
    
    @abstractmethod
    def get_plan(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan by ID"""
        pass
    
    @abstractmethod
    def get_plan_with_company(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get plan with company information"""
        pass
    
    # Participant operations
    @abstractmethod
    def get_participants(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get participants for a plan"""
        pass
    
    @abstractmethod
    def add_participant(self, plan_id: int, participant_data: Dict[str, Any]) -> Optional[int]:
        """Add new participant and return the ID"""
        pass
    
    @abstractmethod
    def get_participant(self, participant_id: int) -> Optional[Dict[str, Any]]:
        """Get participant by ID"""
        pass
    
    @abstractmethod
    def update_participant(self, participant_id: int, participant_data: Dict[str, Any]) -> bool:
        """Update participant data"""
        pass
    
    @abstractmethod
    def delete_participant(self, participant_id: int) -> bool:
        """Delete participant"""
        pass
    
    @abstractmethod
    def update_participant_status(self, participant_id: int, status: str) -> bool:
        """Update participant status"""
        pass
    
    # Message Templates Methods
    @abstractmethod
    def get_message_templates(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get message templates for a plan"""
        pass
    
    @abstractmethod
    def get_message_template(self, plan_id: int, message_type: str) -> Optional[Dict[str, Any]]:
        """Get specific message template"""
        pass
    
    @abstractmethod
    def save_message_template(self, plan_id: int, message_type: str, subject: str, content: str) -> bool:
        """Save or update message template"""
        pass
    
    # Company data operations
    @abstractmethod
    def get_company_data(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """Get company data for a plan"""
        pass
    
    @abstractmethod
    def update_company_data(self, plan_id: int, data: Dict[str, Any]) -> bool:
        """Update company data"""
        pass
    
    # Driver operations
    @abstractmethod
    def get_drivers(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get drivers for a plan"""
        pass
    
    @abstractmethod
    def add_driver(self, plan_id: int, driver_data: Dict[str, Any]) -> bool:
        """Add new driver"""
        pass
    
    # OKR Global preliminary analysis operations
    @abstractmethod
    def get_okr_preliminary_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get preliminary OKR analyses for a plan"""
        pass
    
    @abstractmethod
    def get_okr_preliminary_record(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Get a preliminary OKR analysis by ID"""
        pass
    
    @abstractmethod
    def add_okr_preliminary_record(self, plan_id: int, analysis: str) -> Optional[int]:
        """Create a preliminary OKR analysis and return the new ID"""
        pass
    
    @abstractmethod
    def update_okr_preliminary_record(self, record_id: int, analysis: str) -> bool:
        """Update a preliminary OKR analysis"""
        pass
    
    @abstractmethod
    def delete_okr_preliminary_record(self, record_id: int) -> bool:
        """Delete a preliminary OKR analysis"""
        pass
    
    # OKR Area preliminary analysis operations
    @abstractmethod
    def add_okr_area_preliminary_record(self, plan_id: int, analysis: str) -> Optional[int]:
        """Create a preliminary area OKR analysis and return the new ID"""
        pass
    
    @abstractmethod
    def update_okr_area_preliminary_record(self, record_id: int, analysis: str) -> bool:
        """Update a preliminary area OKR analysis"""
        pass
    
    @abstractmethod
    def delete_okr_area_preliminary_record(self, record_id: int) -> bool:
        """Delete a preliminary area OKR analysis"""
        pass
    
    @abstractmethod
    def get_okr_area_preliminary_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get all preliminary area OKR records for a plan"""
        pass
    
    # OKR Global records operations
    @abstractmethod
    def get_global_okr_records(self, plan_id: int, stage: str) -> List[Dict[str, Any]]:
        """Get OKR records for a plan and stage (e.g. 'workshop' or 'approval')"""
        pass
    
    @abstractmethod
    def get_global_okr_record(self, okr_id: int) -> Optional[Dict[str, Any]]:
        """Get a single OKR record with its key results"""
        pass
    
    @abstractmethod
    def add_global_okr_record(self, plan_id: int, stage: str, okr_data: Dict[str, Any], key_results: List[Dict[str, Any]]) -> Optional[int]:
        """Create a new OKR record and return its ID"""
        pass
    
    @abstractmethod
    def update_global_okr_record(self, okr_id: int, okr_data: Dict[str, Any], key_results: List[Dict[str, Any]]) -> bool:
        """Update an existing OKR record"""
        pass
    
    @abstractmethod
    def delete_global_okr_record(self, okr_id: int) -> bool:
        """Delete an OKR record and its key results"""
        pass
    
    @abstractmethod
    def bulk_delete_global_okr_records(self, plan_id: int, stage: str, okr_ids: List[int]) -> int:
        """Bulk delete OKR records for a given stage and return deleted count"""
        pass
    
    @abstractmethod
    def search_global_okr_records(self, plan_id: int, stage: str, query: str) -> List[Dict[str, Any]]:
        """Search OKR records by objective, owner or observations"""
        pass
    
    # Project operations
    @abstractmethod
    def get_company_projects(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all projects for a company"""
        pass
    
    @abstractmethod
    def create_company_project(self, company_id: int, project_data: Dict[str, Any]) -> Optional[int]:
        """Create a project scoped to a company, optionally linked to a plan"""
        pass
    
    @abstractmethod
    def get_projects(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get projects for a plan"""
        pass
    
    @abstractmethod
    def add_project(self, plan_id: int, project_data: Dict[str, Any]) -> Optional[int]:
        """Add new project and return project ID"""
        pass
    
    @abstractmethod
    def update_project(self, project_id: int, project_data: Dict[str, Any]) -> bool:
        """Update existing project"""
        pass
    
    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        """Delete project"""
        pass
    
    @abstractmethod
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get single project by ID"""
        pass

    @abstractmethod
    def get_company_project(self, company_id: int, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project ensuring it belongs to a company"""
        pass

    # Meeting operations
    @abstractmethod
    def list_company_meetings(self, company_id: int) -> List[Dict[str, Any]]:
        """List meetings registered for a company"""
        pass

    @abstractmethod
    def get_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single meeting by ID"""
        pass

    @abstractmethod
    def create_meeting(self, company_id: int, meeting_data: Dict[str, Any]) -> Optional[int]:
        """Create a meeting record and return its ID"""
        pass

    @abstractmethod
    def update_meeting(self, meeting_id: int, meeting_data: Dict[str, Any]) -> bool:
        """Update meeting information"""
        pass
    
    # Interview operations
    @abstractmethod
    def get_interviews(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get interviews for a plan"""
        pass
    
    @abstractmethod
    def add_interview(self, plan_id: int, interview_data: Dict[str, Any]) -> bool:
        """Add new interview"""
        pass
    
    @abstractmethod
    def get_interview(self, interview_id: int) -> Optional[Dict[str, Any]]:
        """Get interview by ID"""
        pass
    
    @abstractmethod
    def update_interview(self, interview_id: int, interview_data: Dict[str, Any]) -> bool:
        """Update interview data"""
        pass
    
    @abstractmethod
    def delete_interview(self, interview_id: int) -> bool:
        """Delete interview"""
        pass
    
    # Plan Section operations
    @abstractmethod
    def get_section_status(self, plan_id: int, section_name: str) -> Optional[Dict[str, Any]]:
        """Get section status for a plan"""
        pass
    
    @abstractmethod
    def update_section_status(self, plan_id: int, section_name: str, status: str, closed_by: str = None, notes: str = None) -> bool:
        """Update section status"""
        pass
    
    @abstractmethod
    def update_section_consultant_notes(self, plan_id: int, section_name: str, consultant_notes: str) -> bool:
        """Update section consultant notes"""
        pass
    
    @abstractmethod
    def update_section_adjustments(self, plan_id: int, section_name: str, adjustments: str) -> bool:
        """Update section adjustments"""
        pass
    
    # Vision Records operations
    @abstractmethod
    def get_vision_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get vision records for a plan"""
        pass
    
    @abstractmethod
    def add_vision_record(self, plan_id: int, vision_data: Dict[str, Any]) -> bool:
        """Add new vision record"""
        pass
    
    @abstractmethod
    def get_vision_record(self, vision_id: int) -> Optional[Dict[str, Any]]:
        """Get vision record by ID"""
        pass
    
    @abstractmethod
    def update_vision_record(self, vision_id: int, vision_data: Dict[str, Any]) -> bool:
        """Update vision record data"""
        pass
    
    @abstractmethod
    def delete_vision_record(self, vision_id: int) -> bool:
        """Delete vision record"""
        pass
    
    # Market Records Methods
    @abstractmethod
    def get_market_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get market records for a plan"""
        pass
    
    @abstractmethod
    def add_market_record(self, plan_id: int, market_data: Dict[str, Any]) -> bool:
        """Add new market record"""
        pass
    
    @abstractmethod
    def get_market_record(self, market_id: int) -> Optional[Dict[str, Any]]:
        """Get market record by ID"""
        pass
    
    @abstractmethod
    def update_market_record(self, market_id: int, market_data: Dict[str, Any]) -> bool:
        """Update market record data"""
        pass
    
    @abstractmethod
    def delete_market_record(self, market_id: int) -> bool:
        """Delete market record"""
        pass
    
    # Company Records Methods
    @abstractmethod
    def get_company_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get company records for a plan"""
        pass
    
    @abstractmethod
    def add_company_record(self, plan_id: int, company_data: Dict[str, Any]) -> bool:
        """Add new company record"""
        pass
    
    @abstractmethod
    def get_company_record(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Get company record by ID"""
        pass
    
    @abstractmethod
    def update_company_record(self, company_id: int, company_data: Dict[str, Any]) -> bool:
        """Update company record data"""
        pass
    
    @abstractmethod
    def delete_company_record(self, company_id: int) -> bool:
        """Delete company record"""
        pass
    
    # Alignment Records Methods
    @abstractmethod
    def get_alignment_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get alignment records for a plan"""
        pass
    
    @abstractmethod
    def add_alignment_record(self, plan_id: int, alignment_data: Dict[str, Any]) -> bool:
        """Add new alignment record"""
        pass
    
    @abstractmethod
    def get_alignment_record(self, alignment_id: int) -> Optional[Dict[str, Any]]:
        """Get alignment record by ID"""
        pass
    
    @abstractmethod
    def update_alignment_record(self, alignment_id: int, alignment_data: Dict[str, Any]) -> bool:
        """Update alignment record data"""
        pass
    
    @abstractmethod
    def delete_alignment_record(self, alignment_id: int) -> bool:
        """Delete alignment record"""
        pass
    
    # Misalignment Records Methods
    @abstractmethod
    def get_misalignment_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get misalignment records for a plan"""
        pass
    
    @abstractmethod
    def add_misalignment_record(self, plan_id: int, misalignment_data: Dict[str, Any]) -> bool:
        """Add new misalignment record"""
        pass
    
    @abstractmethod
    def get_misalignment_record(self, misalignment_id: int) -> Optional[Dict[str, Any]]:
        """Get misalignment record by ID"""
        pass
    
    @abstractmethod
    def update_misalignment_record(self, misalignment_id: int, misalignment_data: Dict[str, Any]) -> bool:
        """Update misalignment record data"""
        pass
    
    @abstractmethod
    def delete_misalignment_record(self, misalignment_id: int) -> bool:
        """Delete misalignment record"""
        pass
    
    # Directional Records Methods
    @abstractmethod
    def get_directional_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get directional records for a plan"""
        pass
    
    @abstractmethod
    def get_directionals_final_records(self, plan_id: int) -> List[Dict[str, Any]]:
        """Get final directional records for a plan (status = 'final' or 'approved')"""
        pass
    
    @abstractmethod
    def add_directional_record(self, plan_id: int, directional_data: Dict[str, Any]) -> bool:
        """Add new directional record"""
        pass
    
    @abstractmethod
    def get_directional_record(self, directional_id: int) -> Optional[Dict[str, Any]]:
        """Get directional record by ID"""
        pass
    
    @abstractmethod
    def update_directional_record(self, directional_id: int, directional_data: Dict[str, Any]) -> bool:
        """Update directional record data"""
        pass
    
    @abstractmethod
    def delete_directional_record(self, directional_id: int) -> bool:
        """Delete directional record"""
        pass

    # Workshop Discussions operations
    @abstractmethod
    def get_workshop_discussions(self, plan_id: int, section_type: str = 'preliminary') -> Optional[Dict[str, Any]]:
        """Get workshop discussions for a plan and section type"""
        pass
    
    @abstractmethod
    def save_workshop_discussions(self, plan_id: int, section_type: str, content: str) -> bool:
        """Save workshop discussions"""
        pass
    
    @abstractmethod
    def delete_workshop_discussions(self, plan_id: int, section_type: str) -> bool:
        """Delete workshop discussions"""
        pass

    # Employee operations
    @abstractmethod
    def list_employees(self, company_id: int) -> List[Dict[str, Any]]:
        """List employees for a company"""
        pass

    @abstractmethod
    def get_employee(self, company_id: int, employee_id: int) -> Optional[Dict[str, Any]]:
        """Get employee by ID scoped to a company"""
        pass

    @abstractmethod
    def create_employee(self, company_id: int, employee_data: Dict[str, Any]) -> Optional[int]:
        """Create employee and return new ID"""
        pass

    @abstractmethod
    def update_employee(self, company_id: int, employee_id: int, employee_data: Dict[str, Any]) -> bool:
        """Update employee data"""
        pass

    @abstractmethod
    def delete_employee(self, company_id: int, employee_id: int) -> bool:
        """Delete employee"""
        pass

    # AI Agents configuration operations
    @abstractmethod
    def get_ai_agents(self) -> List[Dict[str, Any]]:
        """List all AI agents configurations"""
        pass

    @abstractmethod
    def get_ai_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a single AI agent configuration by ID"""
        pass

    @abstractmethod
    def create_ai_agent(self, agent_data: Dict[str, Any]) -> bool:
        """Create a new AI agent configuration"""
        pass

    @abstractmethod
    def update_ai_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> bool:
        """Update an existing AI agent configuration"""
        pass

    @abstractmethod
    def delete_ai_agent(self, agent_id: str) -> bool:
        """Delete an AI agent configuration"""
        pass
