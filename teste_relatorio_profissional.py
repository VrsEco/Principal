#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Geração de Relatório Profissional
Sistema PEVAPP22
"""

import os
from datetime import datetime, timedelta
import random

print("=" * 60)
print("🚀 TESTE DE RELATÓRIO PROFISSIONAL - PEVAPP22")
print("=" * 60)

# Verifica se as bibliotecas estão instaladas
def verificar_bibliotecas():
    """Verifica se todas as bibliotecas necessárias estão instaladas"""
    bibliotecas = {
        'weasyprint': 'WeasyPrint (PDF)',
        'plotly': 'Plotly (Gráficos)',
        'pandas': 'Pandas (Dados)',
        'kaleido': 'Kaleido (Exportar imagens)'
    }
    
    print("\n📦 Verificando bibliotecas instaladas...\n")
    
    faltando = []
    for lib, nome in bibliotecas.items():
        try:
            __import__(lib)
            print(f"   ✅ {nome}")
        except ImportError:
            print(f"   ❌ {nome} - NÃO INSTALADO")
            faltando.append(lib)
    
    if faltando:
        print("\n⚠️  ATENÇÃO: Algumas bibliotecas não estão instaladas!")
        print(f"\nPara instalar, execute:")
        print(f"   pip install {' '.join(faltando)}")
        print("\nOu instale todas de uma vez:")
        print(f"   pip install -r requirements_relatorios.txt")
        return False
    
    print("\n✅ Todas as bibliotecas estão instaladas!\n")
    return True

if not verificar_bibliotecas():
    print("\n" + "=" * 60)
    input("Pressione ENTER para sair...")
    exit(1)

# Importa as bibliotecas
from weasyprint import HTML
import plotly.graph_objects as go
import pandas as pd

print("=" * 60)
print("📊 Gerando Relatório de Demonstração...")
print("=" * 60)

# Cria diretórios necessários
os.makedirs('temp_relatorios', exist_ok=True)
os.makedirs('relatorios', exist_ok=True)

# ========================================
# 1. GERA DADOS DE EXEMPLO
# ========================================

print("\n1️⃣  Preparando dados...")

# Dados de vendas mensais
meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
vendas = [45000, 52000, 48000, 61000, 58000, 67000]
meta = [50000, 50000, 50000, 50000, 50000, 50000]

# Projetos em andamento
projetos_data = [
    {
        'codigo': 'PROJ-001',
        'nome': 'Implementação Sistema ERP',
        'status': 'Em dia',
        'prazo': '15/12/2024',
        'valor': 150000.00
    },
    {
        'codigo': 'PROJ-002',
        'nome': 'Modernização Infraestrutura',
        'status': 'Atrasado',
        'prazo': '30/11/2024',
        'valor': 89500.00
    },
    {
        'codigo': 'PROJ-003',
        'nome': 'Migração Cloud',
        'status': 'Em dia',
        'prazo': '20/01/2025',
        'valor': 120000.00
    },
    {
        'codigo': 'PROJ-004',
        'nome': 'Automação Processos',
        'status': 'Em dia',
        'prazo': '10/02/2025',
        'valor': 75000.00
    }
]

# Métricas
metricas = {
    'faturamento': sum(vendas),
    'projetos_concluidos': 8,
    'eficiencia': 92,
    'qualidade': 95,
    'prazo': 88,
    'custo': 91,
    'satisfacao': 94
}

print("   ✅ Dados preparados")

# ========================================
# 2. GERA GRÁFICOS
# ========================================

print("\n2️⃣  Gerando gráficos profissionais...")

# Gráfico 1: Vendas vs Meta
fig_vendas = go.Figure()

fig_vendas.add_trace(go.Scatter(
    x=meses,
    y=vendas,
    mode='lines+markers',
    name='Vendas Realizadas',
    line=dict(color='rgb(26, 118, 255)', width=3),
    marker=dict(size=10)
))

fig_vendas.add_trace(go.Scatter(
    x=meses,
    y=meta,
    mode='lines',
    name='Meta',
    line=dict(color='rgb(255, 99, 71)', width=2, dash='dash')
))

fig_vendas.update_layout(
    title={
        'text': 'Evolução de Vendas vs Meta',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 20, 'family': 'Arial'}
    },
    xaxis_title='Mês',
    yaxis_title='Vendas (R$)',
    template='plotly_white',
    hovermode='x unified',
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    font=dict(family="Arial", size=12),
    height=400
)

grafico_vendas_path = os.path.abspath('temp_relatorios/grafico_vendas.png')
fig_vendas.write_image(grafico_vendas_path, width=1000, height=400, scale=2)
print("   ✅ Gráfico de vendas criado")

# Gráfico 2: Indicadores de Desempenho
categorias = ['Qualidade', 'Prazo', 'Custo', 'Satisfação']
valores = [metricas['qualidade'], metricas['prazo'], metricas['custo'], metricas['satisfacao']]
cores = ['#1a76ff', '#28a745', '#ffc107', '#dc3545']

fig_desempenho = go.Figure(data=[
    go.Bar(
        x=categorias,
        y=valores,
        marker_color=cores,
        text=[f'{v}%' for v in valores],
        textposition='auto',
    )
])

fig_desempenho.update_layout(
    title='Indicadores de Desempenho',
    xaxis_title='Indicador',
    yaxis_title='Score (%)',
    template='plotly_white',
    font=dict(family="Arial", size=12),
    yaxis=dict(range=[0, 100]),
    height=400
)

grafico_desempenho_path = os.path.abspath('temp_relatorios/grafico_desempenho.png')
fig_desempenho.write_image(grafico_desempenho_path, width=1000, height=400, scale=2)
print("   ✅ Gráfico de desempenho criado")

# ========================================
# 3. CRIA HTML DO RELATÓRIO
# ========================================

print("\n3️⃣  Montando relatório HTML...")

def format_currency(valor):
    """Formata valor como moeda brasileira"""
    return f'R$ {valor:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

# Monta tabela de projetos
tabela_projetos = ""
for projeto in projetos_data:
    cor_status = 'green' if projeto['status'] == 'Em dia' else 'red'
    icone_status = '✓' if projeto['status'] == 'Em dia' else '⚠'
    
    tabela_projetos += f"""
    <tr>
        <td><strong>{projeto['codigo']}</strong></td>
        <td>{projeto['nome']}</td>
        <td><span style="color: {cor_status};">{icone_status} {projeto['status']}</span></td>
        <td>{projeto['prazo']}</td>
        <td>{format_currency(projeto['valor'])}</td>
    </tr>
    """

# Template HTML completo
html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Mensal - PEVAPP22 Demo</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @top-center {{
                content: "PEVAPP22 - Relatório Gerencial Confidencial";
                font-size: 10pt;
                color: #666;
            }}
            @bottom-right {{
                content: "Página " counter(page) " de " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #1a76ff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #1a76ff;
            font-size: 28pt;
            margin: 0;
        }}
        
        .subtitle {{
            font-size: 14pt;
            color: #666;
            margin-top: 10px;
        }}
        
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid #1a76ff;
            padding: 15px 20px;
            margin: 20px 0;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}
        
        .metric-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .metric-value {{
            font-size: 32pt;
            font-weight: bold;
            color: #1a76ff;
        }}
        
        .metric-label {{
            font-size: 11pt;
            color: #666;
            text-transform: uppercase;
            margin-top: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        th {{
            background: #1a76ff;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        
        .chart {{
            page-break-inside: avoid;
            margin: 30px 0;
        }}
        
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 9pt;
            color: #666;
            text-align: center;
        }}
        
        .section {{
            page-break-inside: avoid;
            margin-bottom: 40px;
        }}
        
        .highlight {{
            background: #fff3cd;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        
        ul {{
            line-height: 2;
        }}
    </style>
</head>
<body>
    <!-- Cabeçalho -->
    <div class="header">
        <div>
            <h1>Relatório Gerencial</h1>
            <p class="subtitle">Período: Janeiro a Junho 2024</p>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 36pt; color: #1a76ff; font-weight: bold;">PEVAPP22</div>
            <div style="font-size: 10pt; color: #666;">Sistema de Gestão</div>
        </div>
    </div>
    
    <!-- Resumo Executivo -->
    <div class="info-box">
        <h2 style="margin-top: 0;">📋 Resumo Executivo</h2>
        <p>
            Este relatório apresenta o desempenho da empresa no primeiro semestre de 2024.
            Os resultados demonstram <strong class="highlight">crescimento consistente de 49%</strong> 
            nas vendas, com destaque para o mês de Junho que alcançou <strong>R$ 67.000,00</strong>.
            A eficiência operacional manteve-se em <strong>92%</strong>, superando a meta estabelecida.
        </p>
    </div>
    
    <!-- Métricas Principais -->
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{format_currency(metricas['faturamento'])}</div>
            <div class="metric-label">Faturamento Total</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metricas['projetos_concluidos']}</div>
            <div class="metric-label">Projetos Concluídos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metricas['eficiencia']}%</div>
            <div class="metric-label">Eficiência Operacional</div>
        </div>
    </div>
    
    <!-- Gráfico de Vendas -->
    <div class="section">
        <h2>📊 Evolução de Vendas</h2>
        <p>Análise comparativa entre vendas realizadas e metas estabelecidas:</p>
        <div class="chart">
            <img src="file:///{grafico_vendas_path}" style="width: 100%;" alt="Gráfico de Vendas">
        </div>
        <p style="font-size: 10pt; color: #666; text-align: center; margin-top: 10px;">
            <em>Figura 1: Evolução mensal de vendas vs meta - Jan a Jun 2024</em>
        </p>
    </div>
    
    <!-- Tabela de Projetos -->
    <div class="section">
        <h2>🚀 Projetos em Andamento</h2>
        <p>Portfólio atual de projetos com status e prazos:</p>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Projeto</th>
                    <th>Status</th>
                    <th>Prazo</th>
                    <th>Investimento</th>
                </tr>
            </thead>
            <tbody>
                {tabela_projetos}
            </tbody>
        </table>
        <p style="font-size: 10pt; color: #666;">
            <strong>Total investido:</strong> {format_currency(sum(p['valor'] for p in projetos_data))}
        </p>
    </div>
    
    <!-- Análise de Desempenho -->
    <div class="section">
        <h2>📈 Análise de Desempenho</h2>
        <p>Indicadores chave de performance (KPIs) do período:</p>
        <div class="chart">
            <img src="file:///{grafico_desempenho_path}" style="width: 100%;" alt="Desempenho">
        </div>
        <p style="font-size: 10pt; color: #666; text-align: center; margin-top: 10px;">
            <em>Figura 2: Indicadores de desempenho - scores percentuais</em>
        </p>
    </div>
    
    <!-- Recomendações -->
    <div class="info-box">
        <h2 style="margin-top: 0;">💡 Recomendações Estratégicas</h2>
        <ul>
            <li><strong>Vendas:</strong> Manter estratégia de crescimento. Meta de +15% para próximo trimestre.</li>
            <li><strong>Projetos:</strong> Atenção ao PROJ-002 (atrasado). Sugerimos revisão de recursos.</li>
            <li><strong>Qualidade:</strong> Excelente performance (95%). Documentar melhores práticas.</li>
            <li><strong>Prazo:</strong> Implementar checkpoints quinzenais para melhorar indicador de 88% para 95%.</li>
            <li><strong>Satisfação Cliente:</strong> Score de 94% é excelente. Manter comunicação proativa.</li>
        </ul>
    </div>
    
    <!-- Próximos Passos -->
    <div class="section">
        <h2>🎯 Próximos Passos</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 30%;">Ação</th>
                    <th style="width: 15%;">Prioridade</th>
                    <th style="width: 30%;">Responsável</th>
                    <th style="width: 25%;">Prazo</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Reunião de revisão PROJ-002</td>
                    <td><span style="color: red;">ALTA</span></td>
                    <td>Gerente de Projetos</td>
                    <td>Esta semana</td>
                </tr>
                <tr>
                    <td>Planejamento Q3 2024</td>
                    <td><span style="color: orange;">MÉDIA</span></td>
                    <td>Diretoria</td>
                    <td>Até 30/06</td>
                </tr>
                <tr>
                    <td>Workshop melhores práticas</td>
                    <td><span style="color: green;">BAIXA</span></td>
                    <td>RH</td>
                    <td>Até 15/07</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <!-- Rodapé -->
    <div class="footer">
        <p><strong>Documento Confidencial</strong></p>
        <p>Gerado automaticamente pelo PEVAPP22 em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        <p>© 2024 PEVAPP22 - Sistema de Gestão Empresarial</p>
    </div>
</body>
</html>
"""

