#!/usr/bin/env python
"""Executa todos os testes e salva resultado"""
import subprocess
import sys
from pathlib import Path

test_dir = Path(__file__).parent
output_file = test_dir / "test_execution_results.txt"

print("Executando testes...")
print(f"Resultados serão salvos em: {output_file}\n")

# Mudar para o diretório pai para executar pytest corretamente
import os

parent_dir = test_dir.parent
os.chdir(parent_dir)

with open(output_file, "w", encoding="utf-8") as f:
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
        stdout=f,
        stderr=subprocess.STDOUT,
        text=True,
    )

print(f"Testes concluídos! Código de saída: {result.returncode}")
print(f"Ver resultados em: {output_file}")
