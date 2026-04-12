from flask import request, jsonify, Blueprint
import telebot
import os
import json
import logging
import traceback
from datetime import datetime
from threading import Thread

# Import LangGraph
from src.intelligence.work_agents.graph import work_agent_graph
from src.intelligence.tools import escalate_technical_issue
from utils.integration_settings import resolve_telegram_bot_token, resolve_webhook_secret
from utils.security import consume_rate_limit, get_request_ip, webhook_secret_verified

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'


def _normalize_text_basic(value: str) -> str:
    return (value or "").strip().lower()


def _is_menu_like_message(text: str) -> bool:
    lower = _normalize_text_basic(text)
    if not lower:
        return False
    return (
        lower == "menu"
        or lower.startswith("menu ")
        or lower == "/menu"
        or lower.startswith("/menu ")
    )


def _is_non_critical_telegram_delivery_error(exc: Exception) -> bool:
    text = _normalize_text_basic(str(exc))
    known_fragments = (
        "chat not found",
        "bot was blocked by the user",
        "user is deactivated",
        "have no rights to send a message",
    )
    return any(fragment in text for fragment in known_fragments)


def _safe_send_telegram_message(
    chat_id,
    text: str,
    *,
    parse_mode: str | None = None,
    reply_to_message_id: int | None = None,
    log_level: int = logging.WARNING,
) -> bool:
    if not bot:
        logger.warning("Tentativa de envio Telegram sem bot ativo.")
        return False

    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id

    try:
        bot.send_message(**payload)
        return True
    except Exception as exc:
        if _is_non_critical_telegram_delivery_error(exc):
            logger.warning(
                "Entrega Telegram ignorada para chat %s: %s",
                chat_id,
                exc,
            )
            return False
        logger.log(
            log_level,
            "Falha ao enviar mensagem Telegram para chat %s: %s",
            chat_id,
            exc,
        )
        return False


def _safe_send_telegram_with_fallbacks(
    chat_id,
    text: str,
    *attempts: dict,
) -> bool:
    if not attempts:
        attempts = ({},)
    for attempt in attempts:
        if _safe_send_telegram_message(chat_id, text, **attempt):
            return True
    return False


def _safe_send_chat_action(chat_id, action: str) -> bool:
    if not bot:
        return False
    try:
        bot.send_chat_action(chat_id, action)
        return True
    except Exception as exc:
        if _is_non_critical_telegram_delivery_error(exc):
            logger.warning("Ação Telegram ignorada para chat %s: %s", chat_id, exc)
            return False
        logger.debug("Falha ao enviar chat action Telegram: %s", exc)
        return False


def _fallback_root_menu(company_id):
    try:
        from src.intelligence.menu_engine import list_menu_options
        from src.intelligence.workflows.presenters import build_root_menu_message

        roots = list_menu_options(
            company_id=company_id,
            parent_code=None,
            include_inactive=False,
            include_global=True,
        )
        return build_root_menu_message(
            [f"{opt.code} - {opt.title}" for opt in roots],
            channel="telegram",
        )
    except Exception as exc:
        logger.exception("Falha ao montar menu fallback no Telegram: %s", exc)
        from src.intelligence.workflows.presenters import build_menu_recovery_message
        return build_menu_recovery_message(channel="telegram")


def _resolve_telegram_token():
    """
    Resolve token por ambiente para impedir mistura entre DEV e PRODUCAO.
    - DEV: usa EXCLUSIVAMENTE TELEGRAM_BOT_TOKEN_DEV.
    - PROD: usa TELEGRAM_BOT_TOKEN_PROD ou fallback TELEGRAM_BOT_TOKEN.
    """
    return resolve_telegram_bot_token()


TOKEN, TOKEN_CONTEXT = _resolve_telegram_token()
if not TOKEN:
    logger.warning(
        "Telegram bot desativado para contexto %s. Configure o token correto no ambiente.",
        TOKEN_CONTEXT
    )
    bot = None
else:
    bot = telebot.TeleBot(TOKEN, threaded=False)

