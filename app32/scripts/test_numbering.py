import os
import sys
import json
from datetime import datetime, date, timedelta

# Setup paths
sys.path.append(os.getcwd())

from app import create_app
from models import db, User, Employee, Company, Project, ProjectTask, AgentAction
from models.process import ProcessInstance, Process
from models.meeting import Meeting
from services.proactive_service import get_user_summary_report

def run_test():
    app = create_app()
    with app.app_context():
        user = User.query.filter(User.telegram.isnot(None)).first()
        if not user:
            print("Nenhum usuário com Telegram.")
            return

        report = get_user_summary_report(user, date_range='week')
        if report:
            # Clean for console printing
            clean_msg = report.replace('<b>', '').replace('</b>', '').replace('<i>', '').replace('</i>', '')
            clean_msg = clean_msg.encode('ascii', 'ignore').decode('ascii')
            print(clean_msg)
        else:
            print("Nenhum report gerado.")

if __name__ == "__main__":
    run_test()
