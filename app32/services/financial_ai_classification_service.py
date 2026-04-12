from __future__ import annotations

import os
from decimal import Decimal
from typing import Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field

from models import db
from models.financial import (
    FinancialClassificationMemory,
    FinancialClassificationRule,
    FinancialClassificationSuggestion,
    FinancialImportBatch,
    FinancialImportRow,
)
from services.financial_catalog_service import FinancialCatalogService
from services.financial_service import FinancialService
from utils.integration_settings import resolve_ai_runtime_config


class FinancialAISuggestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str = Field(..., pattern="^(memory|rule|new)$")
    source_id: Optional[int] = None
    score: Decimal = Field(..., ge=0, le=1)
    reason: str = Field(default="")
    entry_type: Optional[str] = None
    movement_nature: Optional[str] = None
    chart_account_id: Optional[int] = None
    cost_center_id: Optional[int] = None
    activity_id: Optional[int] = None
    process_instance_id: Optional[int] = None
    routine_id: Optional[int] = None
    counterparty_hint: Optional[str] = None


class FinancialAISuggestionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: List[FinancialAISuggestionItem] = Field(default_factory=list)


class FinancialAIClassificationService:
    """IA ranqueadora para classificação financeira com fallback seguro."""

    @staticmethod
    def _get_llm():
        runtime = resolve_ai_runtime_config()
        api_key = runtime.get("api_key")
        if not api_key:
            return None
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=runtime.get("model") or os.getenv("FINANCIAL_CLASSIFIER_MODEL", "gpt-4o-mini"),
            temperature=0,
            api_key=api_key,
        ).with_structured_output(FinancialAISuggestionDecision)

    @staticmethod
    def _build_prompt(
        *,
        row: FinancialImportRow,
        batch: FinancialImportBatch,
        memories: Sequence[FinancialClassificationMemory],
        rules: Sequence[FinancialClassificationRule],
    ) -> str:
        lines = [
            "CONTEXTO DO ITEM FINANCEIRO:",
            f"- lote={batch.batch_code}",
            f"- fonte={batch.source_type}",
            f"- descricao={row.description or '-'}",
            f"- fornecedor={row.counterparty_name or '-'}",
            f"- documento={row.document_number or '-'}",
            f"- referencia_bancaria={row.bank_reference or '-'}",
            f"- valor={row.amount or '-'}",
            f"- natureza={row.movement_nature or '-'}",
            "",
            "MEMORIAS DO CLIENTE:",
        ]
        if memories:
            for item in memories[:8]:
                lines.append(
                    f"- memory_id={item.id}; fornecedor={item.supplier_name or '-'}; "
                    f"descricao={item.description_pattern or '-'}; "
                    f"entry_type={item.entry_type or '-'}; nature={item.movement_nature or '-'}; "
                    f"conta={item.chart_account_id or '-'}; centro={item.cost_center_id or '-'}; "
                    f"atividade={item.activity_id or '-'}; instancia={item.process_instance_id or '-'}; "
                    f"score_hist={item.confidence_score or '-'}; confirmacoes={item.times_confirmed}"
                )
        else:
            lines.append("- nenhuma")

        lines.append("")
        lines.append("REGRAS DO CLIENTE:")
        if rules:
            for item in rules[:8]:
                lines.append(
                    f"- rule_id={item.id}; campo={item.field_name}; op={item.operator}; valor={item.match_value}; "
                    f"entry_type={item.entry_type or '-'}; nature={item.movement_nature or '-'}; "
                    f"conta={item.chart_account_id or '-'}; centro={item.cost_center_id or '-'}; "
                    f"atividade={item.activity_id or '-'}; instancia={item.process_instance_id or '-'}"
                )
        else:
            lines.append("- nenhuma")

        lines.extend(
            [
                "",
                "TAREFA:",
                "Retorne no máximo 3 sugestões ranqueadas para classificar este item financeiro.",
                "Use source_kind=memory quando a sugestão vier de uma memória recebida.",
                "Use source_kind=rule quando a sugestão vier de uma regra recebida.",
                "Use source_kind=new apenas se precisar compor uma hipótese nova.",
                "Não invente source_id quando usar memory/rule.",
                "Prefira sugestões explicáveis e aderentes ao histórico do cliente.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _persist_ai_suggestions(
        *,
        company_id: int,
        batch_id: int,
        row_id: int,
        decision: FinancialAISuggestionDecision,
    ) -> List[FinancialClassificationSuggestion]:
        FinancialClassificationSuggestion.query.filter(
            FinancialClassificationSuggestion.company_id == company_id,
            FinancialClassificationSuggestion.import_row_id == row_id,
            FinancialClassificationSuggestion.source_layer == "ai",
        ).delete(synchronize_session=False)

        created: List[FinancialClassificationSuggestion] = []
        for rank, item in enumerate(decision.suggestions[:3], start=1):
            suggestion = FinancialClassificationSuggestion(
                company_id=company_id,
                import_batch_id=batch_id,
                import_row_id=row_id,
                rank_position=rank,
                source_layer="ai",
                score=item.score,
                reason=item.reason,
                suggested_payload_json={
                    "entry_type": item.entry_type,
                    "movement_nature": item.movement_nature,
                    "chart_account_id": item.chart_account_id,
                    "cost_center_id": item.cost_center_id,
                    "activity_id": item.activity_id,
                    "process_instance_id": item.process_instance_id,
                    "routine_id": item.routine_id,
                    "counterparty_hint": item.counterparty_hint,
                },
                metadata_json={
                    "source_kind": item.source_kind,
                    "source_id": item.source_id,
                },
            )
            db.session.add(suggestion)
            created.append(suggestion)
        return created

    @staticmethod
    def rank_batch_with_ai(
        *,
        batch_id: int,
        company_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        llm = FinancialAIClassificationService._get_llm()
        if llm is None:
            return None, "OPENAI_API_KEY/AI_API_KEY não configurada para classificação por IA."

        batch = FinancialImportBatch.query.filter(
            FinancialImportBatch.id == batch_id,
            FinancialImportBatch.company_id == company_id,
            FinancialImportBatch.deleted_at.is_(None),
        ).first()
        if not batch:
            return None, "Lote de importação não encontrado no escopo da empresa."

        rows = FinancialImportRow.query.filter(
            FinancialImportRow.company_id == company_id,
            FinancialImportRow.import_batch_id == batch_id,
            FinancialImportRow.deleted_at.is_(None),
        ).order_by(FinancialImportRow.row_number.asc()).all()
        memories = FinancialClassificationMemory.query.filter(
            FinancialClassificationMemory.company_id == company_id,
            FinancialClassificationMemory.is_active.is_(True),
            FinancialClassificationMemory.deleted_at.is_(None),
        ).order_by(FinancialClassificationMemory.times_confirmed.desc()).all()
        rules = FinancialClassificationRule.query.filter(
            FinancialClassificationRule.company_id == company_id,
            FinancialClassificationRule.is_active.is_(True),
            FinancialClassificationRule.deleted_at.is_(None),
        ).order_by(FinancialClassificationRule.priority.asc()).all()

        from langchain_core.messages import HumanMessage, SystemMessage

        created_count = 0
        try:
            for row in rows:
                prompt = FinancialAIClassificationService._build_prompt(
                    row=row,
                    batch=batch,
                    memories=memories,
                    rules=rules,
                )
                decision = llm.invoke(
                    [
                        SystemMessage(
                            content=(
                                "Você é um classificador financeiro determinístico assistido por IA.\n"
                                "Sua tarefa é ranquear até 3 possibilidades de classificação para um item financeiro.\n"
                                "Use apenas campos fornecidos e preserve aderência a memórias e regras do cliente."
                            )
                        ),
                        HumanMessage(content=prompt),
                    ]
                )
                created = FinancialAIClassificationService._persist_ai_suggestions(
                    company_id=company_id,
                    batch_id=batch_id,
                    row_id=row.id,
                    decision=decision,
                )
                for suggestion in created:
                    suggestion.suggested_payload_json = FinancialCatalogService.enrich_reference_payload(
                        company_id=company_id,
                        payload=suggestion.suggested_payload_json or {},
                        counterparty_text=row.counterparty_name,
                        description_text=row.description,
                        bank_reference=row.bank_reference,
                    )
                created_count += len(created)

            db.session.commit()
            items = FinancialClassificationSuggestion.query.filter(
                FinancialClassificationSuggestion.company_id == company_id,
                FinancialClassificationSuggestion.import_batch_id == batch_id,
                FinancialClassificationSuggestion.source_layer == "ai",
                FinancialClassificationSuggestion.deleted_at.is_(None),
            ).order_by(
                FinancialClassificationSuggestion.import_row_id.asc(),
                FinancialClassificationSuggestion.rank_position.asc(),
            ).all()
            return {
                "batch_id": batch_id,
                "created_count": created_count,
                "items": [item.to_dict() for item in items],
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao gerar ranking por IA: {str(exc)}"
