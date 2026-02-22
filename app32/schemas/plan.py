from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class PlanSectionStatusUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    status: str = Field(..., pattern="^(pending|in_progress|completed)$")


class PlanParticipantCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    user_id: Optional[int] = None
    employee_id: Optional[int] = None
    role: str = Field("viewer", pattern="^(owner|editor|viewer)$")
    meta_data: Optional[Dict[str, Any]] = None


class PlanDriverCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    type: str = Field(..., pattern="^(driver|opportunity|threat)$")
    description: str = Field(..., min_length=5)
    priority: str = Field("medium", pattern="^(low|medium|high)$")
    meta_data: Optional[Dict[str, Any]] = None


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    company_id: int
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    mode: str = Field("growth", pattern="^(growth|implantation)$")
    status: str = Field("draft", pattern="^(draft|active|archived)$")
    meta_data: Optional[Dict[str, Any]] = None


class PlanUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|archived)$")
    progress: Optional[int] = Field(None, ge=0, le=100)
    meta_data: Optional[Dict[str, Any]] = None
