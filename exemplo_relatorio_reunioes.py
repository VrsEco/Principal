#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemplo Prático: Gerando Relatório de Reuniões
Demonstra como usar o sistema estruturado de relatórios
"""

from modules.report_templates import ReportTemplateGenerator
from modules.report_models import ReportModelsManager
from modules.report_templates import ReportTemplatesManager


def exemplo_relatorio_reunioes():
    """
    Exemplo completo de como gerar um relatório de reuniões
    usando o sistema estruturado
    """
    print("🎯 Exemplo: Gerando Relatório de Reuniões")
    print("=" * 50)
    
    # 1. Lista templates disponíveis
    print("\n📋 Templates de Reuniões Disponíveis:")
    templates_manager = ReportTemplatesManager()
    templates = templates_manager.get_templates_by_type('meetings')
    
    for template in templates:
        print(f"   - ID {template['id']}: {template['name']}")
        print(f"     Configuração: {template['page_config_name']}")
        print(f"     Seções: {list(template['sections_config'].keys())}")
        print()
    
    # 2. Lista configurações de página disponíveis
    print("📄 Configurações de Página Disponíveis:")
    models_manager = ReportModelsManager()
    models = models_manager.get_all_models()
    
    for model in models:
        print(f"   - ID {model['id']}: {model['name']}")
        print(f"     Papel: {model['paper_size']} | Orientação: {model['orientation']}")
        print()
    
    # 3. Dados de exemplo para o relatório
    dados_reunioes = {
        'company_name': 'TechnoSolutions Ltda',
        'report_title': 'Relatório de Reuniões - Janeiro 2024',
        'period_start': '01/01/2024',
        'period_end': '31/01/2024',
        'total_meetings': 15,
        'unique_participants': 25,
        'participation_rate': 85,
        'avg_participation': 8.5,
        'max_participation': 12,
        'min_participation': 5,
        'conclusions': '''As reuniões do mês de janeiro foram altamente produtivas, com uma taxa de participação de 85%. 
        Destacamos a qualidade das discussões e o engajamento da equipe. 
        Recomendamos manter a frequência atual e implementar follow-ups mais estruturados para os próximos meses.''',
        'meetings': [
            {
                'title': 'Reunião de Planejamento Semanal',
                'date': '05/01/2024',
                'time': '09:00 - 10:30',
                'location': 'Sala de Reuniões A',
                'organizer': 'João Silva',
                'description': 'Planejamento das atividades da semana e definição de prioridades',
                'participants': ['João Silva', 'Maria Santos', 'Pedro Costa', 'Ana Lima']
            },
            {
                'title': 'Review de Projetos',
                'date': '12/01/2024',
                'time': '14:00 - 16:00',
                'location': 'Sala de Reuniões B',
                'organizer': 'Maria Santos',
                'description': 'Revisão do progresso dos projetos em andamento e ajustes de cronograma',
                'participants': ['Maria Santos', 'Pedro Costa', 'Ana Lima', 'Carlos Oliveira', 'Lucia Ferreira']
            },
            {
                'title': 'Reunião de Alinhamento Estratégico',
                'date': '19/01/2024',
                'time': '10:00 - 11:30',
                'location': 'Sala de Reuniões A',
                'organizer': 'Pedro Costa',
                'description': 'Alinhamento de objetivos estratégicos e metas do trimestre',
                'participants': ['Pedro Costa', 'Ana Lima', 'Carlos Oliveira', 'Roberto Mendes']
            },
            {
                'title': 'Retrospectiva Mensal',
                'date': '26/01/2024',
                'time': '15:00 - 17:00',
                'location': 'Sala de Reuniões C',
                'organizer': 'Ana Lima',
                'description': 'Análise dos resultados do mês e identificação de melhorias',
                'participants': ['Ana Lima', 'João Silva', 'Maria Santos', 'Pedro Costa', 'Carlos Oliveira', 'Lucia Ferreira', 'Roberto Mendes']
            }
        ]
    }
    
    # 4. Gera relatório usando template completo
    print("🚀 Gerando Relatório Completo...")
    generator = ReportTemplateGenerator()
    
    # Usa o primeiro template de reuniões encontrado
    if templates:
        template_id = templates[0]['id']
        print(f"   Usando template: {templates[0]['name']}")
        
        result = generator.generate_report_from_template(template_id, dados_reunioes)
        
        if 'error' not in result:
            print("   ✅ Relatório gerado com sucesso!")
            print(f"   - Template: {result['template_name']}")
            print(f"   - Configuração: {result['page_config_name']}")
            print(f"   - Tipo: {result['report_type']}")
            
            # Salva o relatório
            filename = 'relatorio_reunioes_exemplo.html'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result['html'])
            print(f"   - Arquivo salvo: {filename}")
            
            return filename
        else:
            print(f"   ❌ Erro: {result['error']}")
            return None
    else:
        print("   ❌ Nenhum template de reuniões encontrado!")
        return None


def exemplo_criar_novo_template():
    """
    Exemplo de como criar um novo template programaticamente
    """
    print("\n🆕 Exemplo: Criando Novo Template")
    print("=" * 50)
    
    templates_manager = ReportTemplatesManager()
    models_manager = ReportModelsManager()
    
    # Busca uma configuração de página (Model 7)
    models = models_manager.get_all_models()
    model_7 = None
    for model in models:
        if 'Model 7' in model['name']:
            model_7 = model
            break
    
    if not model_7:
        print("❌ Model 7 não encontrado!")
        return
    
    print(f"📄 Usando configuração: {model_7['name']} (ID: {model_7['id']})")
    
    # Cria novo template personalizado
    novo_template = {
        'name': 'Relatório de Reuniões - Personalizado',
        'description': 'Template personalizado para relatórios de reuniões com foco em análise de produtividade',
        'page_config_id': model_7['id'],
        'report_type': 'meetings',
        'sections_config': {
            'summary': {
                'enabled': True,
                'title': 'Resumo Executivo',
                'description': 'Visão geral das reuniões do período'
            },
            'meetings_list': {
                'enabled': True,
                'title': 'Lista Detalhada de Reuniões',
                'description': 'Detalhes de todas as reuniões realizadas'
            },
            'participants_analysis': {
                'enabled': True,
                'title': 'Análise de Participação',
                'description': 'Estatísticas detalhadas de participação'
            },
            'conclusions': {
                'enabled': True,
                'title': 'Conclusões e Próximos Passos',
                'description': 'Análise final e recomendações'
            }
        }
    }
    
    try:
        template_id = templates_manager.save_template(novo_template)
        print(f"✅ Template criado com sucesso! ID: {template_id}")
        
        # Testa o novo template
        generator = ReportTemplateGenerator()
        dados_teste = {
            'company_name': 'Empresa Teste',
            'report_title': 'Teste do Novo Template',
            'period_start': '01/01/2024',
            'period_end': '31/01/2024',
            'total_meetings': 5,
            'unique_participants': 10,
            'participation_rate': 90,
            'conclusions': 'Template funcionando perfeitamente!',
            'meetings': []
        }
        
        result = generator.generate_report_from_template(template_id, dados_teste)
        if 'error' not in result:
            print("✅ Teste do template bem-sucedido!")
        else:
            print(f"❌ Erro no teste: {result['error']}")
            
    except Exception as e:
        print(f"❌ Erro ao criar template: {e}")


def exemplo_usar_diferentes_configuracoes():
    """
    Exemplo de como usar diferentes configurações de página
    """
    print("\n🔄 Exemplo: Usando Diferentes Configurações")
    print("=" * 50)
    
    templates_manager = ReportTemplatesManager()
    models_manager = ReportModelsManager()
    
    # Lista todas as configurações disponíveis
    models = models_manager.get_all_models()
    
    print("📄 Configurações disponíveis:")
    for model in models:
        print(f"   - {model['name']} (ID: {model['id']})")
        print(f"     Papel: {model['paper_size']} | Orientação: {model['orientation']}")
        print()
    
    # Cria templates usando diferentes configurações
    for i, model in enumerate(models[:2]):  # Usa as 2 primeiras configurações
        template_data = {
            'name': f'Template Teste - {model["name"]}',
            'description': f'Template de teste usando {model["name"]}',
            'page_config_id': model['id'],
            'report_type': 'meetings',
            'sections_config': {
                'summary': {'enabled': True, 'title': 'Resumo'},
                'meetings_list': {'enabled': True, 'title': 'Reuniões'},
                'conclusions': {'enabled': True, 'title': 'Conclusões'}
            }
        }
        
        try:
            template_id = templates_manager.save_template(template_data)
            print(f"✅ Template criado: {template_data['name']} (ID: {template_id})")
        except Exception as e:
            print(f"❌ Erro ao criar template: {e}")


def main():
    """
    Função principal com todos os exemplos
    """
    print("🎯 EXEMPLOS PRÁTICOS - Sistema de Relatórios Estruturado")
    print("=" * 60)
    
    try:
        # Exemplo 1: Gerar relatório de reuniões
        arquivo_gerado = exemplo_relatorio_reunioes()
        
        # Exemplo 2: Criar novo template
        exemplo_criar_novo_template()
        
        # Exemplo 3: Usar diferentes configurações
        exemplo_usar_diferentes_configuracoes()
        
        print("\n" + "=" * 60)
        print("✅ Todos os exemplos executados com sucesso!")
        
        if arquivo_gerado:
            print(f"\n📄 Relatório de exemplo salvo em: {arquivo_gerado}")
            print("   Abra o arquivo no navegador para visualizar o resultado!")
        
        print("\n🎯 Próximos passos:")
        print("   1. Acesse: http://127.0.0.1:5002/report-templates")
        print("   2. Crie seus próprios templates")
        print("   3. Gere relatórios personalizados")
        print("   4. Use: 'Pegue a página X e o modelo do relatório Y'")
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
