import time
import threading
import os
from datetime import datetime
from models import db, AgentAction
from services.whatsapp_service import whatsapp_service

class EngineeringService:
    """
    Serviço que orquestra o Squad de Engenharia (@ARQUITETO, @QA, @BACKEND).
    Funciona em background monitorando escalonamentos e executando reparos.
    """
    
    _instance = None
    _stop_event = threading.Event()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EngineeringService, cls).__new__(cls)
        return cls._instance

    def start_worker(self, app):
        """Inicia a thread de monitoramento do squad de engenharia"""
        def run_loop():
            with app.app_context():
                print("🛠️ SQUAD DE ENGENHARIA [ONLINE]: Monitorando sistema...")
                while not self._stop_event.is_set():
                    try:
                        self._process_pending_escalations()
                    except Exception as e:
                        print(f"❌ erro no Engineering Worker: {e}")
                    time.sleep(15) # Intervalo de verificação

        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()
        return thread

    def _process_pending_escalations(self):
        """Busca e analisa falhas reportadas pelo squad de trabalho"""
        pending = AgentAction.query.filter_by(type='technical_fix', status='pending').all()
        
        for action in pending:
            print(f"🧠 [ANALYSIS] @ARQUITETO analisando ticket #{action.id}...")
            
            # Simulação de análise técnica real
            # Em produção, aqui chamaríamos um agente de IA de engenharia especializado
            error_info = action.payload.get('error', '')
            
            # Proposta de Patch
            patch_proposal = {
                "proposed_fix": f"Ajuste defensivo para tratar o erro: {error_info[:40]}...",
                "files": [action.payload.get('file', 'unknown')],
                "confidence": 0.95
            }
            
            action.status = 'awaiting_approval'
            action.handling_agent = '@QA_AUTOMATION'
            action.payload['proposal'] = patch_proposal
            db.session.commit()
            
            # Notificação via WhatsApp
            phone = action.user_id # No mundo real, buscaríamos o fone do user_id
            msg = (
                f"✅ *Gestão Versus: Solução Pronta!*\n\n"
                f"O Time de Engenharia analisou o erro no ticket #{action.id}.\n"
                f"*Proposta:* {patch_proposal['proposed_fix']}\n\n"
                f"Acesse o Board de IA para aprovar a aplicação do hotfix."
            )
            whatsapp_service.send_message("5511999999999", msg) # Mock phone for demo

    def execute_repair(self, action_id):
        """Executa o reparo aprovado com suporte a Rollback @QA_AUTOMATION"""
        action = AgentAction.query.get(action_id)
        if not action or action.status != 'awaiting_approval':
            return False, "Ação não está em estado de aprovação."

        proposal = action.payload.get('proposal')
        if not proposal:
            return False, "Nenhuma proposta de reparo encontrada."

        try:
            # 1. Faz Backup do arquivo original (Checkpoints)
            file_path = proposal['files'][0]
            abs_path = os.path.abspath(file_path)
            
            if os.path.exists(abs_path):
                with open(abs_path, 'r', encoding='utf-8') as f:
                    action.backup_content = f.read()
                    action.original_file = abs_path
                db.session.commit()
            
            # 2. Aplica o Patches (Aqui simularíamos a escrita real do patch)
            # No futuro, o Agente de IA usaria replace_file_content aqui.
            print(f"🔧 Aplicando hotfix no arquivo: {file_path}")
            
            # Marcamos como executado
            action.status = 'executed'
            action.executed_at = datetime.utcnow()
            db.session.commit()
            
            return True, "Reparo aplicado com sucesso. Backup gerado para segurança."
        except Exception as e:
            action.status = 'failed'
            db.session.commit()
            return False, f"Falha na execução do reparo: {str(e)}"

    def rollback_repair(self, action_id):
        """Reverte uma alteração caso o @QA detecte instabilidade"""
        action = AgentAction.query.get(action_id)
        if not action or not action.backup_content or not action.original_file:
            return False, "Nenhum backup disponível para este ticket."

        try:
            with open(action.original_file, 'w', encoding='utf-8') as f:
                f.write(action.backup_content)
            
            action.status = 'rolled_back'
            db.session.commit()
            return True, "Rollback executado com sucesso. Arquivo original restaurado."
        except Exception as e:
            return False, f"Erro crítico no Rollback: {str(e)}"

engineering_service = EngineeringService()
