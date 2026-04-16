from __future__ import annotations

from typing import Any

from models import db, AgentMessage


class AgentConversationService:
    """Boundary canônico Route -> Service -> Intelligence para o chat de agentes."""

    @classmethod
    def chat_with_agent(cls, *, user_id: int, company_id: int | None, message: str, contact: str) -> dict[str, Any]:
        normalized_message = str(message or "").strip()
        normalized_contact = str(contact or "sapiens").strip().lower() or "sapiens"
        if not normalized_message:
            raise ValueError("Mensagem vazia. Informe o que deseja executar.")

        previous_outbound_count = AgentMessage.query.filter_by(
            user_id=user_id,
            company_id=company_id,
            direction="outbound",
            channel="platform",
        ).count()

        processed_message = normalized_message
        agent_type = "work_agent_squad"
        if normalized_contact == "engineering" and "[CANAL ENGENHARIA]" not in normalized_message:
            processed_message = f"[CANAL ENGENHARIA] {normalized_message}"
            agent_type = "engineering_squad"
        elif normalized_contact == "factory" and "[SAPIENS FACTORY]" not in normalized_message:
            processed_message = f"[SAPIENS FACTORY] {normalized_message}"

        thread_id = f"web_{user_id}_{normalized_contact}"
        inbound = AgentMessage(
            company_id=company_id,
            user_id=user_id,
            agent_type=agent_type,
            agent_name="Usuário",
            direction="inbound",
            content=normalized_message,
            channel="platform",
            metadata_json={"contact": normalized_contact, "thread_id": thread_id},
        )
        db.session.add(inbound)
        db.session.commit()

        from src.intelligence.execution import extract_response_text, run_agent_with_context

        response = run_agent_with_context(
            user_id=user_id,
            user_msg=processed_message,
            channel="web",
            thread_id=thread_id,
            company_id=company_id,
            metadata={"agent_type": agent_type, "contact": normalized_contact},
        )

        final_text = extract_response_text(response)
        if normalized_contact == "sapiens" and previous_outbound_count == 0:
            user_first_name = str(getattr(getattr(inbound, "user", None), "name", "") or "").strip().split(" ")[0]
            if not user_first_name:
                try:
                    from models import User
                    user = User.query.get(int(user_id))
                    user_first_name = str(getattr(user, "name", "") or "").strip().split(" ")[0]
                except Exception:
                    user_first_name = ""
            if user_first_name:
                lowered = final_text.strip().lower()
                if not lowered.startswith(("olá", "ola", "bom dia", "boa tarde", "boa noite")):
                    final_text = f"Olá, {user_first_name}!\n\n{final_text}"
        fallback_agent = "engineering_squad" if normalized_contact == "engineering" else "sapiens"
        agent_executor = response.get("next_node") or fallback_agent
        if agent_executor == "end":
            agent_executor = fallback_agent
        menu_metadata = dict(response.get("menu_metadata") or {})

        outbound_metadata = {"agent": agent_executor, "contact": normalized_contact, "thread_id": thread_id}
        outbound_metadata.update(menu_metadata)
        outbound = AgentMessage(
            company_id=company_id,
            user_id=user_id,
            agent_type=agent_type,
            agent_name=agent_executor,
            direction="outbound",
            content=final_text,
            channel="platform",
            metadata_json=outbound_metadata,
        )
        db.session.add(outbound)
        db.session.commit()
        return {"response": final_text, "agent": agent_executor, "thread_id": thread_id, "menu_metadata": menu_metadata}
