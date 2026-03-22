from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyAccessExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int
    channel: str = "web"


class CompanyAccessExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class CompanyAccessExecutionHandler:
    def __init__(
        self,
        *,
        load_accessible_companies_for_user: Callable[[int], List[Any]],
        format_report: Callable[..., str],
    ):
        self._load_accessible_companies_for_user = load_accessible_companies_for_user
        self._format_report = format_report

    def execute(self, request: CompanyAccessExecutionRequest) -> CompanyAccessExecutionResult:
        companies = [
            company
            for company in self._load_accessible_companies_for_user(request.user_id)
            if bool(getattr(company, "is_active", True))
        ]
        if not companies:
            return CompanyAccessExecutionResult(
                response_text="Nenhuma empresa vinculada ao seu usuário."
            )

        return CompanyAccessExecutionResult(
            response_text=self._format_report(
                companies=companies,
                channel=request.channel or "web",
            )
        )
