#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migrar dados GRV do APP25 para APP26"""

import sqlite3
import os

def migrar_grv():
    print("\n" + "="*80)
    print("  MIGRACAO DE DADOS GRV: APP25 -> APP26")
    print("="*80 + "\n")
    
    # Conectar aos bancos
    db_origem = '../app25/pevapp22.db'
    db_destino = 'instance/pevapp22.db'
    
    if not os.path.exists(db_origem):
        print(f"ERRO: Banco de origem nao encontrado: {db_origem}")
        return
    
    conn_origem = sqlite3.connect(db_origem)
    conn_destino = sqlite3.connect(db_destino)
    
    cursor_origem = conn_origem.cursor()
    cursor_destino = conn_destino.cursor()
    
    # Verificar dados de origem
    cursor_origem.execute("SELECT COUNT(*) FROM process_areas")
    areas_origem = cursor_origem.fetchone()[0]
    
    cursor_origem.execute("SELECT COUNT(*) FROM macro_processes")
    macros_origem = cursor_origem.fetchone()[0]
    
    cursor_origem.execute("SELECT COUNT(*) FROM processes")
    procs_origem = cursor_origem.fetchone()[0]
    
    cursor_origem.execute("SELECT COUNT(*) FROM process_activities")
    acts_origem = cursor_origem.fetchone()[0]
    
    print("DADOS NO APP25 (ORIGEM):")
    print(f"  - Areas de Processo: {areas_origem}")
    print(f"  - Macroprocessos:    {macros_origem}")
    print(f"  - Processos:         {procs_origem}")
    print(f"  - Atividades:        {acts_origem}")
    print(f"  TOTAL:               {areas_origem + macros_origem + procs_origem + acts_origem}")
    
    # Verificar dados de destino
    cursor_destino.execute("SELECT COUNT(*) FROM process_areas")
    areas_destino = cursor_destino.fetchone()[0]
    
    cursor_destino.execute("SELECT COUNT(*) FROM macro_processes")
    macros_destino = cursor_destino.fetchone()[0]
    
    cursor_destino.execute("SELECT COUNT(*) FROM processes")
    procs_destino = cursor_destino.fetchone()[0]
    
    try:
        cursor_destino.execute("SELECT COUNT(*) FROM process_activities")
        acts_destino = cursor_destino.fetchone()[0]
    except:
        acts_destino = 0
    
    print("\nDADOS NO APP26 (DESTINO - ANTES):")
    print(f"  - Areas de Processo: {areas_destino}")
    print(f"  - Macroprocessos:    {macros_destino}")
    print(f"  - Processos:         {procs_destino}")
    print(f"  - Atividades:        {acts_destino}")
    
    if areas_destino > 0 or macros_destino > 0 or procs_destino > 0:
        print("\n*** AVISO: Ja existem dados GRV no APP26! ***")
        resp = input("\nDeseja SUBSTITUIR os dados? (S/N): ").upper()
        if resp != 'S':
            print("Migracao cancelada.")
            return
        
        # Limpar dados existentes
        print("\nLimpando dados GRV do APP26...")
        cursor_destino.execute("DELETE FROM process_activities")
        cursor_destino.execute("DELETE FROM processes")
        cursor_destino.execute("DELETE FROM macro_processes")
        cursor_destino.execute("DELETE FROM process_areas")
        conn_destino.commit()
        print("Dados limpos!")
    
    print("\n" + "-"*80)
    print("Iniciando migracao...")
    print("-"*80 + "\n")
    
    # 1. Migrar AREAS
    print("1. Migrando Areas de Processo...")
    cursor_origem.execute("SELECT * FROM process_areas")
    areas = cursor_origem.fetchall()
    
    cursor_origem.execute("PRAGMA table_info(process_areas)")
    cols_areas = [col[1] for col in cursor_origem.fetchall()]
    
    placeholders = ','.join(['?' for _ in cols_areas])
    cursor_destino.executemany(
        f"INSERT INTO process_areas ({','.join(cols_areas)}) VALUES ({placeholders})",
        areas
    )
    print(f"   -> {len(areas)} areas migradas")
    
    # 2. Migrar MACROPROCESSOS
    print("2. Migrando Macroprocessos...")
    cursor_origem.execute("SELECT * FROM macro_processes")
    macros = cursor_origem.fetchall()
    
    cursor_origem.execute("PRAGMA table_info(macro_processes)")
    cols_macros = [col[1] for col in cursor_origem.fetchall()]
    
    placeholders = ','.join(['?' for _ in cols_macros])
    cursor_destino.executemany(
        f"INSERT INTO macro_processes ({','.join(cols_macros)}) VALUES ({placeholders})",
        macros
    )
    print(f"   -> {len(macros)} macroprocessos migrados")
    
    # 3. Migrar PROCESSOS
    print("3. Migrando Processos...")
    cursor_origem.execute("SELECT * FROM processes")
    processos = cursor_origem.fetchall()
    
    cursor_origem.execute("PRAGMA table_info(processes)")
    cols_procs = [col[1] for col in cursor_origem.fetchall()]
    
    placeholders = ','.join(['?' for _ in cols_procs])
    cursor_destino.executemany(
        f"INSERT INTO processes ({','.join(cols_procs)}) VALUES ({placeholders})",
        processos
    )
    print(f"   -> {len(processos)} processos migrados")
    
    # 4. Migrar ATIVIDADES
    print("4. Migrando Atividades...")
    cursor_origem.execute("SELECT * FROM process_activities")
    atividades = cursor_origem.fetchall()
    
    if atividades:
        cursor_origem.execute("PRAGMA table_info(process_activities)")
        cols_acts = [col[1] for col in cursor_origem.fetchall()]
        
        placeholders = ','.join(['?' for _ in cols_acts])
        cursor_destino.executemany(
            f"INSERT INTO process_activities ({','.join(cols_acts)}) VALUES ({placeholders})",
            atividades
        )
        print(f"   -> {len(atividades)} atividades migradas")
    else:
        print(f"   -> Nenhuma atividade para migrar")
    
    # Commit
    conn_destino.commit()
    
    # Verificar resultado
    print("\n" + "-"*80)
    print("VERIFICANDO RESULTADO...")
    print("-"*80 + "\n")
    
    cursor_destino.execute("SELECT COUNT(*) FROM process_areas")
    areas_final = cursor_destino.fetchone()[0]
    
    cursor_destino.execute("SELECT COUNT(*) FROM macro_processes")
    macros_final = cursor_destino.fetchone()[0]
    
    cursor_destino.execute("SELECT COUNT(*) FROM processes")
    procs_final = cursor_destino.fetchone()[0]
    
    try:
        cursor_destino.execute("SELECT COUNT(*) FROM process_activities")
        acts_final = cursor_destino.fetchone()[0]
    except:
        acts_final = 0
    
    print("DADOS NO APP26 (DESTINO - DEPOIS):")
    print(f"  - Areas de Processo: {areas_final}")
    print(f"  - Macroprocessos:    {macros_final}")
    print(f"  - Processos:         {procs_final}")
    print(f"  - Atividades:        {acts_final}")
    print(f"  TOTAL:               {areas_final + macros_final + procs_final + acts_final}")
    
    # Fechar conexões
    conn_origem.close()
    conn_destino.close()
    
    print("\n" + "="*80)
    if (areas_final == areas_origem and macros_final == macros_origem and 
        procs_final == procs_origem):
        print("  MIGRACAO CONCLUIDA COM SUCESSO!")
    else:
        print("  AVISO: Algumas divergencias detectadas!")
    print("="*80)
    
    print("\nPROXIMOS PASSOS:")
    print("  1. Acesse: http://127.0.0.1:5002/grv/dashboard")
    print("  2. Selecione a empresa desejada")
    print("  3. Verifique se os dados GRV aparecem")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    migrar_grv()




