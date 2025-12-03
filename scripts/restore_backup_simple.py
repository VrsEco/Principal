#!/usr/bin/env python3
"""
Script simples para restaurar backup do PostgreSQL
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
    print("✅ Módulos importados com sucesso")
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    sys.exit(1)

def main():
    config = Config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI, echo=False)

    # Arquivo de backup
    backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"

    if not os.path.exists(backup_file):
        print(f"❌ Arquivo de backup não encontrado: {backup_file}")
        return

    print(f"📂 Arquivo de backup: {backup_file}")

    try:
        # Ler arquivo com diferentes encodings
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
            print("❌ Não foi possível ler o arquivo com nenhum encoding conhecido")
            return

        # Separar comandos SQL (remover comentários e linhas vazias)
        commands = []
        current_command = ""
        in_comment = False

        for line in sql_content.split('\n'):
            line = line.strip()

            # Pular linhas vazias
            if not line:
                continue

            # Pular comentários
            if line.startswith('--'):
                continue

            # Pular comandos específicos do pg_dump
            if line.startswith('\\') or line.startswith('SET ') or line.startswith('SELECT pg_catalog.'):
                continue

            # Comando completo
            if line.endswith(';'):
                current_command += line
                if current_command and not current_command.startswith('SET'):
                    commands.append(current_command)
                current_command = ""
            else:
                current_command += line + " "

        print(f"📊 Total de comandos SQL encontrados: {len(commands)}")

        # Executar comandos
        with engine.connect() as conn:
            success_count = 0
            error_count = 0

            for i, cmd in enumerate(commands[:10]):  # Executar apenas primeiros 10 para teste
                try:
                    if cmd.strip():
                        conn.execute(text(cmd))
                        success_count += 1
                        print(f"✅ Comando {i+1}/{len(commands)}: OK")
                except Exception as e:
                    error_count += 1
                    print(f"❌ Comando {i+1}/{len(commands)}: {str(e)[:100]}...")

            conn.commit()

        print(f"📈 Resultado: {success_count} sucesso, {error_count} erros")

        if success_count > 0:
            print("🎉 Restauração parcial concluída!")
            print("💡 Execute novamente para processar mais comandos")
        else:
            print("⚠️ Nenhum comando executado com sucesso")

    except Exception as e:
        print(f"❌ Erro durante restauração: {e}")

if __name__ == "__main__":
    main()











