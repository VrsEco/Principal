from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List

ALLOWED_SUMMARY_CHANNELS = {"telegram", "whatsapp", "email"}


def _normalize_summary_channels(value):
    if value is None:
        return None
    items = value if isinstance(value, list) else str(value).split(',')
    normalized = []
    for item in items:
        channel = str(item).strip().lower()
        if channel in ALLOWED_SUMMARY_CHANNELS and channel not in normalized:
            normalized.append(channel)
    return normalized or ["telegram"]


class UserCreateSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=6)
    whatsapp: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    instagram: Optional[str] = Field(None, max_length=100)
    summary_delivery_channels: Optional[List[str]] = None
    role: str = Field("collaborator", pattern="^(admin|user|collaborator|consultant|client)$")

    @field_validator('summary_delivery_channels', mode='before')
    @classmethod
    def validate_summary_delivery_channels(cls, value):
        return _normalize_summary_channels(value)


class UserUpdateSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    whatsapp: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    instagram: Optional[str] = Field(None, max_length=100)
    summary_delivery_channels: Optional[List[str]] = None
    role: Optional[str] = Field(None, pattern="^(admin|user|collaborator|consultant|client)$")
    is_active: Optional[bool] = None

    @field_validator('summary_delivery_channels', mode='before')
    @classmethod
    def validate_summary_delivery_channels(cls, value):
        return _normalize_summary_channels(value)

class CompanyRegisterSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., min_length=2)
    cnpj: Optional[str] = None
    legal_name: Optional[str] = None
    segment: Optional[str] = None
