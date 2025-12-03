#!/usr/bin/env python3
"""
Fazer backup completo do banco atual
"""
import sys
import os
import subprocess
from datetime import datetime

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

from config import Config

def main():
    print("🔒 FAZENDO BACKUP COMPLETO DO BANCO ATUAL")
    print("=" * 50)

    config = Config()
    db_url = config.SQLALCHEMY_DATABASE_URI

    # Parse da URL do banco
    if 'postgresql://' in db_url:
        # postgresql://user:password@host:port/database
        parts = db_url.replace('postgresql://', '').split('@')
        if len(parts) == 2:
            user_pass = parts[0].split(':')
            host_db = parts[1].split('/')

            if len(user_pass) == 2 and len(host_db) == 2:
                user = user_pass[0]
                password = user_pass[1]
                host_port = host_db[0].split(':')
                host = host_port[0]
                port = host_port[1] if len(host_port) > 1 else '5432'
                database = host_db[1]

                print(f"📍 Banco: {database}")
                print(f"🏠 Host: {host}:{port}")
                print(f"👤 Usuário: {user}")

                # Criar nome do arquivo de backup
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"backup_bd_app_versus_{timestamp}.sql"

                print(f"💾 Arquivo: {backup_file}")

                # Comando pg_dump
                cmd = [
                    'pg_dump',
                    '-h', host,
                    '-p', port,
                    '-U', user,
                    '-d', database,
                    '-f', backup_file,
                    '--no-password',
                    '--format=custom',  # Formato binário mais eficiente
                    '--compress=9',
                    '--verbose'
                ]

                # Definir senha no ambiente
                env = os.environ.copy()
                env['PGPASSWORD'] = password

                print("\n🚀 Executando pg_dump...")
                try:
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

                    if result.returncode == 0:
                        # Verificar tamanho do arquivo
                        if os.path.exists(backup_file):
                            size_mb = os.path.getsize(backup_file) / (1024 * 1024)
                            print(".1f"                            print("✅ BACKUP CONCLUÍDO COM SUCESSO!")
                            print(f"📂 Local: {os.path.abspath(backup_file)}")
                        else:
                            print("❌ Arquivo de backup não foi criado")
                            return False
                    else:
                        print("❌ Erro no pg_dump:")
                        print(f"STDOUT: {result.stdout}")
                        print(f"STDERR: {result.stderr}")
                        return False

                except FileNotFoundError:
                    print("❌ pg_dump não encontrado. Instale PostgreSQL client tools.")
                    print("💡 Ou use Docker: docker exec -it postgres-container pg_dump ...")
                    return False
                except Exception as e:
                    print(f"❌ Erro inesperado: {e}")
                    return False

                # Verificar conteúdo do backup
                print("\n🔍 Verificando backup...")
                verify_cmd = ['pg_restore', '--list', backup_file]
                try:
                    verify_result = subprocess.run(verify_cmd, env=env, capture_output=True, text=True)
                    if verify_result.returncode == 0:
                        lines = verify_result.stdout.strip().split('\n')
                        table_count = len([line for line in lines if 'TABLE' in line])
                        print(f"📊 Backup contém aproximadamente {table_count} tabelas")
                    else:
                        print("⚠️ Não foi possível verificar conteúdo (backup pode estar OK)")
                except:
                    print("⚠️ pg_restore não disponível para verificação")

                return True

    print("❌ Não foi possível parsear a URL do banco de dados")
    print(f"URL: {db_url}")
    return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Backup do banco atual concluído!")
        print("💡 Próximo passo: criar banco temporário")
    else:
        print("\n❌ Falha no backup. Abortando operação.")
        sys.exit(1)











