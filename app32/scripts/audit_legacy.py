import os
import sys

PROHIBITED_STRINGS = ["google.cloud", "aiplatform", "vertexai", "sqlite3", ".db", ".sqlite"]
OBSOLETE_EXTENSIONS = [".db", ".sqlite", ".sqlite3"]
EXCLUDE_DIRS = [".git", ".venv", "node_modules", "brain", "__pycache__"]

def audit_project(root_dir):
    print(f"--- INICIANDO AUDITORIA DE CÓDIGO LEGADO EM: {root_dir} ---")
    legacy_files = []
    obsolete_files = []

    for root, dirs, files in os.walk(root_dir):
        # Ignora diretórios excluídos
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            file_path = os.path.join(root, file)
            
            # 1. Verifica extensões obsoletas
            if any(file.endswith(ext) for ext in OBSOLETE_EXTENSIONS):
                obsolete_files.append(file_path)
                continue

            # 2. Verifica conteúdo do arquivo (apenas arquivos de texto)
            if file.endswith(('.py', '.yaml', '.yml', '.json', '.html', '.txt', '.sh', '.bat')):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        found = [s for s in PROHIBITED_STRINGS if s in content]
                        if found:
                            legacy_files.append((file_path, found))
                except Exception as e:
                    print(f"Erro ao ler {file_path}: {e}")

    print("\n[!] ARQUIVOS COM CÓDIGO LEGADO ENCONTRADOS (Strings Proibidas):")
    if not legacy_files:
        print("Nenhum código legado detectado!")
    for path, matches in legacy_files:
        print(f" - {path} (Matches: {', '.join(matches)})")

    print("\n[!] ARQUIVOS DE BANCO DE DADOS LOCAIS ENCONTRADOS (Obsoletos):")
    if not obsolete_files:
        print("Nenhum arquivo de banco SQLite detectado!")
    for path in obsolete_files:
        print(f" - {path}")

    print("\n--- AUDITORIA CONCLUÍDA ---")

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    audit_project(project_root)