def process_telegram_message(app, message: telebot.types.Message):
    """
    Processa a mensagem em background na thread do LangGraph.
    Recebe 'app' para rodar dentro do contexto já instanciado, evitar recriar app.
    """
    from models import db
    from models.user import User

    if not bot:
        logger.warning("process_telegram_message chamado sem bot/token ativo.")
        return

    with app.app_context():
        try:
            telegram_id = str(message.from_user.id)
            user_msg = message.text

            logger.info(f"Mensagem recebida do Telegram ID {telegram_id}: {user_msg}")

            # 1. Resolve Identity (@ARQUITETO)
            from src.intelligence.identity import resolve_user_identity, get_best_company_id
            user = resolve_user_identity(telegram_id, 'telegram')

            if not user:
                # Fallback: Usuário não vinculado. Mandar mensagem pedindo vinculo.
                msg = (
                    "Olá! Eu sou o Sapiens, do Gestão Versus. 🤖\n\n"
                    "Parece que seu Telegram ainda não está vinculado à sua conta no sistema.\n"
                    f"Para me autorizar, acesse o sistema Gestão Versus, vá em seu perfil e informe seu Telegram ID: `{telegram_id}`"
                )
                _safe_send_telegram_with_fallbacks(
                    message.chat.id,
                    msg,
                    {"parse_mode": "Markdown"},
                    {},
                )
                return

            # 2. Identify Company Context
            company_id = get_best_company_id(user)

            # Fluxo rápido: confirmação de envio por e-mail após resumo truncado.
            try:
                from services.proactive_service import try_handle_summary_followup

                handled_email_confirm, email_confirm_response = try_handle_summary_followup(
                    user=user,
                    company_id=company_id,
                    incoming_text=user_msg,
                    channel="telegram",
                )
            except Exception as email_confirm_err:
                logger.exception("Falha ao processar confirmação de e-mail do resumo: %s", email_confirm_err)
                handled_email_confirm, email_confirm_response = False, None

            if handled_email_confirm and email_confirm_response:
                from models.agent_message import AgentMessage

                thread_id = f"tg_{telegram_id}"
                db.session.add(AgentMessage(
                    company_id=company_id,
                    user_id=user.id,
                    agent_type='work_agent_squad',
                    agent_name='Usuário',
                    direction='inbound',
                    channel='telegram',
                    content=user_msg,
                    metadata_json={"thread_id": thread_id, "contact": "sapiens", "telegram_id": telegram_id}
                ))
                db.session.add(AgentMessage(
                    company_id=company_id,
                    user_id=user.id,
                    agent_type='work_agent_squad',
                    agent_name='sapiens',
                    direction='outbound',
                    channel='telegram',
                    content=email_confirm_response,
                    metadata_json={"thread_id": thread_id, "contact": "sapiens", "telegram_id": telegram_id, "flow": "summary_email_confirmation"}
                ))
                db.session.commit()

                _safe_send_telegram_with_fallbacks(
                    message.chat.id,
                    email_confirm_response,
                    {"parse_mode": "HTML"},
                    {},
                )
                return

            # Se encontrou o usuário: enviar confirmação imediata para reduzir percepção de latência.
            try:
                from src.intelligence.workflows.presenters import build_processing_ack_message
                _safe_send_telegram_message(
                    message.chat.id,
                    build_processing_ack_message(channel="telegram"),
                    reply_to_message_id=message.message_id,
                    parse_mode='HTML',
                    log_level=logging.DEBUG,
                )
            except Exception as ack_err:
                logger.debug(f"Falha ao enviar mensagem intermediária de processamento: {ack_err}")

            # Mantém também a ação de digitação enquanto processa.
            try:
                _safe_send_chat_action(message.chat.id, 'typing')
            except Exception: pass

            # 3. Executa o Agente com Contexto Unificado (@ARQUITETO)
            from src.intelligence.execution import (
                run_agent_with_context,
                extract_response_text,
                _capture_workflow_usage_from_execution,
            )
            from src.intelligence.menu_engine import handle_menu_message

            # Usamos tg_{telegram_id} para manter histórico vinculado ao chat do Telegram
            thread_id = f"tg_{telegram_id}"
            final_agent_name = "sapiens"
            menu_like = _is_menu_like_message(user_msg)

            # Hardening Telegram:
            # Força interceptação de menu no próprio webhook para evitar fallback indevido ao LLM.
            menu_result = None
            try:
                menu_result = handle_menu_message(
                    user_id=user.id,
                    company_id=company_id,
                    channel="telegram",
                    thread_id=thread_id,
                    message=user_msg,
                )
            except Exception as menu_err:
                logger.exception("Erro no handle_menu_message do Telegram: %s", menu_err)

            if menu_result and menu_result.handled:
                response_text = menu_result.response_text or _fallback_root_menu(company_id)
                menu_metadata = dict(menu_result.metadata or {})
                _capture_workflow_usage_from_execution(
                    user_id=user.id,
                    company_id=company_id,
                    channel="telegram",
                    thread_id=thread_id,
                    user_msg=user_msg,
                    response_text=response_text,
                    menu_metadata=menu_metadata,
                )
                logger.info(
                    "MENU INTERCEPT [TELEGRAM]: user=%s company=%s thread=%s message=%r",
                    user.id, company_id, thread_id, user_msg
                )
            elif menu_like:
                # Garantia operacional: mensagem de menu nunca cai no LLM.
                response_text = _fallback_root_menu(company_id)
                menu_metadata = {}
                logger.warning(
                    "MENU FALLBACK FORCADO [TELEGRAM]: user=%s company=%s thread=%s message=%r",
                    user.id, company_id, thread_id, user_msg
                )
            else:
                effective_msg = menu_result.override_message or user_msg
                response = run_agent_with_context(
                    user_id=user.id,
                    user_msg=effective_msg,
                    channel="telegram",
                    thread_id=thread_id,
                    company_id=company_id,
                    metadata={"contact": "sapiens", "telegram_id": telegram_id}
                )
                response_text = extract_response_text(response)
                menu_metadata = dict(response.get("menu_metadata") or {})

                # Recupera o nome do agente que deu a palavra final
                final_agent_name = response.get("next_node") or "sapiens"
                if final_agent_name == "end":
                    final_agent_name = "sapiens"  # Fallback padrão

            # 4. Auditoria de Mensagem (Log no Banco de Dados)
            from models.agent_message import AgentMessage

            # Mensagem do Usuário
            db.session.add(AgentMessage(
                company_id=company_id,
                user_id=user.id,
                agent_type='work_agent_squad',
                agent_name='Usuário',
                direction='inbound',
                channel='telegram',
                content=user_msg,
                metadata_json={"thread_id": thread_id, "contact": "sapiens", "telegram_id": telegram_id}
            ))
            # Resposta da IA
            db.session.add(AgentMessage(
                company_id=company_id,
                user_id=user.id,
                agent_type='work_agent_squad',
                agent_name=final_agent_name,
                direction='outbound',
                channel='telegram',
                content=response_text,
                metadata_json={
                    "thread_id": thread_id,
                    "contact": "sapiens",
                    "telegram_id": telegram_id,
                    "agent": final_agent_name,
                    **menu_metadata,
                }
            ))
            db.session.commit()

            # 5. Responde ao Telegram (Utilizando HTML para maior robustez @ARQUITETO)
            _safe_send_telegram_with_fallbacks(
                message.chat.id,
                response_text,
                {"parse_mode": "HTML"},
                {"parse_mode": "Markdown"},
                {},
            )

        except Exception as e:
            if _is_non_critical_telegram_delivery_error(e):
                logger.warning("Entrega Telegram descartada sem escalonamento técnico: %s", e)
                return

            tb = traceback.format_exc()
            logger.error(f"❌ Erro crítico no Telegram Webhook: {str(e)}\n{tb}")

            # Tentar escalonar para o Time de Engenharia (@AI_ENGINEER / @ARQUITETO)
            try:
                with app.app_context():
                    error_msg = f"Crash no Webhook do Telegram: {str(e)}"

                    # 🔍 Recuperar company_id para conformidade multi-tenancy (@ARQUITETO)
                    from models.company import Company
                    from models.agent_action import AgentAction
                    from models import db

                    effective_company_id = None
                    if 'user' in locals() and user:
                        from src.intelligence.identity import get_best_company_id
                        effective_company_id = get_best_company_id(user)

                    if not effective_company_id:
                        first_company = Company.query.first()
                        effective_company_id = first_company.id if first_company else 1

                    action = AgentAction(
                        type='technical_fix',
                        status='pending',
                        requesting_agent='telegram_webhook',
                        handling_agent='engineering_squad',
                        title='Crash no Webhook do Telegram',
                        description=error_msg,
                        payload={"error": str(e), "traceback": tb, "telegram_id": telegram_id, "file": "api/webhooks/telegram_webhook.py"},
                        company_id=effective_company_id,
                        user_id=getattr(user, 'id', None) if 'user' in locals() and user else None
                    )
                    db.session.add(action)
                    db.session.commit()
                    try:
                        from services.agent_action_backlog_service import ensure_backlog_task_for_action

                        ensure_backlog_task_for_action(action, autocommit=True)
                    except Exception:
                        logger.exception(
                            "Falha ao espelhar technical_fix #%s no backlog AA.J.31",
                            action.id,
                        )
                    logger.info(f"✅ Erro escalonado via Ticket #{action.id}")
            except Exception as esc_err:
                logger.error(f"Falha catastrófica ao escalonar erro: {esc_err}")

            if bot:
                from src.intelligence.workflows.presenters import build_internal_error_message
                _safe_send_telegram_message(
                    message.chat.id,
                    build_internal_error_message(channel="telegram"),
                    reply_to_message_id=message.message_id,
                    parse_mode='HTML',
                )

