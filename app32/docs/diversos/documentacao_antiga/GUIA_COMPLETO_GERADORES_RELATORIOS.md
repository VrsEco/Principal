# 📊 GUIA COMPLETO - Sistema de Geradores de Relatórios

## 🎯 VISÃO GERAL

Sistema profissional para criação de relatórios customizados baseado em **código Python**.

### **Conceito:**

```
1. Configure página em /settings/reports → Cria modelo
2. Escreva código Python → Define estrutura e conteúdo
3. Execute o código → Gera HTML/PDF profissional
```

---

## 🏗️ ARQUITETURA

```
relatorios/
├── config/
│   └── visual_identity.py     # Cores, fontes, espaçamentos
│
├── generators/
│   ├── base.py                # Classe base (herdar dela)
│   ├── process_pop.py         # Exemplo: Relatório de POP
│   └── seu_relatorio.py       # ← Você cria aqui!
│
├── templates/                 # Templates HTML (futuro)
└── styles/                    # CSS customizados (futuro)
```

---

## 🚀 QUICK START

### **Passo 1: Criar modelo de página**

```
1. Acesse: http://127.0.0.1:5002/settings/reports

2. Configure:
   - Margens: 20mm, 15mm, 15mm, 20mm
   - Cabeçalho: 25mm
   - Rodapé: 15mm

3. Salve como: "Relatório Padrão Executivo"

4. Anote o ID: 1 (exemplo)
```

### **Passo 2: Gerar relatório**

```python
from relatorios.generators import generate_process_pop_report

# Gerar HTML
html = generate_process_pop_report(
    company_id=6,
    process_id=123,
    model_id=1,  # ID do modelo criado acima
    save_path='meu_relatorio.html'
)

print("Relatório gerado!")
```

**Pronto! Você já tem um relatório profissional!** 🎉

---

## 📖 GUIA DETALHADO

### **1. Criar Seu Próprio Gerador**

Copie o exemplo e adapte:

```python
# relatorios/generators/meu_relatorio.py

from relatorios.generators.base import BaseReportGenerator
from config_database import get_db

class MeuRelatorio(BaseReportGenerator):
    """
    Meu relatório customizado
    """
    
    def __init__(self, report_model_id=None):
        super().__init__(report_model_id)
        
        # Configurações
        self.incluir_graficos = True
        self.incluir_tabelas = True
        
        # Estilos customizados (opcional)
        self.add_custom_style('meu-estilo', """
        .meu-bloco {
            background: #f0f0f0;
            padding: 10px;
        }
        """)
    
    def get_report_title(self):
        """Título do relatório"""
        return "Meu Relatório Customizado"
    
    def fetch_data(self, **kwargs):
        """Buscar dados do banco"""
        db = get_db()
        
        # Buscar o que precisar
        self.data['empresa'] = db.get_company(kwargs['company_id'])
        self.data['projetos'] = db.list_projects(kwargs['company_id'])
        # ... outros dados ...
    
    def build_sections(self):
        """Construir seções"""
        self.clear_sections()
        
        # Seção 1
        self.add_section(
            title='Resumo Executivo',
            content=self._criar_resumo()
        )
        
        # Seção 2
        self.add_section(
            title='Detalhes',
            content=self._criar_detalhes(),
            break_before=True  # Nova página
        )
    
    def _criar_resumo(self):
        """Cria conteúdo da seção de resumo"""
        empresa = self.data.get('empresa', {})
        
        return f"""
        <p>Empresa: {empresa.get('name', '-')}</p>
        <p>Total de projetos: {len(self.data.get('projetos', []))}</p>
        """
    
    def _criar_detalhes(self):
        """Cria tabela de detalhes"""
        projetos = self.data.get('projetos', [])
        
        rows = [[p['name'], p['status']] for p in projetos]
        
        return self.create_table(
            headers=['Projeto', 'Status'],
            rows=rows
        )

# Função auxiliar
def gerar_meu_relatorio(company_id, model_id=None):
    report = MeuRelatorio(report_model_id=model_id)
    return report.generate_html(company_id=company_id)
```

