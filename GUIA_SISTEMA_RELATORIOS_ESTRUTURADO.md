# 📊 Sistema de Relatórios Estruturado - Guia Completo

## 🎯 O que foi implementado

Criei exatamente o sistema que você pediu! Agora você tem:

### **a) Configurações de Página (Model_7, etc)**
- ✅ **Model 7** - Relatórios Executivos (ID: 12)
- ✅ **Model 8** - Relatórios Técnicos (ID: 13)
- ✅ Margens, cabeçalho e rodapé configuráveis
- ✅ Suporte a markdown e variáveis dinâmicas

### **b) Templates de Relatório Específicos**
- ✅ **Template de Reuniões Completo** (ID: 3)
- ✅ **Template de Reuniões Resumido** (ID: 4)
- ✅ Seções configuráveis (Resumo, Lista, Análise, Conclusões)

### **c) Sistema de Combinação**
- ✅ Pega configuração de página + template de relatório
- ✅ Gera relatório específico automaticamente
- ✅ Interface web para gerenciamento

---

## 🚀 Como Usar o Sistema

### **1. Acessar o Gerenciador de Templates**
```
http://127.0.0.1:5002/report-templates
```

### **2. Criar um Novo Relatório**

**Exemplo:** "Pegue a página Model 7 e o modelo do relatório de reuniões para estruturar este novo relatório"

**Passos:**
1. Acesse `/report-templates`
2. Clique em "Criar Template"
3. Selecione:
   - **Nome:** "Relatório de Reuniões - Janeiro 2024"
   - **Tipo:** "Reuniões"
   - **Configuração de Página:** "Model 7 - Relatórios Executivos"
   - **Seções:** Marque as seções desejadas
4. Clique "Criar Template"

### **3. Gerar Relatório**
1. Vá para aba "Gerar Relatório"
2. Selecione o template criado
3. Digite o título do relatório
4. Clique "Gerar Relatório"
5. O relatório será aberto em nova aba

---

## 📋 Estrutura do Sistema

### **Configurações de Página (report_models)**
```sql
- id, name, description
- paper_size, orientation
- margin_top, margin_right, margin_bottom, margin_left
- header_height, header_rows, header_columns, header_content
- footer_height, footer_rows, footer_columns, footer_content
```

### **Templates de Relatório (report_templates)**
```sql
- id, name, description
- page_config_id (referência à configuração de página)
- report_type (meetings, processes, projects, general)
- sections_config (JSON com seções configuradas)
```

### **Exemplo de sections_config:**
```json
{
  "summary": {
    "enabled": true,
    "title": "Resumo Executivo"
  },
  "meetings_list": {
    "enabled": true,
    "title": "Lista de Reuniões"
  },
  "participants_analysis": {
    "enabled": true,
    "title": "Análise de Participantes"
  },
  "conclusions": {
    "enabled": true,
    "title": "Conclusões e Recomendações"
  }
}
```

---

## 🎨 Variáveis Disponíveis

### **No Cabeçalho/Rodapé:**
- `{{ company.name }}` - Nome da empresa
- `{{ report.title }}` - Título do relatório
- `{{ date }}` - Data atual
- `{{ year }}` - Ano atual
- `{{ page }}` - Número da página
- `{{ pages }}` - Total de páginas

### **Exemplo de cabeçalho:**
```markdown
## {{ company.name }}
**{{ report.title }}**
Data: {{ date }} | Sistema PEVAPP22
```

---

## 🔧 APIs Disponíveis

### **Templates:**
- `GET /api/report-templates` - Lista todos os templates
- `POST /api/report-templates` - Cria novo template
- `GET /api/report-templates/<id>` - Busca template específico
- `PUT /api/report-templates/<id>` - Atualiza template
- `DELETE /api/report-templates/<id>` - Exclui template

### **Geração:**
- `POST /api/report-templates/<id>/generate` - Gera relatório

### **Configurações de Página:**
- `GET /api/reports/models` - Lista configurações
- `POST /api/reports/models` - Cria configuração
- `GET /api/reports/models/<id>` - Busca configuração

---

## 📝 Exemplo de Uso Programático

```python
from modules.report_templates import ReportTemplateGenerator

# Gerar relatório usando template específico
generator = ReportTemplateGenerator()

data_context = {
    'company_name': 'Minha Empresa',
    'report_title': 'Relatório de Reuniões - Janeiro 2024',
    'period_start': '01/01/2024',
    'period_end': '31/01/2024',
    'total_meetings': 15,
    'unique_participants': 25,
    'participation_rate': 85,
    'meetings': [
        {
            'title': 'Reunião de Planejamento',
            'date': '05/01/2024',
            'time': '09:00 - 10:30',
            'location': 'Sala A',
            'organizer': 'João Silva',
            'participants': ['João', 'Maria', 'Pedro']
        }
    ]
}

result = generator.generate_report_from_template(
    template_id=3,  # Template de Reuniões Completo
    data_context=data_context
)

# Salvar HTML gerado
with open('meu_relatorio.html', 'w', encoding='utf-8') as f:
    f.write(result['html'])
```

---

## 🎯 Próximos Passos

### **Para criar novos tipos de relatório:**

1. **Criar configuração de página:**
   - Acesse `/settings/reports`
   - Configure margens, cabeçalho, rodapé
   - Salve com nome específico

2. **Criar template específico:**
   - Acesse `/report-templates`
   - Selecione a configuração de página
   - Configure as seções específicas do tipo de relatório

3. **Implementar gerador específico:**
   - Adicione método `_generate_[tipo]_report()` em `ReportTemplateGenerator`
   - Crie template HTML específico
   - Configure seções dinâmicas

### **Exemplo para Relatório de Processos:**
```python
def _generate_processes_report(self, template, page_config, data_context):
    # Template HTML específico para processos
    # Seções: Resumo, Lista de Processos, Análise de Eficiência, Conclusões
    pass
```

---

## ✅ Sistema Pronto!

O sistema está funcionando perfeitamente! Você pode:

1. **Usar as configurações existentes** (Model 7, Model 8)
2. **Usar os templates existentes** (Reuniões Completo/Resumido)
3. **Criar novos templates** facilmente pela interface
4. **Gerar relatórios** com um clique
5. **Expandir** para outros tipos de relatório

**Teste agora:** Acesse `http://127.0.0.1:5002/report-templates` e crie seu primeiro relatório personalizado!
