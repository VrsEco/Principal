#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script simples para criar backup do banco de dados"""

import shutil
import os
from datetime import datetime
from pathlib import Path
import json
import sqlite3

# Criar pasta de backups
backup_dir = Path('backups')
backup_dir.mkdir(exist_ok=True)

# Timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

# Backup do banco
db_origem = Path('instance/pevapp22.db')

if db_origem.exists():
    backup_db = backup_dir / f'pevapp22_backup_{timestamp}.db'
    shutil.copy2(db_origem, backup_db)
    print(f"OK - Backup criado: {backup_db}")
    print(f"   Tamanho: {backup_db.stat().st_size / 1024:.2f} KB")
    
    # Gerar relatorio
    conn = sqlite3.connect(db_origem)
    cursor = conn.cursor()
    
    relatorio = {
        'timestamp': timestamp,
        'data_hora': datetime.now().isoformat(),
        'banco': str(db_origem),
        'tabelas': {}
    }
    
    # Contar registros
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    
    print("\nResumo do backup:")
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            if count > 0:
                relatorio['tabelas'][tabela] = count
                print(f"  - {tabela}: {count} registros")
        except:
            pass
    
    conn.close()
    
    # Salvar relatorio
    relatorio_file = backup_dir / f'relatorio_backup_{timestamp}.json'
    with open(relatorio_file, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print(f"\nRelatorio salvo: {relatorio_file}")
    print("\nBackup concluido com sucesso!")
else:
    print(f"ERRO: Banco nao encontrado: {db_origem}")




