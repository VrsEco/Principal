# 🔌 Integração dos Relatórios Profissionais ao Flask

## 📋 Código para Adicionar ao `app_pev.py`

### 1️⃣ Importações (no início do arquivo)

Adicione estas importações logo após as outras:

```python
# Relatórios Profissionais
from modules.gerador_relatorios import GeradorRelatoriosProfissionais
from flask import send_file
import os
```

---

### 2️⃣ Rotas de Relatórios (adicionar no final, antes do `if __name__ == '__main__':`)

```python
# ========================================
# ROTAS DE RELATÓRIOS PROFISSIONAIS
# ========================================

@app.route('/relatorio/projetos/<int:empresa_id>')
def relatorio_projetos_pdf(empresa_id):
    """
    Gera relatório de projetos em PDF
    URL: /relatorio/projetos/1
    """
    try:
        # Verifica se empresa existe
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT nome FROM companies WHERE id = ?", (empresa_id,))
        empresa = cursor.fetchone()
        
        if not empresa:
            flash('Empresa não encontrada', 'error')
            return redirect(url_for('dashboard'))
        
        # Gera relatório
        gerador = GeradorRelatoriosProfissionais(db)
        pdf_path = gerador.gerar_relatorio_projetos(empresa_id)
        
        # Retorna o PDF para download
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_projetos_{empresa[0].replace(" ", "_")}.pdf'
        )
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/relatorio/projetos/visualizar/<int:empresa_id>')
def relatorio_projetos_visualizar(empresa_id):
    """
    Visualiza relatório no navegador (sem download)
    URL: /relatorio/projetos/visualizar/1
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT nome FROM companies WHERE id = ?", (empresa_id,))
        empresa = cursor.fetchone()
        
        if not empresa:
            flash('Empresa não encontrada', 'error')
            return redirect(url_for('dashboard'))
        
        # Gera relatório
        gerador = GeradorRelatoriosProfissionais(db)
        pdf_path = gerador.gerar_relatorio_projetos(empresa_id)
        
        # Retorna o PDF para visualização
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=False  # False = abre no navegador
        )
        
    except Exception as e:
        flash(f'Erro ao visualizar relatório: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/api/relatorio/projetos/<int:empresa_id>/gerar', methods=['POST'])
def api_gerar_relatorio_projetos(empresa_id):
    """
    API para gerar relatório via AJAX
    Retorna JSON com link do relatório
    """
    try:
        db = get_db()
        gerador = GeradorRelatoriosProfissionais(db)
        pdf_path = gerador.gerar_relatorio_projetos(empresa_id)
        
        # Retorna JSON com sucesso
        return jsonify({
            'success': True,
            'message': 'Relatório gerado com sucesso',
            'file_path': pdf_path,
            'download_url': url_for('relatorio_projetos_pdf', empresa_id=empresa_id),
            'view_url': url_for('relatorio_projetos_visualizar', empresa_id=empresa_id)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao gerar relatório: {str(e)}'
        }), 500
```

---

## 🎨 Adicionar Botões nos Templates

### Opção 1: Botão Simples (download direto)

Adicione onde quiser exibir o botão (ex: página de empresa, dashboard):

```html
<!-- Botão de Download de Relatório -->
<a href="{{ url_for('relatorio_projetos_pdf', empresa_id=empresa.id) }}" 
   class="btn btn-primary" 
   target="_blank">
    <i class="fas fa-file-pdf"></i> Baixar Relatório de Projetos
</a>
```

---

### Opção 2: Botão com Loading (mais profissional)

```html
<!-- Botão com Loading -->
<button id="btnRelatorio" 
        class="btn btn-primary" 
        onclick="gerarRelatorio({{ empresa.id }})">
    <i class="fas fa-file-pdf"></i> 
    <span id="btnTexto">Gerar Relatório</span>
</button>

<script>
function gerarRelatorio(empresaId) {
    const btn = document.getElementById('btnRelatorio');
    const texto = document.getElementById('btnTexto');
    
    // Mostra loading
    btn.disabled = true;
    texto.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';
    
    // Chama API
    fetch(`/api/relatorio/projetos/${empresaId}/gerar`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Sucesso! Abre o relatório
            window.open(data.view_url, '_blank');
            
            // Feedback
            alert('Relatório gerado com sucesso!');
        } else {
            alert('Erro: ' + data.message);
        }
    })
    .catch(error => {
        alert('Erro ao gerar relatório: ' + error);
    })
    .finally(() => {
        // Restaura botão
        btn.disabled = false;
        texto.innerHTML = 'Gerar Relatório';
    });
}
</script>
```

---

### Opção 3: Menu Dropdown (múltiplas opções)

