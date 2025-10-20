#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backup de Arquivos (Uploads, PDFs, etc)
Cria backup dos arquivos e envia para S3/GCS
"""

import os
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

# Configurações
BACKUP_DIR = Path("/app/backups") if os.path.exists("/app") else Path("./backups")
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

# Diretórios para backup
DIRS_TO_BACKUP = [
    Path("/app/uploads") if os.path.exists("/app") else Path("./uploads"),
    Path("/app/temp_pdfs") if os.path.exists("/app") else Path("./temp_pdfs"),
]

def ensure_backup_dir():
    """Garante que diretório de backup existe"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Diretório de backup: {BACKUP_DIR}")

def create_files_backup():
    """Cria backup comprimido dos arquivos"""
    print("\n📦 Criando backup de arquivos...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_files_{timestamp}.tar.gz"
    
    try:
        with tarfile.open(backup_file, "w:gz") as tar:
            for dir_path in DIRS_TO_BACKUP:
                if dir_path.exists():
                    print(f"🔄 Adicionando: {dir_path}")
                    tar.add(dir_path, arcname=dir_path.name)
                else:
                    print(f"⚠️ Diretório não encontrado: {dir_path}")
        
        # Verificar tamanho
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        print(f"✅ Backup criado: {backup_file} ({size_mb:.2f} MB)")
        
        return backup_file
        
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        return None

def upload_to_s3(backup_file):
    """Upload do backup para AWS S3"""
    aws_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    s3_bucket = os.getenv("AWS_S3_BUCKET")
    
    if not all([aws_key, aws_secret, s3_bucket]):
        print("⚠️ Credenciais AWS não configuradas")
        return False
    
    try:
        import boto3
        
        print(f"\n☁️ Enviando para S3: {s3_bucket}...")
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret
        )
        
        s3_key = f"backups/files/{backup_file.name}"
        
        s3_client.upload_file(
            str(backup_file),
            s3_bucket,
            s3_key
        )
        
        print(f"✅ Backup enviado para S3: s3://{s3_bucket}/{s3_key}")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar para S3: {e}")
        return False

def cleanup_old_backups():
    """Remove backups antigos"""
    print(f"\n🗑️ Limpando backups antigos (> {RETENTION_DAYS} dias)...")
    
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    
    for backup_file in BACKUP_DIR.glob("backup_files_*.tar.gz"):
        try:
            date_str = backup_file.stem.split('_')[2]  # YYYYMMDD
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

def main():
    """Função principal"""
    print("=" * 60)
    print("📦 GestaoVersus - Backup de Arquivos")
    print("=" * 60)
    print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    ensure_backup_dir()
    
    backup_file = create_files_backup()
    
    if not backup_file:
        print("\n❌ Falha ao criar backup!")
        sys.exit(1)
    
    # Upload para S3 se configurado
    if os.getenv("BACKUP_STORAGE") in ["s3", "both"]:
        upload_to_s3(backup_file)
    
    cleanup_old_backups()
    
    print("\n" + "=" * 60)
    print("✅ Backup de arquivos concluído!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Backup cancelado")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        sys.exit(1)

