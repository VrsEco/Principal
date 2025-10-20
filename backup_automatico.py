#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Backup Automático
Evita perda de dados entre versões
"""

import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path
import json

def criar_backup_completo():
    """Cria backup completo do banco de dados com timestamp"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Criar pasta de backups
    backup_dir = Path('backups')
    backup_dir.mkdir(exist_ok=True)
    
    # Backup do banco principal
    db_origem = Path('instance/pevapp22.db')
    
    if db_origem.exists():
        backup_db = backup_dir / f'pevapp22_backup_{timestamp}.db'
        shutil.copy2(db_origem, backup_db)
        print(f"✅ Backup criado: {backup_db}")
        
        # Criar relatório do backup
        relatorio = gerar_relatorio_backup(db_origem, timestamp)
        
        # Salvar relatório
        relatorio_file = backup_dir / f'relatorio_backup_{timestamp}.json'
        with open(relatorio_file, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Relatório criado: {relatorio_file}")
        
        return backup_db, relatorio
    else:
        print(f"❌ Banco de dados não encontrado: {db_origem}")
        return None, None

def gerar_relatorio_backup(db_path, timestamp):
    """Gera relatório detalhado do conteúdo do backup"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    relatorio = {
        'timestamp': timestamp,
        'data_hora': datetime.now().isoformat(),
        'banco': str(db_path),
        'tabelas': {}
    }
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    
    # Contar registros em cada tabela
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            relatorio['tabelas'][tabela] = count
        except:
            relatorio['tabelas'][tabela] = 'ERRO'
    
    # Dados críticos - GRV
    tabelas_grv = ['companies', 'process_areas', 'macro_processes', 'processes', 
                   'participants', 'drivers', 'okrs', 'projects']
    
    relatorio['dados_criticos'] = {}
    for tabela in tabelas_grv:
        if tabela in relatorio['tabelas']:
            relatorio['dados_criticos'][tabela] = relatorio['tabelas'][tabela]
    
    conn.close()
    
    return relatorio

def listar_backups():
    """Lista todos os backups disponíveis"""
    
    backup_dir = Path('backups')
    
    if not backup_dir.exists():
        print("Nenhum backup encontrado.")
        return []
    
    backups = sorted(backup_dir.glob('pevapp22_backup_*.db'), reverse=True)
    
    print("\n" + "="*80)
    print("  BACKUPS DISPONÍVEIS")
    print("="*80 + "\n")
    
    for i, backup in enumerate(backups, 1):
        # Tentar carregar relatório
        timestamp = backup.stem.replace('pevapp22_backup_', '')
        relatorio_file = backup_dir / f'relatorio_backup_{timestamp}.json'
        
        print(f"{i}. {backup.name}")
        print(f"   Tamanho: {backup.stat().st_size / 1024:.2f} KB")
        print(f"   Data: {datetime.fromtimestamp(backup.stat().st_mtime).strftime('%d/%m/%Y %H:%M:%S')}")
        
        if relatorio_file.exists():
            with open(relatorio_file, 'r', encoding='utf-8') as f:
                relatorio = json.load(f)
                print(f"   Dados críticos:")
                for tabela, count in relatorio.get('dados_criticos', {}).items():
                    print(f"     - {tabela}: {count}")
        print()
    
    return backups

def restaurar_backup(backup_path):
    """Restaura um backup"""
    
    print(f"\n⚠️  RESTAURANDO BACKUP: {backup_path}")
    print("Isso irá SUBSTITUIR o banco de dados atual!")
    
    resp = input("\nTem certeza? (S/N): ").upper()
    if resp != 'S':
        print("Restauração cancelada.")
        return False
    
    # Fazer backup do atual antes de restaurar
    print("\nCriando backup de segurança do banco atual...")
    criar_backup_completo()
    
    # Restaurar
    db_atual = Path('instance/pevapp22.db')
    shutil.copy2(backup_path, db_atual)
    
    print(f"✅ Backup restaurado com sucesso!")
    return True

def main():
    print("\n" + "="*80)
    print("  SISTEMA DE BACKUP AUTOMÁTICO")
    print("="*80)
    
    print("\n1. Criar novo backup")
    print("2. Listar backups")
    print("3. Restaurar backup")
    print("4. Sair")
    
    opcao = input("\nEscolha: ").strip()
    
    if opcao == '1':
        print("\nCriando backup...")
        criar_backup_completo()
    elif opcao == '2':
        listar_backups()
    elif opcao == '3':
        backups = listar_backups()
        if backups:
            try:
                num = int(input("\nNúmero do backup para restaurar: "))
                if 1 <= num <= len(backups):
                    restaurar_backup(backups[num-1])
                else:
                    print("Número inválido!")
            except ValueError:
                print("Entrada inválida!")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()




