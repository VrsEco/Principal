import os
import sys

# Ensure app is in path
sys.path.append('.')

from app import create_app
from src.intelligence.execution import run_agent_with_context, extract_response_text
from models import User, Company

app = create_app('production')

with app.app_context():
    # Test for a real user (e.g., ID 1 or search for an active user)
    user = User.query.filter_by(role='admin').first()
    if not user:
        print("No admin user found for test")
        sys.exit(1)
        
    print(f"Testing for user: {user.name} (ID: {user.id})")
    
    # Simula a mensagem do usuário
    user_msg = "Olá, quem é você e o que você pode fazer por mim hoje?"
    
    # Pega uma empresa para este usuário
    from src.intelligence.identity import get_best_company_id
    company_id = get_best_company_id(user)
    
    print(f"Context: Company {company_id}")
    
    response = run_agent_with_context(
        user_id=user.id,
        user_msg=user_msg,
        channel="test",
        thread_id="test_thread_999",
        company_id=company_id
    )
    
    text = extract_response_text(response)
    print("\n--- AGENT RESPONSE ---")
    print(text)
    print("----------------------")
