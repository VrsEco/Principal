import os
import sys
import time
from datetime import datetime

# Adiciona o diretório raiz ao path para encontrar os models
sys.path.append(os.getcwd())

from app import create_app
from models import db, AgentAction
from services.whatsapp_service import whatsapp_service

def engineering_squad_loop():
    """
    Simula o Agente de Engenharia (@ARQUITETO / @QA) monitorando o Work Squad.
    """
    app = create_app()
    with app.app_context():
        print("🛠️ SQUAD DE ENGENHARIA ATIVO: Monitorando escalonamentos...")
        
        while True:
            # 1. Busca ações técnicas pendentes vindas do Work Squad
            pending_fixes = AgentAction.query.filter_by(
                type='technical_fix', 
                status='pending'
            ).all()
            
            for action in pending_fixes:
                print(f"📦 [PENDING] Detectado erro: {action.description[:50]}...")
                
                # 2. Simula análise da Engenharia
                # Em real, aqui um agente de IA de engenharia leria os arquivos citados no payload
                print(f"🧠 Analisando causa raiz para ticket #{action.id}...")
                time.sleep(2)
                
                # 3. Propõe a solução (Patch)
                patch_proposal = {
                    "patch_id": f"FIX-{action.id}",
                    "proposed_fix": "Ajuste na lógica de validação do template Jinja para tratar valores None.",
                    "impact": "Baixo",
                    "files_affected": ["templates/cadastro_agent.html"]
                }
                
                # 4. Atualiza o registro e notifica o usuário
                action.status = 'awaiting_approval'
                action.handling_agent = '@QA_AUTOMATION'
                action.payload['proposal'] = patch_proposal
                db.session.commit()
                
                # 5. Notifica via WhatsApp que a solução está pronta
                wa_message = (
                    f"✅ *Gestão Versus: Solução Pronta!*\n\n"
                    f"O Time de Engenharia (@QA) analisou o erro no ticket #{action.id}.\n"
                    f"*Solução:* {patch_proposal['proposed_fix']}\n\n"
                    f"Clique aqui para aprovar e aplicar o reparo: [Link de Aprovação]"
                )
                
                # Buscamos um telefone mockado ou o do user se ele estivesse logado
                # (Aqui usamos fixo para demonstração)
                whatsapp_service.send_message("5511999999999", wa_message)
                
                print(f"📡 [SENT] Notificação de solução enviada para ticket #{action.id}")

            time.sleep(10) # Verifica a cada 10 segundos

if __name__ == "__main__":
    try:
        engineering_squad_loop()
    except KeyboardInterrupt:
        print("\n👋 Squad de Engenharia encerrado.")
