#!/usr/bin/env python
"""
Script para executar todos os testes e gerar relatório completo
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def run_tests():
    """Executa todos os testes e retorna resultados"""
    print("=" * 80)
    print("EXECUTANDO TODOS OS TESTES DO GESTAOVERSUS")
    print("=" * 80)
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Executar pytest
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "test_*.py",
            "-v",
            "--tb=short",
            "--maxfail=100",  # Continuar mesmo com falhas
            "-x",  # Parar no primeiro erro (remover se quiser continuar)
        ],
        cwd="testsprite_tests",
        capture_output=True,
        text=True
    )
    
    # Mostrar saída
    print(result.stdout)
    if result.stderr:
        print("\n" + "=" * 80)
        print("ERROS:")
        print("=" * 80)
        print(result.stderr)
    
    print("\n" + "=" * 80)
    print("RESUMO DA EXECUÇÃO")
    print("=" * 80)
    print(f"Fim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Código de saída: {result.returncode}")
    
    # Contar testes
    lines = result.stdout.split('\n')
    passed = sum(1 for line in lines if 'PASSED' in line)
    failed = sum(1 for line in lines if 'FAILED' in line)
    error = sum(1 for line in lines if 'ERROR' in line)
    
    print(f"\nTestes PASSED: {passed}")
    print(f"Testes FAILED: {failed}")
    print(f"Testes ERROR: {error}")
    print(f"Total: {passed + failed + error}")
    
    return {
        "exitcode": result.returncode,
        "passed": passed,
        "failed": failed,
        "error": error,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

if __name__ == "__main__":
    report = run_tests()
    sys.exit(report.get("exitcode", 0))

