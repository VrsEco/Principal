#!/usr/bin/env python3
"""
Aplicar migrações SQLAlchemy no banco temporário
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

def main():
    print("🔄 APLICANDO MIGRAÇÕES SQLALCHEMY NO BANCO TEMPORÁRIO")
    print("=" * 60)

    # Temporariamente alterar DATABASE_URL para o banco temp
    temp_db_url = "postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus_temp"

    print("🎯 Banco temporário: bd_app_versus_temp")
    print(f"🔗 URL: {temp_db_url}")
    print()

    # Definir variável de ambiente para forçar uso do banco temp
    os.environ['DATABASE_URL'] = temp_db_url

    try:
        # Importar após definir DATABASE_URL
        from config import Config
        from sqlalchemy import create_engine, text
        from flask import Flask
        from models import db
        from flask_migrate import Migrate

        print("✅ Módulos importados")

        # Verificar conexão com banco temp
        config = Config()
        if 'bd_app_versus_temp' not in config.SQLALCHEMY_DATABASE_URI:
            print("❌ DATABASE_URL não foi alterado corretamente")
            return False

        engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Conectado ao banco temp: {version[:30]}...")

            # Contar tabelas antes da migração
            result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            tables_before = result.fetchone()[0]
            print(f"📊 Tabelas antes da migração: {tables_before}")

        print("\n🚀 Criando app Flask...")
        app = Flask(__name__)
        app.config.from_object(config)

        print("🔗 Inicializando SQLAlchemy...")
        db.init_app(app)

        print("📦 Inicializando Flask-Migrate...")
        migrate = Migrate(app, db)

        print("\n🔄 Executando migrações...")

        with app.app_context():
            # Aplicar todas as migrações
            from flask_migrate import upgrade
            upgrade()
            print("✅ Migrações aplicadas com sucesso!")

            # Verificar tabelas após migração
            engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
                tables_after = result.fetchone()[0]
                print(f"📊 Tabelas após migração: {tables_after}")
                print(f"➕ Tabelas adicionadas: {tables_after - tables_before}")

                # Listar tabelas SQLAlchemy criadas
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                all_tables = [row[0] for row in result.fetchall()]

                sql_alchemy_tables = []
                original_tables = []

                for table in all_tables:
                    if (table.startswith(('plan_', 'okr_', 'company_', 'meeting', 'process', 'routine', 'indicator', 'project_activity')) or
                        table in ['notes', 'user_logs']):
                        sql_alchemy_tables.append(table)
                    else:
                        original_tables.append(table)

                print(f"\n🏗️  Tabelas SQLAlchemy: {len(sql_alchemy_tables)}")
                print(f"📚 Tabelas originais: {len(original_tables)}")

                # Verificar dados preservados
                print("
🔍 Verificando dados:")
                for table in ['users', 'companies', 'employees', 'projects']:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.fetchone()[0]
                        print(f"   {table}: {count} registros")
                    except:
                        print(f"   {table}: erro ao contar")

        return True

    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Migração do banco temporário concluída!")
        print("💡 Próximo passo: testar aplicação com banco temporário")
    else:
        print("\n❌ Falha na migração do banco temporário")
        sys.exit(1)











