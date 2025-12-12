# 📋 Análise de Viabilidade: Agente de Cadastro

**Data:** 18/12/2025  
**Versão:** 1.0  
**Status:** 📊 Análise Técnica

---

## 🎯 Objetivo da Funcionalidade

O **Agente de Cadastro** visa:

1. **Cadastro Assistido de Empresas:**
   - Fazer cadastro de empresas exemplo (para demonstração)
   - Fazer cadastro de empresas reais
   - Solicitar ao usuário os dados necessários de forma guiada
   - Garantir que o cadastro seja completo e correto

2. **Análise de Completude:**
   - Ler o cadastro existente de uma empresa
   - Identificar o que está faltando
   - Explicar o impacto da falta desses dados no funcionamento do sistema

---

## ✅ Viabilidade Técnica: **ALTA**

### 1. Infraestrutura Existente

#### ✅ Modelos de Dados
- **`Company`** (`models/company.py`): Modelo principal de empresa
  - Campos: `name`, `legal_name`, `cnpj`, `segment`, `city`, `state`, `coverage_physical`, `coverage_online`, `experience_total`, `experience_segment`, `mission`, `vision`, `values`
  - Relacionamentos: `plans` (1:N)
  
- **`CompanyData`** (`models/company_data.py`): Dados específicos por plano
  - Campos adicionais: `trade_name`, `cnaes`, `headcount_*`, `process_map_file`, `org_chart_file`, `ai_insights`, `consultant_analysis`
  - Relacionamento: `plan_id` (FK para `plans`)

#### ✅ API REST Existente
- `POST /api/companies` - Criar empresa
- `GET /api/companies/<id>` - Obter perfil
- `POST /api/companies/<id>` - Atualizar perfil
- `POST /api/companies/<id>/mvv` - Atualizar MVV
- `POST /api/companies/<id>/economic` - Atualizar dados econômicos

#### ✅ Sistema de Agentes IA
- Documentação em `docs/SISTEMA_AGENTES_IA.md`
- Já existe proposta de "Agente Cadastro & Configuração" (linha 1092-1167)
- Arquitetura baseada em Google Cloud Vertex AI + Gemini

#### ✅ Stack Tecnológica Compatível
- ✅ Python 3.9+ + Flask 2.3.3
- ✅ SQLAlchemy 2.0.21
- ✅ PostgreSQL/SQLite (compatibilidade garantida)
- ✅ Estrutura modular com Blueprints

---

## 🏗️ Arquitetura Proposta

### Componentes Necessários

```
agents/
├── cadastro_agent.py          # Agente principal de cadastro
├── cadastro_validator.py      # Validação de completude
└── cadastro_impact_analyzer.py # Análise de impacto

services/
└── company_registration_service.py  # Serviço de cadastro guiado

api/
└── cadastro_agent_api.py      # Endpoints REST do agente
```

### Fluxo de Funcionamento

#### 1. Cadastro Assistido

```
┌─────────────────────────────────────────────────────────┐
│  USUÁRIO: "Quero cadastrar uma empresa exemplo"        │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Identifica tipo (exemplo/real)                  │
│  AGENTE: Inicia questionário guiado                      │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Solicita dados obrigatórios primeiro:           │
│  - Nome fantasia (obrigatório)                          │
│  - Código do cliente (obrigatório, 1-3 chars)           │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Solicita dados recomendados:                   │
│  - Razão social                                         │
│  - CNPJ                                                 │
│  - Segmento/Indústria                                   │
│  - Cidade/Estado                                        │
│  - Cobertura (física/online)                            │
│  - Experiência (total/segmento)                         │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Solicita dados opcionais (MVV):                │
│  - Missão                                               │
│  - Visão                                                │
│  - Valores                                              │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Valida completude                             │
│  AGENTE: Cria empresa via API /api/companies            │
│  AGENTE: Retorna confirmação + próximos passos          │
└─────────────────────────────────────────────────────────┘
```

#### 2. Análise de Completude

