#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Configuração do Sistema de Relatórios
Cria configurações de página e templates específicos
"""

from modules.report_models import ReportModelsManager
from modules.report_templates import ReportTemplatesManager
from config_database import get_db


def create_page_configurations():
    """
    Cria configurações de página padrão
    """
    print("🔄 Criando configurações de página...")

    manager = ReportModelsManager()

    # Configuração Model 7 - Relatórios Executivos
    model_7_data = {
        "name": "Model 7 - Relatórios Executivos",
        "description": "Configuração padrão para relatórios executivos com cabeçalho e rodapé corporativos",
        "paper_size": "A4",
        "orientation": "Retrato",
        "margin_top": 25,
        "margin_right": 20,
        "margin_bottom": 20,
        "margin_left": 25,
        "header_height": 30,
        "header_rows": 2,
        "header_columns": 3,
        "header_content": """## {{ company.name }}
**{{ report.title }}**
Data: {{ date }} | Sistema PEVAPP22""",
        "footer_height": 15,
        "footer_rows": 1,
        "footer_columns": 2,
        "footer_content": "© {{ year }} {{ company.name }} | Página {{ page }} de {{ pages }} | Sistema PEVAPP22",
    }

    model_7_id = manager.save_model(model_7_data)
    print(f"✅ Model 7 criado com ID: {model_7_id}")

    # Configuração Model 8 - Relatórios Técnicos
    model_8_data = {
        "name": "Model 8 - Relatórios Técnicos",
        "description": "Configuração para relatórios técnicos com layout mais compacto",
        "paper_size": "A4",
        "orientation": "Retrato",
        "margin_top": 20,
        "margin_right": 15,
        "margin_bottom": 15,
        "margin_left": 20,
        "header_height": 25,
        "header_rows": 1,
        "header_columns": 2,
        "header_content": "**{{ report.title }}** | {{ date }}",
        "footer_height": 12,
        "footer_rows": 1,
        "footer_columns": 1,
        "footer_content": "Página {{ page }} | {{ year }}",
    }

    model_8_id = manager.save_model(model_8_data)
    print(f"✅ Model 8 criado com ID: {model_8_id}")

    return {"model_7_id": model_7_id, "model_8_id": model_8_id}


def create_report_templates(page_config_ids):
    """
    Cria templates específicos de relatórios
    """
    print("🔄 Criando templates de relatórios...")

    manager = ReportTemplatesManager()

    # Template para Relatório de Reuniões
    meetings_template = {
        "name": "Relatório de Reuniões - Padrão",
        "description": "Template completo para relatórios de reuniões com todas as seções",
        "page_config_id": page_config_ids["model_7_id"],
        "report_type": "meetings",
        "sections_config": {
            "summary": {
                "enabled": True,
                "title": "Resumo Executivo",
                "description": "Visão geral das reuniões do período",
            },
            "meetings_list": {
                "enabled": True,
                "title": "Lista de Reuniões",
                "description": "Detalhes de todas as reuniões realizadas",
            },
            "participants_analysis": {
                "enabled": True,
                "title": "Análise de Participantes",
                "description": "Estatísticas de participação",
            },
            "conclusions": {
                "enabled": True,
                "title": "Conclusões e Recomendações",
                "description": "Análise final e próximos passos",
            },
        },
    }

    meetings_template_id = manager.save_template(meetings_template)
    print(f"✅ Template de Reuniões criado com ID: {meetings_template_id}")

    # Template para Relatório de Reuniões - Resumido
    meetings_summary_template = {
        "name": "Relatório de Reuniões - Resumido",
        "description": "Template resumido para relatórios de reuniões",
        "page_config_id": page_config_ids["model_8_id"],
        "report_type": "meetings",
        "sections_config": {
            "summary": {
                "enabled": True,
                "title": "Resumo Executivo",
                "description": "Visão geral das reuniões do período",
            },
            "meetings_list": {
                "enabled": True,
                "title": "Lista de Reuniões",
                "description": "Detalhes das reuniões principais",
            },
            "participants_analysis": {
                "enabled": False,
                "title": "Análise de Participantes",
                "description": "Estatísticas de participação",
            },
            "conclusions": {
                "enabled": True,
                "title": "Conclusões",
                "description": "Principais conclusões",
            },
        },
    }

    meetings_summary_template_id = manager.save_template(meetings_summary_template)
    print(
        f"✅ Template de Reuniões Resumido criado com ID: {meetings_summary_template_id}"
    )

    return {
        "meetings_template_id": meetings_template_id,
        "meetings_summary_template_id": meetings_summary_template_id,
    }


def test_report_generation(template_ids):
    """
    Testa a geração de relatórios
    """
    print("🔄 Testando geração de relatórios...")

    from modules.report_templates import ReportTemplateGenerator

    generator = ReportTemplateGenerator()

    # Dados de teste para reuniões
    test_data = {
        "company_name": "TechnoSolutions Ltda",
        "report_title": "Relatório de Reuniões - Janeiro 2024",
        "period_start": "01/01/2024",
        "period_end": "31/01/2024",
        "total_meetings": 15,
        "unique_participants": 25,
        "participation_rate": 85,
        "avg_participation": 8.5,
        "max_participation": 12,
        "min_participation": 5,
        "conclusions": "As reuniões foram produtivas com alta participação. Recomenda-se manter a frequência atual e implementar follow-ups mais estruturados.",
        "meetings": [
            {
                "title": "Reunião de Planejamento Semanal",
                "date": "05/01/2024",
                "time": "09:00 - 10:30",
                "location": "Sala de Reuniões A",
                "organizer": "João Silva",
                "description": "Planejamento das atividades da semana",
                "participants": [
                    "João Silva",
                    "Maria Santos",
                    "Pedro Costa",
                    "Ana Lima",
                ],
            },
            {
                "title": "Review de Projetos",
                "date": "12/01/2024",
                "time": "14:00 - 16:00",
                "location": "Sala de Reuniões B",
                "organizer": "Maria Santos",
                "description": "Revisão do progresso dos projetos em andamento",
                "participants": [
                    "Maria Santos",
                    "Pedro Costa",
                    "Ana Lima",
                    "Carlos Oliveira",
                    "Lucia Ferreira",
                ],
            },
            {
                "title": "Reunião de Alinhamento",
                "date": "19/01/2024",
                "time": "10:00 - 11:00",
                "location": "Sala de Reuniões A",
                "organizer": "Pedro Costa",
                "description": "Alinhamento de objetivos e metas",
                "participants": ["Pedro Costa", "Ana Lima", "Carlos Oliveira"],
            },
        ],
    }

    # Testa geração do template completo
    result = generator.generate_report_from_template(
        template_ids["meetings_template_id"], test_data
    )

    if "error" not in result:
        print(f"✅ Relatório completo gerado com sucesso!")
        print(f"   - Template: {result['template_name']}")
        print(f"   - Configuração: {result['page_config_name']}")
        print(f"   - Tipo: {result['report_type']}")

        # Salva o HTML gerado
        with open("relatorio_reunioes_teste.html", "w", encoding="utf-8") as f:
            f.write(result["html"])
        print(f"   - Arquivo salvo: relatorio_reunioes_teste.html")
    else:
        print(f"❌ Erro na geração: {result['error']}")

    # Testa geração do template resumido
    result_summary = generator.generate_report_from_template(
        template_ids["meetings_summary_template_id"], test_data
    )

    if "error" not in result_summary:
        print(f"✅ Relatório resumido gerado com sucesso!")

        # Salva o HTML gerado
        with open("relatorio_reunioes_resumido.html", "w", encoding="utf-8") as f:
            f.write(result_summary["html"])
        print(f"   - Arquivo salvo: relatorio_reunioes_resumido.html")
    else:
        print(f"❌ Erro na geração resumida: {result_summary['error']}")


def main():
    """
    Função principal de configuração
    """
    print("🚀 Configurando Sistema de Relatórios Estruturado")
    print("=" * 50)

    try:
        # 1. Cria configurações de página
        page_config_ids = create_page_configurations()

        # 2. Cria templates de relatórios
        template_ids = create_report_templates(page_config_ids)

        # 3. Testa geração de relatórios
        test_report_generation(template_ids)

        print("\n" + "=" * 50)
        print("✅ Sistema configurado com sucesso!")
        print("\n📋 Resumo da configuração:")
        print(f"   - Model 7 (Executivo): ID {page_config_ids['model_7_id']}")
        print(f"   - Model 8 (Técnico): ID {page_config_ids['model_8_id']}")
        print(
            f"   - Template Reuniões Completo: ID {template_ids['meetings_template_id']}"
        )
        print(
            f"   - Template Reuniões Resumido: ID {template_ids['meetings_summary_template_id']}"
        )

        print("\n🎯 Como usar:")
        print("   1. Acesse: http://127.0.0.1:5002/settings/reports")
        print("   2. Configure uma nova página ou use as existentes")
        print("   3. Crie um template específico para seu relatório")
        print("   4. Use: Pegue a página X e o modelo do relatório Y")

    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
