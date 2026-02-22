# 📊 Bibliotecas para Relatórios Profissionais - PEVAPP22

## 🏆 Melhor Solução Recomendada

### **WeasyPrint + Plotly + Pandas**

Esta combinação oferece o melhor custo-benefício para relatórios profissionais:

---

## 📦 Bibliotecas Principais

### 1️⃣ **WeasyPrint** (ALTAMENTE RECOMENDADO)
**Por que é a melhor escolha:**
- ✅ Converte HTML/CSS moderno em PDF de **alta qualidade**
- ✅ Usa templates Jinja2 (que você já tem no Flask)
- ✅ Suporta CSS Grid, Flexbox, fontes personalizadas
- ✅ Gráficos, tabelas, imagens, cabeçalhos e rodapés
- ✅ 100% gratuito e open-source
- ✅ Perfeito para relatórios corporativos

**Instalação:**
```bash
pip install weasyprint
```

**Exemplo de uso:**
```python
from weasyprint import HTML
from flask import render_template

# Renderiza template HTML
html_content = render_template('relatorio_mensal.html', dados=dados)

# Converte para PDF profissional
HTML(string=html_content).write_pdf('relatorio.pdf')
```

---

### 2️⃣ **Plotly** (VISUALIZAÇÕES PROFISSIONAIS)
**Por que usar:**
- ✅ Gráficos **interativos** e **impressionantes**
- ✅ Qualidade de publicação científica/corporativa
- ✅ Mais de 40 tipos de gráficos
- ✅ Exporta como imagem estática para PDF
- ✅ Dashboards profissionais

**Instalação:**
```bash
pip install plotly kaleido
```

**Exemplo:**
```python
import plotly.graph_objects as go

# Cria gráfico profissional
fig = go.Figure(data=[
    go.Bar(x=meses, y=vendas, marker_color='rgb(26, 118, 255)')
])

fig.update_layout(
    title='Vendas Mensais 2024',
    xaxis_title='Mês',
    yaxis_title='Vendas (R$)',
    template='plotly_white',
    font=dict(family="Arial", size=12)
)

# Salva como imagem para incluir no PDF
fig.write_image("grafico_vendas.png", width=800, height=500)
```

---

### 3️⃣ **Pandas** (MANIPULAÇÃO DE DADOS)
**Por que usar:**
- ✅ Tabelas profissionais com formatação
- ✅ Análise de dados poderosa
- ✅ Exporta para HTML, Excel, PDF
- ✅ Estatísticas automáticas

**Instalação:**
```bash
pip install pandas openpyxl
```

**Exemplo:**
```python
import pandas as pd

# Cria DataFrame com dados do banco
df = pd.DataFrame(resultados)

# Formata valores
df['Valor'] = df['Valor'].apply(lambda x: f'R$ {x:,.2f}')

# Gera tabela HTML estilizada
html_table = df.to_html(
    index=False,
    classes='table table-striped table-hover',
    border=0
)
```

---

## 🎨 Stack Completa Recomendada

```python
# requirements_relatorios.txt

# 1. Geração de PDF profissional
weasyprint==61.0

# 2. Visualizações de dados
plotly==5.18.0
kaleido==0.2.1  # Para exportar gráficos como imagem

# 3. Manipulação e análise de dados
pandas==2.1.4
numpy==1.26.3

# 4. Gráficos estatísticos adicionais
matplotlib==3.8.2
seaborn==0.13.1

# 5. Tabelas profissionais
tabulate==0.9.0

# 6. Excel avançado (opcional)
openpyxl==3.1.2
xlsxwriter==3.1.9
```

---

## 🔥 Exemplo Completo de Relatório Profissional

