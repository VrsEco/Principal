#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Relatório - Save Water
"""

from modules.report_templates import ReportTemplateGenerator, ReportTemplatesManager


def gerar_relatorio_save_water():
    """Gera relatório específico para Save Water"""

    print("🔄 Gerando Relatório de Reuniões - Save Water")
    print("=" * 50)

    # Busca templates de reuniões
    manager = ReportTemplatesManager()
    templates = manager.get_templates_by_type("meetings")

    if not templates:
        print("❌ Nenhum template de reuniões encontrado!")
        return

    template_id = templates[0]["id"]
    print(f"📋 Usando template: {templates[0]['name']} (ID: {template_id})")

    # Dados específicos para Save Water
    dados_save_water = {
        "company_name": "Save Water Ltda",
        "report_title": "Relatório de Reuniões - Save Water",
        "period_start": "01/10/2024",
        "period_end": "17/10/2024",
        "total_meetings": 3,
        "unique_participants": 8,
        "participation_rate": 92,
        "avg_participation": 6.5,
        "max_participation": 8,
        "min_participation": 5,
        "conclusions": """As reuniões da Save Water foram altamente produtivas, com foco na sustentabilidade e eficiência hídrica. 
        A equipe demonstrou engajamento excepcional nos projetos de conservação de água. 
        Recomendamos manter a frequência atual e expandir os projetos de monitoramento.""",
        "meetings": [
            {
                "title": "Reunião de Planejamento - Projeto AquaSave",
                "date": "05/10/2024",
                "time": "09:00 - 11:00",
                "location": "Sala de Reuniões Principal",
                "organizer": "Maria Silva",
                "description": "Planejamento inicial do projeto de economia de água para clientes residenciais",
                "participants": [
                    "Maria Silva",
                    "João Santos",
                    "Ana Costa",
                    "Pedro Lima",
                    "Lucia Ferreira",
                ],
            },
            {
                "title": "Review Técnico - Sistema de Monitoramento",
                "date": "12/10/2024",
                "time": "14:00 - 16:30",
                "location": "Laboratório Técnico",
                "organizer": "João Santos",
                "description": "Revisão técnica do sistema de monitoramento de consumo em tempo real",
                "participants": [
                    "João Santos",
                    "Ana Costa",
                    "Carlos Oliveira",
                    "Roberto Mendes",
                    "Lucia Ferreira",
                    "Maria Silva",
                ],
            },
            {
                "title": "Apresentação de Resultados",
                "date": "15/10/2024",
                "time": "10:00 - 12:00",
                "location": "Auditório",
                "organizer": "Ana Costa",
                "description": "Apresentação dos resultados preliminares do projeto AquaSave",
                "participants": [
                    "Ana Costa",
                    "Maria Silva",
                    "João Santos",
                    "Pedro Lima",
                    "Carlos Oliveira",
                ],
            },
        ],
    }

    # Gera o relatório
    generator = ReportTemplateGenerator()
    result = generator.generate_report_from_template(template_id, dados_save_water)

    if "error" not in result:
        print("✅ Relatório gerado com sucesso!")

        # Salva o arquivo
        filename = "relatorio_reunioes_save_water.html"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result["html"])

        print(f"📄 Arquivo salvo: {filename}")
        print(f"🎯 Template usado: {result['template_name']}")
        print(f"📋 Configuração: {result['page_config_name']}")
        print(f"📊 Tipo: {result['report_type']}")

        print("\n" + "=" * 50)
        print("🎉 RELATÓRIO PRONTO!")
        print(f"📁 Abra o arquivo: {filename}")
        print("🖨️ Para imprimir: Ctrl+P → Salvar como PDF")

        return filename
    else:
        print(f"❌ Erro: {result['error']}")
        return None


if __name__ == "__main__":
    gerar_relatorio_save_water()