```
┌─────────────────────────────────────────────────────────┐
│  USUÁRIO: "Analise o cadastro da empresa X"            │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Busca dados da empresa (Company + CompanyData) │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Valida campos obrigatórios                     │
│  AGENTE: Identifica campos faltantes                    │
│  AGENTE: Classifica por criticidade                     │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Analisa impacto de cada campo faltante:        │
│  - Impacto no PEV (Planejamento Estratégico)            │
│  - Impacto no GRV (Gestão de Resultados)                │
│  - Impacto em relatórios                                │
│  - Impacto em funcionalidades específicas               │
└─────────────────────────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  AGENTE: Gera relatório estruturado:                    │
│  - Checklist de completude                              │
│  - Campos faltantes por prioridade                      │
│  - Impacto de cada campo                                │
│  - Recomendações de preenchimento                       │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Análise de Dados

### Campos Obrigatórios (Company)

| Campo | Obrigatório | Impacto se Faltar |
|-------|-------------|-------------------|
| `name` | ✅ Sim | **CRÍTICO** - Empresa não pode ser criada |
| `client_code` | ✅ Sim | **CRÍTICO** - Empresa não pode ser criada |

### Campos Recomendados (Company)

| Campo | Recomendado | Impacto se Faltar |
|-------|-------------|-------------------|
| `legal_name` | ⚠️ Alto | **ALTO** - Relatórios formais incompletos, problemas legais |
| `cnpj` | ⚠️ Alto | **ALTO** - Validação fiscal, relatórios contábeis |
| `segment` | ⚠️ Médio | **MÉDIO** - Análises de mercado, benchmarking |
| `city` / `state` | ⚠️ Médio | **MÉDIO** - Análises regionais, relatórios geográficos |
| `coverage_physical` | ⚠️ Baixo | **BAIXO** - Análises de mercado, mas não crítico |
| `coverage_online` | ⚠️ Baixo | **BAIXO** - Análises de mercado, mas não crítico |
| `experience_total` | ⚠️ Baixo | **BAIXO** - Contexto histórico, mas não crítico |
| `experience_segment` | ⚠️ Baixo | **BAIXO** - Contexto histórico, mas não crítico |

### Campos Opcionais (Company - MVV)

| Campo | Opcional | Impacto se Faltar |
|-------|----------|-------------------|
| `mission` | ✅ Sim | **MÉDIO** - PEV incompleto, falta direcionamento estratégico |
| `vision` | ✅ Sim | **MÉDIO** - PEV incompleto, falta visão de futuro |
| `values` | ✅ Sim | **BAIXO** - PEV incompleto, mas não bloqueia funcionalidades |

### Campos Específicos (CompanyData - por Plano)

| Campo | Recomendado | Impacto se Faltar |
|-------|-------------|-------------------|
| `trade_name` | ⚠️ Médio | **MÉDIO** - Pode usar `name` da Company como fallback |
| `cnaes` | ⚠️ Médio | **MÉDIO** - Análises setoriais, mas não crítico |
| `headcount_*` | ⚠️ Alto | **ALTO** - Análises de força de trabalho, cálculos de produtividade |
| `process_map_file` | ⚠️ Baixo | **BAIXO** - Documentação, mas não bloqueia |
| `org_chart_file` | ⚠️ Baixo | **BAIXO** - Documentação, mas não bloqueia |

---

## 🔧 Implementação Técnica

### 1. Classe Base do Agente

```python
# agents/cadastro_agent.py
from agents.base_agent import BaseAgent
from models import Company, CompanyData, Plan
from services.company_registration_service import CompanyRegistrationService