```html
<!-- Dropdown com opções -->
<div class="dropdown">
    <button class="btn btn-primary dropdown-toggle" 
            type="button" 
            id="dropdownRelatorios" 
            data-toggle="dropdown">
        <i class="fas fa-file-pdf"></i> Relatórios
    </button>
    <div class="dropdown-menu">
        <a class="dropdown-item" 
           href="{{ url_for('relatorio_projetos_visualizar', empresa_id=empresa.id) }}" 
           target="_blank">
            <i class="fas fa-eye"></i> Visualizar Relatório de Projetos
        </a>
        <a class="dropdown-item" 
           href="{{ url_for('relatorio_projetos_pdf', empresa_id=empresa.id) }}">
            <i class="fas fa-download"></i> Baixar Relatório de Projetos
        </a>
        <div class="dropdown-divider"></div>
        <a class="dropdown-item" href="#" onclick="alert('Em breve!')">
            <i class="fas fa-chart-line"></i> Relatório Financeiro
        </a>
        <a class="dropdown-item" href="#" onclick="alert('Em breve!')">
            <i class="fas fa-users"></i> Relatório de Equipe
        </a>
    </div>
</div>
```

---

## 📍 Onde Adicionar os Botões

### 1. Dashboard Principal
```html
<!-- Em templates/dashboard.html -->
<div class="card">
    <div class="card-header">
        <h3>Empresa: {{ empresa.nome }}</h3>
    </div>
    <div class="card-body">
        <p>CNPJ: {{ empresa.cnpj }}</p>
        
        <!-- ADICIONAR AQUI -->
        <a href="{{ url_for('relatorio_projetos_pdf', empresa_id=empresa.id) }}" 
           class="btn btn-primary mt-3" 
           target="_blank">
            <i class="fas fa-file-pdf"></i> Relatório de Projetos
        </a>
    </div>
</div>
```

### 2. Página de Projetos
```html
<!-- Em templates/projetos.html -->
<div class="page-header d-flex justify-content-between">
    <h1>Projetos da Empresa</h1>
    
    <!-- ADICIONAR AQUI -->
    <div>
        <a href="{{ url_for('relatorio_projetos_pdf', empresa_id=empresa_id) }}" 
           class="btn btn-primary">
            <i class="fas fa-file-pdf"></i> Exportar PDF
        </a>
    </div>
</div>
```

### 3. Card de Empresa
```html
<!-- Em qualquer lista de empresas -->
<div class="empresa-card">
    <h4>{{ empresa.nome }}</h4>
    <div class="actions">
        <a href="{{ url_for('ver_empresa', id=empresa.id) }}" 
           class="btn btn-sm btn-info">Ver</a>
           
        <!-- ADICIONAR AQUI -->
        <a href="{{ url_for('relatorio_projetos_pdf', empresa_id=empresa.id) }}" 
           class="btn btn-sm btn-primary" 
           target="_blank">
            <i class="fas fa-file-pdf"></i> Relatório
        </a>
    </div>
</div>
```

---

## 🔒 Adicionar Permissões (Opcional)

Se quiser controlar quem pode gerar relatórios:

```python
from functools import wraps
from flask_login import current_user

def requer_permissao_relatorios(f):
    """Decorator para verificar permissão"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Você precisa estar logado', 'error')
            return redirect(url_for('login'))
        
        # Verifica se tem permissão (exemplo)
        if not current_user.pode_gerar_relatorios:
            flash('Você não tem permissão para gerar relatórios', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


# Usa o decorator nas rotas
@app.route('/relatorio/projetos/<int:empresa_id>')
@requer_permissao_relatorios
def relatorio_projetos_pdf(empresa_id):
    # ... código da rota
```

---

## 🧪 Testar a Integração

### 1. Adicione o código ao `app_pev.py`
### 2. Reinicie o servidor Flask
```bash
python app_pev.py
```

### 3. Teste as URLs manualmente:
```
http://localhost:5000/relatorio/projetos/1
http://localhost:5000/relatorio/projetos/visualizar/1
```

### 4. Ou use o botão nos templates

---

## 📊 Próximas Melhorias

Você pode facilmente criar outros tipos de relatórios:

1. **Relatório Financeiro**
   - Receitas e despesas
   - Fluxo de caixa
   - Balanço

2. **Relatório de Equipe**
   - Colaboradores
   - Produtividade
   - Horas trabalhadas

3. **Dashboard Executivo**
   - KPIs principais
   - Metas vs Realizado
   - Tendências

4. **Relatório Personalizado**
   - Cliente escolhe o que incluir
   - Filtros por período
   - Comparativos

---

## 🆘 Solução de Problemas

### Erro: "Module 'gerador_relatorios' not found"
**Solução:** Verifique se o arquivo está em `modules/gerador_relatorios.py`

### Erro: "No library called 'cairo' was found"
**Solução Windows:** 
1. Baixe GTK3 Runtime: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
2. Instale e reinicie

### PDF não exibe gráficos
**Solução:** Instale kaleido: `pip install kaleido --upgrade`

### Relatório demora muito
**Solução:** 
- Limite número de projetos no gráfico timeline (já está limitado a 15)
- Aumente qualidade dos gráficos apenas se necessário
- Use cache para relatórios frequentes

---

## ✅ Checklist de Integração

- [ ] Código adicionado ao `app_pev.py`
- [ ] Botões adicionados aos templates
- [ ] Servidor Flask reiniciado
- [ ] Testado com empresa real
- [ ] PDF gerado com sucesso
- [ ] Gráficos aparecem corretamente
- [ ] Download funciona
- [ ] Visualização funciona

---

**Pronto! Seu sistema agora gera relatórios profissionais! 🎉**


