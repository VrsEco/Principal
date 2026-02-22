#!/usr/bin/env python
"""
Script final para executar todos os testes pytest
"""
import subprocess
import sys
from pathlib import Path

# Garantir que estamos no diretório raiz
root_dir = Path(__file__).parent.parent
import os

os.chdir(root_dir)

print("=" * 80)
print("EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS")
print("=" * 80)
print(f"Diretório: {os.getcwd()}")
print(f"Arquivos de teste: testsprite_tests/test_*.py")
print()

# Executar pytest
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "testsprite_tests/test_*.py",
        "-v",
        "--tb=short",
        "--maxfail=1000",
    ],
    cwd=root_dir,
)

print("\n" + "=" * 80)
print(f"Testes concluídos! Código de saída: {result.returncode}")
print("=" * 80)

sys.exit(result.returncode)