class CadastroAgent(BaseAgent):
    """Agente de Cadastro e Análise de Completude"""
    
    def __init__(self):
        super().__init__(agent_id="cadastro_agent")
        self.registration_service = CompanyRegistrationService()
        self.temperature = 0.3  # Mais factual, menos criativo
    
    def cadastrar_empresa(self, tipo="real", dados_iniciais=None):
        """
        Inicia processo de cadastro guiado de empresa.
        
        Args:
            tipo: "exemplo" ou "real"
            dados_iniciais: Dict com dados já conhecidos (opcional)
        """
        # 1. Identificar campos obrigatórios
        campos_obrigatorios = self._get_campos_obrigatorios()
        
        # 2. Verificar o que já foi fornecido
        dados_coletados = dados_iniciais or {}
        campos_faltantes = self._identificar_campos_faltantes(
            campos_obrigatorios, 
            dados_coletados
        )
        
        # 3. Gerar prompt para solicitar próximo campo
        if campos_faltantes:
            proximo_campo = campos_faltantes[0]
            prompt = self._gerar_prompt_solicitacao(proximo_campo, tipo)
            return {
                'status': 'coletando_dados',
                'proximo_campo': proximo_campo,
                'mensagem': prompt,
                'dados_coletados': dados_coletados,
                'campos_faltantes': campos_faltantes
            }
        else:
            # 4. Todos os dados coletados, criar empresa
            return self._finalizar_cadastro(dados_coletados, tipo)
    
    def analisar_completude(self, company_id):
        """
        Analisa completude do cadastro e identifica impactos.
        """
        # 1. Buscar dados da empresa
        company = Company.query.get(company_id)
        if not company:
            return {'error': 'Empresa não encontrada'}
        
        # 2. Buscar dados específicos de planos
        plans = Plan.query.filter_by(company_id=company_id).all()
        company_data_list = []
        for plan in plans:
            company_data = CompanyData.query.filter_by(plan_id=plan.id).first()
            if company_data:
                company_data_list.append(company_data)
        
        # 3. Validar completude
        validacao = self._validar_completude(company, company_data_list)
        
        # 4. Analisar impacto
        impacto = self._analisar_impacto(validacao['campos_faltantes'])
        
        # 5. Gerar relatório
        relatorio = self._gerar_relatorio_completude(validacao, impacto)
        
        return relatorio
    
    def _get_campos_obrigatorios(self):
        """Retorna lista de campos obrigatórios"""
        return ['name', 'client_code']
    
    def _get_campos_recomendados(self):
        """Retorna lista de campos recomendados"""
        return [
            'legal_name', 'cnpj', 'segment', 
            'city', 'state', 'coverage_physical', 
            'coverage_online', 'experience_total', 
            'experience_segment'
        ]
    
    def _identificar_campos_faltantes(self, campos_obrigatorios, dados_coletados):
        """Identifica quais campos obrigatórios ainda faltam"""
        faltantes = []
        for campo in campos_obrigatorios:
            valor = dados_coletados.get(campo)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes.append(campo)
        return faltantes
    
    def _gerar_prompt_solicitacao(self, campo, tipo):
        """Gera mensagem para solicitar campo específico"""
        prompts = {
            'name': f"Qual é o nome fantasia da empresa {'exemplo' if tipo == 'exemplo' else ''}?",
            'client_code': "Qual é o código do cliente? (1 a 3 caracteres, letras ou números)",
            'legal_name': "Qual é a razão social da empresa?",
            'cnpj': "Qual é o CNPJ da empresa? (formato: XX.XXX.XXX/XXXX-XX)",
            # ... outros campos
        }
        
        return prompts.get(campo, f"Por favor, informe o campo {campo}")
    
    def _finalizar_cadastro(self, dados, tipo):
        """Finaliza cadastro criando empresa via API"""
        try:
            # Criar empresa via serviço
            company = self.registration_service.create_company(dados)
            
            return {
                'status': 'sucesso',
                'company_id': company.id,
                'mensagem': f"Empresa {'exemplo' if tipo == 'exemplo' else ''} cadastrada com sucesso!",
                'proximos_passos': self._sugerir_proximos_passos(company.id)
            }
        except Exception as e:
            return {
                'status': 'erro',
                'erro': str(e)
            }
    
    def _validar_completude(self, company, company_data_list):
        """Valida completude do cadastro"""
        campos_obrigatorios = self._get_campos_obrigatorios()
        campos_recomendados = self._get_campos_recomendados()
        
        faltantes_obrigatorios = []
        faltantes_recomendados = []
        
        # Validar campos da Company
        for campo in campos_obrigatorios:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_obrigatorios.append(campo)
        
        for campo in campos_recomendados:
            valor = getattr(company, campo, None)
            if not valor or (isinstance(valor, str) and not valor.strip()):
                faltantes_recomendados.append(campo)
        
        # Validar campos de CompanyData (se houver planos)
        faltantes_company_data = []
        if company_data_list:
            for company_data in company_data_list:
                # Validar campos específicos de CompanyData
                if not company_data.headcount_strategic:
                    faltantes_company_data.append('headcount_strategic')
                # ... outros campos
        
        return {
            'completo': len(faltantes_obrigatorios) == 0,
            'campos_faltantes': {
                'obrigatorios': faltantes_obrigatorios,
                'recomendados': faltantes_recomendados,
                'company_data': faltantes_company_data
            },
            'percentual_completude': self._calcular_percentual_completude(
                company, company_data_list
            )
        }
    
    def _analisar_impacto(self, campos_faltantes):
        """Analisa impacto de cada campo faltante"""
        impactos = {
            'name': {
                'criticidade': 'CRÍTICO',
                'impacto_pev': 'Bloqueia criação de empresa',
                'impacto_grv': 'Bloqueia criação de empresa',
                'impacto_relatorios': 'Bloqueia todos os relatórios',
                'recomendacao': 'Preencher imediatamente'
            },
            'legal_name': {
                'criticidade': 'ALTO',
                'impacto_pev': 'Relatórios formais incompletos',
                'impacto_grv': 'Documentação legal incompleta',
                'impacto_relatorios': 'Relatórios para stakeholders incompletos',
                'recomendacao': 'Preencher antes de gerar relatórios formais'
            },
            'cnpj': {
                'criticidade': 'ALTO',
                'impacto_pev': 'Análises fiscais e contábeis limitadas',
                'impacto_grv': 'Validação de dados fiscais impossível',
                'impacto_relatorios': 'Relatórios contábeis incompletos',
                'recomendacao': 'Preencher para análises fiscais completas'
            },
            'mission': {
                'criticidade': 'MÉDIO',
                'impacto_pev': 'Planejamento estratégico incompleto',
                'impacto_grv': 'Alinhamento de objetivos limitado',
                'impacto_relatorios': 'Relatórios estratégicos sem contexto de missão',
                'recomendacao': 'Preencher para PEV completo'
            },
            'vision': {
                'criticidade': 'MÉDIO',
                'impacto_pev': 'Planejamento estratégico sem visão de futuro',
                'impacto_grv': 'Objetivos de longo prazo não definidos',
                'impacto_relatorios': 'Relatórios estratégicos sem direcionamento',
                'recomendacao': 'Preencher para PEV completo'
            },
            'headcount_strategic': {
                'criticidade': 'ALTO',
                'impacto_pev': 'Análises de força de trabalho incompletas',
                'impacto_grv': 'Cálculos de produtividade imprecisos',
                'impacto_relatorios': 'Relatórios de RH incompletos',
                'recomendacao': 'Preencher para análises de recursos humanos'
            },
            # ... outros campos
        }
        
        resultado = {}
        for campo in campos_faltantes.get('obrigatorios', []):
            resultado[campo] = impactos.get(campo, {
                'criticidade': 'DESCONHECIDO',
                'impacto_pev': 'A ser analisado',
                'impacto_grv': 'A ser analisado',
                'impacto_relatorios': 'A ser analisado',
                'recomendacao': 'Verificar necessidade'
            })
        
        for campo in campos_faltantes.get('recomendados', []):
            resultado[campo] = impactos.get(campo, {
                'criticidade': 'MÉDIO',
                'impacto_pev': 'Funcionalidade pode estar limitada',
                'impacto_grv': 'Funcionalidade pode estar limitada',
                'impacto_relatorios': 'Relatórios podem estar incompletos',
                'recomendacao': 'Preencher quando possível'
            })
        
        return resultado
    
    def _gerar_relatorio_completude(self, validacao, impacto):
        """Gera relatório estruturado de completude"""
        prompt = f"""
        Analise o cadastro da empresa e gere um relatório estruturado.
        
        Status de Completude: {validacao['percentual_completude']}%
        Campos Obrigatórios Faltantes: {len(validacao['campos_faltantes']['obrigatorios'])}
        Campos Recomendados Faltantes: {len(validacao['campos_faltantes']['recomendados'])}
        
        Impactos Identificados:
        {self._formatar_impactos(impacto)}
        
        Gere um relatório claro, estruturado e acionável.
        """
        
        relatorio_texto = self.generate_response(prompt)
        
        return {
            'completude_percentual': validacao['percentual_completude'],
            'status': 'completo' if validacao['completo'] else 'incompleto',
            'campos_faltantes': validacao['campos_faltantes'],
            'impactos': impacto,
            'relatorio_texto': relatorio_texto,
            'recomendacoes': self._extrair_recomendacoes(relatorio_texto)
        }
    
    def _calcular_percentual_completude(self, company, company_data_list):
        """Calcula percentual de completude do cadastro"""
        total_campos = len(self._get_campos_obrigatorios()) + len(self._get_campos_recomendados())
        campos_preenchidos = 0
        
        for campo in self._get_campos_obrigatorios() + self._get_campos_recomendados():
            valor = getattr(company, campo, None)
            if valor and (not isinstance(valor, str) or valor.strip()):
                campos_preenchidos += 1
        
        # Considerar campos de CompanyData se houver
        if company_data_list:
            # Adicionar lógica para campos de CompanyData
            pass
        
        return int((campos_preenchidos / total_campos) * 100) if total_campos > 0 else 0
