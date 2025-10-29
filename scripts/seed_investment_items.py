"""
Script para inicializar categorias e itens de investimento padrão
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_database import get_db

def seed_investment_items():
    """Inicializa categorias e itens de investimento padrão para todos os plans"""
    
    db = get_db()
    
    print("🌱 Iniciando seed de categorias e itens de investimento...")
    
    # Buscar todos os plans
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM plans ORDER BY id')
    plans = cursor.fetchall()
    
    print(f"📋 Encontrados {len(plans)} plans")
    
    for plan_row in plans:
        plan_id = plan_row[0]
        
        print(f"\n📝 Processando plan_id: {plan_id}")
        
        # Verificar se já existem categorias para este plan
        cursor.execute('''
            SELECT COUNT(*) FROM plan_finance_investment_categories 
            WHERE plan_id = %s
        ''', (plan_id,))
        
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            print(f"  ✓ Categorias já existem para plan_id {plan_id}")
            continue
        
        # Criar categorias
        cursor.execute('''
            INSERT INTO plan_finance_investment_categories (plan_id, category_type, category_name, display_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (plan_id, 'capital_giro', 'Capital de Giro', 1))
        
        capg_id = cursor.fetchone()[0]
        
        cursor.execute('''
            INSERT INTO plan_finance_investment_categories (plan_id, category_type, category_name, display_order)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        ''', (plan_id, 'imobilizado', 'Imobilizado', 2))
        
        imob_id = cursor.fetchone()[0]
        
        print(f"  ✓ Categorias criadas (Capital de Giro: {capg_id}, Imobilizado: {imob_id})")
        
        # Criar itens de Capital de Giro
        items_giro = [
            ('Caixa', 1),
            ('Recebíveis', 2),
            ('Estoques', 3)
        ]
        
        for item_name, order in items_giro:
            cursor.execute('''
                INSERT INTO plan_finance_investment_items (category_id, item_name, display_order)
                VALUES (%s, %s, %s)
            ''', (capg_id, item_name, order))
        
        print(f"  ✓ Itens de Capital de Giro criados: {len(items_giro)}")
        
        # Criar itens de Imobilizado
        items_imob = [
            ('Instalações', 1),
            ('Máquinas e Equipamentos', 2),
            ('Outros Investimentos', 3)
        ]
        
        for item_name, order in items_imob:
            cursor.execute('''
                INSERT INTO plan_finance_investment_items (category_id, item_name, display_order)
                VALUES (%s, %s, %s)
            ''', (imob_id, item_name, order))
        
        print(f"  ✓ Itens de Imobilizado criados: {len(items_imob)}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Seed concluído com sucesso!")
    print(f"📊 Total de plans processados: {len(plans)}")

if __name__ == '__main__':
    try:
        seed_investment_items()
    except Exception as e:
        print(f"\n❌ Erro ao executar seed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

