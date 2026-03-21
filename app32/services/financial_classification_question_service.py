from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple

from models import AgentMessage, User, db
from services.financial_classification_hybrid_service import FinancialClassificationHybridService
from services.notification_hub import notification_hub
from services.proactive_service import _build_summary_attempt_order
from services.financial_service import FinancialService


class FinancialClassificationQuestionService:
    """Gera e despacha perguntas operacionais de classificação via Sapiens/canais."""

    @staticmethod
    def build_question_payload(
        *,
        company_id: int,
        import_row_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        items, error = FinancialClassificationHybridService.list_pending_queue(
            company_id=company_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        target = next((item for item in (items or []) if int(item.get("import_row_id") or 0) == int(import_row_id)), None)
        if not target:
            return None, "Linha pendente de classificação não encontrada."

        suggestions = target.get("suggestions") or []
        suggestions_text = []
        for suggestion in suggestions[:3]:
            payload = suggestion.get("suggested_payload_json") or {}
            suggestions_text.append(
                f"- Opção {suggestion.get('rank_position')}: "
                f"tipo={payload.get('entry_type') or '-'}, "
                f"natureza={payload.get('movement_nature') or '-'}, "
                f"conta={payload.get('chart_account_id') or '-'}, "
                f"centro={payload.get('cost_center_id') or '-'}, "
                f"atividade={payload.get('activity_id') or '-'}, "
                f"instância={payload.get('process_instance_id') or '-'} "
                f"(score={round(float(suggestion.get('score') or 0) * 100, 1)}%)"
            )

        body = (
            "Sapiens identificou uma pendência de classificação financeira.\n\n"
            f"Lote: {target.get('import_batch_id')}\n"
            f"Linha: {target.get('row_number')}\n"
            f"Descrição: {target.get('description') or '-'}\n"
            f"Fornecedor: {target.get('counterparty_name') or '-'}\n"
            f"Valor: {target.get('amount') or '-'}\n"
            f"Status da fila: {target.get('queue_status')}\n\n"
            f"Pergunta:\n{target.get('question')}\n\n"
            "Sugestões disponíveis:\n"
            f"{chr(10).join(suggestions_text) if suggestions_text else '- Nenhuma sugestão registrada'}\n\n"
            "Responda com a classificação correta ou confirme uma das opções."
        )

        return {
            "subject": f"Pendência de Classificação Financeira - Linha {target.get('row_number')}",
            "body": body,
            "html_body": None,
            "queue_item": target,
        }, None

    @staticmethod
    def dispatch_question_to_user(
        *,
        company_id: int,
        import_row_id: int,
        user_id: int,
        preferred_channel: Optional[str] = None,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        scope_error = FinancialService._ensure_company_scope(company_id, allowed_company_ids)
        if scope_error:
            return None, scope_error

        payload, error = FinancialClassificationQuestionService.build_question_payload(
            company_id=company_id,
            import_row_id=import_row_id,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error

        user = User.query.get(user_id)
        if not user or not getattr(user, "is_active", False):
            return None, "Usuário de destino não encontrado ou inativo."

        attempt_order = [preferred_channel] if preferred_channel else _build_summary_attempt_order(user)
        if not attempt_order:
            attempt_order = ["platform"]

        delivery_result: Dict[str, Any] = {"success": False, "channel": "platform"}
        selected_channel = "platform"
        if attempt_order and attempt_order[0] != "platform":
            for channel in attempt_order:
                normalized = str(channel or "").strip().lower()
                if normalized == "platform":
                    continue
                if normalized == "email":
                    result = notification_hub.send_email(
                        user.email,
                        payload["subject"],
                        payload["body"],
                        html_body=payload.get("html_body"),
                    )
                else:
                    result = notification_hub.send_to_user(
                        user,
                        normalized,
                        payload["body"],
                        subject=payload["subject"],
                        html_body=payload.get("html_body"),
                        parse_mode="HTML",
                    )
                if result.get("success"):
                    delivery_result = result
                    selected_channel = normalized
                    break

        message = AgentMessage(
            company_id=company_id,
            user_id=user_id,
            agent_type="work_agent_squad",
            agent_name="sapiens",
            direction="outbound",
            channel=selected_channel,
            content=payload["body"],
            metadata_json={
                "contact": "sapiens",
                "thread_id": f"web_{user_id}_sapiens",
                "financial_classification_question": {
                    "import_row_id": import_row_id,
                    "queue_status": payload["queue_item"].get("queue_status"),
                    "preferred_channel": preferred_channel,
                    "delivery_channel": selected_channel,
                },
            },
        )

        try:
            db.session.add(message)
            db.session.commit()
            return {
                "success": True,
                "delivery": delivery_result,
                "delivery_channel": selected_channel,
                "message_id": message.id,
                "payload": payload,
            }, None
        except Exception as exc:
            db.session.rollback()
            return None, f"Erro ao registrar pergunta de classificação: {str(exc)}"