```

### 2. Serviço de Cadastro

```python
# services/company_registration_service.py
from models import Company, db
from flask_login import current_user

class CompanyRegistrationService:
    """Serviço de cadastro de empresas"""
    
    def create_company(self, dados):
        """Cria empresa com validação"""
        # Validações
        if not dados.get('name'):
            raise ValueError("Nome da empresa é obrigatório")
        
        if not dados.get('client_code'):
            raise ValueError("Código do cliente é obrigatório")
        
        # Criar empresa
        company = Company(
            name=dados['name'],
            legal_name=dados.get('legal_name'),
            cnpj=dados.get('cnpj'),
            segment=dados.get('segment'),
            city=dados.get('city'),
            state=dados.get('state'),
            coverage_physical=dados.get('coverage_physical'),
            coverage_online=dados.get('coverage_online'),
            experience_total=dados.get('experience_total'),
            experience_segment=dados.get('experience_segment'),
            mission=dados.get('mission'),
            vision=dados.get('vision'),
            values=dados.get('values')
        )
        
        db.session.add(company)
        db.session.commit()
        
        return company
```

### 3. API REST

```python
# api/cadastro_agent_api.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from agents.cadastro_agent import CadastroAgent

cadastro_bp = Blueprint('cadastro_agent', __name__, url_prefix='/api/cadastro-agent')

