from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import ProcessInstanceCompleteInput


class ProcessInstanceCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class ProcessInstanceCompleteResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class ProcessInstanceCompleteExecutionHandler:
    def __init__(
        self,
        *,
        extract_id_from_code: Callable[[str], Optional[int]],
        parse_completion_date: Callable[[str], Optional[date]],
        today_provider: Callable[[], date],
        load_instance_by_id: Callable[[int], Any],
        load_company_by_id: Callable[[int], Any],
        user_can_access_company: Callable[[int, int], bool],
        commit_changes: Callable[[], None],
    ):
        self._extract_id_from_code = extract_id_from_code
        self._parse_completion_date = parse_completion_date
        self._today_provider = today_provider
        self._load_instance_by_id = load_instance_by_id
        self._load_company_by_id = load_company_by_id
        self._user_can_access_company = user_can_access_company
        self._commit_changes = commit_changes

    def execute(self, request: ProcessInstanceCompleteRequest) -> ProcessInstanceCompleteResult:
        payload = dict(request.payload or {})

        execution_input, input_error = ProcessInstanceCompleteInput.build_from_legacy_payload(payload)
        if input_error:
            return ProcessInstanceCompleteResult(response_text=input_error)
        if not execution_input:
            return ProcessInstanceCompleteResult(
                response_text="Nao consegui interpretar o payload de conclusao da instancia."
            )

        instance_id = self._extract_id_from_code(execution_input.instance_code)
        if not instance_id:
            return ProcessInstanceCompleteResult(
                response_text=f"Nao consegui identificar o ID no codigo '{execution_input.instance_code}'."
            )

        instance = self._load_instance_by_id(instance_id)
        if not instance:
            return ProcessInstanceCompleteResult(
                response_text=f"Instancia de processo com codigo '{execution_input.instance_code}' nao encontrada."
            )

        instance_company_id = getattr(instance, "company_id", None)
        if (
            request.active_company_id
            and instance_company_id
            and instance_company_id != request.active_company_id
            and not self._user_can_access_company(request.user_id, int(instance_company_id))
        ):
            return ProcessInstanceCompleteResult(
                response_text="A instancia informada nao pertence ao contexto da empresa ativa."
            )

        desired_date = None
        if execution_input.completion_date_raw:
            desired_date = self._parse_completion_date(execution_input.completion_date_raw)
            if not desired_date:
                return ProcessInstanceCompleteResult(
                    response_text="Data de finalizacao invalida. Use DD/MM/AAAA ou AAAA-MM-DD."
                )

        final_date = desired_date or self._today_provider()
        if getattr(instance, "status", None) != "completed":
            instance.status = "completed"
        instance.actual_end_date = final_date
        instance.completed_at = datetime.combine(final_date, datetime.min.time())
        self._commit_changes()

        company = self._load_company_by_id(getattr(instance, "company_id", 0))
        company_code = str(getattr(company, "client_code", "") or "").strip() or "CP"
        instance_code = (
            str(getattr(instance, "instance_code", "") or "").strip()
            or f"{company_code}.C.{getattr(instance, 'process_id', '-')}.{getattr(instance, 'id', '-')}"
        )
        title = str(getattr(instance, "title", "") or "").strip() or f"Instancia {getattr(instance, 'id', '-')}"

        return ProcessInstanceCompleteResult(
            response_text=(
                f"A instancia de processo com o codigo \"{instance_code}\" foi concluida com sucesso!\n\n"
                f"- Instancia: {title}\n"
                f"- Data de Conclusao: {final_date.isoformat()}"
            )
        )