### **1. Template HTML (templates/relatorio_profissional.html)**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatório Mensal - {{ empresa.nome }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "{{ empresa.nome }} - Relatório Confidencial";
                font-size: 10pt;
                color: #666;
            }
            @bottom-right {
                content: "Página " counter(page) " de " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #1a76ff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .logo {
            max-width: 200px;
            height: auto;
        }
        
        h1 {
            color: #1a76ff;
            font-size: 28pt;
            margin: 0;
        }
        
        .info-box {
            background: #f8f9fa;
            border-left: 4px solid #1a76ff;
            padding: 15px 20px;
            margin: 20px 0;
        }
        
        .metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 30px 0;
        }
        
        .metric-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .metric-value {
            font-size: 32pt;
            font-weight: bold;
            color: #1a76ff;
        }
        
        .metric-label {
            font-size: 11pt;
            color: #666;
            text-transform: uppercase;
            margin-top: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th {
            background: #1a76ff;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        
        td {
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .chart {
            page-break-inside: avoid;
            margin: 30px 0;
        }
        
        .footer {
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            font-size: 9pt;
            color: #666;
            text-align: center;
        }
        
        .section {
            page-break-inside: avoid;
            margin-bottom: 40px;
        }
        
        .highlight {
            background: #fff3cd;
            padding: 2px 6px;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <!-- Cabeçalho -->
    <div class="header">
        <div>
            <h1>Relatório Gerencial</h1>
            <p style="font-size: 14pt; color: #666;">
                Período: {{ periodo_inicio }} a {{ periodo_fim }}
            </p>
        </div>
        {% if empresa.logo %}
        <img src="{{ empresa.logo }}" class="logo" alt="Logo">
        {% endif %}
    </div>
    
    <!-- Resumo Executivo -->
    <div class="info-box">
        <h2 style="margin-top: 0;">📋 Resumo Executivo</h2>
        <p>{{ resumo_executivo }}</p>
    </div>
    
    <!-- Métricas Principais -->
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value">{{ faturamento|format_currency }}</div>
            <div class="metric-label">Faturamento</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ projetos_concluidos }}</div>
            <div class="metric-label">Projetos Concluídos</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{{ eficiencia }}%</div>
            <div class="metric-label">Eficiência</div>
        </div>
    </div>
    
    <!-- Gráfico de Vendas -->
    <div class="section">
        <h2>📊 Evolução de Vendas</h2>
        <div class="chart">
            <img src="file://{{ grafico_vendas_path }}" style="width: 100%;" alt="Gráfico de Vendas">
        </div>
    </div>
    
    <!-- Tabela de Projetos -->
    <div class="section">
        <h2>🚀 Projetos em Andamento</h2>
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
                {% for projeto in projetos %}
                <tr>
                    <td><strong>{{ projeto.codigo }}</strong></td>
                    <td>{{ projeto.nome }}</td>
                    <td>
                        {% if projeto.status == 'Em dia' %}
                        <span style="color: green;">✓ {{ projeto.status }}</span>
                        {% else %}
                        <span style="color: red;">⚠ {{ projeto.status }}</span>
                        {% endif %}
                    </td>
                    <td>{{ projeto.prazo }}</td>
                    <td>{{ projeto.valor|format_currency }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- Análise de Desempenho -->
    <div class="section">
        <h2>📈 Análise de Desempenho</h2>
        <div class="chart">
            <img src="file://{{ grafico_desempenho_path }}" style="width: 100%;" alt="Desempenho">
        </div>
    </div>
    
    <!-- Recomendações -->
    <div class="info-box">
        <h2 style="margin-top: 0;">💡 Recomendações</h2>
        <ul>
            {% for recomendacao in recomendacoes %}
            <li>{{ recomendacao }}</li>
            {% endfor %}
        </ul>
    </div>
    
    <!-- Rodapé -->
    <div class="footer">
        <p>Documento confidencial gerado em {{ data_geracao }}</p>
        <p>{{ empresa.nome }} - {{ empresa.endereco }}</p>
    </div>
</body>
</html>
```

---

### **2. Código Python para Gerar o Relatório**

```python
# modules/relatorio_profissional.py

from flask import render_template
from weasyprint import HTML
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import os

class GeradorRelatorio:
    """Gerador de relatórios profissionais em PDF"""
    
    def __init__(self):
        self.temp_dir = "temp_relatorios"
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def gerar_grafico_vendas(self, dados_vendas):
        """Gera gráfico profissional de vendas"""
        fig = go.Figure()
        
        # Adiciona linha de vendas
        fig.add_trace(go.Scatter(
            x=dados_vendas['mes'],
            y=dados_vendas['valor'],
            mode='lines+markers',
            name='Vendas',
            line=dict(color='rgb(26, 118, 255)', width=3),
            marker=dict(size=10)
        ))
        
        # Adiciona linha de meta
        fig.add_trace(go.Scatter(
            x=dados_vendas['mes'],
            y=dados_vendas['meta'],
            mode='lines',
            name='Meta',
            line=dict(color='rgb(255, 99, 71)', width=2, dash='dash')
        ))
        
        # Layout profissional
        fig.update_layout(
            title={
                'text': 'Evolução de Vendas vs Meta',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20}
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
            font=dict(family="Arial", size=12)
        )
        
        # Salva como imagem
        path = os.path.join(self.temp_dir, 'grafico_vendas.png')
        fig.write_image(path, width=1000, height=500, scale=2)
        return os.path.abspath(path)
    
    def gerar_grafico_desempenho(self, categorias, valores):
        """Gera gráfico de barras comparativo"""
        fig = go.Figure(data=[
            go.Bar(
                x=categorias,
                y=valores,
                marker_color=['#1a76ff', '#28a745', '#ffc107', '#dc3545'],
                text=valores,
                textposition='auto',
            )
        ])
        
        fig.update_layout(
            title='Indicadores de Desempenho',
            xaxis_title='Indicador',
            yaxis_title='Score',
            template='plotly_white',
            font=dict(family="Arial", size=12)
        )
        
        path = os.path.join(self.temp_dir, 'grafico_desempenho.png')
        fig.write_image(path, width=1000, height=500, scale=2)
        return os.path.abspath(path)
    
    def formatar_dados_projetos(self, projetos):
        """Formata dados dos projetos com Pandas"""
        df = pd.DataFrame(projetos)
        
        # Formata valores monetários
        if 'valor' in df.columns:
            df['valor_formatado'] = df['valor'].apply(
                lambda x: f'R$ {x:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
            )
        
        return df.to_dict('records')
    
    def gerar_relatorio_completo(self, empresa_id, periodo_inicio, periodo_fim):
        """Gera relatório completo em PDF"""
        
        # 1. Busca dados do banco
        empresa = self.buscar_empresa(empresa_id)
        dados_vendas = self.buscar_dados_vendas(empresa_id, periodo_inicio, periodo_fim)
        projetos = self.buscar_projetos(empresa_id)
        metricas = self.calcular_metricas(empresa_id, periodo_inicio, periodo_fim)
        
        # 2. Gera gráficos
        grafico_vendas = self.gerar_grafico_vendas(dados_vendas)
        grafico_desempenho = self.gerar_grafico_desempenho(
            ['Qualidade', 'Prazo', 'Custo', 'Satisfação'],
            [metricas['qualidade'], metricas['prazo'], metricas['custo'], metricas['satisfacao']]
        )
        
        # 3. Prepara dados para o template
        contexto = {
            'empresa': empresa,
            'periodo_inicio': periodo_inicio.strftime('%d/%m/%Y'),
            'periodo_fim': periodo_fim.strftime('%d/%m/%Y'),
            'faturamento': metricas['faturamento'],
            'projetos_concluidos': metricas['projetos_concluidos'],
            'eficiencia': metricas['eficiencia'],
            'resumo_executivo': metricas['resumo'],
            'projetos': self.formatar_dados_projetos(projetos),
            'grafico_vendas_path': grafico_vendas,
            'grafico_desempenho_path': grafico_desempenho,
            'recomendacoes': metricas['recomendacoes'],
            'data_geracao': datetime.now().strftime('%d/%m/%Y às %H:%M')
        }
        
        # 4. Renderiza HTML
        html_content = render_template('relatorio_profissional.html', **contexto)
        
        # 5. Converte para PDF
        output_path = f'relatorios/relatorio_{empresa_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        HTML(string=html_content).write_pdf(output_path)
        
        # 6. Limpa arquivos temporários
        self.limpar_temp()
        
        return output_path
    
    def buscar_empresa(self, empresa_id):
        """Busca dados da empresa"""
        # Implementar conforme seu banco
        pass
    
    def buscar_dados_vendas(self, empresa_id, inicio, fim):
        """Busca dados de vendas"""
        # Implementar conforme seu banco
        pass
    
    def buscar_projetos(self, empresa_id):
        """Busca projetos"""
        # Implementar conforme seu banco
        pass
    
    def calcular_metricas(self, empresa_id, inicio, fim):
        """Calcula métricas do período"""
        # Implementar lógica de cálculo
        pass
    
    def limpar_temp(self):
        """Remove arquivos temporários"""
        for arquivo in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, arquivo))


# Filtro Jinja2 para formatar moeda
@app.template_filter('format_currency')
def format_currency_filter(value):
    """Formata valor como moeda brasileira"""
    return f'R$ {value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
```

---

### **3. Rota Flask para Gerar Relatório**

```python
# No seu app_pev.py

from modules.relatorio_profissional import GeradorRelatorio

@app.route('/relatorio/gerar/<int:empresa_id>')
def gerar_relatorio_pdf(empresa_id):
    """Gera relatório profissional em PDF"""
    try:
        gerador = GeradorRelatorio()
        
        # Define período (exemplo: último mês)
        periodo_fim = datetime.now()
        periodo_inicio = periodo_fim - timedelta(days=30)
        
        # Gera relatório
        pdf_path = gerador.gerar_relatorio_completo(
            empresa_id,
            periodo_inicio,
            periodo_fim
        )
        
        # Retorna o arquivo PDF
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_{empresa_id}.pdf'
        )
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('dashboard'))
```

---

## 🎯 Comparação de Bibliotecas

| Biblioteca | Qualidade | Facilidade | Performance | Custo | Recomendação |
|-----------|-----------|------------|-------------|-------|--------------|
| **WeasyPrint** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Grátis | ✅ **MELHOR ESCOLHA** |
| ReportLab | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Grátis | Já instalado (básico) |
| Plotly | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Grátis | ✅ **GRÁFICOS** |
| Pandas | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Grátis | ✅ **DADOS** |
| xhtml2pdf | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Grátis | Alternativa |
| Borb | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Grátis | Moderna, mas menos docs |

---

## 📦 Instalação Completa

Adicione ao seu `requirements.txt`:

```txt
# Relatórios Profissionais
weasyprint==61.0
plotly==5.18.0
kaleido==0.2.1
pandas==2.1.4
numpy==1.26.3
openpyxl==3.1.2
```

Instale:
```bash
pip install weasyprint plotly kaleido pandas numpy openpyxl
```

---

## 🚀 Vantagens da Solução

✅ **Relatórios com qualidade gráfica**
✅ **Templates HTML/CSS (fácil customização)**
✅ **Gráficos interativos de nível corporativo**
✅ **Totalmente gratuito e open-source**
✅ **Integração perfeita com Flask**
✅ **Suporta cabeçalhos, rodapés, numeração de páginas**
✅ **Exporta para PDF, Excel, HTML**
✅ **Marca d'água e assinatura digital (se necessário)**

---

## 📚 Recursos Adicionais

### Gráficos Avançados com Plotly:
- Gráficos de pizza, rosca, funil
- Mapas geográficos
- Gráficos 3D
- Gantt para cronogramas
- Sunburst para hierarquias

### Excel Profissional:
```python
# Exportar para Excel com formatação
with pd.ExcelWriter('relatorio.xlsx', engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Dados', index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Dados']
    
    # Formata cabeçalho
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#1a76ff',
        'font_color': 'white'
    })
```

---

## 🎨 Exemplos de Templates Prontos

Posso criar templates para:
- 📊 Relatório Gerencial Mensal
- 💰 Relatório Financeiro
- 🚀 Relatório de Projetos
- 👥 Relatório de RH/Colaboradores
- 📈 Dashboard Executivo
- 🔄 Relatório de Processos

---

**Pronto para implementar! Escolha WeasyPrint como base e você terá relatórios de qualidade profissional! 🚀**


