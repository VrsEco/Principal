# 🤖 Plano de Refatoração Completa: Módulo PEV com Agentes IA

**Data:** 15/02/2026  
**Objetivo:** Refatorar completamente o módulo de Planejamento Estratégico (PEV) do APP31 para APP32 usando agentes IA para análise e reconstrução.

---

## 📊 Análise da Situação Atual

### APP31 - Estrutura Existente

#### Arquivos Principais
- **`app_pev.py`** (547KB, 15.107 linhas) - Aplicação monolítica
- **`modules/pev/__init__.py`** (115KB) - Módulo PEV
- **`modules/pev/implantation_data.py`** (138KB) - Dados de implantação
- **`modules/pev/products_service.py`** (29KB) - Serviço de produtos
- **`modules/pev/financial_metrics.py`** (8KB) - Métricas financeiras

#### Tipos de Planejamento Identificados
1. **Crescimento (Clássico)** - Planejamento para empresas em operação
2. **Implantação (Novo Negócio)** - Planejamento para novos negócios

### APP32 - Estrutura Atual

#### Arquivos Principais
- **`api/routes/pev.py`** (180KB, 5.015 linhas) - Rotas PEV
- **`templates/modules/pev/`** - Templates do módulo
- **Agentes IA** - Estrutura de orquestração já implementada

#### Problemas Relatados
- "Muitos erros" na implementação atual
- Necessidade de reconstrução completa
- Falta de clareza entre os dois tipos de planejamento

---

## 🎯 Objetivos da Refatoração

### 1. **Análise Completa com Agentes IA**
- Usar agentes para analisar o código do APP31
- Identificar padrões, funcionalidades e lógica de negócio
- Mapear diferenças entre Crescimento e Implantação
- Gerar documentação automática

### 2. **Reconstrução Modular**
- Separar claramente os dois tipos de planejamento
- Criar arquitetura limpa e escalável
- Implementar padrões modernos
- Integrar com agentes IA desde o início

### 3. **Funcionalidades Preservadas**
- Todas as funcionalidades do APP31
- Melhorias de UX/UI
- Performance otimizada
- Código limpo e manutenível

---

## 🏗️ Arquitetura Proposta

### Estrutura de Diretórios

```
app32/
├── agents/
│   ├── pev/
│   │   ├── __init__.py
│   │   ├── analyzer_agent.py       # Agente para análise de planos
│   │   ├── growth_agent.py         # Especialista em crescimento
│   │   ├── implantation_agent.py   # Especialista em implantação
│   │   └── tools/
│   │       ├── plan_tools.py       # Ferramentas de plano
│   │       ├── okr_tools.py        # Ferramentas de OKR
│   │       └── market_tools.py     # Ferramentas de mercado
│   └── graph.py                    # Orquestração (atualizar)
│
├── api/routes/
│   └── pev/
│       ├── __init__.py
│       ├── common.py               # Rotas comuns
│       ├── growth.py               # Rotas de crescimento
│       ├── implantation.py         # Rotas de implantação
│       └── ai_endpoints.py         # Endpoints de IA
│
├── services/pev/
│   ├── __init__.py
│   ├── base_service.py             # Serviço base
│   ├── growth_service.py           # Lógica de crescimento
│   ├── implantation_service.py     # Lógica de implantação
│   ├── okr_service.py              # Serviço de OKRs
│   ├── drivers_service.py          # Serviço de direcionadores
│   └── financial_service.py        # Serviço financeiro
│
├── models/pev/
│   ├── __init__.py
│   ├── plan.py                     # Modelo de plano (já existe)
│   ├── driver_topic.py             # Direcionadores (já existe)
│   ├── okr.py                      # OKRs
│   ├── participant.py              # Participantes
│   └── financial_model.py          # Modelo financeiro
│
└── templates/modules/pev/
    ├── common/                     # Templates comuns
    │   ├── dashboard.html
    │   ├── participants.html
    │   └── ai_assistant.html
    ├── growth/                     # Templates de crescimento
    │   ├── drivers.html
    │   ├── okr_global.html
    │   └── okr_area.html
    └── implantation/               # Templates de implantação
        ├── alignment.html
        ├── products.html
        └── financial_model.html
```