@cadastro_bp.route('/empresa/cadastrar', methods=['POST'])
@login_required
def cadastrar_empresa():
    """Inicia ou continua cadastro de empresa"""
    try:
        data = request.get_json() or {}
        tipo = data.get('tipo', 'real')  # 'exemplo' ou 'real'
        dados_iniciais = data.get('dados', {})
        
        agent = CadastroAgent()
        resultado = agent.cadastrar_empresa(tipo, dados_iniciais)
        
        return jsonify({
            'success': True,
            'data': resultado
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@cadastro_bp.route('/empresa/<int:company_id>/analisar', methods=['GET'])
@login_required
def analisar_completude(company_id):
    """Analisa completude do cadastro"""
    try:
        agent = CadastroAgent()
        relatorio = agent.analisar_completude(company_id)
        
        return jsonify({
            'success': True,
            'data': relatorio
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

## ⚠️ Riscos e Mitigações

### Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Dados inválidos fornecidos pelo usuário | Média | Alto | Validação rigorosa antes de salvar |
| Processo de cadastro muito longo | Baixa | Médio | Cadastro incremental, salvar progresso |
| Análise de impacto imprecisa | Média | Médio | Usar regras baseadas em conhecimento do sistema |
| Integração com Vertex AI complexa | Baixa | Alto | Usar BaseAgent existente, seguir padrão |
| Performance com muitas empresas | Baixa | Baixo | Cache de análises, processamento assíncrono |

---

## 📈 Benefícios Esperados

### Para Usuários
- ✅ **Cadastro mais rápido** - Processo guiado reduz erros
- ✅ **Cadastro mais completo** - Agente garante dados essenciais
- ✅ **Visibilidade de gaps** - Usuário sabe o que falta e por quê
- ✅ **Melhor experiência** - Interação natural via chat/API

### Para o Sistema
- ✅ **Dados de melhor qualidade** - Cadastros mais completos
- ✅ **Menos erros** - Validação proativa
- ✅ **Melhor utilização** - Usuários sabem o que preencher
- ✅ **Redução de suporte** - Agente responde dúvidas comuns

---

## 🚀 Plano de Implementação

### Fase 1: MVP (2 semanas)
- [ ] Implementar `CadastroAgent` básico
- [ ] Implementar validação de campos obrigatórios
- [ ] Criar API REST básica
- [ ] Testes unitários

### Fase 2: Análise de Completude (2 semanas)
- [ ] Implementar análise de completude
- [ ] Implementar análise de impacto
- [ ] Gerar relatórios estruturados
- [ ] Interface web para visualização

### Fase 3: Integração com IA (2 semanas)
- [ ] Integrar com Vertex AI (Gemini)
- [ ] Melhorar prompts e respostas
- [ ] Adicionar contexto de conversação
- [ ] Testes de integração

### Fase 4: Refinamento (1 semana)
- [ ] Otimizações de performance
- [ ] Melhorias de UX
- [ ] Documentação
- [ ] Deploy em produção

**Total Estimado:** 7 semanas

---

## 💰 Custos Estimados

### Google Cloud (Vertex AI)
- **Gemini 1.5 Pro:**
  - Input: $0.00125 / 1K chars
  - Output: $0.00375 / 1K chars
  - Estimativa: 100K chars/mês = ~$0.50/mês

### Desenvolvimento
- **Tempo:** 7 semanas (1 desenvolvedor)
- **Custo:** Baseado em rate do desenvolvedor

### Manutenção
- **Mensal:** ~$1-2/mês (uso de IA)
- **Suporte:** Baseado em demanda

---

## ✅ Conclusão

### Viabilidade: **ALTA** ✅

**Justificativa:**
1. ✅ Infraestrutura existente (modelos, APIs, arquitetura de agentes)
2. ✅ Stack tecnológica compatível
3. ✅ Documentação de referência disponível
4. ✅ Complexidade técnica moderada
5. ✅ Benefícios claros para usuários e sistema
6. ✅ Custos baixos (apenas uso de IA)

### Recomendação

**APROVAR** a implementação do Agente de Cadastro, seguindo o plano de implementação proposto.

### Próximos Passos

1. **Aprovação do escopo** - Validar requisitos com stakeholders
2. **Definição de prioridades** - Decidir se começar por cadastro ou análise
3. **Alocação de recursos** - Definir desenvolvedor responsável
4. **Início da Fase 1** - Começar implementação do MVP

---

**Versão:** 1.0  
**Data:** 18/12/2025  
**Autor:** Análise Técnica  
**Status:** ✅ Aprovado para Implementação















