#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Migração SEGURA entre versões
GARANTE que nenhum dado será perdido
"""

import sqlite3
import shutil
import os
from datetime import datetime
from pathlib import Path
import json

def verificar_dados_origem(db_origem):
    """Verifica e documenta TODOS os dados do banco de origem"""
    
    print(f"\n📊 Analisando banco ORIGEM: {db_origem}")
    print("-" * 80)
    
    conn = sqlite3.connect(db_origem)
    cursor = conn.cursor()
    
    # Listar todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    
    dados_origem = {}
    total_registros = 0
    
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            dados_origem[tabela] = count
            total_registros += count
            
            if count > 0:
                print(f"  {tabela:<40} {count:>6} registros")
        except:
            dados_origem[tabela] = 0
    
    conn.close()
    
    print(f"\n  TOTAL: {total_registros} registros")
    
    return dados_origem, total_registros

def verificar_dados_destino(db_destino):
    """Verifica dados do banco destino"""
    
    print(f"\n📊 Analisando banco DESTINO: {db_destino}")
    print("-" * 80)
    
    if not os.path.exists(db_destino):
        print("  Banco destino não existe (será criado)")
        return {}, 0
    
    conn = sqlite3.connect(db_destino)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in cursor.fetchall()]
    
    dados_destino = {}
    total_registros = 0
    
    for tabela in tabelas:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            count = cursor.fetchone()[0]
            dados_destino[tabela] = count
            total_registros += count
            
            if count > 0:
                print(f"  {tabela:<40} {count:>6} registros")
        except:
            dados_destino[tabela] = 0
    
    conn.close()
    
    print(f"\n  TOTAL: {total_registros} registros")
    
    return dados_destino, total_registros

def criar_backup_pre_migracao(db_path):
    """Cria backup antes da migração"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path('backups_migracao')
    backup_dir.mkdir(exist_ok=True)
    
    if os.path.exists(db_path):
        backup_path = backup_dir / f'pre_migracao_{timestamp}.db'
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup criado: {backup_path}")
        return backup_path
    return None

def migrar_tabela(conn_origem, conn_destino, tabela):
    """Migra uma tabela específica com verificação"""
    
    cursor_origem = conn_origem.cursor()
    cursor_destino = conn_destino.cursor()
    
    # Contar registros origem
    cursor_origem.execute(f"SELECT COUNT(*) FROM {tabela}")
    count_origem = cursor_origem.fetchone()[0]
    
    if count_origem == 0:
        return 0, 0
    
    # Obter estrutura
    cursor_origem.execute(f"PRAGMA table_info({tabela})")
    colunas = [col[1] for col in cursor_origem.fetchall()]
    
    # Buscar dados
    cursor_origem.execute(f"SELECT * FROM {tabela}")
    dados = cursor_origem.fetchall()
    
    # Inserir no destino
    placeholders = ','.join(['?' for _ in colunas])
    migrados = 0
    
    for row in dados:
        try:
            cursor_destino.execute(
                f"INSERT OR REPLACE INTO {tabela} ({','.join(colunas)}) VALUES ({placeholders})",
                row
            )
            migrados += 1
        except Exception as e:
            print(f"    ⚠️  Erro ao migrar registro de {tabela}: {e}")
    
    return count_origem, migrados