---

## 🤖 Estratégia de Uso dos Agentes IA

### FASE 1: Análise Automatizada do APP31

#### Agente Analisador de Código
**Objetivo:** Analisar o código do APP31 e extrair conhecimento

**Tarefas:**
1. **Análise de Funcionalidades**
   - Ler `app_pev.py` e `modules/pev/__init__.py`
   - Identificar todas as rotas e endpoints
   - Mapear fluxos de dados
   - Documentar lógica de negócio

2. **Diferenciação de Tipos**
   - Identificar código específico de "Crescimento"
   - Identificar código específico de "Implantação"
   - Mapear código compartilhado
   - Criar matriz de funcionalidades

3. **Extração de Regras de Negócio**
   - Validações
   - Cálculos
   - Fluxos de aprovação
   - Integrações

**Implementação:**
```python
# agents/pev/analyzer_agent.py
from langchain_core.messages import SystemMessage, HumanMessage
from src.intelligence.llm import model_with_tools
from langchain_core.tools import tool

@tool
def read_app31_file(file_path: str):
    """Lê um arquivo do APP31 para análise."""
    with open(f"c:/GestaoVersus/app31/{file_path}", 'r', encoding='utf-8') as f:
        return f.read()

@tool
def extract_routes(code: str):
    """Extrai rotas Flask de um código Python."""
    import re
    routes = re.findall(r'@\w+\.route\(["\']([^"\']+)["\']', code)
    return routes

class CodeAnalyzerAgent:
    def __init__(self):
        self.system_prompt = """
        Você é um Agente Especialista em Análise de Código Python/Flask.
        
        Sua missão é analisar o código do APP31 (PEV) e:
        1. Identificar TODAS as funcionalidades
        2. Separar código de "Crescimento" vs "Implantação"
        3. Extrair regras de negócio
        4. Mapear fluxos de dados
        5. Documentar padrões e anti-padrões
        
        Seja METICULOSO e COMPLETO. Não pule nenhum detalhe.
        """
    
    def analyze_file(self, file_path: str):
        """Analisa um arquivo do APP31."""
        code = read_app31_file(file_path)
        
        response = model_with_tools.invoke([
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""
            Analise este arquivo do APP31:
            
            Arquivo: {file_path}
            
            Código:
            ```python
            {code[:10000]}  # Primeiros 10k caracteres
            ```
            
            Forneça:
            1. Resumo das funcionalidades
            2. Rotas identificadas
            3. Modelos de dados usados
            4. Regras de negócio encontradas
            5. Dependências externas
            """)
        ])
        
        return response.content
    
    def differentiate_plan_types(self):
        """Identifica diferenças entre Crescimento e Implantação."""
        # Implementar análise comparativa
        pass
```

**Saída Esperada:**
- `docs/pev_analysis/app31_full_analysis.md` - Análise completa
- `docs/pev_analysis/growth_features.md` - Funcionalidades de crescimento
- `docs/pev_analysis/implantation_features.md` - Funcionalidades de implantação
- `docs/pev_analysis/shared_features.md` - Funcionalidades compartilhadas
- `docs/pev_analysis/business_rules.md` - Regras de negócio
- `docs/pev_analysis/data_models.md` - Modelos de dados

---

### FASE 2: Geração de Especificações

#### Agente Arquiteto
**Objetivo:** Criar especificações técnicas para o APP32

**Tarefas:**
1. **Design de Arquitetura**
   - Propor estrutura modular
   - Definir separação de responsabilidades
   - Especificar APIs
   - Planejar banco de dados

2. **Especificações de Funcionalidades**
   - Para cada funcionalidade do APP31
   - Criar especificação detalhada para APP32
   - Incluir melhorias e modernizações