---

### **2. Customizar Cabeçalho e Rodapé**

#### **Opção A: Usar o do modelo** (recomendado)
```python
# Não precisa fazer nada!
# Se você passou model_id, ele usa o cabeçalho/rodapé do modelo
```

#### **Opção B: Sobrescrever com código**
```python
class MeuRelatorio(BaseReportGenerator):
    
    def get_default_header(self):
        """Cabeçalho customizado"""
        empresa = self.data.get('empresa', {})
        
        return f"""
        <div class="report-header">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 33%;">
                        <strong>{empresa.get('name', '')}</strong>
                    </td>
                    <td style="width: 34%; text-align: center;">
                        <strong>{self.get_report_title()}</strong>
                    </td>
                    <td style="width: 33%; text-align: right;">
                        Data: {datetime.now().strftime('%d/%m/%Y')}
                    </td>
                </tr>
            </table>
        </div>
        """
    
    def get_default_footer(self):
        """Rodapé customizado"""
        return """
        <div class="report-footer">
            <div style="display: flex; justify-content: space-between;">
                <span>© 2025 Minha Empresa</span>
                <span>Página <span class="page-number"></span></span>
            </div>
        </div>
        """
```

---

### **3. Adicionar Seções**

```python
def build_sections(self):
    self.clear_sections()
    
    # Seção simples
    self.add_section(
        title='Introdução',
        content='<p>Texto da introdução...</p>'
    )
    
    # Seção com quebra de página antes
    self.add_section(
        title='Nova Seção',
        content='<p>Começa em página nova</p>',
        break_before=True
    )
    
    # Seção com classe CSS customizada
    self.add_section(
        title='Seção Especial',
        content='<p>Conteúdo especial</p>',
        section_class='secao-destaque'
    )
```

---

### **4. Criar Tabelas**

```python
def _criar_tabela_projetos(self):
    projetos = self.data.get('projetos', [])
    
    # Preparar dados
    headers = ['Código', 'Nome', 'Status', 'Responsável']
    rows = [
        [
            p.get('code', '-'),
            p.get('name', '-'),
            p.get('status', '-'),
            p.get('responsible', '-')
        ]
        for p in projetos
    ]
    
    # Criar tabela
    return self.create_table(headers, rows)
```

---

### **5. Criar Caixas de Informação**

```python
def _criar_alertas(self):
    content = ""
    
    # Info
    content += self.create_info_box(
        title='Informação',
        content='Este é um texto informativo.',
        box_type='info'
    )
    
    # Aviso
    content += self.create_info_box(
        title='Atenção',
        content='Isto requer atenção!',
        box_type='warning'
    )
    
    # Sucesso
    content += self.create_info_box(
        title='Sucesso',
        content='Operação concluída!',
        box_type='success'
    )
    
    # Erro
    content += self.create_info_box(
        title='Erro',
        content='Ocorreu um problema!',
        box_type='error'
    )
    
    return content
```

---

### **6. Customizar Estilos**

```python
def __init__(self, report_model_id=None):
    super().__init__(report_model_id)
    
    # Adicionar estilos customizados
    self.add_custom_style('cards', """
    .card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .card-title {
        font-weight: 600;
        font-size: 14pt;
        color: #1a76ff;
        margin-bottom: 8px;
    }
    """)
    
    self.add_custom_style('destaque', """
    .destaque {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
    }
    """)
```

---

### **7. Usar Identidade Visual Padrão**

O sistema já vem com cores, fontes e espaçamentos padrão definidos em `relatorios/config/visual_identity.py`:

