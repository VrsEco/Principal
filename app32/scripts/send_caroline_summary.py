import os
import sys
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

from app import create_app
from models import db, User
from services.proactive_service import get_user_summary_report
from api.webhooks.telegram_webhook import bot

def run():
    app = create_app()
    with app.app_context():
        # User who requested
        requester = User.query.filter(User.telegram == '8507771166').first()
        if not requester:
             print("Requester not found")
             return

        # Target User
        target = User.query.filter(User.name.ilike('%Caroline Marques%')).first()
        if not target:
            print("Caroline Marques not found")
            return
        
        print(f"Generating summary for {target.name} to send to {requester.name}")
        
        report = get_user_summary_report(target, date_range='week')
        
        if report:
            header = f"📊 **RESUMO DE {target.name.upper()} (ESTA SEMANA)**\n\n"
            full_msg = header + report
            bot.send_message(requester.telegram, full_msg, parse_mode='HTML')
            print("Message sent successfully")
        else:
            print(f"No pending items for {target.name} today.")
            bot.send_message(requester.telegram, f"Caroline Marques está plenamente em dia hoje! Nenhuma pendência encontrada.")

if __name__ == "__main__":
    run()
