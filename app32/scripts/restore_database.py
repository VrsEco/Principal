#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Restauração de Backup
GestaoVersus (APP30)

Restaura backups do banco de dados e uploads
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


class DatabaseRestore:
    """Classe para restaurar backups de banco de dados."""

    def __init__(self):
        """Inicializa configurações de restauração."""
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///database.db")
        self.backup_dir = Path(os.getenv("BACKUP_DIR", "./backups"))

    def is_postgresql(self):
        """Verifica se o banco é PostgreSQL."""
        return self.database_url.startswith(
            "postgresql://"
        ) or self.database_url.startswith("postgres://")

    def is_sqlite(self):
        """Verifica se o banco é SQLite."""
        return self.database_url.startswith("sqlite:///")

    def list_backups(self, db_type="all"):
        """Lista backups disponíveis."""
        print("\n" + "=" * 80)
        print("  BACKUPS DISPONÍVEIS")
        print("=" * 80 + "\n")

        backups = {
            "database": sorted(
                self.backup_dir.glob("backup_*sql")
                if db_type == "postgresql"
                else self.backup_dir.glob("backup_*.db")
                if db_type == "sqlite"
                else list(self.backup_dir.glob("backup_*sql"))
                + list(self.backup_dir.glob("backup_*.db")),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            ),
            "uploads": sorted(
                self.backup_dir.glob("backup_uploads_*.tar.gz"),
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            ),
        }

        # Listar backups de banco
        print("📦 BACKUPS DE BANCO DE DADOS:")
        if backups["database"]:
            for i, backup in enumerate(backups["database"], 1):
                size_mb = backup.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {i}. {backup.name}")
                print(f"     Tamanho: {size_mb:.2f} MB")
                print(f"     Data: {mtime.strftime('%d/%m/%Y %H:%M:%S')}")
                print()
        else:
            print("  Nenhum backup encontrado.\n")

        # Listar backups de uploads
        print("📁 BACKUPS DE UPLOADS:")
        if backups["uploads"]:
            for i, backup in enumerate(backups["uploads"], 1):
                size_mb = backup.stat().st_size / (1024 * 1024)
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {i}. {backup.name}")
                print(f"     Tamanho: {size_mb:.2f} MB")
                print(f"     Data: {mtime.strftime('%d/%m/%Y %H:%M:%S')}")
                print()
        else:
            print("  Nenhum backup encontrado.\n")

        return backups

    def restore_postgresql(self, backup_file):
        """Restaura backup do PostgreSQL."""
        print(f"📦 Restaurando backup PostgreSQL: {backup_file.name}")

        # Parsear DATABASE_URL
        from urllib.parse import urlparse

        parsed = urlparse(self.database_url)

        # Configurar variáveis de ambiente
        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password or ""

        # Comando pg_restore
        cmd = [
            "pg_restore",
            "-h",
            parsed.hostname or "localhost",
            "-p",
            str(parsed.port or 5432),
            "-U",
            parsed.username or "postgres",
            "-d",
            parsed.path.lstrip("/"),
            "--clean",  # Limpar objetos existentes
            "--if-exists",  # Não dar erro se objeto não existir
            str(backup_file),
        ]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            print(f"✅ Backup PostgreSQL restaurado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao restaurar PostgreSQL: {e.stderr.decode()}")
            return False
        except FileNotFoundError:
            print("❌ pg_restore não encontrado. Instale PostgreSQL client.")
            return False

    def restore_sqlite(self, backup_file):
        """Restaura backup do SQLite."""
        print(f"📦 Restaurando backup SQLite: {backup_file.name}")

        # Extrair caminho do arquivo
        db_path = self.database_url.replace("sqlite:///", "")
        target_db = Path(db_path)

        # Fazer backup do atual antes de substituir
        if target_db.exists():
            backup_current = target_db.with_suffix(".db.backup_antes_restore")
            shutil.copy2(target_db, backup_current)
            print(f"  💾 Backup do atual criado: {backup_current}")

        try:
            shutil.copy2(backup_file, target_db)
            print(f"✅ Backup SQLite restaurado com sucesso!")
            return True
        except Exception as e:
            print(f"❌ Erro ao restaurar SQLite: {e}")
            return False

    def restore_uploads(self, backup_file):
        """Restaura backup de uploads."""
        print(f"📁 Restaurando backup de uploads: {backup_file.name}")

        uploads_dir = Path(os.getenv("UPLOAD_FOLDER", "./uploads"))

        # Fazer backup do atual
        if uploads_dir.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_current = (
                uploads_dir.parent / f"uploads_backup_antes_restore_{timestamp}"
            )
            shutil.copytree(uploads_dir, backup_current)
            print(f"  💾 Backup do atual criado: {backup_current}")

        try:
            # Extrair arquivo tar.gz
            import tarfile

            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(uploads_dir.parent)

            print(f"✅ Backup uploads restaurado com sucesso!")
            return True
        except Exception as e:
            print(f"❌ Erro ao restaurar uploads: {e}")
            return False

    def run_interactive(self):
        """Executa restauração de forma interativa."""
        print("\n" + "=" * 80)
        print("  SISTEMA DE RESTAURAÇÃO - GestaoVersus")
        print("=" * 80 + "\n")

        # Listar backups
        backups = self.list_backups()

        if not backups["database"] and not backups["uploads"]:
            print("❌ Nenhum backup disponível!")
            return False

        # Menu
        print("\nO que deseja restaurar?")
        print("1. Banco de dados")
        print("2. Uploads")
        print("3. Ambos")
        print("0. Cancelar")

        try:
            choice = input("\nEscolha: ").strip()

            if choice == "0":
                print("❌ Restauração cancelada.")
                return False

            # Confirmar
            print("\n⚠️  ATENÇÃO: Esta operação irá SUBSTITUIR os dados atuais!")
            confirm = input("Tem certeza que deseja continuar? (S/N): ").upper()

            if confirm != "S":
                print("❌ Restauração cancelada.")
                return False

            # Restaurar banco
            if choice in ["1", "3"] and backups["database"]:
                print("\nSelecione o backup de banco:")
                for i, backup in enumerate(backups["database"], 1):
                    print(f"  {i}. {backup.name}")

                idx = int(input("\nNúmero: ")) - 1
                if 0 <= idx < len(backups["database"]):
                    backup_file = backups["database"][idx]

                    if self.is_postgresql():
                        self.restore_postgresql(backup_file)
                    elif self.is_sqlite():
                        self.restore_sqlite(backup_file)

            # Restaurar uploads
            if choice in ["2", "3"] and backups["uploads"]:
                print("\nSelecione o backup de uploads:")
                for i, backup in enumerate(backups["uploads"], 1):
                    print(f"  {i}. {backup.name}")

                idx = int(input("\nNúmero: ")) - 1
                if 0 <= idx < len(backups["uploads"]):
                    backup_file = backups["uploads"][idx]
                    self.restore_uploads(backup_file)

            print("\n" + "=" * 80)
            print("  RESTAURAÇÃO CONCLUÍDA")
            print("=" * 80 + "\n")

            return True

        except (ValueError, IndexError):
            print("❌ Entrada inválida!")
            return False


def main():
    """Função principal."""
    restore = DatabaseRestore()
    success = restore.run_interactive()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
