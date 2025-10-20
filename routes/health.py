#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Endpoint
Endpoint para verificar saúde da aplicação
"""

from flask import Blueprint, jsonify
from datetime import datetime
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint para Docker, Kubernetes, Load Balancers, etc.
    
    Retorna:
        - 200 OK se aplicação está saudável
        - 503 Service Unavailable se há problemas
    """
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'GestaoVersus',
        'version': '1.0',
    }
    
    checks = {}
    
    # Check 1: Database
    try:
        from models import db
        # Simple query to test connection
        db.session.execute('SELECT 1')
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check 2: Redis (opcional)
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        try:
            import redis
            import re
            
            # Parse Redis URL
            match = re.match(r'redis://(?::(.+)@)?([^:]+):(\d+)/(\d+)', redis_url)
            if match:
                password = match.group(1)
                host = match.group(2)
                port = int(match.group(3))
                db_num = int(match.group(4))
                
                r = redis.Redis(host=host, port=port, db=db_num, password=password, socket_timeout=2)
                r.ping()
                checks['redis'] = 'ok'
            else:
                checks['redis'] = 'skipped'
        except Exception as e:
            checks['redis'] = f'error: {str(e)}'
            # Redis é opcional, não marca como unhealthy
    else:
        checks['redis'] = 'not_configured'
    
    # Check 3: Disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        
        if free_percent < 10:
            checks['disk_space'] = f'warning: only {free_percent:.1f}% free'
            health_status['status'] = 'degraded'
        else:
            checks['disk_space'] = f'ok: {free_percent:.1f}% free'
    except Exception as e:
        checks['disk_space'] = f'error: {str(e)}'
    
    health_status['checks'] = checks
    
    # Return appropriate status code
    if health_status['status'] == 'healthy':
        return jsonify(health_status), 200
    elif health_status['status'] == 'degraded':
        return jsonify(health_status), 200
    else:
        return jsonify(health_status), 503


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Readiness check - Aplicação está pronta para receber tráfego?
    """
    try:
        from models import db
        db.session.execute('SELECT 1')
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Liveness check - Aplicação está viva?
    """
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.utcnow().isoformat()
    }), 200

