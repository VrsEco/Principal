#!/usr/bin/env python
"""
Script para executar todos os testes pytest corretamente
"""
import subprocess
import sys
import glob
from pathlib import Path

# Obter diretório raiz do projeto
root_dir = Path(__file__).parent.parent
test_dir = Path(__file__).parent

print("=" * 80)
print("EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS")
print("=" * 80)
print(f"Diretório raiz: {root_dir}")
print(f"Diretório de testes: {test_dir}")
print()

# Encontrar todos os arquivos de teste
test_files = list(test_dir.glob("test_*.py"))
print(f"Arquivos de teste encontrados: {len(test_files)}")
for tf in test_files:
    print(f"  - {tf.name}")

if not test_files:
    print("\nERRO: Nenhum arquivo de teste encontrado!")
    sys.exit(1)

print("\n" + "=" * 80)
print("INICIANDO EXECUÇÃO DOS TESTES")
print("=" * 80)
print()

# Construir lista de arquivos para o pytest
test_paths = [str(tf.relative_to(root_dir)) for tf in test_files]

# Executar pytest
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        *test_paths,
        "-v",
        "--tb=short",
        "--maxfail=1000"
    ],
    cwd=root_dir
)

print("\n" + "=" * 80)
print(f"TESTES CONCLUÍDOS - Código de saída: {result.returncode}")
print("=" * 80)

sys.exit(result.returncode)

