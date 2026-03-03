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
                bot.reply_to(message, msg, parse_mode='Markdown')
                return
            
            # Se encontrou o usuário: enviar aviso de digitando (ignora erros de rate limit)
            try:
                bot.send_chat_action(message.chat.id, 'typing')
            except Exception as typing_err:
                logger.warning(f"send_chat_action ignorado: {typing_err}")
            
            # 2. Configura a Thread (Sessão) do LangGraph
            # Vamos usar um thread_id unívoco para este usuário no Telegram
            thread_id = f"tg_{telegram_id}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # 3. Invoca o Work Agent (Graph V2) com Persistência SQL
            from src.intelligence.memory import get_checkpointer
            from src.intelligence.work_agents.graph import create_work_agent_workflow
            from models.employee import Employee
            
            # Set employee/company context temporarily for the LLM context if available.
            employee = Employee.query.filter_by(user_id=user.id, status='active').first()
            if employee:
                os.environ['ACTIVE_COMPANY_ID'] = str(employee.company_id)
            os.environ['ACTIVE_USER_ID'] = str(user.id)
            
            with get_checkpointer() as checkpointer:
                graph = create_work_agent_workflow(checkpointer=checkpointer)
                
                # Verifica se já existe um estado no banco para esta thread
                state = graph.get_state(config)
                
                # Para Telegram, não temos histórico externo fácil, então enviamos a mensagem atual.
                # Se não houver estado, ela inicia a thread. Se houver, ela adiciona à thread SQL.
                inputs = {"messages": [("user", user_msg)]}
                
                logger.info(f"Enviando para LangGraph (SQL) na thread {thread_id}...")
                response = graph.invoke(inputs, config=config)
            
            # Limpa env temporário
            if 'ACTIVE_COMPANY_ID' in os.environ:
                del os.environ['ACTIVE_COMPANY_ID']
            if 'ACTIVE_USER_ID' in os.environ:
                del os.environ['ACTIVE_USER_ID']
            
            # 4. Extrai a resposta final
            final_messages = response.get("messages", [])
            if not final_messages:
                bot.reply_to(message, "Processamento concluído, mas sem mensagem de retorno.")
                return
                
            last_message = final_messages[-1]
            if isinstance(last_message, tuple):
                response_text = last_message[1]
            else:
                response_text = last_message.content
            
            # 5. Salva no Banco de Dados para rastreio de logs e timeout
            from models.agent_message import AgentMessage
            
            effective_company_id = employee.company_id if employee else None

            # Mensagem do Usuário
            db.session.add(AgentMessage(
                company_id=effective_company_id,
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
                company_id=effective_company_id,
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
                bot.reply_to(message, response_text, parse_mode='Markdown')
            except Exception as markdown_err:
                logger.warning(f"Erro ao parsear Markdown. Tentando plain text. Erro: {markdown_err}")
                bot.reply_to(message, response_text)
                
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
                    if 'employee' in locals() and employee:
                        effective_company_id = employee.company_id
                    elif 'user' in locals() and user:
                        from models.employee import Employee
                        emp = Employee.query.filter_by(user_id=user.id).first()
                        if emp: effective_company_id = emp.company_id
                    
                    if not effective_company_id:
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

            bot.reply_to(message, "Desculpe, ocorreu um erro interno ao processar sua solicitação no Gestão Versus. O time de engenharia foi notificado.")

# Rota HTTP (Webhook) que será chamada pelo servidor do Telegram
@telegram_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/request_debug.log'
    try:
        # Emergency Log for Production Debug (@ARQUITETO)
        with open(log_path, 'a') as f:
            f.write(f"\n--- REQ: {datetime.now()} ---\n")
            
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            
            # Iniciar processamento síncrono para evitar Deadlocks no uWSGI
            # A menos que tenhamos celery/redis, Thread no uWSGI bloqueia o worker
            if update.message and update.message.text:
                from flask import current_app
                app = current_app._get_current_object()
                
                # Envia um 'digitando...' antes de bloquear
                try:
                    bot.send_chat_action(update.message.chat.id, 'typing')
                except Exception:
                    pass
                    
                process_telegram_message(app, update.message)
                
            return '', 200
        else:
            return "Not found", 404
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"❌ Erro Crítico na Rota do Webhook: {e}")
        with open(log_path, 'a') as f:
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