# Rota HTTP (Webhook) que será chamada pelo servidor do Telegram
@telegram_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        if not webhook_secret_verified(
            expected_secret=resolve_webhook_secret("telegram"),
            header_names=["X-Telegram-Bot-Api-Secret-Token", "X-Webhook-Secret", "X-Telegram-Secret"],
            query_names=["secret", "token"],
        ):
            return "Forbidden", 403

        if not consume_rate_limit("webhook.telegram", get_request_ip(), limit=120, window_seconds=60):
            return "Too Many Requests", 429

        if not bot:
            logger.warning("Webhook Telegram recebido, mas bot esta inativo para este ambiente.")
            return '', 200

        if not request.is_json:
            logger.warning("Webhook Telegram recebeu Content-Type invalido: %s", request.content_type)
            return "Unsupported Media Type", 415

        payload = request.get_json(silent=True)
        if not payload:
            logger.warning("Webhook Telegram recebeu payload JSON vazio/invalido.")
            return "Invalid JSON", 400

        update = telebot.types.Update.de_json(json.dumps(payload))
        if not update:
            logger.warning("Webhook Telegram recebeu update vazio.")
            return '', 200

        incoming_message = None
        for attr in ("message", "edited_message", "channel_post", "edited_channel_post"):
            candidate = getattr(update, attr, None)
            if candidate and getattr(candidate, "text", None):
                incoming_message = candidate
                break

        if incoming_message:
            from flask import current_app
            app = current_app._get_current_object()
            t = Thread(target=process_telegram_message, args=(app, incoming_message))
            t.start()
        else:
            logger.info("Update Telegram sem mensagem textual; ignorado.")

        return '', 200
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"❌ Erro Crítico na Rota do Webhook: {e}")
        with open('request_debug.log', 'a') as f:
            f.write(f"ERROR: {str(e)}\n{tb}\n")
        return PUBLIC_ERROR_MESSAGE, 500

