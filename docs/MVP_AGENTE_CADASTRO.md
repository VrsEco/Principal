# 🚀 MVP - Agente de Cadastro

**Data:** 18/12/2025  
**Versão:** MVP 1.0  
**Status:** ✅ Implementado

---

## 📋 Resumo

MVP do Agente de Cadastro implementado com **lógica baseada em regras** (sem IA inicialmente). Funcionalidades:

1. ✅ **Cadastro Assistido** - Processo guiado passo a passo
2. ✅ **Análise de Completude** - Identifica campos faltantes e impactos

---

## 🏗️ Arquitetura Implementada

### Service
- **`services/cadastro_agent_service.py`** - Lógica de negócio completa

### Rotas API
- `POST /api/cadastro-agent/empresa/iniciar` - Inicia cadastro
- `POST /api/cadastro-agent/empresa/processar` - Processa resposta do usuário
- `POST /api/cadastro-agent/empresa/finalizar` - Finaliza e cria empresa
- `GET /api/cadastro-agent/empresa/<id>/analisar` - Analisa completude

---

## 📡 Como Usar

### 1. Iniciar Cadastro

```bash
POST /api/cadastro-agent/empresa/iniciar
Content-Type: application/json

{
  "tipo": "real",  // ou "exemplo"
  "dados": {}  // opcional: dados já conhecidos
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "status": "coletando_dados",
    "tipo": "real",
    "proximo_campo": "name",
    "mensagem": "Qual é o nome fantasia da empresa?",
    "dados_coletados": {},
    "progresso": 0
  }
}
```

### 2. Processar Resposta

```bash
POST /api/cadastro-agent/empresa/processar
Content-Type: application/json

{
  "dados_coletados": {
    "name": "Minha Empresa"
  },
  "campo": "name",
  "valor": "Minha Empresa",
  "tipo": "real"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "status": "coletando_dados",
    "proximo_campo": "client_code",
    "mensagem": "Qual é o código do cliente? (1 a 3 caracteres, letras ou números)",
    "dados_coletados": {
      "name": "Minha Empresa"
    },
    "progresso": 50
  }
}
```

### 3. Finalizar Cadastro

```bash
POST /api/cadastro-agent/empresa/finalizar
Content-Type: application/json

{
  "dados": {
    "name": "Minha Empresa",
    "client_code": "ABC",
    "legal_name": "Minha Empresa LTDA",
    "cnpj": "12.345.678/0001-90",
    "segment": "Tecnologia"
  },
  "tipo": "real"
}
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "status": "sucesso",
    "company_id": 123,
    "mensagem": "Empresa cadastrada com sucesso!",
    "proximos_passos": [
      "Criar um plano estratégico para a empresa (ID: 123)",
      "Cadastrar colaboradores da empresa",
      "Configurar indicadores e métricas"
    ]
  }
}
```

### 4. Analisar Completude

```bash
GET /api/cadastro-agent/empresa/123/analisar
```

**Resposta:**
```json
{
  "success": true,
  "data": {
    "status": "sucesso",
    "company_id": 123,
    "company_name": "Minha Empresa",
    "completude_percentual": 75,
    "status_completude": "incompleto",
    "campos_faltantes": {
      "obrigatorios": [],
      "recomendados_alta": ["cnpj"],
      "recomendados_media": ["city", "state"],
      "recomendados_baixa": [],
      "opcionais": ["mission", "vision"]
    },
    "impactos": {
      "cnpj": {
        "criticidade": "ALTO",
        "impacto_pev": "Análises fiscais e contábeis limitadas",
        "impacto_grv": "Validação de dados fiscais impossível",
        "impacto_relatorios": "Relatórios contábeis incompletos",
        "recomendacao": "Preencher para análises fiscais completas"
      }
    },
    "relatorio": "📊 ANÁLISE DE COMPLETUDE - Minha Empresa\n..."
  }
}
```

---

## 🎯 Campos Suportados

### Obrigatórios
- `name` - Nome fantasia
- `client_code` - Código do cliente (1-3 caracteres)

### Recomendados (Alta Prioridade)
- `legal_name` - Razão social
- `cnpj` - CNPJ
- `segment` - Segmento/Indústria

### Recomendados (Média Prioridade)
- `city` - Cidade
- `state` - Estado (2 letras)
- `coverage_physical` - Cobertura física
- `coverage_online` - Cobertura online

### Recomendados (Baixa Prioridade)
- `experience_total` - Experiência total
- `experience_segment` - Experiência no segmento

### Opcionais (MVV)
- `mission` - Missão
- `vision` - Visão
- `values` - Valores

---

## 🔄 Fluxo Completo

```
1. Iniciar → Solicita "name"
2. Usuário responde → Solicita "client_code"
3. Usuário responde → Solicita "legal_name" (recomendado)
4. Usuário responde → Solicita "cnpj" (recomendado)
5. ... continua até todos os campos obrigatórios
6. Finalizar → Cria empresa
7. Analisar → Mostra completude e impactos
```

---

## 🧪 Teste Rápido

### Via cURL

```bash
# 1. Iniciar
curl -X POST http://localhost:5003/api/cadastro-agent/empresa/iniciar \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"tipo": "real"}'

# 2. Processar (após receber próximo_campo)
curl -X POST http://localhost:5003/api/cadastro-agent/empresa/processar \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{
    "dados_coletados": {},
    "campo": "name",
    "valor": "Teste Empresa",
    "tipo": "real"
  }'

# 3. Finalizar (quando status = "pronto_para_criar")
curl -X POST http://localhost:5003/api/cadastro-agent/empresa/finalizar \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{
    "dados": {
      "name": "Teste Empresa",
      "client_code": "TST"
    },
    "tipo": "real"
  }'

# 4. Analisar (após criar empresa)
curl -X GET http://localhost:5003/api/cadastro-agent/empresa/123/analisar \
  -H "Cookie: session=..."
```

---

## 📝 Próximos Passos (Futuro)

1. **Integração com IA** - Usar Vertex AI para respostas mais naturais
2. **Interface Web** - Criar UI para interação com o agente
3. **Validações Avançadas** - Validação de CNPJ, CEP, etc.
4. **Cadastro em Lote** - Suporte para múltiplas empresas
5. **Templates** - Templates de empresas exemplo pré-configuradas

---

## ✅ Status de Implementação

- [x] Service de cadastro assistido
- [x] Service de análise de completude
- [x] Rotas API REST
- [x] Validações de campos
- [x] Análise de impactos
- [x] Geração de relatórios
- [ ] Interface web (futuro)
- [ ] Integração com IA (futuro)

---

**Versão:** MVP 1.0  
**Status:** ✅ Pronto para Testes














