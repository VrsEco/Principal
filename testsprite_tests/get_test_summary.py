#!/usr/bin/env python
"""
Script para executar testes e gerar resumo
"""
import subprocess
import sys
import re
from pathlib import Path

root_dir = Path(__file__).parent.parent
test_dir = Path(__file__).parent

# Encontrar todos os arquivos de teste
test_files = list(test_dir.glob("test_*.py"))
test_paths = [str(tf.relative_to(root_dir)) for tf in test_files]

print("Executando testes e gerando resumo...")
print("=" * 80)

# Executar pytest com saída capturada
result = subprocess.run(
    [
        sys.executable, "-m", "pytest",
        *test_paths,
        "-v",
        "--tb=no",
        "--maxfail=1000"
    ],
    cwd=root_dir,
    capture_output=True,
    text=True
)

# Analisar resultados
output = result.stdout + result.stderr

# Extrair estatísticas
collected_match = re.search(r'collected (\d+)', output)
passed_matches = re.findall(r'PASSED', output)
failed_matches = re.findall(r'FAILED', output)
error_matches = re.findall(r'ERROR', output)

collected = int(collected_match.group(1)) if collected_match else 0
passed = len(passed_matches)
failed = len(failed_matches)
error = len(error_matches)

# Extrair resumo final
summary_match = re.search(r'(\d+) passed.*?(\d+) failed', output)
if summary_match:
    passed = int(summary_match.group(1))
    failed = int(summary_match.group(2))

print("\n" + "=" * 80)
print("RESUMO DOS TESTES")
print("=" * 80)
print(f"Total de testes coletados: {collected}")
print(f"Testes PASSED: {passed}")
print(f"Testes FAILED: {failed}")
print(f"Testes ERROR: {error}")
print(f"Taxa de sucesso: {(passed/collected*100) if collected > 0 else 0:.1f}%")
print("=" * 80)

# Mostrar algumas linhas de saída
lines = output.split('\n')
print("\nÚltimas linhas da execução:")
print("-" * 80)
for line in lines[-20:]:
    if line.strip():
        print(line)

sys.exit(result.returncode)

