from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class UserCreateSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(..., min_length=6)
    whatsapp: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    instagram: Optional[str] = Field(None, max_length=100)
    role: str = Field("user", pattern="^(admin|user|client)$")

class UserUpdateSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    whatsapp: Optional[str] = Field(None, max_length=20)
    telegram: Optional[str] = Field(None, max_length=50)
    instagram: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|user|client)$")
    is_active: Optional[bool] = None

class CompanyRegisterSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(..., min_length=2)
    cnpj: Optional[str] = None
    legal_name: Optional[str] = None
    segment: Optional[str] = None