**Implementação:**
```python
# agents/pev/architect_agent.py
class ArchitectAgent:
    def __init__(self):
        self.system_prompt = """
        Você é um Arquiteto de Software Sênior especializado em Flask/Python.
        
        Sua missão é:
        1. Analisar as funcionalidades do APP31
        2. Propor arquitetura moderna para APP32
        3. Criar especificações técnicas detalhadas
        4. Garantir escalabilidade e manutenibilidade
        
        Princípios:
        - Clean Architecture
        - SOLID
        - DRY
        - Separation of Concerns
        """
    
    def design_module_structure(self, analysis_data):
        """Propõe estrutura de módulos."""
        pass
    
    def create_api_specs(self, features):
        """Cria especificações de API."""
        pass
```

**Saída Esperada:**
- `docs/pev_specs/architecture.md` - Arquitetura geral
- `docs/pev_specs/api_specification.md` - Especificação de APIs
- `docs/pev_specs/database_schema.md` - Schema do banco
- `docs/pev_specs/growth_module_spec.md` - Spec do módulo Crescimento
- `docs/pev_specs/implantation_module_spec.md` - Spec do módulo Implantação

---

### FASE 3: Geração de Código

#### Agente Desenvolvedor
**Objetivo:** Gerar código do APP32 baseado nas especificações

**Tarefas:**
1. **Geração de Modelos**
   - Criar/atualizar modelos SQLAlchemy
   - Gerar migrations

2. **Geração de Serviços**
   - Implementar lógica de negócio
   - Criar serviços reutilizáveis

3. **Geração de APIs**
   - Implementar rotas Flask
   - Criar endpoints RESTful

4. **Geração de Templates**
   - Criar templates HTML modernos
   - Implementar componentes reutilizáveis

**Implementação:**
```python
# agents/pev/developer_agent.py
class DeveloperAgent:
    def __init__(self):
        self.system_prompt = """
        Você é um Desenvolvedor Python/Flask Expert.
        
        Sua missão é:
        1. Gerar código limpo e manutenível
        2. Seguir as especificações rigorosamente
        3. Implementar testes unitários
        4. Documentar o código
        
        Padrões:
        - PEP 8
        - Type hints
        - Docstrings
        - Error handling
        """
    
    def generate_model(self, spec):
        """Gera modelo SQLAlchemy."""
        pass
    
    def generate_service(self, spec):
        """Gera serviço de negócio."""
        pass
    
    def generate_route(self, spec):
        """Gera rota Flask."""
        pass
```

---

### FASE 4: Testes e Validação

#### Agente Testador
**Objetivo:** Validar o código gerado

**Tarefas:**
1. **Testes Unitários**
   - Gerar testes para cada função
   - Validar regras de negócio

2. **Testes de Integração**
   - Testar fluxos completos
   - Validar APIs

3. **Comparação com APP31**
   - Verificar paridade de funcionalidades
   - Identificar gaps

---

## 📋 Plano de Execução Detalhado

### Semana 1: Análise e Documentação

#### Dia 1-2: Análise Automatizada
```bash
# Executar agente analisador
python scripts/analyze_app31_pev.py

# Saída:
# - docs/pev_analysis/*.md
```

**Tarefas do Agente:**
1. Ler todos os arquivos do módulo PEV do APP31
2. Identificar rotas, modelos, serviços
3. Separar funcionalidades por tipo (Crescimento/Implantação)
4. Extrair regras de negócio
5. Gerar documentação completa

#### Dia 3-4: Especificações Técnicas
```bash
# Executar agente arquiteto
python scripts/generate_pev_specs.py

# Saída:
# - docs/pev_specs/*.md
```

**Tarefas do Agente:**
1. Analisar documentação gerada
2. Propor arquitetura modular
3. Criar especificações de API
4. Definir schema de banco de dados
5. Planejar estrutura de templates

#### Dia 5: Revisão e Ajustes
- Revisar documentação gerada
- Ajustar especificações conforme necessário
- Validar com stakeholders

---

### Semana 2-3: Implementação Base

#### Módulo Comum (Base)
**Prioridade:** Alta  
**Tempo Estimado:** 3 dias

**Componentes:**
1. **Modelos Base**
   - `Plan` (atualizar)
   - `Participant`
   - `SectionStatus`

