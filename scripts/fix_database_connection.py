#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para diagnosticar e corrigir problemas de conexão com PostgreSQL.

Este script verifica:
1. Se a aplicação está rodando dentro ou fora do Docker
2. Se host.docker.internal pode ser resolvido
3. Sugere a configuração correta para o .env
"""

import os
import socket
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.env_helpers import running_inside_docker, _can_resolve_host


def check_docker_environment():
    """Verifica se está rodando dentro do Docker."""
    is_docker = running_inside_docker()
    print(f"🔍 Ambiente Docker: {'✅ SIM (dentro do container)' if is_docker else '❌ NÃO (fora do container)'}")
    return is_docker


def check_host_resolution():
    """Verifica se host.docker.internal pode ser resolvido."""
    host = "host.docker.internal"
    can_resolve = _can_resolve_host(host)
    
    if can_resolve:
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ '{host}' pode ser resolvido → {ip}")
        except Exception as e:
            print(f"⚠️  '{host}' pode ser resolvido mas houve erro: {e}")
    else:
        print(f"❌ '{host}' NÃO pode ser resolvido")
    
    return can_resolve


def check_localhost():
    """Verifica se localhost pode ser resolvido."""
    try:
        ip = socket.gethostbyname("localhost")
        print(f"✅ 'localhost' pode ser resolvido → {ip}")
        return True
    except Exception as e:
        print(f"❌ 'localhost' NÃO pode ser resolvido: {e}")
        return False


def check_postgres_connection(host, port=5432):
    """Tenta conectar ao PostgreSQL."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ PostgreSQL acessível em {host}:{port}")
            return True
        else:
            print(f"❌ PostgreSQL NÃO acessível em {host}:{port}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar conexão com {host}:{port}: {e}")
        return False


def get_env_file_path():
    """Retorna o caminho do arquivo .env."""
    root = Path(__file__).parent.parent
    return root / ".env"


def read_env_file():
    """Lê o arquivo .env e retorna um dict."""
    env_path = get_env_file_path()
    if not env_path.exists():
        return {}
    
    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    
    return env_vars


def suggest_configuration():
    """Sugere a configuração correta baseada no ambiente."""
    print("\n" + "=" * 60)
    print("📋 DIAGNÓSTICO E RECOMENDAÇÕES")
    print("=" * 60)
    
    is_docker = check_docker_environment()
    can_resolve_host = check_host_resolution()
    can_resolve_localhost = check_localhost()
    
    print("\n" + "-" * 60)
    print("🔌 TESTE DE CONECTIVIDADE")
    print("-" * 60)
    
    # Testar localhost
    localhost_ok = check_postgres_connection("localhost", 5432)
    
    # Testar host.docker.internal se aplicável
    if is_docker:
        host_docker_ok = check_postgres_connection("host.docker.internal", 5432)
    else:
        host_docker_ok = False
    
    print("\n" + "-" * 60)
    print("💡 RECOMENDAÇÕES")
    print("-" * 60)
    
    # Ler configuração atual
    env_vars = read_env_file()
    current_host = env_vars.get("POSTGRES_HOST", "não definido")
    
    print(f"\n📝 Configuração atual no .env:")
    print(f"   POSTGRES_HOST={current_host}")
    
    recommended_host = None
    
    if is_docker:
        # Dentro do Docker
        if host_docker_ok:
            recommended_host = "host.docker.internal"
            print(f"\n✅ RECOMENDAÇÃO: Usar 'host.docker.internal'")
            print(f"   (Container → Host: use host.docker.internal)")
        elif localhost_ok:
            recommended_host = "localhost"
            print(f"\n⚠️  RECOMENDAÇÃO: Usar 'localhost'")
            print(f"   (host.docker.internal não respondeu, mas localhost respondeu)")
            print(f"   Isso geralmente significa que o PostgreSQL está no mesmo container")
        else:
            recommended_host = "host.docker.internal"
            print(f"\n❌ PROBLEMA: Nenhuma conexão funcionou!")
            print(f"   Verifique se o PostgreSQL está rodando e acessível")
    else:
        # Fora do Docker: manter host.docker.internal e usar fallback automático
        recommended_host = None  # Normalmente não precisamos alterar o .env
        if current_host == "host.docker.internal":
            print(f"\n✅ Fora do Docker: mantenha 'host.docker.internal'")
            print(f"   O helper normalize_docker_host converte para 'localhost' automaticamente")
            print(f"   Ajuste PEV_FALLBACK_DB_HOST se precisar usar outro host local")
        else:
            print(f"\n⚠️ Ambiente fora do Docker detectado.")
            print(f"   Recomenda-se definir POSTGRES_HOST=host.docker.internal no .env")
            print(f"   Assim o mesmo arquivo serve para rodar dentro e fora do Docker.")
            recommended_host = "host.docker.internal"
    
    if recommended_host and current_host != recommended_host:
        print(f"\n🔧 AÇÃO NECESSÁRIA:")
        print(f"   Atualize o arquivo .env:")
        print(f"   POSTGRES_HOST={recommended_host}")
        
        # Perguntar se quer atualizar automaticamente
        if "--auto-fix" in sys.argv:
            update_env_file(recommended_host)
        else:
            print(f"\n💡 Dica: Execute com --auto-fix para atualizar automaticamente:")
            print(f"   python scripts/fix_database_connection.py --auto-fix")
    
    return recommended_host


def update_env_file(new_host):
    """Atualiza o arquivo .env com o host recomendado."""
    env_path = get_env_file_path()
    
    if not env_path.exists():
        print(f"❌ Arquivo .env não encontrado em {env_path}")
        return False
    
    # Ler linhas
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # Atualizar POSTGRES_HOST
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("POSTGRES_HOST="):
            new_lines.append(f"POSTGRES_HOST={new_host}\n")
            updated = True
        elif "DATABASE_URL" in line and "host.docker.internal" in line:
            # Atualizar também DATABASE_URL se contiver host.docker.internal
            new_line = line.replace("host.docker.internal", new_host)
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)
    
    if updated:
        # Fazer backup
        backup_path = env_path.with_suffix(".env.backup")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"✅ Backup criado: {backup_path}")
        
        # Escrever novo arquivo
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        print(f"✅ Arquivo .env atualizado!")
        print(f"   POSTGRES_HOST={new_host}")
        return True
    else:
        print(f"⚠️  POSTGRES_HOST não encontrado no .env")
        return False


def main():
    """Função principal."""
    print("=" * 60)
    print("🔧 DIAGNÓSTICO DE CONEXÃO POSTGRESQL")
    print("=" * 60)
    print()
    
    suggest_configuration()
    
    print("\n" + "=" * 60)
    print("✅ Diagnóstico concluído!")
    print("=" * 60)


if __name__ == "__main__":
    main()

