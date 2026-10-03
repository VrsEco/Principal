"""Read-only diagnostic pilot. Authorization remains in the MCP policy wrapper."""
from typing import Optional, Sequence


class FinancialReconciliationDiagnosticService:
    # Additional restriction for the approved investigation, not a grant.
    COMPANY_ID = 9

    @staticmethod
    def _validate(company_id, **ids):
        if type(company_id) is not int or company_id != FinancialReconciliationDiagnosticService.COMPANY_ID:
            return "Diagnóstico de conciliação restrito à empresa autorizada."
        if any(type(value) is not int or value <= 0 for value in ids.values()):
            return "IDs do diagnóstico devem ser inteiros positivos."
        return None

    @staticmethod
    def list_batches(*, company_id: int):
        error = FinancialReconciliationDiagnosticService._validate(company_id)
        if error:
            return None, error
        from services.financial_import_service import FinancialImportService

        items, error = FinancialImportService.list_import_batches(
            company_id=company_id, allowed_company_ids=(company_id,),
        )
        if error:
            return None, error
        return {"items": items, "count": len(items)}, None

    @staticmethod
    def get_batch(*, company_id: int, batch_id: int, row_ids: Optional[Sequence[int]] = None):
        error = FinancialReconciliationDiagnosticService._validate(company_id, batch_id=batch_id)
        if error:
            return None, error
        if row_ids is not None:
            if not isinstance(row_ids, (list, tuple)) or not row_ids or len(row_ids) > 100:
                return None, "Informe de 1 a 100 IDs de linhas para o diagnóstico."
            error = FinancialReconciliationDiagnosticService._validate(
                company_id, **{str(index): value for index, value in enumerate(row_ids)},
            )
            if error:
                return None, error
        from services.financial_import_service import FinancialImportService

        result, error = FinancialImportService.get_import_batch(
            company_id=company_id, batch_id=batch_id, allowed_company_ids=(company_id,),
        )
        if error:
            return None, error
        if row_ids is None:
            return result, None
        selected = set(row_ids)
        rows = [row for row in result["rows"] if row["id"] in selected]
        if {row["id"] for row in rows} != selected:
            return None, "Linha não encontrada no lote e na empresa autorizados."
        return {
            "batch": result["batch"],
            "rows": rows,
            "matches": [item for item in result["matches"] if item["import_row_id"] in selected],
            "suggestions": [item for item in result["suggestions"] if item["import_row_id"] in selected],
        }, None

    @staticmethod
    def get_settlement(*, company_id: int, settlement_id: int):
        error = FinancialReconciliationDiagnosticService._validate(company_id, settlement_id=settlement_id)
        if error:
            return None, error
        from models.financial import FinancialSettlement
        from services.financial_service import FinancialService

        settlement = FinancialSettlement.query.filter(
            FinancialSettlement.id == settlement_id,
            FinancialSettlement.company_id == company_id,
            FinancialSettlement.deleted_at.is_(None),
        ).first()
        if not settlement:
            return None, "Baixa não encontrada no escopo da empresa autorizada."
        return {"item": FinancialService.serialize_settlement(settlement, include_components=True)}, None
