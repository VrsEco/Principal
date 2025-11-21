#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check da Aplicação
Verifica se todos os serviços estão funcionando
"""

import os
import sys
import requests
from datetime import datetime


def check_flask_app():
    """Verifica se aplicação Flask está respondendo"""
    print("🌐 Verificando aplicação Flask...")

    url = os.getenv("HEALTH_CHECK_URL", "http://localhost:5002/health")

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            print(f"✅ Flask App OK - Status: {response.status_code}")
            return True
        else:
            print(f"❌ Flask App com problema - Status: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Flask App não está respondendo")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar Flask: {e}")
        return False


def check_database():
    """Verifica conexão com banco de dados"""
    print("\n💾 Verificando banco de dados...")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return False

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url, echo=False)

        with engine.connect() as connection:
            # Executar query simples
            result = connection.execute(text("SELECT 1"))
            result.fetchone()

            print("✅ Banco de dados OK")
            return True

    except Exception as e:
        print(f"❌ Erro no banco de dados: {e}")
        return False


def check_redis():
    """Verifica conexão com Redis"""
    print("\n⚡ Verificando Redis...")

    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        print("⚠️ REDIS_URL não configurada (opcional)")
        return True

    try:
        import redis
        import re

        match = re.match(r"redis://(?::(.+)@)?([^:]+):(\d+)/(\d+)", redis_url)

        if match:
            password = match.group(1)
            host = match.group(2)
            port = int(match.group(3))
            db = int(match.group(4))

            r = redis.Redis(
                host=host, port=port, db=db, password=password, socket_timeout=5
            )

            # Ping Redis
            if r.ping():
                print("✅ Redis OK")
                return True
            else:
                print("❌ Redis não respondeu ao ping")
                return False
        else:
            print("⚠️ REDIS_URL inválida")
            return True

    except Exception as e:
        print(f"⚠️ Erro no Redis: {e}")
        return True


def check_disk_space():
    """Verifica espaço em disco"""
    print("\n💽 Verificando espaço em disco...")

    try:
        import shutil

        total, used, free = shutil.disk_usage("/")

        # Converter para GB
        total_gb = total // (2**30)
        used_gb = used // (2**30)
        free_gb = free // (2**30)

        # Percentual usado
        percent_used = (used / total) * 100

        print(f"Total: {total_gb} GB")
        print(f"Usado: {used_gb} GB ({percent_used:.1f}%)")
        print(f"Livre: {free_gb} GB")

        # Alerta se menos de 10% livre
        if free_gb < (total_gb * 0.1):
            print("⚠️ ATENÇÃO: Pouco espaço em disco!")
            return False

        print("✅ Espaço em disco OK")
        return True

    except Exception as e:
        print(f"⚠️ Erro ao verificar disco: {e}")
        return True


def check_ssl_certificate():
    """Verifica validade do certificado SSL"""
    print("\n🔒 Verificando certificado SSL...")

    domain = os.getenv("DOMAIN_NAME", "your-domain.com")

    try:
        import ssl
        import socket
        from datetime import datetime, timedelta

        context = ssl.create_default_context()

        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

                # Data de expiração
                not_after = cert["notAfter"]
                expire_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")

                days_remaining = (expire_date - datetime.now()).days

                print(f"Válido até: {expire_date.strftime('%Y-%m-%d')}")
                print(f"Dias restantes: {days_remaining}")

                if days_remaining < 7:
                    print("⚠️ ATENÇÃO: Certificado expira em menos de 7 dias!")
                    return False
                elif days_remaining < 30:
                    print("⚠️ Certificado expira em menos de 30 dias")

                print("✅ Certificado SSL OK")
                return True

    except Exception as e:
        print(f"⚠️ Não foi possível verificar SSL: {e}")
        return True  # Não é crítico para dev


def main():
    """Função principal"""
    print("=" * 60)
    print("🏥 GestaoVersus - Health Check")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    checks = {
        "Flask App": check_flask_app(),
        "Database": check_database(),
        "Redis": check_redis(),
        "Disk Space": check_disk_space(),
        "SSL Certificate": check_ssl_certificate(),
    }

    print("\n" + "=" * 60)
    print("📊 Resumo do Health Check")
    print("=" * 60)

    all_passed = all(checks.values())

    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")

    print("=" * 60)

    if all_passed:
        print("✅ Todos os serviços estão funcionando!")
        sys.exit(0)
    else:
        print("⚠️ Alguns serviços precisam de atenção")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Health check cancelado")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        sys.exit(1)
