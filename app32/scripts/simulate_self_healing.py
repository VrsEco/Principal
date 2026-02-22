import sys
import os
import time
from datetime import datetime

# Setup path
sys.path.append(os.getcwd())

from app import create_app
from models import db, AgentAction, AgentMessage
from src.intelligence.work_agents.graph import work_agent_graph
from langchain_core.messages import HumanMessage, AIMessage

def log_event(squad, agent, message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{squad.upper()}] @{agent}: {message}")

def simulate():
    app = create_app()
    with app.app_context():
        print("\n" + "="*80)
        print("🚀 SIMULAÇÃO DE AUTO-RECUPERAÇÃO: WORK SQUAD ↔ ENGINEERING SQUAD")
        print("="*80 + "\n")

        # 1. USUÁRIO FAZ UMA PERGUNTA QUE GERA UM ERRO (Simulado)
        user_input = "Sapiens, tente renderizar o template de cadastro agora!"
        log_event("user", "CLIENTE", user_input)
        
        # Simulamos que o Sapiens detectou um erro interno ao tentar processar
        log_event("work", "SAPIENS", "Tentando processar renderização de template...")
        time.sleep(1)
        
        error_msg = "Jinja2.exceptions.TemplateNotFound: templates/cadastro_agent_v2_broken.html"
        log_event("system", "ERROR", error_msg)
        
        # 2. SAPIENS ESCALONA O ERRO
        log_event("work", "SAPIENS", f"Ops! Detectei um erro crítico. Escalando para engenharia...")
        
        # Chamada real da ferramenta de escalonamento (via lógica direta para o log)
        action = AgentAction(
            type='technical_fix',
            status='pending',
            requesting_agent='sapiens',
            handling_agent='engineering_squad',
            title='Erro de Template detectado pelo Sapiens',
            description=f"Ocorreu um erro ao renderizar: {error_msg}",
            payload={"error": error_msg, "file": "templates/cadastro_agent.html"},
            company_id=1,
            user_id=1
        )
        db.session.add(action)
        db.session.commit()
        
        log_event("system", "WHATSAPP", "Enviando alerta para o cliente: '🚨 Erro detectado, acionando engenharia...'")
        log_event("db", "TICKET", f"Ticket #{action.id} criado com sucesso.")
        
        time.sleep(2)

        # 3. ENGENHARIA RECEBE E ANALISA
        print("\n" + "-"*40)
        log_event("engineering", "@ARQUITETO", f"Recebi escalonamento de @SAPIENS (Ticket #{action.id}).")
        log_event("engineering", "@QA_AUTOMATION", "Analisando logs e estrutura de pastas...")
        time.sleep(1.5)
        
        log_event("engineering", "@QA_AUTOMATION", "Causa raiz identificada: Referência a arquivo inexistente no template.")
        log_event("engineering", "@BACKEND_API", "Preparando patch de correção...")
        
        patch = "Replace 'cadastro_agent_v2_broken.html' with 'cadastro_agent.html' in registry."
        action.payload["proposal"] = {"fix": patch, "safe": True}
        action.status = 'awaiting_approval'
        db.session.commit()
        
        log_event("system", "WHATSAPP", "Enviando solução para o cliente: '✅ Solução pronta! Clique para aprovar.'")
        print("-"*40 + "\n")
        
        time.sleep(2)

        # 4. USUÁRIO APROVA (Simulado)
        log_event("user", "CLIENTE", "Aprovado! Podem executar a correção.")
        action.status = 'executed'
        action.executed_at = datetime.utcnow()
        db.session.commit()
        
        log_event("engineering", "@ARQUITETO", "Aprovação recebida. Aplicando hotfix em produção...")
        time.sleep(1)
        log_event("system", "HOTFIX", "Patch aplicado com sucesso. Validando rotas...")
        log_event("engineering", "@QA_AUTOMATION", "Testes unitários passaram. Sistema estável.")
        
        # 5. RETORNO PARA O SAPIENS
        print("\n" + "-"*40)
        log_event("work", "LEADER", f"Líder de Engenharia deu o OK. Notificando @SAPIENS.")
        
        log_event("work", "SAPIENS", "Obrigado time! Retomando conversa com o usuário.")
        
        final_msg = "Desculpe a interrupção! O time de engenharia já corrigiu o erro de template que eu encontrei. Agora podemos continuar o cadastro. Qual o CNPJ da sua empresa?"
        log_event("work", "SAPIENS", final_msg)
        print("-"*40 + "\n")

if __name__ == "__main__":
    simulate()
