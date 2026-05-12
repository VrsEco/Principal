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
    company_ids: Optional[List[int]] = None
    role: str = Field("collaborator", pattern="^(admin|user|collaborator|consultant|client)$")

    @field_validator('summary_delivery_channels', mode='before')
    @classmethod
    def validate_summary_delivery_channels(cls, value):
        return _normalize_summary_channels(value)

    @field_validator('company_ids', mode='before')
    @classmethod
    def validate_company_ids(cls, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise ValueError("company_ids deve ser uma lista de IDs")

        normalized = []
        for item in value:
            company_id = int(item)
            if company_id <= 0:
                raise ValueError("company_ids deve conter apenas IDs positivos")
            if company_id not in normalized:
                normalized.append(company_id)
        return normalized


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


class UserChannelTestSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    channel: str = Field(...)
    recipient: Optional[str] = Field(None, max_length=255)
    temporary_password: Optional[str] = Field(None, min_length=6, max_length=128)

    @field_validator('channel')
    @classmethod
    def validate_channel(cls, value):
        normalized = str(value or '').strip().lower()
        allowed = {'email', 'whatsapp', 'telegram', 'instagram'}
        if normalized not in allowed:
            raise ValueError('Canal de teste inválido')
        return normalized

    @field_validator('recipient', mode='before')
    @classmethod
    def validate_recipient(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator('temporary_password', mode='before')
    @classmethod
    def validate_temporary_password(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class UserProfileUpdateSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., min_length=2, max_length=100)
    whatsapp: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    instagram: Optional[str] = Field(None, max_length=100)
    summary_delivery_channels: Optional[List[str]] = None

    @field_validator('summary_delivery_channels', mode='before')
    @classmethod
    def validate_summary_delivery_channels(cls, value):
        return _normalize_summary_channels(value)

    @field_validator('whatsapp', 'telegram', 'instagram', mode='before')
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class UserPasswordChangeSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    old_password: str = Field(..., min_length=1, max_length=255)
    new_password: str = Field(..., min_length=6, max_length=255)
    confirm_password: str = Field(..., min_length=6, max_length=255)


class UserMcpTokenConfigSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    company_id: Optional[int] = None
    surface: str = Field("user", pattern="^(user)$")
    client_name: Optional[str] = Field(None, max_length=120)
    runtime: Optional[str] = Field("claude", pattern="^(codex|claude|antigravity|other)$")
    squad: Optional[str] = Field("squad_cliente", pattern="^(engineering|squad_cliente|squad_versus)$")

    @field_validator('company_id', mode='before')
    @classmethod
    def normalize_company_id(cls, value):
        if value in (None, "", 0, "0"):
            return None
        company_id = int(value)
        if company_id <= 0:
            raise ValueError("company_id deve ser positivo")
        return company_id

    @field_validator('client_name', mode='before')
    @classmethod
    def normalize_client_name(cls, value):
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator('runtime', 'squad', mode='before')
    @classmethod
    def normalize_optional_choice(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized or None
