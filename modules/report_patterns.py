#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Padrões de Relatório
Sistema PEVAPP22
Gerencia padrões de relatório com seções pré-configuradas
"""

from database.postgres_helper import connect as pg_connect
from datetime import datetime
from contextlib import contextmanager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_database import get_db


class ReportPatternsManager:
    """
    Classe para gerenciar padrões de relatório
    """
    
    def __init__(self, db_connection=None):
        """
        Inicializa o gerenciador de padrões
        
        Args:
            db_connection: Conexão com banco de dados (opcional)
        """
        self.db = db_connection or get_db()
        self._create_table()
    
    def _create_table(self):
        """Cria a tabela de padrões de relatório se não existir"""
        with self.db._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS report_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL UNIQUE,
                    description TEXT,
                    pattern_type TEXT NOT NULL,  -- 'process', 'company', 'custom'
                    sections_config TEXT NOT NULL,  -- JSON com configuração das seções
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def create_pattern(self, name, code, description, pattern_type, sections_config):
        """
        Cria um novo padrão de relatório
        
        Args:
            name: Nome do padrão
            code: Código único do padrão
            description: Descrição do padrão
            pattern_type: Tipo do padrão ('process', 'company', 'custom')
            sections_config: Configuração das seções em JSON
            
        Returns:
            int: ID do padrão criado
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO report_patterns (name, code, description, pattern_type, sections_config)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, code, description, pattern_type, sections_config))
            return cursor.lastrowid
    
    def get_all_patterns(self):
        """
        Retorna todos os padrões de relatório
        
        Returns:
            list: Lista de padrões
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, code, description, pattern_type, sections_config, created_at, updated_at
                FROM report_patterns
                ORDER BY name
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pattern_by_id(self, pattern_id):
        """
        Retorna um padrão específico pelo ID
        
        Args:
            pattern_id: ID do padrão
            
        Returns:
            dict: Dados do padrão ou None
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, code, description, pattern_type, sections_config, created_at, updated_at
                FROM report_patterns
                WHERE id = ?
            ''', (pattern_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_patterns_by_type(self, pattern_type):
        """
        Retorna padrões de um tipo específico
        
        Args:
            pattern_type: Tipo do padrão ('process', 'company', 'custom')
            
        Returns:
            list: Lista de padrões do tipo especificado
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                SELECT id, name, code, description, pattern_type, sections_config, created_at, updated_at
                FROM report_patterns
                WHERE pattern_type = ?
                ORDER BY name
            ''', (pattern_type,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_pattern(self, pattern_id, name, code, description, pattern_type, sections_config):
        """
        Atualiza um padrão existente
        
        Args:
            pattern_id: ID do padrão
            name: Novo nome
            code: Novo código
            description: Nova descrição
            pattern_type: Novo tipo
            sections_config: Nova configuração das seções
            
        Returns:
            bool: True se atualizado com sucesso
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                UPDATE report_patterns
                SET name = ?, code = ?, description = ?, pattern_type = ?, sections_config = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, code, description, pattern_type, sections_config, pattern_id))
            return cursor.rowcount > 0
    
    def delete_pattern(self, pattern_id):
        """
        Exclui um padrão
        
        Args:
            pattern_id: ID do padrão
            
        Returns:
            bool: True se excluído com sucesso
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('DELETE FROM report_patterns WHERE id = ?', (pattern_id,))
            return cursor.rowcount > 0


# Padrões pré-definidos
DEFAULT_PATTERNS = [
    {
        'name': 'Relatório Executivo de Processo',
        'code': 'EXEC_PROC',
        'description': 'Relatório resumido para executivos com foco em indicadores e resumo',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'Informações do Processo', 'required': True},
                {'id': 'flow', 'name': 'Fluxo do Processo', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    },
    {
        'name': 'Relatório Operacional Completo',
        'code': 'OP_COMPLETE',
        'description': 'Relatório completo com todas as seções para uso operacional',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'Informações do Processo', 'required': True},
                {'id': 'flow', 'name': 'Fluxo do Processo', 'required': True},
                {'id': 'pop', 'name': 'Procedimento Operacional', 'required': True},
                {'id': 'routine', 'name': 'Rotinas e Colaboradores', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    },
    {
        'name': 'Relatório de Auditoria',
        'code': 'AUDIT',
        'description': 'Relatório focado em auditoria com POP e rotinas detalhadas',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'Informações do Processo', 'required': True},
                {'id': 'pop', 'name': 'Procedimento Operacional', 'required': True},
                {'id': 'routine', 'name': 'Rotinas e Colaboradores', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    }
]


def initialize_default_patterns():
    """
    Inicializa os padrões padrão do sistema
    """
    import json
    manager = ReportPatternsManager()
    
    for pattern_data in DEFAULT_PATTERNS:
        try:
            # Verificar se já existe
            existing = manager.get_all_patterns()
            if not any(p['code'] == pattern_data['code'] for p in existing):
                manager.create_pattern(
                    name=pattern_data['name'],
                    code=pattern_data['code'],
                    description=pattern_data['description'],
                    pattern_type=pattern_data['pattern_type'],
                    sections_config=json.dumps(pattern_data['sections_config'])
                )
                print(f"✅ Padrão '{pattern_data['name']}' criado")
        except Exception as e:
            print(f"❌ Erro ao criar padrão '{pattern_data['name']}': {e}")


if __name__ == "__main__":
    # Inicializar padrões padrão
    initialize_default_patterns()