2. **Serviços Base**
   - `BasePEVService`
   - `ParticipantService`
   - `SectionService`

3. **Rotas Comuns**
   - `/pev/dashboard`
   - `/pev/plans/<id>`
   - `/pev/plans/<id>/participants`

4. **Templates Comuns**
   - `dashboard.html`
   - `plan_selector.html`
   - `participants.html`

**Geração com Agente:**
```bash
python scripts/generate_pev_common.py
```

---

#### Módulo Crescimento (Clássico)
**Prioridade:** Alta  
**Tempo Estimado:** 5 dias

**Componentes:**
1. **Modelos**
   - `DriverTopic` (já existe)
   - `OKRGlobal`
   - `OKRArea`
   - `Interview`
   - `VisionRecord`
   - `MarketRecord`
   - `CompanyRecord`

2. **Serviços**
   - `DriversService`
   - `OKRService`
   - `InterviewService`

3. **Rotas**
   - `/pev/plans/<id>/drivers`
   - `/pev/plans/<id>/okr-global`
   - `/pev/plans/<id>/okr-area`
   - `/pev/plans/<id>/projects`
   - `/pev/plans/<id>/reports`

4. **Templates**
   - `plan_drivers.html`
   - `plan_okr_global.html`
   - `plan_okr_area.html`
   - `plan_projects.html`
   - `plan_reports.html`

**Geração com Agente:**
```bash
python scripts/generate_pev_growth.py
```

---

#### Módulo Implantação (Novo Negócio)
**Prioridade:** Média  
**Tempo Estimado:** 5 dias

**Componentes:**
1. **Modelos**
   - `AlignmentData`
   - `Product`
   - `Segment`
   - `Structure`
   - `FinancialModel`
   - `Investment`

2. **Serviços**
   - `AlignmentService`
   - `ProductService`
   - `FinancialService`
   - `InvestmentService`

3. **Rotas**
   - `/pev/plans/<id>/alignment`
   - `/pev/plans/<id>/products`
   - `/pev/plans/<id>/segments`
   - `/pev/plans/<id>/structures`
   - `/pev/plans/<id>/financial-model`
   - `/pev/plans/<id>/implantation-reports`

4. **Templates**
   - `alignment_canvas.html`
   - `products_model.html`
   - `segments_manager.html`
   - `structures_manager.html`
   - `financial_model.html`

**Geração com Agente:**
```bash
python scripts/generate_pev_implantation.py
```

---

### Semana 4: Integração com Agentes IA

#### Agentes PEV Especializados

**1. Agente Analisador de Planos**
```python
# agents/pev/plan_analyzer.py
class PlanAnalyzerAgent:
    """Analisa planos estratégicos e fornece insights."""
    
    def analyze_plan_maturity(self, plan_id):
        """Analisa maturidade do plano."""
        pass
    
    def validate_okrs(self, okrs):
        """Valida qualidade dos OKRs."""
        pass
    
    def suggest_improvements(self, plan_data):
        """Sugere melhorias para o plano."""
        pass
```

**2. Agente de Crescimento**
```python
# agents/pev/growth_agent.py
class GrowthAgent:
    """Especialista em planejamento de crescimento."""
    
    def analyze_market(self, industry, region):
        """Analisa mercado e tendências."""
        pass
    
    def suggest_drivers(self, company_data):
        """Sugere direcionadores estratégicos."""
        pass
    
    def validate_strategy(self, plan_data):
        """Valida coerência da estratégia."""
        pass
```

**3. Agente de Implantação**
```python
# agents/pev/implantation_agent.py
class ImplantationAgent:
    """Especialista em novos negócios."""
    
    def analyze_viability(self, business_model):
        """Analisa viabilidade do negócio."""
        pass
    
    def calculate_metrics(self, financial_data):
        """Calcula métricas financeiras."""
        pass
    
    def suggest_products(self, market_data):
        """Sugere produtos/serviços."""
        pass
```

