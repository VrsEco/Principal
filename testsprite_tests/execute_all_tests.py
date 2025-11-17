#!/usr/bin/env python
"""
Executa todos os testes e gera relatório
"""
import subprocess
import sys
from datetime import datetime

print("=" * 80)
print("EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS")
print("=" * 80)
print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Executar pytest com relatório detalhado
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        "testsprite_tests/test_*.py",
        "-v",
        "--tb=short",
        "--maxfail=1000",  # Continuar mesmo com muitas falhas
        f"--junitxml=testsprite_tests/test_report.xml",
        f"--html=testsprite_tests/test_report.html",
        "--self-contained-html"
    ],
    capture_output=False,  # Mostrar saída em tempo real
    text=True
)

print("\n" + "=" * 80)
print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Código de saída: {result.returncode}")
print("=" * 80)

sys.exit(result.returncode)

