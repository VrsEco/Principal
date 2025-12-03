#!/usr/bin/env python3
"""
Criar banco de dados temporário para testes
"""
import sys
import os

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from config import Config
from sqlalchemy import create_engine, text

def main():
    print("🏗️ CRIANDO BANCO TEMPORÁRIO PARA TESTES")
    print("=" * 50)

    config = Config()
    original_url = config.SQLALCHEMY_DATABASE_URI

    # Parse da URL original para criar URL do banco temp
    if 'postgresql://' in original_url:
        # Trocar nome do banco para _temp
        temp_url = original_url.replace('/bd_app_versus', '/bd_app_versus_temp')

        print("📍 Banco original: bd_app_versus")
        print("🆕 Banco temporário: bd_app_versus_temp")
        print()

        # Criar conexão com postgres (banco padrão)
        postgres_url = original_url.replace('/bd_app_versus', '/postgres')

        try:
            print("🔗 Conectando ao PostgreSQL...")
            postgres_engine = create_engine(postgres_url, echo=False)

            with postgres_engine.connect() as conn:
                # Verificar se banco temp já existe
                result = conn.execute(text("""
                    SELECT datname FROM pg_database
                    WHERE datname = 'bd_app_versus_temp'
                """))

                if result.fetchone():
                    print("⚠️ Banco temporário já existe!")
                    response = input("Deseja recriá-lo? (s/n): ").lower().strip()
                    if response == 's':
                        # Dropar conexões existentes e recriar
                        conn.execute(text("COMMIT"))  # Fechar transação atual
                        conn.execute(text("""
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = 'bd_app_versus_temp'
                        """))
                        conn.execute(text("DROP DATABASE IF EXISTS bd_app_versus_temp"))
                        print("✅ Banco antigo removido")
                    else:
                        print("✅ Usando banco temporário existente")
                        return temp_url

                # Criar banco temporário
                print("🚀 Criando banco temporário...")
                conn.execute(text("COMMIT"))  # Necessário para DDL
                conn.execute(text("CREATE DATABASE bd_app_versus_temp"))

                print("✅ Banco temporário criado com sucesso!")
                return temp_url

        except Exception as e:
            print(f"❌ Erro ao criar banco temporário: {e}")
            return None

    else:
        print("❌ URL do banco não é PostgreSQL")
        return None

if __name__ == "__main__":
    temp_url = main()
    if temp_url:
        print(f"\n🎯 Banco temporário criado!")
        print(f"🔗 URL: {temp_url}")
        print("\n💡 Próximo passo: restaurar backup no banco temporário")
    else:
        print("\n❌ Falha ao criar banco temporário")
        sys.exit(1)











