"""Regras determinísticas de auditoria financeira, sempre isoladas por empresa."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from models import db
from models.financial import FinancialChartAccount, FinancialCounterparty, FinancialEntry, FinancialSettlement
from models.internal_audit import AuditPoint

SOURCE_MODULE = "audit_financial_analyzer"
RULE_COUNTERPARTY_CLASSIFICATION = "counterparty_classification_divergence"
RULE_EMPLOYEE_CLASSIFICATION = "employee_payment_unexpected_classification"
RULE_DUPLICATE_REFERENCE = "duplicate_payment_reference_divergence"


@dataclass(frozen=True)
class FinancialAuditCandidate:
    rule_id: str
    fingerprint: str
    title: str
    description: str
    severity: str
    subject_id: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "subject_id": self.subject_id,
            "metadata": self.metadata,
        }


class InternalAuditFinancialAnalyzer:
    """Detecta hipóteses; nunca altera lançamentos ou liquidações financeiras."""

    @classmethod
    def analyze(cls, company_id: int) -> list[FinancialAuditCandidate]:
        if not company_id:
            raise ValueError("company_id é obrigatório.")
        rows = (
            db.session.query(FinancialSettlement, FinancialEntry)
            .join(FinancialEntry, FinancialEntry.id == FinancialSettlement.financial_entry_id)
            .filter(
                FinancialSettlement.company_id == company_id,
                FinancialEntry.company_id == company_id,
                FinancialSettlement.settlement_status == "posted",
                FinancialEntry.entry_type == "payable",
                FinancialEntry.movement_nature == "debit",
                FinancialSettlement.deleted_at.is_(None),
                FinancialEntry.deleted_at.is_(None),
            )
            .all()
        )
        counterparties = {
            item.id: item
            for item in FinancialCounterparty.query.filter_by(company_id=company_id).all()
        }
        accounts = {
            item.id: item
            for item in FinancialChartAccount.query.filter_by(company_id=company_id).all()
        }
        return cls.detect(rows, counterparties=counterparties, accounts=accounts)

    @classmethod
    def detect(
        cls,
        rows: Iterable[tuple[Any, Any]],
        *,
        counterparties: dict[int, Any],
        accounts: dict[int, Any],
    ) -> list[FinancialAuditCandidate]:
        normalized = list(rows)
        candidates: list[FinancialAuditCandidate] = []
        candidates.extend(cls._counterparty_classification(normalized, counterparties, accounts))
        candidates.extend(cls._employee_classification(normalized, counterparties, accounts))
        candidates.extend(cls._duplicate_reference(normalized, accounts))
        return candidates

    @staticmethod
    def _account_label(account: Any) -> str:
        return str(getattr(account, "name", "") or "").casefold()

    @classmethod
    def _counterparty_classification(cls, rows, counterparties, accounts):
        groups: dict[int, list[tuple[Any, Any]]] = defaultdict(list)
        for settlement, entry in rows:
            if getattr(entry, "counterparty_id", None) and getattr(entry, "chart_account_id", None):
                groups[entry.counterparty_id].append((settlement, entry))
        result = []
        for counterparty_id, items in groups.items():
            classifications = sorted({entry.chart_account_id for _, entry in items})
            if len(classifications) < 2:
                continue
            counterparty = counterparties.get(counterparty_id)
            name = getattr(counterparty, "name", None) or f"destinatário #{counterparty_id}"
            labels = [getattr(accounts.get(item), "name", None) or f"conta #{item}" for item in classifications]
            fingerprint = f"{RULE_COUNTERPARTY_CLASSIFICATION}:{counterparty_id}:{','.join(map(str, classifications))}"
            result.append(FinancialAuditCandidate(
                RULE_COUNTERPARTY_CLASSIFICATION, fingerprint,
                f"Classificações divergentes para {name}",
                "Foram identificados pagamentos ao mesmo destinatário com classificações financeiras distintas. Validar se a diversidade é justificada.",
                "medium", items[0][0].id,
                {"counterparty_id": counterparty_id, "counterparty_name": name, "chart_account_ids": classifications, "chart_account_names": labels, "settlement_ids": [s.id for s, _ in items]},
            ))
        return result

    @classmethod
    def _employee_classification(cls, rows, counterparties, accounts):
        result = []
        allowed_terms = ("salári", "folha", "pró-labore", "pro-labore", "viagem", "diária", "diaria", "reembolso")
        for settlement, entry in rows:
            counterparty = counterparties.get(getattr(entry, "counterparty_id", None))
            metadata = getattr(counterparty, "metadata_json", None) or {}
            if not metadata.get("employee_id"):
                continue
            account = accounts.get(getattr(entry, "chart_account_id", None))
            label = cls._account_label(account)
            if any(term in label for term in allowed_terms):
                continue
            fingerprint = f"{RULE_EMPLOYEE_CLASSIFICATION}:{settlement.id}:{getattr(entry, 'chart_account_id', None)}"
            result.append(FinancialAuditCandidate(
                RULE_EMPLOYEE_CLASSIFICATION, fingerprint,
                f"Pagamento de colaborador fora das classes previstas: {getattr(counterparty, 'name', 'destinatário')}",
                "Pagamento vinculado a colaborador foi classificado fora das categorias salário, folha, viagem, diária ou reembolso. Validar a natureza e a aprovação.",
                "high", settlement.id,
                {"employee_id": metadata["employee_id"], "counterparty_id": counterparty.id, "counterparty_name": counterparty.name, "chart_account_id": getattr(entry, "chart_account_id", None), "chart_account_name": getattr(account, "name", None), "settlement_id": settlement.id, "financial_entry_id": entry.id},
            ))
        return result

    @classmethod
    def _duplicate_reference(cls, rows, accounts):
        groups: dict[tuple[int, str], list[tuple[Any, Any]]] = defaultdict(list)
        for settlement, entry in rows:
            reference = str(getattr(settlement, "external_reference", "") or "").strip().casefold()
            bank_account_id = getattr(settlement, "bank_account_id", None)
            if reference and bank_account_id and getattr(entry, "chart_account_id", None):
                groups[(bank_account_id, reference)].append((settlement, entry))
        result = []
        for (bank_account_id, reference), items in groups.items():
            classifications = sorted({entry.chart_account_id for _, entry in items})
            if len(items) < 2 or len(classifications) < 2:
                continue
            fingerprint = f"{RULE_DUPLICATE_REFERENCE}:{bank_account_id}:{reference}:{','.join(map(str, classifications))}"
            result.append(FinancialAuditCandidate(
                RULE_DUPLICATE_REFERENCE, fingerprint,
                "Referência de pagamento repetida com classificações divergentes",
                "A mesma referência bancária foi encontrada mais de uma vez na mesma conta bancária com classificações diferentes. Verificar duplicidade, rateio ou erro de classificação.",
                "high", items[0][0].id,
                {"bank_account_id": bank_account_id, "external_reference": reference, "chart_account_ids": classifications, "chart_account_names": [getattr(accounts.get(item), "name", None) or f"conta #{item}" for item in classifications], "settlement_ids": [s.id for s, _ in items]},
            ))
        return result

    @classmethod
    def materialize_points(cls, company_id: int) -> dict[str, Any]:
        """Cria apenas novos pontos; candidatos pré-existentes permanecem imutáveis."""
        candidates = cls.analyze(company_id)
        existing = AuditPoint.query.filter_by(company_id=company_id, origin_type="analyzer", source_module=SOURCE_MODULE).all()
        fingerprints = {str((point.metadata_json or {}).get("fingerprint")) for point in existing}
        created = []
        for candidate in candidates:
            if candidate.fingerprint in fingerprints:
                continue
            point = AuditPoint(
                company_id=company_id, title=candidate.title, description=candidate.description,
                origin_type="analyzer", source_module=SOURCE_MODULE,
                subject_type="financial_settlement", subject_id=candidate.subject_id,
                severity=candidate.severity, status="open",
                metadata_json={**candidate.metadata, "rule_id": candidate.rule_id, "fingerprint": candidate.fingerprint},
            )
            db.session.add(point)
            created.append(point)
        if created:
            db.session.commit()
        return {"candidates": [item.to_dict() for item in candidates], "created_points": [item.to_dict() for item in created], "created_count": len(created)}
