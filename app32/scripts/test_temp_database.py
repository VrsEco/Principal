#!/usr/bin/env python3
"""
Testar banco temporário com a aplicação
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

def main():
    print("🧪 TESTANDO BANCO TEMPORÁRIO COM APLICAÇÃO")
    print("=" * 50)

    # Alterar para banco temporário
    temp_db_url = "postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus_temp"
    os.environ['DATABASE_URL'] = temp_db_url

    print("🎯 Testando banco: bd_app_versus_temp")
    print()

    try:
        from config import Config
        from sqlalchemy import create_engine, text
        from flask import Flask
        from models import db

        print("✅ Módulos importados")

        config = Config()
        if 'bd_app_versus_temp' not in config.SQLALCHEMY_DATABASE_URI:
            print("❌ DATABASE_URL não foi configurado corretamente")
            return False

        engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

        # Teste básico de conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conexão OK: PostgreSQL {version.split()[1]}")

            # Verificar tabelas
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            table_count = result.fetchone()[0]
            print(f"📊 Tabelas encontradas: {table_count}")

            # Testar tabelas essenciais
            essential_tables = ['users', 'companies', 'employees', 'projects', 'plans']
            missing_tables = []

            for table in essential_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"   ✅ {table}: {count} registros")
                except Exception as e:
                    missing_tables.append(table)
                    print(f"   ❌ {table}: tabela não encontrada")

            if missing_tables:
                print(f"\n⚠️ Tabelas faltando: {', '.join(missing_tables)}")
                return False

        # Teste do Flask app
        print("\n🏗️  Testando Flask app...")
        app = Flask(__name__)
        app.config.from_object(config)
        db.init_app(app)

        with app.app_context():
            # Testar models
            try:
                from models import User, Company, Project
                print("✅ Models importados com sucesso")

                # Testar queries básicas
                user_count = User.query.count()
                company_count = Company.query.count()
                project_count = Project.query.count()

                print("✅ Queries funcionando:")
                print(f"   👤 Usuários: {user_count}")
                print(f"   🏢 Empresas: {company_count}")
                print(f"   📋 Projetos: {project_count}")

            except Exception as e:
                print(f"❌ Erro nos models: {e}")
                return False

        # Verificar admin user
        with engine.connect() as conn:
            result = conn.execute(text("SELECT id, email FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            admin = result.fetchone()
            if admin:
                print(f"✅ Admin encontrado: {admin[1]} (ID: {admin[0]})")
            else:
                print("⚠️ Admin não encontrado - será criado no primeiro acesso")

        print("\n🎉 TESTE DO BANCO TEMPORÁRIO APROVADO!")
        print("✅ Todas as verificações passaram")
        return True

    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 Banco temporário está funcionando!")
        print("💡 Próximo passo: iniciar aplicação para teste completo")
        print("   Execute: DATABASE_URL='postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus_temp' python app_pev.py")
    else:
        print("\n❌ Banco temporário com problemas")
        print("🔄 Verifique os logs acima e corrija antes de prosseguir")
        sys.exit(1)














