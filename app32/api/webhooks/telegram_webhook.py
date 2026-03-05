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

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)


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


def _fallback_root_menu(company_id):
    try:
        from src.intelligence.menu_engine import list_menu_options

        roots = list_menu_options(
            company_id=company_id,
            parent_code=None,
            include_inactive=False,
            include_global=True,
        )
        if not roots:
            return "Nenhuma opcao de menu ativa encontrada."

        lines = ["Selecione uma opcao do menu principal:"]
        for opt in roots:
            lines.append(f"{opt.code} - {opt.title}")
        lines.append("")
        lines.append("Voce pode responder com o codigo (ex: 1.4) ou 'menu 1.4 executar ...'.")
        return "\n".join(lines)
    except Exception as exc:
        logger.exception("Falha ao montar menu fallback no Telegram: %s", exc)
        return "Nao consegui abrir o menu agora. Tente novamente em alguns segundos."


def _resolve_telegram_token():
    """
    Resolve token por ambiente para impedir mistura entre DEV e PRODUCAO.
    - DEV: usa EXCLUSIVAMENTE TELEGRAM_BOT_TOKEN_DEV.
    - PROD: usa TELEGRAM_BOT_TOKEN_PROD ou fallback TELEGRAM_BOT_TOKEN.
    """
    telegram_env = (os.environ.get("TELEGRAM_ENV") or "").strip().lower()
    flask_env = (os.environ.get("FLASK_ENV") or os.environ.get("FLASK_CONFIG") or "").strip().lower()
    is_prod = telegram_env in {"prod", "production", "live"} or flask_env in {"prod", "production"}
    if is_prod:
        prod_token = os.environ.get("TELEGRAM_BOT_TOKEN_PROD") or os.environ.get("TELEGRAM_BOT_TOKEN")
        return prod_token, "PROD"

    is_dev = telegram_env in {"dev", "development", "local", "test"} or flask_env in {"dev", "development", "default", "testing"}

    if is_dev:
        dev_token = os.environ.get("TELEGRAM_BOT_TOKEN_DEV")
        return dev_token, "DEV"

    prod_token = os.environ.get("TELEGRAM_BOT_TOKEN_PROD") or os.environ.get("TELEGRAM_BOT_TOKEN")
    return prod_token, "PROD"


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
                try:
                    bot.send_message(message.chat.id, msg, parse_mode='Markdown')
                except:
                    bot.send_message(message.chat.id, msg)
                return
            
            # 2. Identify Company Context
            company_id = get_best_company_id(user)

            # Fluxo rápido: confirmação de envio por e-mail após resumo truncado.
            try:
                from services.proactive_service import try_handle_summary_email_confirmation

                handled_email_confirm, email_confirm_response = try_handle_summary_email_confirmation(
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

                try:
                    bot.send_message(message.chat.id, email_confirm_response, parse_mode='HTML')
                except Exception:
                    bot.send_message(message.chat.id, email_confirm_response)
                return
            
            # Se encontrou o usuário: enviar confirmação imediata para reduzir percepção de latência.
            try:
                bot.send_message(
                    message.chat.id,
                    "Aguarde, processando sua solicitação.",
                    reply_to_message_id=message.message_id
                )
            except Exception as ack_err:
                logger.debug(f"Falha ao enviar mensagem intermediária de processamento: {ack_err}")

            # Mantém também a ação de digitação enquanto processa.
            try:
                bot.send_chat_action(message.chat.id, 'typing')
            except: pass
            
            # 3. Executa o Agente com Contexto Unificado (@ARQUITETO)
            from src.intelligence.execution import run_agent_with_context, extract_response_text
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
                logger.info(
                    "MENU INTERCEPT [TELEGRAM]: user=%s company=%s thread=%s message=%r",
                    user.id, company_id, thread_id, user_msg
                )
            elif menu_like:
                # Garantia operacional: mensagem de menu nunca cai no LLM.
                response_text = _fallback_root_menu(company_id)
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
                metadata_json={"thread_id": thread_id, "contact": "sapiens", "telegram_id": telegram_id, "agent": final_agent_name}
            ))
            db.session.commit()

            # 5. Responde ao Telegram (Utilizando HTML para maior robustez @ARQUITETO)
            try:
                # Converte Markdown básico para HTML se necessário, ou apenas manda como HTML
                # telebot suporta parse_mode='HTML'
                # Markdown do gpt-4o às vezes quebra o parse_mode='Markdown' do Telegram (v2)
                bot.send_message(message.chat.id, response_text, parse_mode='HTML')
            except Exception as html_err:
                logger.warning(f"Erro ao enviar via HTML: {html_err}. Tentando Markdown.")
                try:
                    bot.send_message(message.chat.id, response_text, parse_mode='Markdown')
                except:
                    bot.send_message(message.chat.id, response_text)
                
        except Exception as e:
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
                    logger.info(f"✅ Erro escalonado via Ticket #{action.id}")
            except Exception as esc_err:
                logger.error(f"Falha catastrófica ao escalonar erro: {esc_err}")

            if bot:
                bot.send_message(message.chat.id, "Desculpe, ocorreu um erro interno ao processar sua solicitação no Gestão Versus. O time de engenharia foi notificado.", reply_to_message_id=message.message_id)

# Rota HTTP (Webhook) que será chamada pelo servidor do Telegram
@telegram_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
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

        # Captura diferentes tipos de update com texto.
        incoming_message = None
        for attr in ("message", "edited_message", "channel_post", "edited_channel_post"):
            candidate = getattr(update, attr, None)
            if candidate and getattr(candidate, "text", None):
                incoming_message = candidate
                break

        # Iniciar thread separada para não causar timeout no servidor do Telegram
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
        return f"Internal Error Logged: {str(e)}", 500

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

    # @ARQUITETO: não removemos webhook antes de setar.
    # Em caso de falha de rede temporária no boot, remover antes causa outage total.
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