print("   ✅ HTML montado")

# ========================================
# 4. CONVERTE PARA PDF
# ========================================

print("\n4️⃣  Convertendo para PDF...")

output_path = f'relatorios/relatorio_demo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'

try:
    HTML(string=html_content).write_pdf(output_path)
    print(f"   ✅ PDF criado com sucesso!")
except Exception as e:
    print(f"   ❌ Erro ao criar PDF: {str(e)}")
    print("\n" + "=" * 60)
    input("Pressione ENTER para sair...")
    exit(1)

# ========================================
# 5. RESULTADO
# ========================================

print("\n" + "=" * 60)
print("✅ RELATÓRIO GERADO COM SUCESSO!")
print("=" * 60)
print(f"\n📄 Arquivo criado:")
print(f"   {os.path.abspath(output_path)}")
print(f"\n📊 Estatísticas:")
print(f"   • Páginas: ~4 páginas")
print(f"   • Gráficos: 2 gráficos profissionais")
print(f"   • Tabelas: 2 tabelas formatadas")
print(f"   • Tamanho: {os.path.getsize(output_path) / 1024:.1f} KB")

print("\n📂 Abra o arquivo para visualizar o relatório profissional!")
print("\n💡 Dica: Este é apenas um exemplo. Você pode personalizar:")
print("   • Layout e cores")
print("   • Adicionar logo da empresa")
print("   • Incluir mais gráficos")
print("   • Adicionar assinatura digital")
print("   • Exportar para Excel também")

print("\n" + "=" * 60)

# Pergunta se quer abrir o arquivo
try:
    resposta = input("\n🚀 Deseja abrir o PDF agora? (S/N): ").strip().upper()
    if resposta == 'S':
        os.startfile(output_path)
except:
    pass

print("\n✅ Teste concluído com sucesso!")
print("=" * 60)


