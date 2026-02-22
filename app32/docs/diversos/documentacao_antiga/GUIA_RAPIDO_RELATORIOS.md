# 🚀 Guia Rápido - Relatórios Profissionais

## ⚡ Instalação Rápida (3 passos)

### 1️⃣ Instalar Bibliotecas
Execute o instalador automático:
```bash
INSTALAR_RELATORIOS.bat
```

Ou manualmente:
```bash
pip install weasyprint plotly kaleido pandas numpy openpyxl
```

---

### 2️⃣ Testar Funcionamento
Execute o script de teste:
```bash
python teste_relatorio_profissional.py
```

Isso vai gerar um PDF de demonstração na pasta `relatorios/`

---

### 3️⃣ Integrar ao PEVAPP22

Adicione ao seu `app_pev.py`:

```python
from weasyprint import HTML
from datetime import datetime
import plotly.graph_objects as go
import os

@app.route('/relatorio/mensal/<int:empresa_id>')
def gerar_relatorio_mensal(empresa_id):
    """Gera relatório mensal profissional"""
    
    # 1. Busca dados do banco
    empresa = buscar_empresa(empresa_id)
    vendas = buscar_vendas(empresa_id, mes_atual)
    projetos = buscar_projetos(empresa_id)
    
    # 2. Gera gráfico
    fig = go.Figure(data=[
        go.Bar(x=vendas['meses'], y=vendas['valores'])
    ])
    fig.write_image('temp_relatorios/grafico.png')
    
    # 3. Renderiza HTML
    html = render_template('relatorio_mensal.html',
        empresa=empresa,
        vendas=vendas,
        projetos=projetos,
        grafico='temp_relatorios/grafico.png'
    )
    
    # 4. Gera PDF
    pdf_path = f'relatorios/relatorio_{empresa_id}.pdf'
    HTML(string=html).write_pdf(pdf_path)
    
    # 5. Retorna arquivo
    return send_file(pdf_path, as_attachment=True)
```

---

## 📊 Exemplos Prontos

### Gráfico de Linha (Vendas)
```python
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=['Jan', 'Fev', 'Mar', 'Abr'],
    y=[45000, 52000, 48000, 61000],
    mode='lines+markers',
    line=dict(color='rgb(26, 118, 255)', width=3)
))

fig.update_layout(
    title='Evolução de Vendas',
    template='plotly_white'
)

fig.write_image('grafico_vendas.png', width=1000, height=500)
```

### Gráfico de Pizza (Distribuição)
```python
fig = go.Figure(data=[go.Pie(
    labels=['Produto A', 'Produto B', 'Produto C'],
    values=[35, 40, 25],
    hole=0.3  # Gráfico de rosca
)])

fig.update_layout(title='Distribuição de Vendas por Produto')
fig.write_image('grafico_pizza.png')
```

### Gráfico de Barras (Comparativo)
```python
fig = go.Figure(data=[
    go.Bar(name='2023', x=['Q1', 'Q2', 'Q3', 'Q4'], y=[20, 25, 30, 35]),
    go.Bar(name='2024', x=['Q1', 'Q2', 'Q3', 'Q4'], y=[25, 30, 38, 42])
])

fig.update_layout(barmode='group', title='Comparativo Anual')
fig.write_image('grafico_comparativo.png')
```

### Tabela com Pandas
```python
import pandas as pd

dados = [
    {'Produto': 'Produto A', 'Vendas': 150000, 'Lucro': 45000},
    {'Produto': 'Produto B', 'Vendas': 120000, 'Lucro': 38000},
    {'Produto': 'Produto C', 'Vendas': 95000, 'Lucro': 28500}
]

df = pd.DataFrame(dados)

# Formata valores
df['Vendas'] = df['Vendas'].apply(lambda x: f'R$ {x:,.2f}')
df['Lucro'] = df['Lucro'].apply(lambda x: f'R$ {x:,.2f}')

# Gera HTML
html_table = df.to_html(classes='table table-striped', index=False)
```

---

## 🎨 Template HTML Básico

Crie `templates/relatorio_simples.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Relatório</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        h1 { color: #1a76ff; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #1a76ff; color: white; padding: 10px; }
        td { padding: 8px; border-bottom: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>{{ titulo }}</h1>
    <p>Período: {{ periodo }}</p>
    
    <img src="file:///{{ grafico_path }}" style="width: 100%;">
    
    <table>
        <tr>
            <th>Item</th>
            <th>Valor</th>
        </tr>
        {% for item in dados %}
        <tr>
            <td>{{ item.nome }}</td>
            <td>{{ item.valor }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

Usar:
```python
html = render_template('relatorio_simples.html',
    titulo='Relatório Mensal',
    periodo='Janeiro 2024',
    grafico_path=os.path.abspath('grafico.png'),
    dados=lista_dados
)

HTML(string=html).write_pdf('relatorio.pdf')
```

---

## 💡 Dicas Importantes

### ✅ DO (Faça)
- Use `file:///` antes do caminho completo das imagens
- Salve gráficos como PNG antes de incluir no PDF
- Use `os.path.abspath()` para caminhos de arquivo
- Teste o HTML no navegador antes de gerar PDF
- Use CSS Grid/Flexbox para layouts profissionais

### ❌ DON'T (Não Faça)
- Não use caminhos relativos para imagens
- Não use JavaScript (WeasyPrint não executa JS)
- Não use Bootstrap CSS (pode causar problemas)
- Não gere PDFs muito grandes (> 50 MB)

---

## 📚 Recursos Adicionais

### Documentação Oficial
- **WeasyPrint:** https://doc.courtbouillon.org/weasyprint/
- **Plotly:** https://plotly.com/python/
- **Pandas:** https://pandas.pydata.org/docs/

### Galeria de Exemplos Plotly
- https://plotly.com/python/basic-charts/
- https://plotly.com/python/financial-charts/
- https://plotly.com/python/statistical-charts/

---

## 🆘 Solução de Problemas

### Erro: "OSError: no library called "cairo" was found"
**Windows:**
```bash
# Instale GTK3 Runtime
# Download: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
```

**Linux:**
```bash
sudo apt-get install python3-pip python3-cffi python3-brotli libpango-1.0-0 libpangoft2-1.0-0
```

### Erro ao exportar gráficos Plotly
```bash
pip install kaleido --upgrade
```

### PDF não exibe imagens
Verifique se está usando `file:///` + caminho absoluto:
```python
img_path = os.path.abspath('grafico.png')
html = f'<img src="file:///{img_path}">'
```

---

## 🎯 Próximos Passos

1. ✅ Instalar bibliotecas
2. ✅ Executar teste de demonstração
3. ✅ Personalizar template HTML
4. ✅ Criar rota no Flask
5. ✅ Integrar com banco de dados
6. ✅ Adicionar logo da empresa
7. ✅ Implementar envio por e-mail

---

**Documentação completa:** `BIBLIOTECAS_RELATORIOS_PROFISSIONAIS.md`


