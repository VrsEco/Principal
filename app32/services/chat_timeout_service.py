import logging
from datetime import datetime, timedelta
from models import db, AgentMessage
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ChatTimeoutService:
    @staticmethod
    def check_and_handle_timeouts(app):
        """
        Varre as threads do Sapiens em busca de inatividade.
        - Após 10 min: Envia aviso de 30 segundos.
        - Após +30 seg: Encerra a conversa.
        """
        with app.app_context():
            # Tempos de corte baseados em UTC (padrão do model)
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            thirty_seconds_ago = datetime.utcnow() - timedelta(seconds=30)
            
            # 1. Identifica threads ativas na última hora (otimização)
            # Uma thread é definida por (user_id, channel, thread_id)
            try:
                # Query para as últimas mensagens de cada thread
                subquery = db.session.query(
                    AgentMessage.user_id,
                    AgentMessage.channel,
                    AgentMessage.metadata_json['thread_id'].astext.label('thread_id'),
                    db.func.max(AgentMessage.created_at).label('last_at')
                ).filter(
                    # Apenas mensagens das últimas 2 horas
                    AgentMessage.created_at > datetime.utcnow() - timedelta(hours=2)
                ).group_by(
                    AgentMessage.user_id, 
                    AgentMessage.channel, 
                    'thread_id'
                ).subquery()

                # Busca as mensagens reais correspondentes aos agrupamentos
                recent_threads = db.session.query(AgentMessage).join(
                    subquery,
                    (AgentMessage.user_id == subquery.c.user_id) &
                    (AgentMessage.channel == subquery.c.channel) &
                    (AgentMessage.metadata_json['thread_id'].astext == subquery.c.thread_id) &
                    (AgentMessage.created_at == subquery.c.last_at)
                ).all()

                for msg in recent_threads:
                    # Ignorar se o thread_id estiver vazio
                    if not msg.metadata_json.get('thread_id'):
                        continue

                    # Casos:
                    # A - Inatividade > 10 min e ainda não enviou aviso
                    if msg.created_at < ten_minutes_ago:
                        is_warning = msg.metadata_json.get('is_timeout_warning')
                        is_closed = msg.metadata_json.get('is_timeout_closed')

                        if not is_warning and not is_closed:
                            ChatTimeoutService._send_warning(msg)
                        
                        # B - Se já é um aviso e passaram mais 30 segundos
                        elif is_warning and not is_closed and msg.created_at < thirty_seconds_ago:
                             ChatTimeoutService._close_conversation(msg)

            except Exception as e:
                logger.error(f"Erro no processamento de timeouts de chat: {str(e)}")

    @staticmethod
    def _send_warning(template_msg):
        """Envia a mensagem de aviso de 30 segundos"""
        warning_text = "Por inatividade iremos encerrar essa conversa, você tem 30 segundo para interagir comigo."
        
        new_meta = dict(template_msg.metadata_json)
        new_meta['is_timeout_warning'] = True
        
        new_msg = AgentMessage(
            company_id=template_msg.company_id,
            user_id=template_msg.user_id,
            agent_type='system',
            agent_name='Sapiens',
            direction='outbound',
            channel=template_msg.channel,
            content=warning_text,
            metadata_json=new_meta
        )
        db.session.add(new_msg)
        db.session.commit()
        
        # Envio Real para canais externos
        if template_msg.channel == 'telegram':
            ChatTimeoutService._send_telegram(template_msg.user_id, warning_text)
        
        logger.info(f"--- TIMEOUT WARNING: User {template_msg.user_id} ({template_msg.channel}) ---")

    @staticmethod
    def _close_conversation(template_msg):
        """Envia mensagem final de encerramento"""
        close_text = "Conversa encerrada por inatividade. Quando precisar, estou à disposição!"
        
        new_meta = dict(template_msg.metadata_json)
        new_meta['is_timeout_closed'] = True
        new_meta.pop('is_timeout_warning', None)
        
        new_msg = AgentMessage(
            company_id=template_msg.company_id,
            user_id=template_msg.user_id,
            agent_type='system',
            agent_name='Sapiens',
            direction='outbound',
            channel=template_msg.channel,
            content=close_text,
            metadata_json=new_meta
        )
        db.session.add(new_msg)
        db.session.commit()
        
        # Envio Real para canais externos
        if template_msg.channel == 'telegram':
            ChatTimeoutService._send_telegram(template_msg.user_id, close_text)
            
        logger.info(f"--- TIMEOUT CLOSED: User {template_msg.user_id} ({template_msg.channel}) ---")

    @staticmethod
    def _send_telegram(user_id, text):
        """Utilitário para enviar mensagem via Telegram fora do webhook"""
        try:
            from api.webhooks.telegram_webhook import bot
            from models.user import User
            user = User.query.get(user_id)
            if user and user.telegram:
                bot.send_message(user.telegram, text)
        except Exception as e:
            logger.error(f"Erro ao enviar Telegram proativo: {e}")