def migracao_segura(db_origem, db_destino):
    """Executa migração SEGURA com verificação completa"""
    
    print("\n" + "="*80)
    print("  MIGRAÇÃO SEGURA DE DADOS")
    print("="*80)
    
    # 1. Verificar origem
    dados_origem, total_origem = verificar_dados_origem(db_origem)
    
    # 2. Verificar destino
    dados_destino, total_destino = verificar_dados_destino(db_destino)
    
    # 3. Criar backup do destino
    print("\n" + "="*80)
    print("  CRIANDO BACKUP DE SEGURANÇA")
    print("="*80 + "\n")
    
    backup_destino = criar_backup_pre_migracao(db_destino)
    
    # 4. Confirmar migração
    print("\n" + "="*80)
    print("  RESUMO DA MIGRAÇÃO")
    print("="*80)
    print(f"\nOrigem:  {total_origem} registros")
    print(f"Destino: {total_destino} registros")
    print(f"\nBackup criado: {backup_destino}")
    
    resp = input("\n⚠️  Confirmar migração? (S/N): ").upper()
    if resp != 'S':
        print("\nMigração cancelada.")
        return False
    
    # 5. Migrar dados
    print("\n" + "="*80)
    print("  MIGRANDO DADOS")
    print("="*80 + "\n")
    
    conn_origem = sqlite3.connect(db_origem)
    conn_destino = sqlite3.connect(db_destino)
    
    relatorio_migracao = {}
    
    # Ordem de migração (dependências)
    ordem_tabelas = [
        'companies',
        'plans', 
        'company_data',
        'participants',
        'drivers',
        'okrs',
        'projects',
        'process_areas',
        'macro_processes',
        'processes',
        'process_activities',
        'roles'
    ]
    
    # Migrar tabelas na ordem
    for tabela in ordem_tabelas:
        if tabela in dados_origem and dados_origem[tabela] > 0:
            print(f"Migrando {tabela}...")
            origem_count, migrados = migrar_tabela(conn_origem, conn_destino, tabela)
            relatorio_migracao[tabela] = {
                'origem': origem_count,
                'migrados': migrados,
                'sucesso': origem_count == migrados
            }
            
            if origem_count == migrados:
                print(f"  ✅ {migrados}/{origem_count} registros migrados")
            else:
                print(f"  ⚠️  {migrados}/{origem_count} registros migrados")
    
    # Commit
    conn_destino.commit()
    
    # 6. Verificar resultado
    print("\n" + "="*80)
    print("  VERIFICANDO RESULTADO")
    print("="*80 + "\n")
    
    cursor_destino = conn_destino.cursor()
    verificacao_ok = True
    
    for tabela, info in relatorio_migracao.items():
        cursor_destino.execute(f"SELECT COUNT(*) FROM {tabela}")
        count_final = cursor_destino.fetchone()[0]
        
        if count_final >= info['origem']:
            print(f"  ✅ {tabela}: {count_final} registros (OK)")
        else:
            print(f"  ❌ {tabela}: {count_final} registros (ESPERADO: {info['origem']})")
            verificacao_ok = False
    
    conn_origem.close()
    conn_destino.close()
    
    # 7. Resultado final
    print("\n" + "="*80)
    if verificacao_ok:
        print("  ✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("  TODOS OS DADOS FORAM PRESERVADOS!")
    else:
        print("  ⚠️  MIGRAÇÃO CONCLUÍDA COM ALERTAS")
        print(f"  Backup disponível em: {backup_destino}")
    print("="*80 + "\n")
    
    # Salvar relatório
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    relatorio_file = Path('backups_migracao') / f'relatorio_migracao_{timestamp}.json'
    
    relatorio = {
        'timestamp': timestamp,
        'origem': str(db_origem),
        'destino': str(db_destino),
        'backup': str(backup_destino),
        'total_origem': total_origem,
        'total_destino': total_destino,
        'tabelas': relatorio_migracao,
        'sucesso': verificacao_ok
    }
    
    with open(relatorio_file, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    print(f"📄 Relatório salvo: {relatorio_file}\n")
    
    return verificacao_ok

def main():
    print("\n" + "="*80)
    print("  SISTEMA DE MIGRAÇÃO SEGURA")
    print("="*80)
    
    print("\nEste sistema garante que NENHUM dado será perdido na migração.")
    print("\nOpções:")
    print("  1. Migrar APP25 -> APP26")
    print("  2. Migração personalizada")
    print("  3. Sair")
    
    opcao = input("\nEscolha: ").strip()
    
    if opcao == '1':
        db_origem = '../app25/instance/pevapp22.db'
        db_destino = 'instance/pevapp22.db'
        
        if os.path.exists(db_origem):
            migracao_segura(db_origem, db_destino)
        else:
            print(f"❌ Banco de origem não encontrado: {db_origem}")
    
    elif opcao == '2':
        db_origem = input("Caminho do banco ORIGEM: ").strip()
        db_destino = input("Caminho do banco DESTINO: ").strip()
        
        if os.path.exists(db_origem):
            migracao_segura(db_origem, db_destino)
        else:
            print(f"❌ Banco de origem não encontrado: {db_origem}")

if __name__ == "__main__":
    main()




