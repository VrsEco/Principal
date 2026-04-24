from __future__ import annotations

import csv
import hashlib
import io
import logging
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Sequence, Tuple

from models import db
from models.financial import (
    FinancialClassificationSuggestion,
    FinancialEntry,
    FinancialImportBatch,
    FinancialImportRow,
    FinancialReconciliationMatch,
)
from schemas.financial import FinancialImportBatchInput, FinancialImportRowInput
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService


logger = logging.getLogger(__name__)


class FinancialImportService:
    """Hub determinístico de staging para importações financeiras."""

    IMPORT_TEMPLATE_COLUMNS = [
        {"key": "tipo_registro", "label": "Tipo de Registro *", "required": True, "example": "agendamento"},
        {"key": "tipo_titulo", "label": "Tipo do Título *", "required": True, "example": "Pagar ou Receber"},
        {"key": "historico", "label": "Histórico *", "required": True, "example": "Mensalidade escritório março/2026"},
        {"key": "numero_documento", "label": "Número do Documento", "required": False, "example": "NF-10293"},
        {"key": "favorecido", "label": "Favorecido *", "required": True, "example": "Fornecedor XPTO"},
        {"key": "documento_favorecido", "label": "CPF/CNPJ Favorecido", "required": False, "example": "12345678000199"},
        {"key": "valor", "label": "Valor *", "required": True, "example": "1500,75"},
        {"key": "competencia", "label": "Competência *", "required": True, "example": "31/03/2026"},
        {"key": "vencimento", "label": "Vencimento", "required": False, "example": "10/04/2026"},
        {"key": "data_lancamento", "label": "Data do Lançamento", "required": False, "example": "31/03/2026"},
        {"key": "plano_conta", "label": "Plano de Conta", "required": False, "example": "3.01.001 ou 145"},
        {"key": "centro_resultado", "label": "Centro de Resultado", "required": False, "example": "2.03.001 ou 245"},
        {"key": "projeto_processo", "label": "Projeto / Processo", "required": False, "example": "PRJ-001 Implantação ERP"},
        {"key": "correcao_financeira", "label": "Correção Financeira", "required": False, "example": "Padrão"},
        {"key": "desconto", "label": "Desconto", "required": False, "example": "Desconto Comercial"},
        {"key": "conta_bancaria", "label": "Conta Bancária", "required": False, "example": "001 - Banco do Brasil"},
        {"key": "observacoes", "label": "Observações", "required": False, "example": "Registro importado da planilha do cliente"},
    ]

    @staticmethod
    def _parse_decimal(value: Any) -> Optional[Decimal]:
        if value in (None, ""):
            return None
        if isinstance(value, Decimal):
            return value

        text = str(value).strip().replace("R$", "").replace(" ", "")
        if not text:
            return None

        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            return Decimal(text)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_date(value: Any) -> Optional[datetime.date]:
        if value in (None, ""):
            return None
        if hasattr(value, "isoformat") and hasattr(value, "year"):
            return value

        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _guess_movement_nature(amount: Optional[Decimal]) -> Optional[str]:
        if amount is None:
            return None
        return "credit" if amount >= 0 else "debit"

    @staticmethod
    def _normalize_row(row_number: int, raw_payload: Dict[str, Any]) -> FinancialImportRowInput:
        normalized = {str(key).strip().lower(): value for key, value in (raw_payload or {}).items()}
        amount = (
            FinancialImportService._parse_decimal(normalized.get("amount"))
            or FinancialImportService._parse_decimal(normalized.get("valor"))
            or FinancialImportService._parse_decimal(normalized.get("valor_documento"))
            or FinancialImportService._parse_decimal(normalized.get("amount_br"))
        )
        description = (
            normalized.get("description")
            or normalized.get("descricao")
            or normalized.get("memo")
            or normalized.get("historico")
            or normalized.get("payee")
        )
        occurred_on = (
            FinancialImportService._parse_date(normalized.get("occurred_on"))
            or FinancialImportService._parse_date(normalized.get("data"))
            or FinancialImportService._parse_date(normalized.get("date"))
            or FinancialImportService._parse_date(normalized.get("posted_at"))
        )
        due_date = (
            FinancialImportService._parse_date(normalized.get("due_date"))
            or FinancialImportService._parse_date(normalized.get("vencimento"))
        )
        document_number = (
            normalized.get("document_number")
            or normalized.get("documento")
            or normalized.get("doc")
            or normalized.get("checknum")
        )
        bank_reference = (
            normalized.get("bank_reference")
            or normalized.get("fitid")
            or normalized.get("ref")
            or normalized.get("reference")
        )
        counterparty_name = (
            normalized.get("counterparty_name")
            or normalized.get("favorecido")
            or normalized.get("payee")
            or normalized.get("name")
        )
        movement_nature = normalized.get("movement_nature") or FinancialImportService._guess_movement_nature(amount)
        if amount is not None and amount < 0:
            amount = abs(amount)

        error_message = None
        processing_status = "staged"
        if not description:
            error_message = "Descrição não identificada na linha importada."
            processing_status = "rejected"
        elif amount is None:
            error_message = "Valor financeiro não identificado na linha importada."
            processing_status = "rejected"

        return FinancialImportRowInput(
            company_id=0,
            row_number=row_number,
            processing_status=processing_status,
            document_number=document_number,
            description=description,
            occurred_on=occurred_on,
            due_date=due_date,
            amount=amount,
            movement_nature=movement_nature,
            bank_reference=bank_reference,
            counterparty_name=counterparty_name,
            raw_payload=raw_payload,
            normalized_payload={
                "description": description,
                "occurred_on": occurred_on.isoformat() if occurred_on else None,
                "due_date": due_date.isoformat() if due_date else None,
                "amount": float(amount) if amount is not None else None,
                "movement_nature": movement_nature,
                "document_number": document_number,
                "bank_reference": bank_reference,
                "counterparty_name": counterparty_name,
            },
            error_message=error_message,
        )

    @staticmethod
    def _enrich_row_catalogs(company_id: int, row: FinancialImportRow) -> None:
        normalized = dict(row.normalized_payload or {})
        enriched = FinancialCatalogService.enrich_reference_payload(
            company_id=company_id,
            payload=normalized,
            counterparty_text=row.counterparty_name,
            description_text=row.description,
            bank_reference=row.bank_reference,
        )
        row.normalized_payload = enriched
        if row.processing_status == "staged" and (
            enriched.get("counterparty_id")
            or enriched.get("chart_account_id")
            or enriched.get("cost_center_id")
            or enriched.get("bank_account_id")
        ):
            row.processing_status = "validated"

    @staticmethod
    def _parse_csv_bytes(file_bytes: bytes, delimiter: str = ",") -> List[Dict[str, Any]]:
        text = file_bytes.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return [dict(row) for row in reader]

    @staticmethod
    def _parse_xlsx_bytes(file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("openpyxl não está disponível para leitura XLSX.") from exc

        workbook = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(item).strip() if item is not None else f"column_{idx+1}" for idx, item in enumerate(rows[0])]
        items: List[Dict[str, Any]] = []
        for values in rows[1:]:
            if values is None:
                continue
            item = {}
            for idx, header in enumerate(headers):
                item[header] = values[idx] if idx < len(values) else None
            if any(value not in (None, "") for value in item.values()):
                items.append(item)
        return items

    @staticmethod
    def _parse_xls_bytes(file_bytes: bytes) -> List[Dict[str, Any]]:
        try:
            import xlrd
        except ImportError as exc:
            raise RuntimeError("xlrd não está disponível para leitura XLS.") from exc

        workbook = xlrd.open_workbook(file_contents=file_bytes)
        if workbook.nsheets <= 0:
            return []

        sheet = workbook.sheet_by_index(0)
        if sheet.nrows <= 0:
            return []

        headers = [
            str(sheet.cell_value(0, idx)).strip() if sheet.cell_value(0, idx) not in (None, "") else f"column_{idx+1}"
            for idx in range(sheet.ncols)
        ]
        items: List[Dict[str, Any]] = []
        for row_idx in range(1, sheet.nrows):
            item: Dict[str, Any] = {}
            has_value = False
            for col_idx, header in enumerate(headers):
                cell = sheet.cell(row_idx, col_idx)
                value: Any = cell.value
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        value = xlrd.xldate.xldate_as_datetime(value, workbook.datemode)
                    except Exception:
                        pass
                elif cell.ctype == xlrd.XL_CELL_NUMBER and float(value).is_integer():
                    value = int(value)
                if value not in (None, ""):
                    has_value = True
                item[header] = value
            if has_value:
                items.append(item)
        return items

    @staticmethod
    def _extract_ofx_tag(block: str, tag: str) -> Optional[str]:
        match = re.search(rf"<{tag}>([^\r\n<]+)", block, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _parse_ofx_bytes(file_bytes: bytes) -> List[Dict[str, Any]]:
        text = file_bytes.decode("latin-1", errors="ignore")
        blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, flags=re.IGNORECASE | re.DOTALL)
        items: List[Dict[str, Any]] = []
        for block in blocks:
            dtposted = FinancialImportService._extract_ofx_tag(block, "DTPOSTED")
            items.append(
                {
                    "date": dtposted[:8] if dtposted else None,
                    "amount": FinancialImportService._extract_ofx_tag(block, "TRNAMT"),
                    "fitid": FinancialImportService._extract_ofx_tag(block, "FITID"),
                    "memo": FinancialImportService._extract_ofx_tag(block, "MEMO"),
                    "payee": FinancialImportService._extract_ofx_tag(block, "NAME"),
                    "document_number": FinancialImportService._extract_ofx_tag(block, "CHECKNUM"),
                }
            )
        return items

    @staticmethod
    def _parse_source_rows(source_type: str, file_bytes: bytes) -> List[Dict[str, Any]]:
        source = (source_type or "").lower()
        if source == "csv":
            return FinancialImportService._parse_csv_bytes(file_bytes, delimiter=",")
        if source == "csc":
            return FinancialImportService._parse_csv_bytes(file_bytes, delimiter=";")
        if source == "xlsx":
            return FinancialImportService._parse_xlsx_bytes(file_bytes)
        if source == "xls":
            return FinancialImportService._parse_xls_bytes(file_bytes)
        if source == "ofx":
            return FinancialImportService._parse_ofx_bytes(file_bytes)
        raise ValueError("Fonte de importação não suportada. Utilize CSV, XLS, XLSX ou OFX.")

    @staticmethod
    def build_import_template() -> Tuple[Optional[bytes], Optional[str]]:
        try:
            from openpyxl import Workbook
            from openpyxl.drawing.image import Image as XLImage
            from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
            from openpyxl.worksheet.datavalidation import DataValidation
        except ImportError as exc:
            return None, f"openpyxl não está disponível para geração do modelo XLSX: {exc}"

        workbook = Workbook()
        ws_instructions = workbook.active
        ws_instructions.title = "Instruções"
        ws_data = workbook.create_sheet("Importação")
        ws_instructions.sheet_view.showGridLines = False

        title_fill = PatternFill("solid", fgColor="0F766E")
        header_fill = PatternFill("solid", fgColor="E0F2FE")
        required_fill = PatternFill("solid", fgColor="DCFCE7")
        optional_fill = PatternFill("solid", fgColor="F8FAFC")
        border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1"),
        )

        for column, width in {
            "A": 8,
            "B": 14,
            "C": 14,
            "D": 14,
            "E": 4,
            "F": 14,
            "G": 14,
            "H": 14,
            "I": 14,
        }.items():
            ws_instructions.column_dimensions[column].width = width

        ws_instructions.row_dimensions[1].height = 30
        ws_instructions.row_dimensions[2].height = 24
        ws_instructions.row_dimensions[4].height = 22
        ws_instructions.row_dimensions[5].height = 36
        ws_instructions.row_dimensions[7].height = 22

        ws_instructions.merge_cells("A1:D1")
        ws_instructions.merge_cells("A2:D2")
        ws_instructions.merge_cells("A5:I5")

        ws_instructions["A1"] = "Versus Gestão Corporativa"
        ws_instructions["A1"].font = Font(size=16, bold=True, color="0F172A")
        ws_instructions["A1"].alignment = Alignment(vertical="center")
        ws_instructions["A2"] = "Modelo de importação financeira APP32"
        ws_instructions["A2"].font = Font(size=12, bold=True, color="0F766E")
        ws_instructions["A2"].alignment = Alignment(vertical="center")
        ws_instructions["A4"] = "Objetivo"
        ws_instructions["A4"].font = Font(bold=True)
        ws_instructions["A5"] = (
            "Use esta planilha para preparar dados de agendamentos e lançamentos financeiros. "
            "Após preencher, faça o upload no Hub de Importação do APP32."
        )
        ws_instructions["A5"].alignment = Alignment(wrap_text=True, vertical="top")
        ws_instructions["A7"] = "Regras de preenchimento"
        ws_instructions["A7"].font = Font(bold=True)
        rules = [
            "Preencha obrigatoriamente as colunas marcadas com *.",
            "Datas podem ser digitadas como dd/mm/aaaa ou ddmmaaaa.",
            "Valores devem ser informados no padrão brasileiro, por exemplo: 1500,75.",
            "Tipo de Registro: use 'agendamento' para conta a pagar / receber. Use 'lancamento' para conta já paga / já recebida.",
            "Tipo do Título: use 'Pagar' para contas a pagar e 'Receber' para contas a receber.",
            "Plano de Conta, Centro de Resultado e Projeto / Processo: informe apenas itens analíticos. O sistema deve aceitar código completo ou código reduzido. Exemplos: Plano de Conta 3.01.001 ou 145; Centro de Resultado 2.03.001 ou 245.",
            "Em Projeto / Processo, utilize apenas itens habilitados no Financeiro.",
            "Não altere a ordem das colunas da aba Importação.",
        ]
        for offset, rule in enumerate(rules, start=8):
            ws_instructions[f"A{offset}"] = f"{offset - 7}."
            ws_instructions[f"A{offset}"].alignment = Alignment(horizontal="right", vertical="top")
            ws_instructions.merge_cells(f"B{offset}:I{offset}")
            ws_instructions[f"B{offset}"] = rule
            ws_instructions[f"B{offset}"].alignment = Alignment(wrap_text=True, vertical="top")
            ws_instructions.row_dimensions[offset].height = 34 if len(rule) < 120 else 50

        ws_instructions["A18"] = "Legenda"
        ws_instructions["A18"].font = Font(bold=True)
        ws_instructions["A19"] = "Obrigatório"
        ws_instructions["A19"].fill = required_fill
        ws_instructions["A20"] = "Opcional"
        ws_instructions["A20"].fill = optional_fill

        image_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "img")
        logo_candidates = [
            os.path.join(image_dir, "logo-versus-preta.png"),
            os.path.join(image_dir, "logo-versus-clara.png"),
            os.path.join(image_dir, "versus-logo.png"),
            os.path.join(image_dir, "logo-versus.png"),
            os.path.join(image_dir, "logo-versus-slogan.png"),
        ]
        logo_path = next((path for path in logo_candidates if os.path.exists(path)), None)
        if logo_path:
            try:
                image = XLImage(logo_path)
                image.width = 220
                image.height = 39
                ws_instructions.add_image(image, "F1")
            except Exception:
                logger.exception("Falha ao inserir logo no modelo financeiro XLSX")

        for col_idx, column in enumerate(FinancialImportService.IMPORT_TEMPLATE_COLUMNS, start=1):
            cell = ws_data.cell(row=1, column=col_idx, value=column["label"])
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = title_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

            desc = ws_data.cell(row=2, column=col_idx, value="Obrigatório" if column["required"] else "Opcional")
            desc.font = Font(bold=True, color="0F172A")
            desc.fill = required_fill if column["required"] else optional_fill
            desc.alignment = Alignment(horizontal="center", vertical="center")
            desc.border = border

            sample = ws_data.cell(row=3, column=col_idx, value=column["example"])
            sample.font = Font(italic=True, color="475569")
            sample.fill = header_fill
            sample.alignment = Alignment(wrap_text=True)
            sample.border = border

            ws_data.column_dimensions[chr(64 + col_idx if col_idx <= 26 else 65)].width = max(18, min(34, len(column["label"]) + 6))

        ws_data.freeze_panes = "A4"
        ws_data.sheet_view.showGridLines = True

        tipo_registro_validation = DataValidation(
            type="list",
            formula1='"agendamento,lancamento"',
            allow_blank=False,
        )
        tipo_titulo_validation = DataValidation(
            type="list",
            formula1='"Pagar,Receber"',
            allow_blank=False,
        )
        ws_data.add_data_validation(tipo_registro_validation)
        ws_data.add_data_validation(tipo_titulo_validation)
        tipo_registro_validation.add("A4:A500")
        tipo_titulo_validation.add("B4:B500")

        sample_rows = [
            ["agendamento", "Pagar", "Mensalidade coworking março/2026", "NF-10293", "Cowork XPTO", "12345678000199", 1850.75, "31/03/2026", "10/04/2026", "", "3.01.001", "2.03.001", "PRJ-001 Implantação ERP", "Padrão", "", "", "Importado da rotina financeira"],
            ["lancamento", "Pagar", "Tarifa bancária março/2026", "", "Banco do Brasil", "", 25.90, "31/03/2026", "", "31/03/2026", "145", "245", "", "", "", "001 - Conta Movimento", "Despesa direta sem agendamento prévio"],
        ]
        for row_idx, sample_values in enumerate(sample_rows, start=4):
            for col_idx, value in enumerate(sample_values, start=1):
                cell = ws_data.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border
                if col_idx in (7,):
                    cell.number_format = '#,##0.00'
                else:
                    cell.alignment = Alignment(wrap_text=True)

        for row in range(4, 501):
            for col_idx, column in enumerate(FinancialImportService.IMPORT_TEMPLATE_COLUMNS, start=1):
                cell = ws_data.cell(row=row, column=col_idx)
                cell.border = border
                if row > 5 and cell.value in (None, ""):
                    cell.fill = required_fill if column["required"] else optional_fill

        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), None

    @staticmethod
    def create_import_batch(
        *,
        payload: Dict[str, Any],
        file_bytes: bytes,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            data = FinancialImportBatchInput(**payload)
        except Exception as exc:
            return None, f"Payload inválido para lote de importação: {str(exc)}"

        scope_error = FinancialService._ensure_company_scope(data.company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        try:
            parsed_rows = FinancialImportService._parse_source_rows(data.source_type, file_bytes)
        except Exception as exc:
            return None, f"Falha ao interpretar arquivo importado: {str(exc)}"

        try:
            batch = FinancialImportBatch(
                **data.model_dump(),
                file_hash=hashlib.sha256(file_bytes).hexdigest(),
                status="parsed",
            )
            db.session.add(batch)
            db.session.flush()

            staged_rows: List[FinancialImportRow] = []
            valid_rows = 0
            error_rows = 0

            for idx, raw_row in enumerate(parsed_rows, start=1):
                row_input = FinancialImportService._normalize_row(idx, raw_row)
                row_payload = row_input.model_dump()
                row_payload["company_id"] = data.company_id
                row_payload["import_batch_id"] = batch.id
                row = FinancialImportRow(**row_payload)
                db.session.add(row)
                staged_rows.append(row)
                FinancialImportService._enrich_row_catalogs(data.company_id, row)
                fallback_bank_account_id = (data.metadata_json or {}).get("bank_account_id")
                if fallback_bank_account_id and not (row.normalized_payload or {}).get("bank_account_id"):
                    row.normalized_payload = {
                        **(row.normalized_payload or {}),
                        "bank_account_id": int(fallback_bank_account_id),
                    }
                    if row.processing_status == "staged":
                        row.processing_status = "validated"
                if row.processing_status == "rejected":
                    error_rows += 1
                else:
                    valid_rows += 1

            batch.total_rows = len(staged_rows)
            batch.valid_rows = valid_rows
            batch.error_rows = error_rows
            batch.finished_at = datetime.utcnow()

            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "rows": [row.to_dict() for row in staged_rows],
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar lote de importação financeira")
            return None, f"Erro ao criar lote de importação: {str(exc)}"

    @staticmethod
    def list_import_batches(
        *,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batches = FinancialImportBatch.query.filter(
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).order_by(FinancialImportBatch.imported_at.desc(), FinancialImportBatch.id.desc()).all()
        return [batch.to_dict() for batch in batches], None

    @staticmethod
    def get_import_batch(
        *,
        batch_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de importação não encontrado no escopo da empresa."

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch.id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()
        matches = FinancialReconciliationMatch.query.filter(
            FinancialReconciliationMatch.company_id == company_id,
            FinancialReconciliationMatch.import_batch_id == batch.id,
            FinancialReconciliationMatch.deleted_at.is_(None),
        ).order_by(FinancialReconciliationMatch.id.asc()).all()
        suggestions = FinancialClassificationSuggestion.query.filter(
            FinancialClassificationSuggestion.company_id == company_id,
            FinancialClassificationSuggestion.import_batch_id == batch.id,
            FinancialClassificationSuggestion.deleted_at.is_(None),
        ).order_by(
            FinancialClassificationSuggestion.import_row_id.asc(),
            FinancialClassificationSuggestion.rank_position.asc(),
        ).all()
        return {
            "batch": batch.to_dict(),
            "rows": [row.to_dict() for row in rows],
            "matches": [match.to_dict() for match in matches],
            "suggestions": [suggestion.to_dict() for suggestion in suggestions],
        }, None

    @staticmethod
    def _build_entry_payload_from_row(batch: FinancialImportBatch, row: FinancialImportRow) -> Dict[str, Any]:
        normalized = row.normalized_payload or {}
        occurred_on = row.occurred_on or FinancialImportService._parse_date(normalized.get("occurred_on"))
        due_date = row.due_date or FinancialImportService._parse_date(normalized.get("due_date"))

        payload = {
            "company_id": batch.company_id,
            "entry_code": f"{batch.batch_code}-{row.row_number}",
            "entry_type": normalized.get("entry_type") or "bank_movement",
            "movement_nature": normalized.get("movement_nature") or row.movement_nature or "debit",
            "origin_type": batch.source_type,
            "status": "posted",
            "review_status": "pending_review",
            "description": row.description or normalized.get("description") or f"Importação {batch.batch_code} linha {row.row_number}",
            "document_number": row.document_number,
            "external_reference": row.bank_reference,
            "origin_reference": batch.batch_code,
            "competence_date": occurred_on or due_date or batch.imported_at.date(),
            "due_date": due_date,
            "occurred_on": occurred_on,
            "original_amount": row.amount or Decimal("0"),
            "bank_account_id": normalized.get("bank_account_id"),
            "counterparty_id": normalized.get("counterparty_id"),
            "chart_account_id": normalized.get("chart_account_id"),
            "cost_center_id": normalized.get("cost_center_id"),
            "activity_id": normalized.get("activity_id"),
            "process_instance_id": normalized.get("process_instance_id"),
            "routine_id": normalized.get("routine_id"),
            "notes": f"Gerado a partir do lote {batch.batch_code}, linha {row.row_number}.",
            "metadata_json": {
                "import_batch_id": batch.id,
                "import_row_id": row.id,
                "source_type": batch.source_type,
                "counterparty_name": row.counterparty_name,
                "classification_rule_id": normalized.get("classification_rule_id"),
                "classification_rule_name": normalized.get("classification_rule_name"),
                "raw_payload": row.raw_payload or {},
            },
        }
        return FinancialCatalogService.enrich_reference_payload(
            company_id=batch.company_id,
            payload=payload,
            counterparty_text=row.counterparty_name,
            description_text=row.description,
            bank_reference=row.bank_reference,
        )

    @staticmethod
    def process_import_batch(
        *,
        batch_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de importação não encontrado no escopo da empresa."

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch.id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()

        created_count = 0
        skipped_count = 0
        rejected_count = 0

        try:
            for row in rows:
                if row.processing_status == "rejected":
                    rejected_count += 1
                    continue
                if row.created_entry_id:
                    skipped_count += 1
                    continue

                existing = FinancialEntry.query.filter(
                    FinancialEntry.company_id == company_id,
                    FinancialEntry.entry_code == f"{batch.batch_code}-{row.row_number}",
                ).first()
                if existing:
                    row.created_entry_id = existing.id
                    row.processing_status = "imported"
                    skipped_count += 1
                    continue

                payload = FinancialImportService._build_entry_payload_from_row(batch, row)
                entry, error = FinancialService.create_entry(
                    payload=payload,
                    allowed_company_ids=allowed_company_ids,
                )
                if error:
                    row.processing_status = "rejected"
                    row.error_message = error
                    rejected_count += 1
                    continue

                row.created_entry_id = entry.id
                row.processing_status = "imported"
                row.error_message = None
                created_count += 1

            batch.status = "processed_with_errors" if rejected_count else "processed"
            batch.finished_at = datetime.utcnow()
            batch.error_rows = rejected_count
            batch.valid_rows = sum(1 for row in rows if row.processing_status in {"validated", "imported", "staged"})
            db.session.commit()
            return {
                "batch": batch.to_dict(),
                "summary": {
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "rejected_count": rejected_count,
                    "total_rows": len(rows),
                },
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao processar lote financeiro %s", batch_id)
            return None, f"Erro ao processar lote de importação: {str(exc)}"
