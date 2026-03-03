from flask import request, jsonify, Blueprint
import telebot
import os
import logging
import traceback
from datetime import datetime
from threading import Thread

# Import LangGraph
from src.intelligence.work_agents.graph import work_agent_graph
from src.intelligence.tools import escalate_technical_issue

logger = logging.getLogger(__name__)

telegram_bp = Blueprint('telegram', __name__)

# Initialize bot with the specific token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")

bot = telebot.TeleBot(TOKEN, threaded=False)

def process_telegram_message(app, message: telebot.types.Message):
    """
    Processa a mensagem em background na thread do LangGraph.
    Recebe 'app' para rodar dentro do contexto já instanciado, evitar recriar app.
    """
    from models import db
    from models.user import User
    
    with app.app_context():
        try:
            telegram_id = str(message.from_user.id)
            user_msg = message.text
            
            logger.info(f"Mensagem recebida do Telegram ID {telegram_id}: {user_msg}")
            
            # 1. Tentar achar quem é o usuário no Gestão Versus associado a este Telegram ID
            # Por enquanto usando .telegram, mas o banco já deve estar alimentado com isso.
            user = User.query.filter_by(telegram=telegram_id).first()
            
            if not user:
                # Fallback: Usuário não vinculado. Mandar mensagem pedindo vinculo.
                msg = (
                    "Olá! Eu sou o Sapiens, do Gestão Versus. 🤖\n\n"
                    "Parece que seu número do Telegram ainda não está vinculado à sua conta no sistema.\n"
                    f"Para me autorizar, acesse o sistema Gestão Versus, vá em seu perfil e informe seu Telegram ID: `{telegram_id}`"
                )
                bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_to_message_id=message.message_id)
                return
            
            # Se encontrou o usuário: enviar aviso de digitando
            bot.send_chat_action(message.chat.id, 'typing')
            
            # 2. Configura a Thread (Sessão) do LangGraph
            # Vamos usar um thread_id unívoco para este usuário no Telegram
            thread_id = f"tg_{telegram_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # --- CONTEXTO DE AGENTE (Thread-Safe) ---
            from src.intelligence.tool_context import active_user_id_ctx, active_company_id_ctx
            token_uid = active_user_id_ctx.set(user.id)
            token_cid = None
            
            # Set employee/company context temporarily for legacy services (@ARQUITETO)
            os.environ['ACTIVE_USER_ID'] = str(user.id)
            if hasattr(user, 'employees') and user.employees:
                cid = user.employees[0].company_id
                os.environ['ACTIVE_COMPANY_ID'] = str(cid)
                token_cid = active_company_id_ctx.set(cid)
            
            # 3. Invoca o Work Agent (Graph V2) com Persistência SQL
            from src.intelligence.memory import get_checkpointer
            from src.intelligence.work_agents.graph import create_work_agent_workflow
            
            try:
                with get_checkpointer() as checkpointer:
                    graph = create_work_agent_workflow(checkpointer=checkpointer)
                    
                    # Verifica se já existe um estado no banco para esta thread
                    state = graph.get_state(config)
                
                # Para Telegram, não temos histórico externo fácil, então enviamos a mensagem atual.
                # Se não houver estado, ela inicia a thread. Se houver, ela adiciona à thread SQL.
                inputs = {"messages": [("user", user_msg)]}
                
                logger.info(f"Enviando para LangGraph (SQL) na thread {thread_id} para usuário {user.id}...")
                response = graph.invoke(inputs, config=config)
            finally:
                # Limpa env temporário
                if 'ACTIVE_COMPANY_ID' in os.environ:
                    del os.environ['ACTIVE_COMPANY_ID']
                if 'ACTIVE_USER_ID' in os.environ:
                    del os.environ['ACTIVE_USER_ID']
                
                # Reseta contextos de thread (@ARQUITETO)
                active_user_id_ctx.reset(token_uid)
                if token_cid:
                    active_company_id_ctx.reset(token_cid)
            
            # 4. Extrai a resposta final
            final_messages = response.get("messages", [])
            if not final_messages:
                bot.send_message(message.chat.id, "Processamento concluído, mas sem mensagem de retorno.", reply_to_message_id=message.message_id)
                return
                
            last_message = final_messages[-1]
            if isinstance(last_message, tuple):
                response_text = last_message[1]
            else:
                response_text = last_message.content
            
            # 5. Salva no Banco de Dados para rastreio de logs e timeout
            from models.agent_message import AgentMessage
            # Mensagem do Usuário
            db.session.add(AgentMessage(
                company_id=getattr(user.employees[0], 'company_id', None) if user.employees else None,
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
                company_id=getattr(user.employees[0], 'company_id', None) if user.employees else None,
                user_id=user.id,
                agent_type='work_agent_squad',
                agent_name='sapiens',
                direction='outbound',
                channel='telegram',
                content=response_text,
                metadata_json={"thread_id": thread_id, "contact": "sapiens", "telegram_id": telegram_id, "agent": "sapiens"}
            ))
            db.session.commit()

            # 6. Responde ao Telegram
            try:
                bot.send_message(message.chat.id, response_text, parse_mode='Markdown', reply_to_message_id=message.message_id)
            except Exception as markdown_err:
                logger.warning(f"Erro ao parsear Markdown. Tentando plain text. Erro: {markdown_err}")
                bot.send_message(message.chat.id, response_text, reply_to_message_id=message.message_id)
                
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"❌ Erro crítico no Telegram Webhook: {str(e)}\n{tb}")
            
            # Tentar escalonar para o Time de Engenharia (@AI_ENGINEER / @ARQUITETO)
            try:
                with app.app_context():
                    error_msg = f"Crash no Webhook do Telegram: {str(e)}"
                    context_info = f"Usuário TG ID: {telegram_id}\n\nTraceback:\n{tb}"
                    
                    # 🔍 Recuperar company_id para conformidade multi-tenancy (@ARQUITETO)
                    # Se usuário não existe, tentamos pegar a empresa do ID 1 ou a primeira do banco
                    from models.company import Company
                    from models.agent_action import AgentAction
                    from models import db
                    
                    effective_company_id = None
                    if 'user' in locals() and user and user.employees:
                        effective_company_id = user.employees[0].company_id
                    else:
                        # Fallback seguro para erros de infra/sistema
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

            bot.send_message(message.chat.id, "Desculpe, ocorreu um erro interno ao processar sua solicitação no Gestão Versus. O time de engenharia foi notificado.", reply_to_message_id=message.message_id)

# Rota HTTP (Webhook) que será chamada pelo servidor do Telegram
@telegram_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    try:
        # Emergency Log for Production Debug (@ARQUITETO)
        with open('request_debug.log', 'a') as f:
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"\n--- REQ: {now_str} ---\n")
            if request.is_json:
                f.write(f"SQUAD: Recebido JSON do Telegram\n")
            
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            
            # Iniciar thread separada para não causar TIMEOUT no servidor do Telegram
            if update.message and update.message.text:
                from flask import current_app
                app = current_app._get_current_object()
                t = Thread(target=process_telegram_message, args=(app, update.message,))
                t.start()
                
            return '', 200
        else:
            return "Not found", 404
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
    if not TOKEN:
        logger.error("❌ Não foi possível configurar o Webhook: TELEGRAM_BOT_TOKEN não definido.")
        return None

    try:
        bot.remove_webhook()
        webhook_url = f"{host_url.rstrip('/')}/webhook/telegram"
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook do Telegram registrado com sucesso: {webhook_url}")
        return webhook_url
    except Exception as e:
        logger.error(f"❌ Erro ao registrar Webhook do Telegram: {str(e)}")
        return None
