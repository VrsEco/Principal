#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste - Gerador de Relatórios
Testa a geração de um relatório de exemplo
"""

import os
from relatorios.generators import generate_process_pop_report

print("=" * 60)
print("🔄 TESTANDO GERADOR DE RELATÓRIOS")
print("=" * 60)

# Configurações
company_id = 6
process_id = 1  # Vamos tentar com ID 1 primeiro
model_id = 8  # Modelo "Relatório POP Padrão" - LIMPO (sem cabeçalho/rodapé no modelo)

# Caminho correto para Windows (usando barras duplas ou r"")
save_path = r"C:\GestaoVersus\teste_relatorio.html"
# Alternativa: save_path = "C:\\GestaoVersus\\teste_relatorio.html"
# Alternativa: save_path = "C:/GestaoVersus/teste_relatorio.html"

print(f"\n📋 Configurações:")
print(f"   Company ID: {company_id}")
print(f"   Process ID: {process_id}")
print(f"   Model ID: {model_id or 'Padrão'}")
print(f"   Save Path: {save_path}")

print(f"\n🔍 Verificando se o diretório existe...")
dir_path = os.path.dirname(save_path)
if os.path.exists(dir_path):
    print(f"   ✅ Diretório existe: {dir_path}")
else:
    print(f"   ❌ Diretório NÃO existe: {dir_path}")
    print(f"   🔧 Criando diretório...")
    os.makedirs(dir_path, exist_ok=True)
    print(f"   ✅ Diretório criado!")

print(f"\n🚀 Gerando relatório...")

try:
    html = generate_process_pop_report(
        company_id=company_id,
        process_id=process_id,
        model_id=model_id,
        save_path=save_path,
    )

    print(f"\n✅ SUCESSO!")
    print(f"   📄 Relatório gerado com sucesso!")
    print(f"   📁 Localização: {save_path}")

    # Verificar se o arquivo foi criado
    if os.path.exists(save_path):
        file_size = os.path.getsize(save_path)
        print(f"   📊 Tamanho do arquivo: {file_size:,} bytes")
        print(f"\n💡 Para abrir:")
        print(f"   1. Navegador: abra o arquivo {save_path}")
        print(f"   2. Ou digite no terminal: start {save_path}")
    else:
        print(f"   ⚠️ ATENÇÃO: O arquivo não foi encontrado após a geração!")

except Exception as e:
    print(f"\n❌ ERRO ao gerar relatório:")
    print(f"   {type(e).__name__}: {str(e)}")
    print(f"\n📋 Detalhes do erro:")
    import traceback

    traceback.print_exc()

    print(f"\n💡 Possíveis soluções:")
    print(f"   1. Verifique se o processo ID={process_id} existe")
    print(f"   2. Verifique se a empresa ID={company_id} existe")
    print(f"   3. Tente com outros IDs")

print("\n" + "=" * 60)
print("FIM DO TESTE")
print("=" * 60)