**Integração no Graph:**
```python
# agents/graph.py (atualizar)
from agents.pev.plan_analyzer import plan_analyzer_node
from agents.pev.growth_agent import growth_agent_node
from agents.pev.implantation_agent import implantation_agent_node

# Adicionar nós
workflow.add_node("PEV_ANALYZER", plan_analyzer_node)
workflow.add_node("GROWTH", growth_agent_node)
workflow.add_node("IMPLANTATION", implantation_agent_node)

# Adicionar rotas
workflow.add_edge("PEV_ANALYZER", "supervisor")
workflow.add_edge("GROWTH", "supervisor")
workflow.add_edge("IMPLANTATION", "supervisor")
```

---

### Semana 5: Testes e Refinamento

#### Testes Automatizados
```bash
# Executar suite de testes
pytest tests/pev/ -v --cov=api/routes/pev --cov=services/pev

# Testes de integração
pytest tests/integration/pev/ -v

# Testes E2E
pytest tests/e2e/pev/ -v
```

#### Validação de Paridade
```bash
# Comparar funcionalidades APP31 vs APP32
python scripts/validate_pev_parity.py

# Saída:
# - Funcionalidades implementadas: 95%
# - Funcionalidades faltantes: 5%
# - Melhorias adicionadas: 15
```

---

## 🛠️ Scripts de Automação

### Script 1: Analisador do APP31
```python
# scripts/analyze_app31_pev.py
"""
Analisa o módulo PEV do APP31 usando agentes IA.
"""
import os
from agents.pev.analyzer_agent import CodeAnalyzerAgent

def main():
    analyzer = CodeAnalyzerAgent()
    
    # Arquivos para analisar
    files = [
        "app_pev.py",
        "modules/pev/__init__.py",
        "modules/pev/implantation_data.py",
        "modules/pev/products_service.py",
        "modules/pev/financial_metrics.py"
    ]
    
    results = {}
    for file_path in files:
        print(f"Analisando {file_path}...")
        analysis = analyzer.analyze_file(file_path)
        results[file_path] = analysis
        
        # Salvar resultado
        output_path = f"docs/pev_analysis/{file_path.replace('/', '_')}.md"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(analysis)
    
    # Análise comparativa
    print("Diferenciando tipos de planejamento...")
    differentiation = analyzer.differentiate_plan_types()
    
    with open("docs/pev_analysis/plan_types_comparison.md", 'w') as f:
        f.write(differentiation)
    
    print("✅ Análise completa!")

if __name__ == "__main__":
    main()
```

### Script 2: Gerador de Especificações
```python
# scripts/generate_pev_specs.py
"""
Gera especificações técnicas para o APP32.
"""
from agents.pev.architect_agent import ArchitectAgent

def main():
    architect = ArchitectAgent()
    
    # Ler análises
    analysis_files = [
        "docs/pev_analysis/app_pev.py.md",
        "docs/pev_analysis/modules_pev___init__.py.md",
        # ... outros
    ]
    
    analysis_data = {}
    for file_path in analysis_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            analysis_data[file_path] = f.read()
    
    # Gerar especificações
    print("Gerando arquitetura...")
    architecture = architect.design_module_structure(analysis_data)
    
    print("Gerando especificações de API...")
    api_specs = architect.create_api_specs(analysis_data)
    
    print("Gerando schema de banco...")
    db_schema = architect.create_database_schema(analysis_data)
    
    # Salvar
    with open("docs/pev_specs/architecture.md", 'w') as f:
        f.write(architecture)
    
    with open("docs/pev_specs/api_specification.md", 'w') as f:
        f.write(api_specs)
    
    with open("docs/pev_specs/database_schema.md", 'w') as f:
        f.write(db_schema)
    
    print("✅ Especificações geradas!")

if __name__ == "__main__":
    main()
```

