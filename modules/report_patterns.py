#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MÃ³dulo de PadrÃµes de RelatÃ³rio
Sistema PEVAPP22
Gerencia padrÃµes de relatÃ³rio com seÃ§Ãµes prÃ©-configuradas
"""

import logging
from database.postgres_helper import connect as pg_connect
from datetime import datetime

logger = logging.getLogger(__name__)
from contextlib import contextmanager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_database import get_db


class ReportPatternsManager:
    """
    Classe para gerenciar padrÃµes de relatÃ³rio
    """
    
    def __init__(self, db_connection=None):
        """
        Inicializa o gerenciador de padrÃµes
        
        Args:
            db_connection: ConexÃ£o com banco de dados (opcional)
        """
        self.db = db_connection or get_db()
        self._create_table()
    
    def _create_table(self):
        """Cria a tabela de padrÃµes de relatÃ³rio se nÃ£o existir"""
        with self.db._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS report_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT NOT NULL UNIQUE,
                    description TEXT,
                    pattern_type TEXT NOT NULL,  -- 'process', 'company', 'custom'
                    sections_config TEXT NOT NULL,  -- JSON com configuraÃ§Ã£o das seÃ§Ãµes
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def create_pattern(self, name, code, description, pattern_type, sections_config):
        """
        Cria um novo padrÃ£o de relatÃ³rio
        
        Args:
            name: Nome do padrÃ£o
            code: CÃ³digo Ãºnico do padrÃ£o
            description: DescriÃ§Ã£o do padrÃ£o
            pattern_type: Tipo do padrÃ£o ('process', 'company', 'custom')
            sections_config: ConfiguraÃ§Ã£o das seÃ§Ãµes em JSON
            
        Returns:
            int: ID do padrÃ£o criado
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO report_patterns (name, code, description, pattern_type, sections_config)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, code, description, pattern_type, sections_config))
            return cursor.lastrowid
    
    def get_all_patterns(self):
        """
        Retorna todos os padrÃµes de relatÃ³rio
        
        Returns:
            list: Lista de padrÃµes
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
        Retorna um padrÃ£o especÃ­fico pelo ID
        
        Args:
            pattern_id: ID do padrÃ£o
            
        Returns:
            dict: Dados do padrÃ£o ou None
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
        Retorna padrÃµes de um tipo especÃ­fico
        
        Args:
            pattern_type: Tipo do padrÃ£o ('process', 'company', 'custom')
            
        Returns:
            list: Lista de padrÃµes do tipo especificado
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
        Atualiza um padrÃ£o existente
        
        Args:
            pattern_id: ID do padrÃ£o
            name: Novo nome
            code: Novo cÃ³digo
            description: Nova descriÃ§Ã£o
            pattern_type: Novo tipo
            sections_config: Nova configuraÃ§Ã£o das seÃ§Ãµes
            
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
        Exclui um padrÃ£o
        
        Args:
            pattern_id: ID do padrÃ£o
            
        Returns:
            bool: True se excluÃ­do com sucesso
        """
        with self.db._get_connection() as conn:
            cursor = conn.execute('DELETE FROM report_patterns WHERE id = ?', (pattern_id,))
            return cursor.rowcount > 0


# PadrÃµes prÃ©-definidos
DEFAULT_PATTERNS = [
    {
        'name': 'RelatÃ³rio Executivo de Processo',
        'code': 'EXEC_PROC',
        'description': 'RelatÃ³rio resumido para executivos com foco em indicadores e resumo',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'InformaÃ§Ãµes do Processo', 'required': True},
                {'id': 'flow', 'name': 'Fluxo do Processo', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    },
    {
        'name': 'RelatÃ³rio Operacional Completo',
        'code': 'OP_COMPLETE',
        'description': 'RelatÃ³rio completo com todas as seÃ§Ãµes para uso operacional',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'InformaÃ§Ãµes do Processo', 'required': True},
                {'id': 'flow', 'name': 'Fluxo do Processo', 'required': True},
                {'id': 'pop', 'name': 'Procedimento Operacional', 'required': True},
                {'id': 'routine', 'name': 'Rotinas e Colaboradores', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    },
    {
        'name': 'RelatÃ³rio de Auditoria',
        'code': 'AUDIT',
        'description': 'RelatÃ³rio focado em auditoria com POP e rotinas detalhadas',
        'pattern_type': 'process',
        'sections_config': {
            'sections': [
                {'id': 'info', 'name': 'InformaÃ§Ãµes do Processo', 'required': True},
                {'id': 'pop', 'name': 'Procedimento Operacional', 'required': True},
                {'id': 'routine', 'name': 'Rotinas e Colaboradores', 'required': True},
                {'id': 'indicators', 'name': 'Indicadores de Desempenho', 'required': True}
            ]
        }
    }
]


def initialize_default_patterns():
    """
    Inicializa os padrÃµes padrÃ£o do sistema
    """
    import json
    manager = ReportPatternsManager()
    
    for pattern_data in DEFAULT_PATTERNS:
        try:
            # Verificar se jÃ¡ existe
            existing = manager.get_all_patterns()
            if not any(p['code'] == pattern_data['code'] for p in existing):
                manager.create_pattern(
                    name=pattern_data['name'],
                    code=pattern_data['code'],
                    description=pattern_data['description'],
                    pattern_type=pattern_data['pattern_type'],
                    sections_config=json.dumps(pattern_data['sections_config'])
                )
                logger.info(f"âœ… PadrÃ£o '{pattern_data['name']}' criado")
        except Exception as e:
            logger.info(f"âŒ Erro ao criar padrÃ£o '{pattern_data['name']}': {e}")


if __name__ == "__main__":
    # Inicializar padrÃµes padrÃ£o
    initialize_default_patterns()


