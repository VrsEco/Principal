#!/usr/bin/env python3
"""
Restaurar backup usando SQLAlchemy diretamente
"""
import sys
import os
import codecs

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

def create_admin_user(engine):
    """Criar usuário administrador"""
    try:
        with engine.connect() as conn:
            # Verificar se já existe
            result = conn.execute(text("SELECT id FROM users WHERE email = 'versus@gestaoversus.com.br'"))
            if result.fetchone():
                print("✅ Usuário admin já existe")
                return

            # Criar admin
            password_hash = generate_password_hash('abc123')
            conn.execute(text(f"""
                INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
                VALUES ('versus@gestaoversus.com.br', '{password_hash}', 'Administrador', 'admin', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """))
            conn.commit()
            print("✅ Usuário admin criado com sucesso")

    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")

def restore_backup(engine, backup_file):
    """Restaurar backup completo"""
    print(f"📂 Lendo arquivo: {backup_file}")

    # Tentar diferentes encodings
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    sql_content = None

    for encoding in encodings:
        try:
            with codecs.open(backup_file, 'r', encoding=encoding) as f:
                sql_content = f.read()
            print(f"✅ Arquivo lido com encoding: {encoding}")
            break
        except UnicodeDecodeError:
            continue

    if sql_content is None:
        print("❌ Não foi possível ler o arquivo")
        return False

    # Separar comandos SQL válidos
    commands = []
    current_command = ""
    in_transaction = False

    for line in sql_content.split('\n'):
        line = line.strip()

        # Pular linhas vazias e comentários
        if not line or line.startswith('--'):
            continue

        # Pular comandos específicos do pg_dump
        if (line.startswith('\\') or
            line.startswith('SET ') or
            'pg_catalog.set_config' in line or
            'pg_catalog.setval' in line or
            line.startswith('SELECT pg_catalog.')):
            continue

        # Início de transação
        if line.upper().startswith('BEGIN'):
            in_transaction = True
            continue
        elif line.upper().startswith('COMMIT'):
            in_transaction = False
            continue

        # Comando completo
        if line.endswith(';'):
            current_command += line
            if current_command and not in_transaction:
                # Filtrar apenas INSERTs e alguns CREATEs essenciais
                if (current_command.upper().startswith('INSERT INTO') or
                    current_command.upper().startswith('CREATE TABLE') or
                    current_command.upper().startswith('ALTER TABLE')):
                    commands.append(current_command)
            current_command = ""
        else:
            current_command += line + " "

    print(f"📊 Comandos SQL válidos encontrados: {len(commands)}")

    # Executar comandos em lotes
    batch_size = 50
    success_count = 0
    error_count = 0

    with engine.connect() as conn:
        for i in range(0, len(commands), batch_size):
            batch = commands[i:i + batch_size]
            print(f"🔄 Processando lote {i//batch_size + 1}/{(len(commands) + batch_size - 1)//batch_size}")

            for cmd in batch:
                try:
                    # Pular comandos que podem causar problemas
                    if ('CREATE SCHEMA' in cmd.upper() or
                        'DROP TABLE' in cmd.upper() or
                        'TRUNCATE' in cmd.upper()):
                        continue

                    conn.execute(text(cmd))
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    if "already exists" not in str(e).lower():
                        print(f"❌ Erro: {str(e)[:80]}...")

            # Commit do lote
            try:
                conn.commit()
                print(f"✅ Lote {i//batch_size + 1}: {success_count} OK, {error_count} erros")
            except Exception as e:
                print(f"❌ Erro no commit do lote: {e}")
                conn.rollback()

    print(f"\n📈 RESULTADO FINAL:")
    print(f"✅ Sucessos: {success_count}")
    print(f"❌ Erros: {error_count}")
    print(f"📊 Taxa de sucesso: {(success_count/(success_count+error_count)*100):.1f}%" if (success_count+error_count) > 0 else "0%")

    return success_count > 0

def main():
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Arquivo de backup
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo não encontrado: {backup_file}")
        return

    print("🚀 Iniciando restauração do backup...")
    print(f"📂 Arquivo: {backup_file}")

    # Criar admin primeiro
    create_admin_user(engine)

    # Restaurar backup
    if restore_backup(engine, backup_file):
        print("\n🎉 RESTAURAÇÃO CONCLUÍDA!")
        print("💡 Teste o sistema fazendo login com:")
        print("   Email: versus@gestaoversus.com.br")
        print("   Senha: abc123")
    else:
        print("\n⚠️ Restauração não foi completamente bem-sucedida")
        print("💡 Verifique os logs acima para detalhes")

if __name__ == "__main__":
    main()










