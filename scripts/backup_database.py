#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Backup Automático de Banco de Dados
GestaoVersus (APP30)

Suporta PostgreSQL e SQLite
Faz upload para AWS S3 ou Google Cloud Storage
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
import shutil

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


class DatabaseBackup:
    """Classe para gerenciar backups de banco de dados."""
    
    def __init__(self):
        """Inicializa configurações de backup."""
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
        self.backup_dir = Path(os.getenv('BACKUP_DIR', './backups'))
        self.backup_retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', 30))
        
        # AWS S3
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.s3_bucket = os.getenv('S3_BUCKET')
        
        # Google Cloud Storage
        self.gcs_bucket = os.getenv('GCS_BUCKET')
        self.gcp_credentials = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        # Criar diretório de backups
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def is_postgresql(self):
        """Verifica se o banco é PostgreSQL."""
        return self.database_url.startswith('postgresql://') or \
               self.database_url.startswith('postgres://')
    
    def is_sqlite(self):
        """Verifica se o banco é SQLite."""
        return self.database_url.startswith('sqlite:///')
    
    def generate_filename(self, extension='sql'):
        """Gera nome de arquivo para backup."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_type = 'postgresql' if self.is_postgresql() else 'sqlite'
        return f'backup_{db_type}_{timestamp}.{extension}'
    
    def backup_postgresql(self):
        """Faz backup do PostgreSQL usando pg_dump."""
        print("📦 Iniciando backup PostgreSQL...")
        
        # Parsear DATABASE_URL
        from urllib.parse import urlparse
        parsed = urlparse(self.database_url)
        
        # Configurar variáveis de ambiente para pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = parsed.password or ''
        
        # Nome do arquivo
        backup_file = self.backup_dir / self.generate_filename('sql')
        
        # Comando pg_dump
        cmd = [
            'pg_dump',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-U', parsed.username or 'postgres',
            '-d', parsed.path.lstrip('/'),
            '-F', 'c',  # Custom format (comprimido)
            '-f', str(backup_file)
        ]
        
        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            print(f"✅ Backup PostgreSQL criado: {backup_file}")
            return backup_file
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao fazer backup PostgreSQL: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            print("❌ pg_dump não encontrado. Instale PostgreSQL client.")
            return None
    
    def backup_sqlite(self):
        """Faz backup do SQLite copiando o arquivo."""
        print("📦 Iniciando backup SQLite...")
        
        # Extrair caminho do arquivo
        db_path = self.database_url.replace('sqlite:///', '')
        source_db = Path(db_path)
        
        if not source_db.exists():
            print(f"❌ Banco SQLite não encontrado: {source_db}")
            return None
        
        # Nome do arquivo
        backup_file = self.backup_dir / self.generate_filename('db')
        
        try:
            shutil.copy2(source_db, backup_file)
            print(f"✅ Backup SQLite criado: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ Erro ao fazer backup SQLite: {e}")
            return None
    
    def backup_uploads(self):
        """Faz backup da pasta de uploads."""
        print("📦 Iniciando backup de uploads...")
        
        uploads_dir = Path(os.getenv('UPLOAD_FOLDER', './uploads'))
        
        if not uploads_dir.exists():
            print("⚠️  Pasta de uploads não encontrada")
            return None
        
        # Nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'backup_uploads_{timestamp}.tar.gz'
        
        try:
            # Criar arquivo tar.gz
            import tarfile
            with tarfile.open(backup_file, 'w:gz') as tar:
                tar.add(uploads_dir, arcname='uploads')
            
            print(f"✅ Backup uploads criado: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ Erro ao fazer backup uploads: {e}")
            return None
    
    def upload_to_s3(self, file_path):
        """Faz upload do backup para AWS S3."""
        if not self.s3_bucket or not self.aws_access_key:
            print("⚠️  AWS S3 não configurado")
            return False
        
        print(f"☁️  Fazendo upload para S3: {self.s3_bucket}")
        
        try:
            import boto3
            s3 = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            # Nome do objeto no S3
            s3_key = f'backups/{file_path.name}'
            
            # Upload
            s3.upload_file(str(file_path), self.s3_bucket, s3_key)
            print(f"✅ Upload S3 concluído: s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            print(f"❌ Erro no upload S3: {e}")
            return False
    
    def upload_to_gcs(self, file_path):
        """Faz upload do backup para Google Cloud Storage."""
        if not self.gcs_bucket or not self.gcp_credentials:
            print("⚠️  Google Cloud Storage não configurado")
            return False
        
        print(f"☁️  Fazendo upload para GCS: {self.gcs_bucket}")
        
        try:
            from google.cloud import storage
            
            # Criar cliente
            client = storage.Client.from_service_account_json(self.gcp_credentials)
            bucket = client.bucket(self.gcs_bucket)
            
            # Nome do blob
            blob_name = f'backups/{file_path.name}'
            blob = bucket.blob(blob_name)
            
            # Upload
            blob.upload_from_filename(str(file_path))
            print(f"✅ Upload GCS concluído: gs://{self.gcs_bucket}/{blob_name}")
            return True
        except Exception as e:
            print(f"❌ Erro no upload GCS: {e}")
            return False
    
    def cleanup_old_backups(self):
        """Remove backups antigos (mais que retention_days)."""
        print(f"🧹 Limpando backups antigos (>{self.backup_retention_days} dias)...")
        
        cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
        removed_count = 0
        
        for backup_file in self.backup_dir.glob('backup_*'):
            if backup_file.is_file():
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    removed_count += 1
                    print(f"  🗑️  Removido: {backup_file.name}")
        
        if removed_count > 0:
            print(f"✅ {removed_count} backup(s) antigo(s) removido(s)")
        else:
            print("✅ Nenhum backup antigo para remover")
    
    def create_backup_report(self, backup_files):
        """Cria relatório do backup."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_type': 'postgresql' if self.is_postgresql() else 'sqlite',
            'files': [str(f) for f in backup_files if f],
            'retention_days': self.backup_retention_days
        }
        
        # Salvar relatório
        report_file = self.backup_dir / f'backup_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📄 Relatório criado: {report_file}")
        return report_file
    
    def run(self):
        """Executa o processo completo de backup."""
        print("\n" + "="*80)
        print("  SISTEMA DE BACKUP AUTOMÁTICO - GestaoVersus")
        print("="*80 + "\n")
        
        backup_files = []
        
        # 1. Backup do banco de dados
        if self.is_postgresql():
            db_backup = self.backup_postgresql()
        elif self.is_sqlite():
            db_backup = self.backup_sqlite()
        else:
            print("❌ Tipo de banco não suportado")
            db_backup = None
        
        if db_backup:
            backup_files.append(db_backup)
        
        # 2. Backup de uploads
        uploads_backup = self.backup_uploads()
        if uploads_backup:
            backup_files.append(uploads_backup)
        
        # 3. Upload para cloud (se configurado)
        for backup_file in backup_files:
            if self.s3_bucket:
                self.upload_to_s3(backup_file)
            if self.gcs_bucket:
                self.upload_to_gcs(backup_file)
        
        # 4. Criar relatório
        if backup_files:
            self.create_backup_report(backup_files)
        
        # 5. Limpeza de backups antigos
        self.cleanup_old_backups()
        
        print("\n" + "="*80)
        print("  BACKUP CONCLUÍDO")
        print("="*80 + "\n")
        
        return len(backup_files) > 0


def main():
    """Função principal."""
    backup = DatabaseBackup()
    success = backup.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


