#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar todos os códigos de projetos e suas atividades.
Gera códigos no formato: {company_code}.J.{project_sequence} para projetos
e {project_code}.{activity_sequence:02d} para atividades.
"""

import sys
import os
import json
import logging
from typing import Optional, Dict, Any, List

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.postgres_helper import connect as pg_connect
from config_database import db_config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def _sanitize_company_code(raw_code: Optional[str], company_id: int) -> str:
    """Sanitize company code fallback used to compose project identifiers."""
    if raw_code:
        cleaned = "".join(
            ch for ch in str(raw_code).strip().upper() if ch.isalnum()
        )
        if cleaned:
            return cleaned
    return str(company_id).zfill(2)


def _parse_project_activities(raw: Any) -> List[Dict[str, Any]]:
    """Parse activities JSON/text into a list of dictionaries."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [activity for activity in raw if isinstance(activity, dict)]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [activity for activity in parsed if isinstance(activity, dict)]
        except Exception:
            return []
    return []


def _extract_sequence_from_code(code: Optional[str], project_code: Optional[str]) -> Optional[int]:
    """Return numeric sequence found at the end of an activity code."""
    if not code:
        return None

    text = str(code).strip()
    if not text:
        return None

    # Check for format: {company_code}.J.{project_num}.{activity_num}
    parts = text.split(".")
    if len(parts) >= 4 and parts[1] == "J":
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            pass
    
    # Check for format: {project_code}.{activity_num}
    if project_code:
        prefix = f"{project_code}."
        if text.startswith(prefix):
            suffix = text[len(prefix):]
            digits = "".join(ch for ch in suffix if ch.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    pass
    
    # Fallback: extract last numeric part
    if len(parts) > 1:
        suffix = parts[-1]
    else:
        suffix = text
    
    digits = "".join(ch for ch in suffix if ch.isdigit())
    if not digits:
        return None

    try:
        return int(digits)
    except ValueError:
        return None


def update_all_project_codes():
    """Atualiza todos os códigos de projetos e atividades."""
    conn = None
    cursor = None
    
    try:
        # Conectar ao banco
        logger.info("Conectando ao banco de dados...")
        conn = pg_connect()
        if not conn:
            raise Exception("Falha ao conectar ao banco de dados")
        cursor = conn.cursor()
        
        # Buscar todos os projetos agrupados por empresa
        logger.info("Buscando projetos...")
        cursor.execute("""
            SELECT 
                cp.id,
                cp.company_id,
                cp.code,
                cp.code_sequence,
                cp.activities,
                co.client_code
            FROM company_projects cp
            LEFT JOIN companies co ON co.id = cp.company_id
            ORDER BY cp.company_id, cp.id
        """)
        
        projects = cursor.fetchall()
        logger.info(f"Encontrados {len(projects)} projetos")
        
        if not projects:
            logger.warning("Nenhum projeto encontrado no banco de dados.")
            return
        
        # Agrupar projetos por empresa para calcular sequências
        projects_by_company: Dict[int, List[Dict[str, Any]]] = {}
        for row in projects:
            # RowProxy funciona como dict
            company_id = row.get('company_id') if hasattr(row, 'get') else row['company_id']
            if company_id not in projects_by_company:
                projects_by_company[company_id] = []
            projects_by_company[company_id].append({
                'id': row.get('id') if hasattr(row, 'get') else row['id'],
                'code': row.get('code') if hasattr(row, 'get') else row['code'],
                'code_sequence': row.get('code_sequence') if hasattr(row, 'get') else row['code_sequence'],
                'activities': row.get('activities') if hasattr(row, 'get') else row['activities'],
                'client_code': row.get('client_code') if hasattr(row, 'get') else row['client_code']
            })
        
        total_updated_projects = 0
        total_updated_activities = 0
        
        # Processar cada empresa
        for company_id, company_projects in projects_by_company.items():
            logger.info(f"\nProcessando empresa {company_id} ({len(company_projects)} projetos)...")
            
            # Obter código da empresa
            cursor.execute("SELECT client_code FROM companies WHERE id = %s", (company_id,))
            company_row = cursor.fetchone()
            client_code = None
            if company_row:
                client_code = company_row.get('client_code') if hasattr(company_row, 'get') else company_row['client_code']
            company_code = _sanitize_company_code(client_code, company_id)
            
            # Ordenar projetos por ID para manter sequência consistente
            company_projects.sort(key=lambda p: p['id'])
            
            # Atualizar códigos dos projetos
            for seq, project in enumerate(company_projects, start=1):
                project_id = project['id']
                new_project_code = f"{company_code}.J.{seq}"
                new_code_sequence = seq
                
                # Verificar se precisa atualizar o código do projeto
                needs_update = (
                    project['code'] != new_project_code or
                    project['code_sequence'] != new_code_sequence
                )
                
                if needs_update:
                    logger.info(f"  Atualizando projeto {project_id}: {project['code']} -> {new_project_code}")
                    cursor.execute("""
                        UPDATE company_projects
                        SET code = %s, code_sequence = %s
                        WHERE id = %s
                    """, (new_project_code, new_code_sequence, project_id))
                    total_updated_projects += 1
                else:
                    logger.debug(f"  Projeto {project_id} já tem código correto: {new_project_code}")
                
                # Processar atividades do projeto
                activities = _parse_project_activities(project['activities'])
                if not activities:
                    continue
                
                # Extrair sequências existentes
                assigned_sequences = set()
                max_sequence = 0
                for activity in activities:
                    code = str(activity.get("code") or "").strip()
                    if code:
                        sequence = _extract_sequence_from_code(code, new_project_code)
                        if sequence:
                            assigned_sequences.add(sequence)
                            if sequence > max_sequence:
                                max_sequence = sequence
                
                # Gerar códigos para atividades sem código ou com código inválido
                next_sequence = 1
                activities_updated = False
                for activity in activities:
                    code = str(activity.get("code") or "").strip()
                    expected_code = f"{new_project_code}.{next_sequence:02d}"
                    
                    # Se não tem código ou o código não corresponde ao esperado
                    if not code or not code.startswith(new_project_code):
                        # Encontrar próxima sequência disponível
                        while next_sequence in assigned_sequences:
                            next_sequence += 1
                        
                        activity['code'] = f"{new_project_code}.{next_sequence:02d}"
                        assigned_sequences.add(next_sequence)
                        if next_sequence > max_sequence:
                            max_sequence = next_sequence
                        next_sequence += 1
                        activities_updated = True
                    else:
                        # Código já existe e está correto, apenas extrair sequência
                        sequence = _extract_sequence_from_code(code, new_project_code)
                        if sequence:
                            if sequence >= next_sequence:
                                next_sequence = sequence + 1
                
                # Se atividades foram atualizadas, salvar no banco
                if activities_updated:
                    logger.info(f"    Atualizando {len(activities)} atividades do projeto {project_id}")
                    activities_json = json.dumps(activities, ensure_ascii=False)
                    # Usar CAST explícito para evitar problemas com placeholders
                    cursor.execute("""
                        UPDATE company_projects
                        SET activities = CAST(%s AS jsonb)
                        WHERE id = %s
                    """, (activities_json, project_id))
                    total_updated_activities += len(activities)
        
        # Commit das alterações
        logger.info("\nFazendo commit das alterações...")
        conn.commit()
        
        logger.info(f"\n✅ Atualização concluída!")
        logger.info(f"   Projetos atualizados: {total_updated_projects}")
        logger.info(f"   Atividades atualizadas: {total_updated_activities}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar códigos: {e}", exc_info=True)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Conexão fechada.")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Script de Atualização de Códigos de Projetos e Atividades")
    logger.info("=" * 60)
    try:
        update_all_project_codes()
    except Exception as e:
        logger.error(f"ERRO CRÍTICO: {e}", exc_info=True)
        sys.exit(1)

