#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Upload de backups SQLite para AWS S3 com criptografia do lado do servidor.

Requer variáveis de ambiente:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_DEFAULT_REGION (ex.: us-east-1)
- S3_BACKUP_BUCKET (nome do bucket)
- S3_BACKUP_PREFIX (prefixo opcional, ex.: app28/backups)
- S3_SSE (opcional, ex.: AES256)
"""

import os
import sys
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv


def find_latest_backup(backup_directory: Path) -> Optional[Path]:
    """Retorna o arquivo de backup .db mais recente dentro de backups/."""
    if not backup_directory.exists():
        return None
    candidates = sorted(
        backup_directory.glob("*backup*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def build_s3_key(prefix: Optional[str], local_path: Path) -> str:
    """Monta a chave S3 preservando nome e opcionalmente aplicando um prefixo."""
    prefix_clean = (prefix or "").strip("/")
    return f"{prefix_clean}/{local_path.name}" if prefix_clean else local_path.name


def upload_file_s3(local_path: Path, bucket: str, key: str, region: Optional[str], sse: Optional[str]) -> None:
    """Faz upload do arquivo para S3 com SSE opcional."""
    s3_client = boto3.client("s3", region_name=region)
    extra_args = {}
    if sse:
        extra_args["ServerSideEncryption"] = sse
    s3_client.upload_file(str(local_path), bucket, key, ExtraArgs=extra_args)


def main() -> int:
    load_dotenv()

    backup_dir = Path("backups")
    latest_backup = find_latest_backup(backup_dir)
    if latest_backup is None:
        print("Nenhum backup encontrado em 'backups/'. Crie um backup antes.")
        return 1

    bucket = os.getenv("S3_BACKUP_BUCKET")
    if not bucket:
        print("S3_BACKUP_BUCKET não definido no ambiente.")
        return 1

    prefix = os.getenv("S3_BACKUP_PREFIX")
    region = os.getenv("AWS_DEFAULT_REGION")
    sse = os.getenv("S3_SSE")

    key_db = build_s3_key(prefix, latest_backup)

    # Tenta enviar também o relatório JSON correspondente, se existir
    timestamp_guess = None
    try:
        name = latest_backup.name
        if "backup_" in name:
            timestamp_guess = name.split("backup_")[-1].split(".")[0]
    except Exception:
        pass

    report_path = None
    if timestamp_guess:
        report_candidate = backup_dir / f"relatorio_backup_{timestamp_guess}.json"
        if report_candidate.exists():
            report_path = report_candidate

    try:
        print(f"Enviando DB para S3: s3://{bucket}/{key_db}")
        upload_file_s3(latest_backup, bucket, key_db, region, sse)
        if report_path:
            key_report = build_s3_key(prefix, report_path)
            print(f"Enviando relatório para S3: s3://{bucket}/{key_report}")
            upload_file_s3(report_path, bucket, key_report, region, sse)
        print("Upload concluído com sucesso.")
        return 0
    except (BotoCoreError, ClientError) as exc:
        print(f"Falha ao enviar para S3: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