### Script 3: Gerador de Código
```python
# scripts/generate_pev_code.py
"""
Gera código do APP32 baseado nas especificações.
"""
from agents.pev.developer_agent import DeveloperAgent

def main():
    developer = DeveloperAgent()
    
    # Ler especificações
    with open("docs/pev_specs/architecture.md", 'r') as f:
        architecture = f.read()
    
    with open("docs/pev_specs/api_specification.md", 'r') as f:
        api_specs = f.read()
    
    # Gerar código
    print("Gerando modelos...")
    models = developer.generate_models(architecture)
    
    print("Gerando serviços...")
    services = developer.generate_services(api_specs)
    
    print("Gerando rotas...")
    routes = developer.generate_routes(api_specs)
    
    print("Gerando templates...")
    templates = developer.generate_templates(architecture)
    
    # Salvar arquivos
    # ... (implementar salvamento)
    
    print("✅ Código gerado!")

if __name__ == "__main__":
    main()
```

---

## 📊 Métricas de Sucesso

### Critérios de Aceitação

1. **Paridade Funcional**
   - ✅ 100% das funcionalidades do APP31 implementadas
   - ✅ Ambos os tipos de planejamento funcionando
   - ✅ Todos os fluxos testados

2. **Qualidade de Código**
   - ✅ Cobertura de testes > 80%
   - ✅ Sem code smells críticos
   - ✅ Documentação completa

3. **Performance**
   - ✅ Tempo de resposta < 2s
   - ✅ Queries otimizadas
   - ✅ Caching implementado

4. **UX/UI**
   - ✅ Interface moderna e responsiva
   - ✅ Feedback visual adequado
   - ✅ Acessibilidade (WCAG 2.1)

---

## 🚀 Próximos Passos Imediatos

### Passo 1: Configurar Ambiente
```bash
# Criar diretórios
mkdir -p docs/pev_analysis
mkdir -p docs/pev_specs
mkdir -p scripts
mkdir -p agents/pev/tools

# Instalar dependências
pip install langchain langchain-openai chromadb
```

### Passo 2: Executar Análise
```bash
# Executar análise do APP31
python scripts/analyze_app31_pev.py
```

### Passo 3: Revisar Análise
- Ler documentos gerados em `docs/pev_analysis/`
- Validar identificação de funcionalidades
- Confirmar separação Crescimento vs Implantação

### Passo 4: Gerar Especificações
```bash
# Gerar specs técnicas
python scripts/generate_pev_specs.py
```

### Passo 5: Revisar e Aprovar
- Revisar especificações em `docs/pev_specs/`
- Ajustar conforme necessário
- Aprovar para implementação

### Passo 6: Implementação Gradual
```bash
# Gerar código módulo por módulo
python scripts/generate_pev_common.py
python scripts/generate_pev_growth.py
python scripts/generate_pev_implantation.py
```

---

## ❓ Perguntas para o Usuário

Antes de começar, preciso confirmar:

1. **Prioridade:** Qual módulo devemos implementar primeiro?
   - [ ] Comum (Base)
   - [ ] Crescimento (Clássico)
   - [ ] Implantação (Novo Negócio)

2. **Escopo:** Devemos migrar 100% das funcionalidades ou focar nas principais?
   - [ ] 100% (completo)
   - [ ] 80% (principais)
   - [ ] MVP (mínimo viável)

3. **Abordagem:** Prefere:
   - [ ] Análise automática completa primeiro
   - [ ] Implementação incremental com validação
   - [ ] Protótipo rápido de uma funcionalidade

4. **Dados:** Precisa migrar dados existentes do APP31?
   - [ ] Sim, migração completa
   - [ ] Não, começar do zero
   - [ ] Apenas dados de teste

---

## 📚 Documentação Gerada

Ao final do processo, teremos:

1. **Análise Completa**
   - `docs/pev_analysis/` - Análise do APP31
   
2. **Especificações Técnicas**
   - `docs/pev_specs/` - Specs do APP32
   
3. **Código Fonte**
   - `api/routes/pev/` - Rotas
   - `services/pev/` - Serviços
   - `models/pev/` - Modelos
   - `templates/modules/pev/` - Templates
   
4. **Testes**
   - `tests/pev/` - Testes unitários
   - `tests/integration/pev/` - Testes de integração
   
5. **Documentação de Usuário**
   - `docs/user_guide/pev/` - Guia do usuário

---

**Pronto para começar?** 🚀