```python
from relatorios.config.visual_identity import COLORS, TYPOGRAPHY, SPACING

# Usar nas suas customizações
self.add_custom_style('meu-bloco', f"""
.meu-bloco {{
    background: {COLORS['bg_light']};
    color: {COLORS['text_dark']};
    padding: {SPACING['padding_md']};
    font-family: {TYPOGRAPHY['font_family_primary']};
}}
""")
```

**Cores disponíveis:**
- `COLORS['primary']` → #1a76ff (azul)
- `COLORS['success']` → #10b981 (verde)
- `COLORS['warning']` → #f59e0b (laranja)
- `COLORS['error']` → #ef4444 (vermelho)

---

## 🎨 IDENTIDADE VISUAL

### **Configuração Padrão:**

```python
# Cores
primary: #1a76ff
secondary: #6366f1
accent: #f59e0b

# Tipografia
Fonte: Arial, Helvetica, sans-serif
H1: 18pt (bold)
H2: 15pt (semibold)
H3: 13pt (medium)
Body: 10pt (normal)

# Espaçamentos
Margens: 25mm, 20mm, 20mm, 20mm
Cabeçalho: 25mm
Rodapé: 15mm

# Tabelas
Cabeçalho: azul (#1a76ff) com texto branco
Linhas: alternadas (branco/cinza claro)
```

### **Customizar:**

Edite o arquivo: `relatorios/config/visual_identity.py`

---

## 📄 REGRAS DE QUEBRA DE PÁGINA

### **Automáticas:**

O sistema já evita quebrar:
- Blocos de atividades
- Linhas de tabelas
- Itens de rotinas
- Containers de gráficos

### **Manuais:**

```python
# Forçar nova página antes da seção
self.add_section(
    title='Nova Seção',
    content='...',
    break_before=True
)

# Evitar quebra dentro de um elemento
self.add_custom_style('meu-bloco', """
.meu-bloco {
    page-break-inside: avoid;
}
""")
```

---

## 🔧 INTEGRAÇÃO COM FLASK

### **Criar rota para gerar relatório:**

```python
# Em app_pev.py

@app.route('/api/companies/<int:company_id>/meu-relatorio')
def gerar_meu_relatorio_route(company_id):
    from relatorios.generators.meu_relatorio import gerar_meu_relatorio
    
    # Capturar modelo selecionado (opcional)
    model_id = request.args.get('model', type=int)
    
    # Gerar HTML
    html = gerar_meu_relatorio(
        company_id=company_id,
        model_id=model_id
    )
    
    # Retornar HTML
    response = app.make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response
```

---

## 💡 EXEMPLOS PRÁTICOS

### **Exemplo 1: Relatório Simples**

```python
# relatorios/generators/relatorio_simples.py

from relatorios.generators.base import BaseReportGenerator
from config_database import get_db

class RelatorioSimples(BaseReportGenerator):
    def get_report_title(self):
        return "Relatório Simples"
    
    def fetch_data(self, **kwargs):
        db = get_db()
        self.data['empresa'] = db.get_company(kwargs['company_id'])
    
    def build_sections(self):
        self.clear_sections()
        self.add_section(
            title='Dados da Empresa',
            content=f"<p>Empresa: {self.data['empresa']['name']}</p>"
        )

# Usar
report = RelatorioSimples(report_model_id=1)
html = report.generate_html(company_id=6)
```

### **Exemplo 2: Relatório com Múltiplas Seções**

```python
class RelatorioCompleto(BaseReportGenerator):
    def get_report_title(self):
        return "Relatório Completo"
    
    def fetch_data(self, **kwargs):
        db = get_db()
        self.data['empresa'] = db.get_company(kwargs['company_id'])
        self.data['projetos'] = db.list_projects(kwargs['company_id'])
        self.data['processos'] = db.list_processes(kwargs['company_id'])
    
    def build_sections(self):
        self.clear_sections()
        
        # Seção 1
        self.add_section('Resumo', self._resumo())
        
        # Seção 2
        self.add_section('Projetos', self._projetos(), break_before=True)
        
        # Seção 3
        self.add_section('Processos', self._processos())
    
    def _resumo(self):
        return f"""
        <p>Total de projetos: {len(self.data['projetos'])}</p>
        <p>Total de processos: {len(self.data['processos'])}</p>
        """
    
    def _projetos(self):
        rows = [[p['name'], p['status']] for p in self.data['projetos']]
        return self.create_table(['Nome', 'Status'], rows)
    
    def _processos(self):
        rows = [[p['name'], p['code']] for p in self.data['processos']]
        return self.create_table(['Nome', 'Código'], rows)
```

