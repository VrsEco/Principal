"""Reprocessamento de títulos do ledger que sobraram de faturamentos cancelados.

Antes da correção em `ContractService.cancel_native_billing`, cancelar um faturamento
nativo cancelava só os agendamentos (schedules) e deixava o título (entry) aberto no
contas a receber. Este serviço localiza esses títulos órfãos, gera o relatório de
dry-run e, após aprovação humana, aplica a mesma rotina de cancelamento usada pela
correção (`ContractFinancialService.cancel_billing_titles`).

Ações propostas por faturamento cancelado (grupo = título principal + satélites):
- ``cancelar``: só há baixa automática de retenção (ou nenhuma); pode ser cancelado.
- ``bloqueado``: há baixa real, baixa conciliada ou borderô ativo; NÃO é alterado.
- ``revisar``: inconsistência que exige decisão humana; NÃO é alterado.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Optional

from models import db
from models.contracts import ContractNativeBilling
from models.financial import FinancialEntry, FinancialEntryAllocation, FinancialSettlement
from services.contract_financial_service import ContractFinancialService

ACTION_CANCEL = "cancelar"
ACTION_BLOCKED = "bloqueado"
ACTION_REVIEW = "revisar"
ACTIONS = (ACTION_CANCEL, ACTION_BLOCKED, ACTION_REVIEW)
OPEN_ENTRY_STATUSES = ("draft", "pending_review", "scheduled", "posted", "partially_settled")
RETENTION_TOLERANCE = Decimal("0.01")

CSV_COLUMNS = [
    "entry_id",
    "entry_code",
    "papel",
    "tipo",
    "status",
    "billing_code",
    "contrato",
    "cliente",
    "valor_original",
    "valor_baixado",
    "saldo_aberto",
    "tipo_baixa",
    "vencimento",
    "acao",
    "motivo",
]


def _money(value: Any) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _billing_schedule_ids(billing: ContractNativeBilling) -> list[int]:
    integration = dict((billing.metadata_json or {}).get("financial_integration") or {})
    raw_ids = [integration.get("main_schedule_id")]
    raw_ids.extend(integration.get("satellite_schedule_ids") or [])
    raw_ids.extend(integration.get("cancelled_schedule_ids") or [])
    ids = [ContractFinancialService._normalize_int(item) for item in raw_ids]
    return list(dict.fromkeys(item for item in ids if item))


class OrphanBillingTitlesService:
    @staticmethod
    def _settlement_kind(analysis: dict) -> str:
        has_auto = bool(analysis["automatic_settlements"])
        has_real = bool(analysis["real_settlements"])
        if has_auto and has_real:
            return "mista"
        if has_real:
            return "baixa_real"
        if has_auto:
            return "retencao_automatica"
        return "nenhuma"

    @staticmethod
    def _review_reasons(*, billing: ContractNativeBilling, analyses: list[dict]) -> list[str]:
        reasons: list[str] = []
        retention = _money((billing.metadata_json or {}).get("retention_amount"))
        for analysis in analyses:
            entry = analysis["entry"]
            metadata = dict(entry.metadata_json or {})
            role = metadata.get("financial_role")
            linked_billing_id = ContractFinancialService._normalize_int(metadata.get("contract_native_billing_id"))
            if linked_billing_id and linked_billing_id != billing.id:
                reasons.append(f"{entry.entry_code}: pertence ao faturamento {linked_billing_id}, não ao {billing.id}")
            if role == "main" or (role is None and entry.entry_type == "receivable"):
                automatic = analysis["automatic_amount"]
                if automatic > Decimal("0.00") and abs(automatic - retention) > RETENTION_TOLERANCE:
                    reasons.append(
                        f"{entry.entry_code}: baixa automática R$ {automatic} difere da retenção do faturamento R$ {retention}"
                    )
        return reasons

    @staticmethod
    def scan(*, company_id: int) -> list[dict]:
        """Somente leitura. Um item por faturamento cancelado que ainda tem título ativo."""
        billings = (
            ContractNativeBilling.query.filter(
                ContractNativeBilling.company_id == company_id,
                ContractNativeBilling.status == "cancelled",
            )
            .order_by(ContractNativeBilling.id.asc())
            .all()
        )
        groups: list[dict] = []
        for billing in billings:
            entries = ContractFinancialService.list_entries_for_schedules(
                company_id=company_id, schedule_ids=_billing_schedule_ids(billing)
            )
            if not entries:
                continue
            analyses = [ContractFinancialService.analyze_billing_entry(entry) for entry in entries]
            blocking = [
                f"{item['entry'].entry_code}: {', '.join(item['blocking_reasons'])}"
                for item in analyses
                if item["blocking_reasons"]
            ]
            review = OrphanBillingTitlesService._review_reasons(billing=billing, analyses=analyses)
            if blocking:
                action, reasons = ACTION_BLOCKED, blocking
            elif review:
                action, reasons = ACTION_REVIEW, review
            else:
                action, reasons = ACTION_CANCEL, []
            groups.append({"billing": billing, "analyses": analyses, "action": action, "reasons": reasons})
        return groups

    @staticmethod
    def build_rows(groups: Iterable[dict]) -> list[dict]:
        rows: list[dict] = []
        for group in groups:
            billing = group["billing"]
            contract = billing.contract
            party = billing.party
            for analysis in group["analyses"]:
                entry = analysis["entry"]
                metadata = dict(entry.metadata_json or {})
                original = _money(entry.original_amount)
                settled = analysis["automatic_amount"] + analysis["real_amount"]
                rows.append(
                    {
                        "entry_id": entry.id,
                        "entry_code": entry.entry_code,
                        "papel": "principal" if metadata.get("financial_role") == "main" else "satelite",
                        "tipo": entry.entry_type,
                        "status": entry.status,
                        "billing_code": billing.billing_code,
                        "contrato": getattr(contract, "code", None),
                        "cliente": getattr(party, "name", None),
                        "valor_original": float(original),
                        "valor_baixado": float(settled),
                        "saldo_aberto": float(max(original - settled, Decimal("0.00"))),
                        "tipo_baixa": OrphanBillingTitlesService._settlement_kind(analysis),
                        "vencimento": entry.due_date.isoformat() if entry.due_date else None,
                        "acao": group["action"],
                        "motivo": " | ".join(group["reasons"]),
                    }
                )
        return rows

    @staticmethod
    def summarize(rows: list[dict]) -> dict:
        summary: dict[str, Any] = {"por_acao": {}, "por_acao_receber": {}}
        for action in ACTIONS:
            selected = [row for row in rows if row["acao"] == action]
            receivable = [row for row in selected if row["tipo"] == "receivable"]
            summary["por_acao"][action] = {
                "titulos": len(selected),
                "valor_original": round(sum(row["valor_original"] for row in selected), 2),
                "valor_baixado": round(sum(row["valor_baixado"] for row in selected), 2),
                "saldo_aberto": round(sum(row["saldo_aberto"] for row in selected), 2),
            }
            summary["por_acao_receber"][action] = {
                "titulos": len(receivable),
                "valor_original": round(sum(row["valor_original"] for row in receivable), 2),
                "valor_baixado": round(sum(row["valor_baixado"] for row in receivable), 2),
                "saldo_aberto": round(sum(row["saldo_aberto"] for row in receivable), 2),
            }
        return summary

    @staticmethod
    def write_report(*, rows: list[dict], summary: dict, directory: Path, stem: str, meta: dict) -> dict:
        directory.mkdir(parents=True, exist_ok=True)
        csv_path = directory / f"{stem}.csv"
        json_path = directory / f"{stem}.json"
        with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
        json_path.write_text(
            json.dumps({"meta": meta, "totais": summary, "titulos": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"csv": str(csv_path), "json": str(json_path)}

    @staticmethod
    def ledger_snapshot(*, company_id: int, entries: list[FinancialEntry]) -> list[dict]:
        """Estado completo dos títulos antes de alterar, para permitir reversão."""
        snapshot: list[dict] = []
        for entry in entries:
            settlements = FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id == entry.id,
            ).all()
            allocations = FinancialEntryAllocation.query.filter(
                FinancialEntryAllocation.company_id == company_id,
                FinancialEntryAllocation.financial_entry_id == entry.id,
            ).all()
            snapshot.append(
                {
                    "entry": {**entry.to_dict(), "deleted_at": entry.deleted_at.isoformat() if entry.deleted_at else None},
                    "settlements": [
                        {**item.to_dict(), "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None}
                        for item in settlements
                    ],
                    "allocations": [
                        {**item.to_dict(), "deleted_at": item.deleted_at.isoformat() if item.deleted_at else None}
                        for item in allocations
                    ],
                }
            )
        return snapshot

    @staticmethod
    def ledger_metrics(*, company_id: int) -> dict:
        """Contagem e totais do a receber (e dos títulos de faturamentos ativos) para o antes/depois."""
        open_receivables = FinancialEntry.query.filter(
            FinancialEntry.company_id == company_id,
            FinancialEntry.deleted_at.is_(None),
            FinancialEntry.entry_type == "receivable",
            FinancialEntry.status.in_(OPEN_ENTRY_STATUSES),
        ).all()
        settled_by_entry = OrphanBillingTitlesService._settled_by_entry(company_id, [item.id for item in open_receivables])
        open_original = sum((_money(item.original_amount) for item in open_receivables), Decimal("0.00"))
        open_balance = sum(
            (max(_money(item.original_amount) - settled_by_entry.get(item.id, Decimal("0.00")), Decimal("0.00")) for item in open_receivables),
            Decimal("0.00"),
        )

        active_schedule_ids: list[int] = []
        for billing in ContractNativeBilling.query.filter(
            ContractNativeBilling.company_id == company_id, ContractNativeBilling.status != "cancelled"
        ).all():
            active_schedule_ids.extend(_billing_schedule_ids(billing))
        active_entries = ContractFinancialService.list_entries_for_schedules(
            company_id=company_id, schedule_ids=active_schedule_ids
        )
        active_settled = OrphanBillingTitlesService._settled_by_entry(company_id, [item.id for item in active_entries])
        return {
            "receber_aberto": {
                "titulos": len(open_receivables),
                "valor_original": float(open_original),
                "saldo_aberto": float(open_balance),
            },
            "faturamentos_ativos": {
                "titulos": len(active_entries),
                "valor_original": float(sum((_money(item.original_amount) for item in active_entries), Decimal("0.00"))),
                "valor_baixado": float(sum(active_settled.values(), Decimal("0.00"))),
            },
        }

    @staticmethod
    def _settled_by_entry(company_id: int, entry_ids: list[int]) -> dict[int, Decimal]:
        totals: dict[int, Decimal] = {}
        if not entry_ids:
            return totals
        for start in range(0, len(entry_ids), 500):
            chunk = entry_ids[start : start + 500]
            for settlement in FinancialSettlement.query.filter(
                FinancialSettlement.company_id == company_id,
                FinancialSettlement.financial_entry_id.in_(chunk),
                FinancialSettlement.deleted_at.is_(None),
                FinancialSettlement.settlement_status != "cancelled",
            ).all():
                totals[settlement.financial_entry_id] = totals.get(settlement.financial_entry_id, Decimal("0.00")) + _money(
                    settlement.principal_amount
                )
        return totals

    @staticmethod
    def is_eligible(group: dict, accepted_review_billing_codes: Optional[set[str]] = None) -> bool:
        if group["action"] == ACTION_CANCEL:
            return True
        return group["action"] == ACTION_REVIEW and group["billing"].billing_code in (accepted_review_billing_codes or set())

    @staticmethod
    def execute(
        *,
        company_id: int,
        user_id: int,
        approved_entry_ids: set[int],
        accepted_review_billing_codes: Optional[set[str]] = None,
        log=print,
    ) -> list[dict]:
        """Cancela os grupos aprovados que continuam elegíveis. Um commit por faturamento.

        Elegível = ação ``cancelar`` ou, só para os faturamentos aceitos explicitamente por
        um humano, ação ``revisar``. Nunca ``bloqueado``.
        """
        results: list[dict] = []
        for group in OrphanBillingTitlesService.scan(company_id=company_id):
            billing = group["billing"]
            entry_ids = [item["entry"].id for item in group["analyses"]]
            if not approved_entry_ids.intersection(entry_ids):
                continue
            if not OrphanBillingTitlesService.is_eligible(group, accepted_review_billing_codes):
                log(f"[ignorado] {billing.billing_code}: ação atual '{group['action']}' ({'; '.join(group['reasons'])})")
                results.append({"billing_code": billing.billing_code, "entry_ids": entry_ids, "resultado": f"ignorado_{group['action']}"})
                continue
            if not set(entry_ids).issubset(approved_entry_ids):
                log(f"[ignorado] {billing.billing_code}: títulos do grupo diferem do dry-run aprovado")
                results.append({"billing_code": billing.billing_code, "entry_ids": entry_ids, "resultado": "ignorado_fora_do_dry_run"})
                continue
            try:
                outcome = ContractFinancialService.cancel_billing_titles(
                    company_id=company_id,
                    schedule_ids=_billing_schedule_ids(billing),
                    native_billing=billing,
                    user_id=user_id,
                    reason="Reprocessamento: título órfão de faturamento cancelado",
                )
                metadata = dict(billing.metadata_json or {})
                integration = dict(metadata.get("financial_integration") or {})
                integration["cancelled_entry_ids"] = sorted(
                    set(integration.get("cancelled_entry_ids") or []) | set(outcome["cancelled_entry_ids"])
                )
                integration["reversed_settlement_ids"] = sorted(
                    set(integration.get("reversed_settlement_ids") or []) | set(outcome["reversed_settlement_ids"])
                )
                integration["orphan_titles_reprocessed_at"] = datetime.utcnow().isoformat()
                integration["orphan_titles_reprocessed_by_user_id"] = user_id
                metadata["financial_integration"] = integration
                billing.metadata_json = metadata
                db.session.commit()
                log(
                    f"[ok] {billing.billing_code}: títulos {outcome['cancelled_entry_ids']} cancelados, "
                    f"baixas {outcome['reversed_settlement_ids']} estornadas"
                )
                results.append({"billing_code": billing.billing_code, "entry_ids": entry_ids, "resultado": "cancelado", **outcome})
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                log(f"[erro] {billing.billing_code}: {exc}")
                results.append({"billing_code": billing.billing_code, "entry_ids": entry_ids, "resultado": "erro", "erro": str(exc)})
        return results