# Script manual para registrar o webhook no Telegram
def setup_webhook(host_url):
    """
    Seta o Webhook na API do telegram indicando sua URL pública (ngrok/domínio)
    Exemplo: setup_webhook("https://seungrok.ngrok.io/")
    """
    if not TOKEN or not bot:
        logger.error("❌ Não foi possível configurar o Webhook: token Telegram ausente/inativo para contexto %s.", TOKEN_CONTEXT)
        return None

    webhook_url = f"{host_url.rstrip('/')}/webhook/telegram"

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            result = bot.set_webhook(url=webhook_url)
            if result is False:
                raise RuntimeError("Telegram API retornou False no set_webhook.")

            info = bot.get_webhook_info()
            current_url = getattr(info, "url", "") or ""
            if current_url != webhook_url:
                raise RuntimeError(f"Webhook divergente após set: '{current_url}'")

            logger.info(f"✅ Webhook do Telegram registrado com sucesso: {webhook_url}")
            return webhook_url
        except Exception as e:
            logger.error(
                "❌ Erro ao registrar Webhook do Telegram (tentativa %s/%s): %s",
                attempt,
                max_attempts,
                str(e),
            )
            if attempt < max_attempts:
                try:
                    from time import sleep
                    sleep(2)
                except Exception:
                    pass

    logger.error("❌ Falha final ao registrar Webhook do Telegram para URL: %s", webhook_url)
    return None
