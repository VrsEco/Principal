#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper para conexões PostgreSQL
Substitui conexões diretas ao SQLite
"""

from sqlalchemy import create_engine, text
import os

# Configurações do PostgreSQL
# Priorizar DATABASE_URL do ambiente (já vem com psycopg2)
DATABASE_URL = os.environ.get('DATABASE_URL')

# Se DATABASE_URL não existir, construir a partir de variáveis individuais
if not DATABASE_URL:
    PG_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
    PG_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
    PG_DB = os.environ.get('POSTGRES_DB', 'bd_app_versus')
    PG_USER = os.environ.get('POSTGRES_USER', 'postgres')
    PG_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '*Paraiso1978')
    DATABASE_URL = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}'
elif not DATABASE_URL.startswith('postgresql+psycopg2'):
    # Se DATABASE_URL existe mas não tem o driver, adicionar
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg2://')

# Engine global
_engine = None

def get_engine():
    """Retorna engine SQLAlchemy para PostgreSQL"""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
    return _engine

def get_connection():
    """Retorna uma conexão PostgreSQL (compatível com sqlite3.connect)"""
    engine = get_engine()
    return engine.connect()

def execute_query(sql, params=None):
    """Executa uma query e retorna resultados"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        if sql.strip().upper().startswith('SELECT'):
            return result.fetchall()
        else:
            conn.commit()
            return result.rowcount

def execute_fetchone(sql, params=None):
    """Executa query e retorna um registro"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.fetchone()

def execute_fetchall(sql, params=None):
    """Executa query e retorna todos os registros"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.fetchall()

def execute_insert(sql, params=None):
    """Executa INSERT e retorna o ID inserido"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        conn.commit()
        
        # Tentar pegar o ID inserido
        if hasattr(result, 'inserted_primary_key'):
            return result.inserted_primary_key[0]
        
        # Se não conseguir, tentar lastval()
        try:
            result = conn.execute(text("SELECT lastval()"))
            return result.fetchone()[0]
        except:
            return None

def execute_update(sql, params=None):
    """Executa UPDATE e retorna número de linhas afetadas"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        conn.commit()
        return result.rowcount

def execute_delete(sql, params=None):
    """Executa DELETE e retorna número de linhas afetadas"""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        conn.commit()
        return result.rowcount

class PostgresConnection:
    """Classe que emula sqlite3.Connection"""
    
    def __init__(self):
        self.engine = get_engine()
        self._conn = self.engine.connect()  # Inicializar conexão imediatamente
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._conn.close()
    
    def cursor(self):
        """Retorna um cursor PostgreSQL"""
        if not self._conn:
            self._conn = self.engine.connect()
        return PostgresCursor(self._conn)
    
    def commit(self):
        """Commit da transação"""
        if self._conn:
            self._conn.commit()
        else:
            print("WARNING: Tentando commit sem conexão ativa")
    
    def rollback(self):
        """Rollback da transação"""
        if self._conn:
            self._conn.rollback()
    
    def close(self):
        """Fecha a conexão"""
        if self._conn:
            self._conn.close()
            self._conn = None

class RowProxy:
    """Classe que emula sqlite3.Row - compatível com dict()"""
    
    def __init__(self, keys, values):
        self._keys = keys
        self._values = values
        self._dict = dict(zip(keys, values))
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._dict[key]
    
    def __iter__(self):
        return iter(self._dict.items())
    
    def keys(self):
        return self._dict.keys()
    
    def values(self):
        return self._dict.values()
    
    def items(self):
        return self._dict.items()
    
    def get(self, key, default=None):
        return self._dict.get(key, default)

class PostgresCursor:
    """Classe que emula sqlite3.Cursor"""
    
    def __init__(self, conn):
        self.conn = conn
        self._result = None
        self._description = None
    
    def execute(self, sql, params=None):
        """Executa SQL - suporta placeholders ?, %s e :param"""
        import re
        
        if params is None:
            params = {}
        elif isinstance(params, (list, tuple)):
            # Converter lista/tupla para dict com placeholders posicionais
            param_dict = {}
            
            # Verificar qual tipo de placeholder está sendo usado
            if '%s' in sql:
                # Placeholders estilo psycopg2 (%s)
                count = 0
                def replace_percent_s(match):
                    nonlocal count
                    param_name = f'p{count}'
                    count += 1
                    return f':{param_name}'
                
                sql = re.sub(r'%s', replace_percent_s, sql)
                param_dict = {f'p{i}': val for i, val in enumerate(params)}
            
            elif '?' in sql:
                # Placeholders estilo SQLite (?)
                sql = re.sub(r'\?', lambda m, c=iter(range(len(params))): f':p{next(c)}', sql)
                param_dict = {f'p{i}': val for i, val in enumerate(params)}
            
            else:
                # Já deve ter placeholders nomeados
                param_dict = params if isinstance(params, dict) else {}
            
            params = param_dict
        
        self._result = self.conn.execute(text(sql), params)
        
        # Tentar pegar description (pode falhar em DELETE/UPDATE sem RETURNING)
        try:
            if hasattr(self._result, 'cursor') and self._result.cursor:
                self._description = self._result.cursor.description
            else:
                self._description = None
        except:
            self._description = None
        
        return self
    
    @property
    def description(self):
        """Retorna descrição das colunas"""
        return self._description
    
    def fetchone(self):
        """Retorna um registro como RowProxy"""
        if self._result:
            try:
                row = self._result.fetchone()
                if row:
                    # SQLAlchemy Result: usar keys() do próprio row
                    keys = list(row._mapping.keys()) if hasattr(row, '_mapping') else list(row.keys())
                    return RowProxy(keys, tuple(row))
                return None
            except:
                # Para operações sem resultado (INSERT/UPDATE/DELETE sem RETURNING)
                return None
        return None
    
    def fetchall(self):
        """Retorna todos os registros como RowProxy"""
        if self._result:
            try:
                rows = self._result.fetchall()
                if rows:
                    # SQLAlchemy Result: usar keys() do primeiro row
                    keys = list(rows[0]._mapping.keys()) if hasattr(rows[0], '_mapping') else list(rows[0].keys())
                    return [RowProxy(keys, tuple(row)) for row in rows]
                return []
            except:
                # Para operações sem resultado
                return []
        return []
    
    def fetchmany(self, size=None):
        """Retorna vários registros"""
        if self._result:
            if size:
                return self._result.fetchmany(size)
            return self._result.fetchall()
        return []
    
    @property
    def lastrowid(self):
        """Retorna ID do último registro inserido"""
        try:
            result = self.conn.execute(text("SELECT lastval()"))
            return result.fetchone()[0]
        except:
            return None
    
    @property
    def rowcount(self):
        """Retorna número de linhas afetadas"""
        if self._result:
            return self._result.rowcount
        return -1
    
    def close(self):
        """Fecha o cursor"""
        self._result = None

def connect():
    """Função compatível com sqlite3.connect()"""
    return PostgresConnection()

