#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para o novo formato de relatório de processo
"""

import sys
import os
import webbrowser

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

from relatorios.generators.process_pop import generate_process_pop_report

def test_new_report():
    """Testa o novo formato de relatório"""
    
    print("=" * 60)
    print("🧪 TESTE DO NOVO FORMATO DE RELATÓRIO DE PROCESSO")
    print("=" * 60)
    
    # Parâmetros do teste
    company_id = 5
    process_id = 17
    output_path = r"C:\GestaoVersus\teste_relatorio_novo.html"
    
    print(f"\n📊 Gerando relatório:")
    print(f"   - Empresa ID: {company_id}")
    print(f"   - Processo ID: {process_id}")
    print(f"   - Arquivo: {output_path}")
    
    try:
        # Gerar relatório
        html = generate_process_pop_report(
            company_id=company_id,
            process_id=process_id,
            save_path=output_path,
            model_id=7,  # Modelo com margens menores
            flow=True,
            activities=True,
            routines=True,
            indicators=True  # ✅ Ativado para exibir indicadores
        )
        
        print(f"\n✅ Relatório gerado com sucesso!")
        print(f"   - Tamanho: {len(html)} caracteres")
        print(f"   - Arquivo salvo em: {output_path}")
        
        # Verificar alterações
        print(f"\n🔍 Verificando alterações:")
        
        alteracoes = {
            "Sem cabeçalho fixo": "custom-report-header" not in html,
            "Título 'BOOK DO PROCESSO'": "BOOK DO PROCESSO:" in html,
            "Formato com hífen (-)": " - " in html,
            "Seção de informações": "process-info-section" in html,
            "Campo 'Empresa'": "Empresa:" in html,
            "Campo 'Processo | Responsável'": "Processo:" in html and "Responsável:" in html,
            "Campo 'Macroprocesso | Dono'": "Macroprocesso:" in html and "Dono:" in html,
            "Campo 'Nº de Páginas'": "Nº de Páginas:" in html or "páginas" in html.lower(),
        }
        
        for descricao, presente in alteracoes.items():
            simbolo = "✅" if presente else "❌"
            print(f"   {simbolo} {descricao}")
        
        # Abrir no navegador
        print(f"\n🌐 Abrindo relatório no navegador...")
        webbrowser.open(f"file:///{output_path}")
        
        print(f"\n{'=' * 60}")
        print(f"✨ TESTE CONCLUÍDO!")
        print(f"{'=' * 60}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO ao gerar relatório:")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_new_report()

