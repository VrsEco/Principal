#!/usr/bin/env python3
"""
Configurar dados básicos e admin
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

try:
    from config import Config
    from sqlalchemy import create_engine, text
    from werkzeug.security import generate_password_hash
    print("✅ Módulos importados com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

def main():
    print("🚀 Configurando dados básicos...")

    config = Config()

    # Verificar conexão
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conectado ao PostgreSQL: {version[:30]}...")

            # Contar tabelas
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            table_count = result.fetchone()[0]
            print(f"📊 Tabelas no banco: {table_count}")

    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return

    # Criar admin
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            if result.fetchone():
                print("✅ Usuário admin já existe")
            else:
                password_hash = generate_password_hash('abc123')
                conn.execute(text(f"""
                    INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
                    VALUES ('versus@gestaoversus.com.br', '{password_hash}', 'Administrador', 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """))
                conn.commit()
                print("✅ Usuário admin criado:")
                print("   Email: versus@gestaoversus.com.br")
                print("   Senha: abc123")

    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")

    print("\n📋 PRÓXIMOS PASSOS PARA RESTAURAÇÃO COMPLETA:")
    print("1. Abra pgAdmin ou DBeaver")
    print("2. Conecte ao banco PostgreSQL (bd_app_versus)")
    print("3. Execute o arquivo SQL: Cloud_SQL_Export_2025-11-30 (02_47_15).sql")
    print("4. Teste o login no sistema")

    print("\n🎯 SISTEMA PRONTO PARA USO!")
    print("💡 Acesse: http://localhost:5000")
    print("👤 Login: versus@gestaoversus.com.br / abc123")

if __name__ == "__main__":
    main()











