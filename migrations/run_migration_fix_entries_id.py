#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migração: Corrigir auto-increment da tabela process_activity_entries
Data: 2025-11-05
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config_database import get_db
import psycopg2

def main():
    print("="*70)
    print("MIGRAÇÃO: Corrigir auto-increment de process_activity_entries")
    print("="*70)
    
    # Obter conexão
    db = get_db()
    
    # Verificar se é PostgreSQL
    if not hasattr(db, '_get_connection'):
        print("❌ ERRO: Este script é apenas para PostgreSQL!")
        return False
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        print("\n📋 Verificando estado atual da tabela...")
        
        # Verificar se a coluna id tem default
        cursor.execute("""
            SELECT column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'process_activity_entries' 
            AND column_name = 'id'
        """)
        result = cursor.fetchone()
        
        if result:
            current_default = result[0]
            is_nullable = result[1]
            print(f"   - Default atual: {current_default}")
            print(f"   - Nullable: {is_nullable}")
            
            if current_default and 'nextval' in str(current_default):
                print("\n✅ A coluna 'id' já possui auto-increment configurado!")
                print("   Nenhuma migração necessária.")
                conn.close()
                return True
        
        # Contar registros existentes
        cursor.execute("SELECT COUNT(*) FROM process_activity_entries")
        count = cursor.fetchone()[0]
        print(f"\n📊 Registros existentes na tabela: {count}")
        
        if count > 0:
            cursor.execute("SELECT MAX(id) FROM process_activity_entries")
            max_id = cursor.fetchone()[0]
            print(f"   - Maior ID atual: {max_id}")
        
        # Confirmar migração
        print("\n⚠️  Esta migração irá:")
        print("   1. Criar uma sequence 'process_activity_entries_id_seq'")
        print("   2. Configurar a coluna 'id' para usar auto-increment")
        print("   3. Ajustar a sequence para o próximo valor disponível")
        
        resposta = input("\n🔹 Deseja prosseguir? (sim/não): ").strip().lower()
        
        if resposta not in ['sim', 's', 'yes', 'y']:
            print("\n❌ Migração cancelada pelo usuário.")
            conn.close()
            return False
        
        print("\n🔧 Executando migração...")
        
        # Ler arquivo SQL
        sql_file = Path(__file__).parent / 'fix_process_activity_entries_id.sql'
        if not sql_file.exists():
            print(f"❌ ERRO: Arquivo SQL não encontrado: {sql_file}")
            conn.close()
            return False
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Executar migração
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Migração executada com sucesso!")
        
        # Verificar resultado
        print("\n🔍 Verificando resultado...")
        cursor.execute("""
            SELECT column_default
            FROM information_schema.columns
            WHERE table_name = 'process_activity_entries' 
            AND column_name = 'id'
        """)
        result = cursor.fetchone()
        
        if result and result[0]:
            print(f"   ✅ Novo default: {result[0]}")
        
        # Teste de inserção
        print("\n🧪 Testando inserção...")
        try:
            cursor.execute("""
                INSERT INTO process_activity_entries 
                (activity_id, order_index, text_content, image_path, image_width, layout)
                VALUES (1, 999, 'TESTE DE MIGRAÇÃO - PODE DELETAR', NULL, 280, 'dual')
                RETURNING id
            """)
            test_id = cursor.fetchone()[0]
            print(f"   ✅ Teste OK! ID gerado automaticamente: {test_id}")
            
            # Deletar registro de teste
            cursor.execute("DELETE FROM process_activity_entries WHERE id = %s", (test_id,))
            conn.commit()
            print(f"   ✅ Registro de teste removido")
            
        except Exception as e:
            print(f"   ❌ Erro no teste: {e}")
            conn.rollback()
        
        conn.close()
        
        print("\n" + "="*70)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*70)
        print("\n💡 Próximo passo: Reiniciar o servidor Python para aplicar as mudanças")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante a migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)






