import sys
import os

print("🚀 Iniciando debug...")

# Adicionar diretório raiz ao path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)
print(f"📁 Path adicionado: {root_dir}")

try:
    from config import Config
    print("✅ Config importado")
    config = Config()
    print("✅ Config criado")
except Exception as e:
    print(f"❌ Config erro: {e}")
    sys.exit(1)

backup_file = r"C:\Users\mff20\Downloads\Cloud_SQL_Export_2025-11-30 (02_47_15).sql"
print(f"📂 Arquivo backup: {os.path.exists(backup_file)}")

if os.path.exists(backup_file):
    print("✅ Arquivo existe")
    try:
        with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        print(f"✅ Arquivo lido: {len(content)} caracteres")
        print(f"📄 Primeiras 200 chars: {content[:200]}")
    except Exception as e:
        print(f"❌ Erro lendo arquivo: {e}")
else:
    print("❌ Arquivo não encontrado")

print("🎯 Debug concluído")