---

## 📚 REFERÊNCIA RÁPIDA

### **Métodos da Classe Base:**

| Método | O que faz |
|--------|-----------|
| `get_report_title()` | Retorna título do relatório |
| `fetch_data(**kwargs)` | Busca dados do banco |
| `build_sections()` | Constrói seções |
| `add_section(title, content, ...)` | Adiciona seção |
| `clear_sections()` | Limpa seções |
| `create_table(headers, rows)` | Cria tabela HTML |
| `create_info_box(title, content, type)` | Cria caixa de info |
| `add_custom_style(name, css)` | Adiciona CSS customizado |
| `get_default_header()` | Cabeçalho padrão |
| `get_default_footer()` | Rodapé padrão |
| `generate_html(**kwargs)` | Gera HTML final |

---

## 🎯 BOAS PRÁTICAS

### **1. Organize seus geradores**
```
relatorios/generators/
├── process_pop.py        # POPs de processos
├── project_status.py     # Status de projetos
├── monthly_report.py     # Relatório mensal
└── executive_summary.py  # Resumo executivo
```

### **2. Documente bem**
```python
class MeuRelatorio(BaseReportGenerator):
    """
    Relatório de Status Mensal
    
    Inclui:
    - Resumo executivo
    - Métricas de desempenho
    - Projetos em andamento
    - Alertas e pendências
    
    Uso:
        report = MeuRelatorio(model_id=1)
        html = report.generate_html(company_id=6, month=10, year=2025)
    """
```

### **3. Reutilize código**
```python
class ReportBase(BaseReportGenerator):
    """Métodos comuns a vários relatórios"""
    
    def _criar_header_empresa(self):
        # Código reutilizável
        pass

class MeuRelatorio1(ReportBase):
    # Herda os métodos comuns
    pass

class MeuRelatorio2(ReportBase):
    # Herda os métodos comuns
    pass
```

### **4. Teste seus relatórios**
```python
if __name__ == '__main__':
    # Teste rápido
    report = MeuRelatorio(model_id=1)
    html = report.generate_html(company_id=6)
    
    with open('teste.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ Relatório de teste gerado!")
```

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ **Teste o exemplo:** Execute `process_pop.py`
2. ✅ **Crie seu modelo:** Configure em `/settings/reports`
3. ✅ **Copie o exemplo:** Use como template
4. ✅ **Customize:** Adapte para suas necessidades
5. ✅ **Integre:** Adicione rota no Flask

---

## 💡 DICAS AVANÇADAS

### **Gráficos com Chart.js**
```python
def _criar_grafico(self):
    return """
    <canvas id="meuGrafico" width="400" height="200"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById('meuGrafico'), {
        type: 'bar',
        data: { labels: ['Jan', 'Fev', 'Mar'], datasets: [...] }
    });
    </script>
    """
```

### **Imagens**
```python
def _adicionar_logo(self):
    return '<img src="/static/img/logo.png" style="height: 50px;">'
```

### **Condicionais**
```python
def build_sections(self):
    if self.data.get('mostrar_graficos'):
        self.add_section('Gráficos', self._graficos())
    
    if len(self.data.get('alertas', [])) > 0:
        self.add_section('Alertas', self._alertas())
```

---

**🎉 SISTEMA COMPLETO E PROFISSIONAL!**

**Agora você tem total controle sobre seus relatórios! 🚀**

