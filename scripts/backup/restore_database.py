#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Restauração de Backup do Banco de Dados
Restaura backup do PostgreSQL a partir de arquivo local ou cloud
"""

import os
import sys
import subprocess
import gzip
from datetime import datetime
from pathlib import Path
import tempfile

# Configurações
BACKUP_DIR = Path("/app/backups") if os.path.exists("/app") else Path("./backups")
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection_params():
    """Extrai parâmetros de conexão do DATABASE_URL"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL não configurada!")
    
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
    
    if not match:
        raise ValueError("DATABASE_URL inválida!")
    
    return {
        'user': match.group(1),
        'password': match.group(2),
        'host': match.group(3),
        'port': match.group(4),
        'database': match.group(5)
    }

def list_available_backups():
    """Lista backups disponíveis"""
    backups = sorted(BACKUP_DIR.glob("backup_*.sql.gz"), reverse=True)
    
    if not backups:
        print("❌ Nenhum backup encontrado em", BACKUP_DIR)
        return []
    
    print("\n📋 Backups disponíveis:")
    print("-" * 80)
    
    backup_list = []
    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        
        print(f"{i}. {backup.name}")
        print(f"   Tamanho: {size_mb:.2f} MB")
        print(f"   Data: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        backup_list.append(backup)
    
    return backup_list

def verify_backup_integrity(backup_file):
    """Verifica integridade do arquivo de backup"""
    print(f"\n🔍 Verificando integridade de {backup_file.name}...")
    
    try:
        with gzip.open(backup_file, 'rb') as f:
            # Tentar ler o arquivo
            f.read(1024)
        
        print("✅ Backup íntegro!")
        return True
    except Exception as e:
        print(f"❌ Backup corrompido: {e}")
        return False

def create_pre_restore_backup():
    """Cria backup do estado atual antes de restaurar"""
    print("\n💾 Criando backup de segurança do estado atual...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_pre_restore_{timestamp}.sql.gz"
    
    try:
        db_params = get_db_connection_params()
        
        # Comando pg_dump
        cmd = [
            "pg_dump",
            "-h", db_params['host'],
            "-p", db_params['port'],
            "-U", db_params['user'],
            "-d", db_params['database'],
            "-F", "p"
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_params['password']
        
        # Executar pg_dump e comprimir
        print(f"🔄 Criando backup de segurança...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ Aviso: Não foi possível criar backup de segurança")
            return None
        
        # Comprimir
        with gzip.open(backup_file, 'wb') as f:
            f.write(result.stdout.encode())
        
        print(f"✅ Backup de segurança criado: {backup_file.name}")
        return backup_file
        
    except Exception as e:
        print(f"⚠️ Aviso: Erro ao criar backup de segurança: {e}")
        return None

def restore_backup(backup_file):
    """Restaura backup do banco de dados"""
    print(f"\n🔄 Restaurando backup: {backup_file.name}...")
    
    try:
        db_params = get_db_connection_params()
        
        # Descomprimir backup para arquivo temporário
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
            temp_path = temp_file.name
            
            print("🔄 Descomprimindo backup...")
            with gzip.open(backup_file, 'rt') as f:
                temp_file.write(f.read())
        
        # Comando psql para restaurar
        cmd = [
            "psql",
            "-h", db_params['host'],
            "-p", db_params['port'],
            "-U", db_params['user'],
            "-d", db_params['database'],
            "-f", temp_path
        ]
        
        env = os.environ.copy()
        env['PGPASSWORD'] = db_params['password']
        
        # Executar restauração
        print(f"🔄 Restaurando dados...")
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        # Limpar arquivo temporário
        os.unlink(temp_path)
        
        if result.returncode != 0:
            print(f"❌ Erro ao restaurar: {result.stderr}")
            return False
        
        print(f"✅ Backup restaurado com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao restaurar backup: {e}")
        return False

def main():
    """Função principal"""
    print("=" * 80)
    print("🔄 GestaoVersus - Restauração de Backup do Banco de Dados")
    print("=" * 80)
    print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Listar backups disponíveis
    backups = list_available_backups()
    
    if not backups:
        sys.exit(1)
    
    # Selecionar backup
    print("\n" + "=" * 80)
    try:
        choice = input("Digite o número do backup para restaurar (ou 'q' para sair): ").strip()
        
        if choice.lower() == 'q':
            print("👋 Operação cancelada")
            sys.exit(0)
        
        backup_index = int(choice) - 1
        
        if backup_index < 0 or backup_index >= len(backups):
            print("❌ Opção inválida!")
            sys.exit(1)
        
        selected_backup = backups[backup_index]
        
    except ValueError:
        print("❌ Entrada inválida!")
        sys.exit(1)
    
    # Confirmar restauração
    print("\n" + "=" * 80)
    print("⚠️ ATENÇÃO: Esta operação irá SUBSTITUIR todos os dados atuais!")
    print(f"📁 Backup selecionado: {selected_backup.name}")
    print("=" * 80)
    
    confirmation = input("Digite 'CONFIRMAR' para prosseguir: ").strip()
    
    if confirmation != "CONFIRMAR":
        print("👋 Operação cancelada")
        sys.exit(0)
    
    # Verificar integridade
    if not verify_backup_integrity(selected_backup):
        sys.exit(1)
    
    # Criar backup de segurança
    pre_restore_backup = create_pre_restore_backup()
    
    if pre_restore_backup:
        print(f"✅ Backup de segurança salvo em: {pre_restore_backup.name}")
    
    # Restaurar
    success = restore_backup(selected_backup)
    
    if success:
        print("\n" + "=" * 80)
        print("✅ Restauração concluída com sucesso!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ Falha na restauração!")
        if pre_restore_backup:
            print(f"⚠️ Você pode reverter usando: {pre_restore_backup.name}")
        print("=" * 80)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Restauração cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

