from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Tuple

from models.process import ProcessInstance
from services.financial_automation_service import FinancialAutomationService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialProcessTriggerService:
    @staticmethod
    def dispatch_for_instance(
        *,
        company_id: int,
        process_instance_id: int,
        trigger_status: Optional[str] = None,
        event_name: str = "manual_dispatch",
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        instance = ProcessInstance.query.filter(
            ProcessInstance.id == process_instance_id,
            ProcessInstance.company_id == company_id,
        ).first()
        if not instance:
            return None, "Instância de processo não encontrada no escopo da empresa."

        result, error = FinancialAutomationService.apply_rules_to_instance(
            company_id=company_id,
            process_instance_id=process_instance_id,
            trigger_status=trigger_status or instance.status,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        result["event_name"] = event_name
        return result, None

    @staticmethod
    def dispatch_batch(
        *,
        company_id: int,
        process_instance_ids: List[int],
        trigger_status: str,
        event_name: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Dict:
        results = []
        errors = []
        for instance_id in process_instance_ids:
            result, error = FinancialProcessTriggerService.dispatch_for_instance(
                company_id=company_id,
                process_instance_id=instance_id,
                trigger_status=trigger_status,
                event_name=event_name,
                allowed_company_ids=allowed_company_ids,
            )
            if error:
                errors.append({"process_instance_id": instance_id, "error": error})
            else:
                results.append(result)

        payload = {
            "company_id": company_id,
            "event_name": event_name,
            "trigger_status": trigger_status,
            "processed_instances": len(process_instance_ids),
            "success_count": len(results),
            "error_count": len(errors),
            "results": results,
            "errors": errors,
        }
        if errors:
            logger.warning("Trigger financeiro em lote com falhas: %s", payload)
        return payload
