import sys
import os

# Garantir que o diretório raiz esteja no path
sys.path.append(os.getcwd())

from app import create_app
from models import db
from sqlalchemy import text

def migrate():
    app = create_app()
    with app.app_context():
        # Alter RuleSet table
        try:
            print("Adicionando max_red_total em incentive_rule_sets...")
            db.session.execute(text("ALTER TABLE incentive_rule_sets ADD COLUMN IF NOT EXISTS max_red_total NUMERIC(15, 4)"))
        except Exception as e:
            print(f"Erro ao adicionar max_red_total: {e}")

        # Alter Rule table
        try:
            print("Adicionando max_reduction em incentive_rules...")
            db.session.execute(text("ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS max_reduction NUMERIC(15, 4)"))
        except Exception as e:
            print(f"Erro ao adicionar max_reduction: {e}")
            
        try:
            print("Adicionando impact_value em incentive_rules...")
            db.session.execute(text("ALTER TABLE incentive_rules ADD COLUMN IF NOT EXISTS impact_value NUMERIC(15, 4)"))
        except Exception as e:
            print(f"Erro ao adicionar impact_value: {e}")

        db.session.commit()
        print("Migração concluída com sucesso.")

if __name__ == "__main__":
    migrate()
