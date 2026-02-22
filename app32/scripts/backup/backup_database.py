#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup Automático do Banco de Dados
Cria backup do PostgreSQL e envia para S3/GCS
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
import gzip
import shutil

# Configurações
BACKUP_DIR = Path("/app/backups") if os.path.exists("/app") else Path("./backups")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
DATABASE_URL = os.getenv("DATABASE_URL")


def ensure_backup_dir():
    """Garante que diretório de backup existe"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Diretório de backup: {BACKUP_DIR}")


def get_db_connection_params():
    """Extrai parâmetros de conexão do DATABASE_URL"""
    # postgresql://user:password@host:port/dbname
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada!")

    import re

    match = re.match(r"postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", DATABASE_URL)

    if not match:
        raise ValueError("DATABASE_URL inválida!")

    return {
        "user": match.group(1),
        "password": match.group(2),
        "host": match.group(3),
        "port": match.group(4),
        "database": match.group(5),
    }


def create_backup():
    """Cria backup do banco de dados"""
    print("\n💾 Criando backup do banco de dados...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}.sql"
    backup_compressed = BACKUP_DIR / f"backup_{timestamp}.sql.gz"

    try:
        db_params = get_db_connection_params()

        # Comando pg_dump
        cmd = [
            "pg_dump",
            "-h",
            db_params["host"],
            "-p",
            db_params["port"],
            "-U",
            db_params["user"],
            "-d",
            db_params["database"],
            "-F",
            "p",  # Plain SQL
            "-f",
            str(backup_file),
        ]

        # Configurar senha via variável de ambiente
        env = os.environ.copy()
        env["PGPASSWORD"] = db_params["password"]

        # Executar pg_dump
        print(f"🔄 Executando pg_dump...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Erro ao executar pg_dump: {result.stderr}")
            return None

        print(f"✅ Backup criado: {backup_file}")

        # Comprimir backup
        print(f"🔄 Comprimindo backup...")
        with open(backup_file, "rb") as f_in:
            with gzip.open(backup_compressed, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Remover arquivo não comprimido
        backup_file.unlink()

        # Verificar tamanho
        size_mb = backup_compressed.stat().st_size / (1024 * 1024)
        print(f"✅ Backup comprimido: {backup_compressed} ({size_mb:.2f} MB)")

        return backup_compressed

    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return None


def upload_to_s3(backup_file):
    """Upload do backup para AWS S3"""
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket = os.getenv("AWS_S3_BUCKET")

    if not all([aws_key, aws_secret, s3_bucket]):
        print("⚠️ Credenciais AWS não configuradas, pulando upload S3")
        return False

    try:
        import boto3
        from botocore.exceptions import ClientError

        print(f"\n☁️ Enviando para S3: {s3_bucket}...")

        s3_client = boto3.client(
            "s3", aws_access_key_id=aws_key, aws_secret_access_key=aws_secret
        )

        s3_key = f"backups/database/{backup_file.name}"

        s3_client.upload_file(str(backup_file), s3_bucket, s3_key)

        print(f"✅ Backup enviado para S3: s3://{s3_bucket}/{s3_key}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar para S3: {e}")
        return False


def upload_to_gcs(backup_file):
    """Upload do backup para Google Cloud Storage"""
    gcs_bucket = os.getenv("GCS_BUCKET")
    gcp_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if not all([gcs_bucket, gcp_credentials]):
        print("⚠️ Credenciais GCP não configuradas, pulando upload GCS")
        return False

    try:
        from google.cloud import storage

        print(f"\n☁️ Enviando para GCS: {gcs_bucket}...")

        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket)

        blob_name = f"backups/database/{backup_file.name}"
        blob = bucket.blob(blob_name)

        blob.upload_from_filename(str(backup_file))

        print(f"✅ Backup enviado para GCS: gs://{gcs_bucket}/{blob_name}")
        return True

    except Exception as e:
        print(f"❌ Erro ao enviar para GCS: {e}")
        return False


def cleanup_old_backups():
    """Remove backups antigos (mais de RETENTION_DAYS dias)"""
    print(f"\n🗑️ Limpando backups antigos (> {RETENTION_DAYS} dias)...")

    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0

    for backup_file in BACKUP_DIR.glob("backup_*.sql.gz"):
        # Extrair data do nome do arquivo: backup_YYYYMMDD_HHMMSS.sql.gz
        try:
            date_str = backup_file.stem.split("_")[1]  # YYYYMMDD
            backup_date = datetime.strptime(date_str, "%Y%m%d")

            if backup_date < cutoff_date:
                backup_file.unlink()
                removed += 1
                print(f"🗑️ Removido: {backup_file.name}")
        except:
            continue

    if removed > 0:
        print(f"✅ {removed} backup(s) antigo(s) removido(s)")
    else:
        print("✅ Nenhum backup antigo para remover")


def list_backups():
    """Lista todos os backups disponíveis"""
    print("\n📋 Backups disponíveis:")

    backups = sorted(BACKUP_DIR.glob("backup_*.sql.gz"), reverse=True)

    if not backups:
        print("❌ Nenhum backup encontrado")
        return

    for i, backup in enumerate(backups[:10], 1):  # Mostrar últimos 10
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        print(
            f"{i}. {backup.name} - {size_mb:.2f} MB - {mtime.strftime('%Y-%m-%d %H:%M:%S')}"
        )


def main():
    """Função principal"""
    print("=" * 60)
    print("💾 GestaoVersus - Backup Automático do Banco de Dados")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Garantir diretório de backup
    ensure_backup_dir()

    # Criar backup
    backup_file = create_backup()

    if not backup_file:
        print("\n❌ Falha ao criar backup!")
        sys.exit(1)

    # Upload para cloud (S3 ou GCS)
    backup_storage = os.getenv("BACKUP_STORAGE", "local")

    if backup_storage == "s3":
        upload_to_s3(backup_file)
    elif backup_storage == "gcs":
        upload_to_gcs(backup_file)
    elif backup_storage == "both":
        upload_to_s3(backup_file)
        upload_to_gcs(backup_file)
    else:
        print("ℹ️ Backup armazenado localmente apenas")

    # Limpar backups antigos
    cleanup_old_backups()

    # Listar backups disponíveis
    list_backups()

    print("\n" + "=" * 60)
    print("✅ Backup concluído com sucesso!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Backup cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
