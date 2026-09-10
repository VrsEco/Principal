from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class CommercialDeliverableV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=2, max_length=160)
    description: str = Field(..., min_length=2)
    acceptance_criterion: str = Field(..., min_length=2)
    evidence_type: str = Field(..., min_length=2, max_length=80)
    responsible_role: str = Field(..., min_length=2, max_length=120)


class CommercialProcessLinkV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: int = Field(..., gt=0)
    role: Literal["market", "sales", "implementation", "delivery", "support", "review"]
    required: bool = True
    owner_verified_at: Optional[datetime] = None


class CommercialIndicatorContractV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indicator_key: str = Field(..., min_length=2, max_length=80)
    name: str = Field(..., min_length=2, max_length=160)
    purpose: str = Field(..., min_length=2)
    frequency: str = Field(..., min_length=2, max_length=80)
    responsible_role: str = Field(..., min_length=2, max_length=120)
    target_rule: Optional[str] = None
    target_pending_reason: Optional[str] = None
    source: str = Field(..., min_length=2, max_length=120)

    @model_validator(mode="after")
    def require_target_or_reason(self):
        if not _normalize_text(self.target_rule) and not _normalize_text(self.target_pending_reason):
            raise ValueError("Informe a regra de meta ou a justificativa para a meta ainda não existir.")
        return self


class CommercialOfferContractV1(BaseModel):
    """Contrato operacional versionado de uma oferta comercial."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    status: Literal["draft", "validated", "active", "retired"] = "draft"
    offer_role: Literal["qualification", "canonical_offer", "sustainment"]
    method_track: Optional[Literal["urgent_need", "business_structuring"]] = None
    icp_summary: str = Field(..., min_length=10)
    buying_triggers: List[str] = Field(..., min_length=1)
    exclusion_criteria: List[str] = Field(default_factory=list)
    sponsor_required: str = Field(..., min_length=2)
    required_participants: List[str] = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=10)
    promised_outcome: str = Field(..., min_length=10)
    scope_in: List[str] = Field(..., min_length=1)
    scope_out: List[str] = Field(..., min_length=1)
    deliverables: List[CommercialDeliverableV1] = Field(..., min_length=1)
    client_dependencies: List[str] = Field(..., min_length=1)
    versus_capabilities: List[str] = Field(..., min_length=1)
    execution_model: Literal["project", "program", "recurring"]
    process_links: List[CommercialProcessLinkV1] = Field(default_factory=list)
    indicator_contract: List[CommercialIndicatorContractV1] = Field(..., min_length=1)
    business_review_policy: str = Field(..., min_length=10)
    closure_criteria: List[str] = Field(..., min_length=1)
    evidence_requirements: List[str] = Field(..., min_length=1)
    pricing_policy: str = Field(..., min_length=10)
    approved_by_user_id: Optional[int] = Field(None, gt=0)
    approved_at: Optional[datetime] = None

    @field_validator(
        "buying_triggers",
        "exclusion_criteria",
        "required_participants",
        "scope_in",
        "scope_out",
        "client_dependencies",
        "versus_capabilities",
        "closure_criteria",
        "evidence_requirements",
        mode="before",
    )
    @classmethod
    def normalize_text_lists(cls, value):
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def validate_governance(self):
        if self.offer_role == "canonical_offer" and not self.method_track:
            raise ValueError("Oferta canônica deve informar o trilho metodológico.")
        if self.offer_role != "canonical_offer" and self.method_track == "urgent_need":
            raise ValueError("O trilho urgent_need é exclusivo de uma oferta canônica.")
        if self.status in {"validated", "active", "retired"}:
            if not self.approved_by_user_id or not self.approved_at:
                raise ValueError("Oferta validada, ativa ou retirada exige aprovação humana registrada.")
        if self.status == "active":
            if not self.process_links:
                raise ValueError("Oferta ativa deve possuir ao menos um processo vinculado.")
            if any(link.required and not link.owner_verified_at for link in self.process_links):
                raise ValueError("Processos obrigatórios da oferta ativa exigem dono verificado.")
        return self


def normalize_contract_catalog_metadata(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata = dict(value or {})
    commercial_contract = metadata.get("commercial_contract_v1")
    if commercial_contract is not None:
        metadata["commercial_contract_v1"] = CommercialOfferContractV1.model_validate(
            commercial_contract
        ).model_dump(mode="json")
    return metadata


class ContractCatalogItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int
    parent_id: Optional[int] = None
    code_suffix: Optional[str] = Field(None, max_length=10)
    name: str = Field(..., min_length=2, max_length=255)
    item_kind: str = Field("service", pattern="^(service|product)$")
    description: Optional[str] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    accepts_contracting: bool = True
    is_active: bool = True
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("code_suffix", "unit_code", mode="before")
    @classmethod
    def normalize_short_text(cls, value):
        return _normalize_text(value)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_long_text(cls, value):
        return _normalize_text(value)

    @field_validator("metadata_json", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        return normalize_contract_catalog_metadata(value)


class ContractCatalogItemUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: Optional[int] = None
    code_suffix: Optional[str] = Field(None, max_length=10)
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    item_kind: Optional[str] = Field(None, pattern="^(service|product)$")
    description: Optional[str] = None
    unit_code: Optional[str] = Field(None, max_length=20)
    accepts_contracting: Optional[bool] = None
    is_active: Optional[bool] = None
    metadata_json: Optional[Dict[str, Any]] = None

    @field_validator("code_suffix", "unit_code", mode="before")
    @classmethod
    def normalize_short_text(cls, value):
        return _normalize_text(value)

    @field_validator("name", "description", mode="before")
    @classmethod
    def normalize_long_text(cls, value):
        return _normalize_text(value)

    @field_validator("metadata_json", mode="before")
    @classmethod
    def validate_metadata(cls, value):
        if value is None:
            return None
        return normalize_contract_catalog_metadata(value)
