# 🛠️ Stack Tecnológica Oficial (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Ativo - Migração Concluída

---

## 🎯 Filosofia

> "Escolhemos tecnologias de ponta para Inteligência Artificial, priorizando a robustez do PostgreSQL e a flexibilidade do ecossistema LangGraph/OpenAI. Não suportamos mais bancos de dados leves ou legados."

---

## 📚 Stack Aprovada

### Backend Core

| Tecnologia | Versão | Justificativa | Status |
|------------|--------|---------------|--------|
| **Python** | 3.10+ | Suporte a novos recursos de tipagem e LangGraph | ✅ Obrigatório |
| **Flask** | 2.3.3 | Framework web para interface e APIs | ✅ Obrigatório |
| **LangGraph** | Latest | Orquestração de grafos de agentes e estados | ✅ Obrigatório |
| **SQLAlchemy** | 2.0+ | ORM oficial (foco total em PostgreSQL) | ✅ Obrigatório |

### Inteligência Artificial (Brain)

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **OpenAI GPT-4o** | - | Modelo de raciocínio principal | ✅ Obrigatório |
| **LangGraph** | - | Orquestração de Agentes (StateGraph) | ✅ Obrigatório |
| **ChromaDB** | - | Vector Database local para RAG (Memória de Longo Prazo) | ✅ Obrigatório |

### Banco de Dados (Persistência)

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **PostgreSQL** | 14 | Único banco aceito (Prod e Dev) | ✅ Obrigatório |
| **psycopg2-binary** | - | Driver de conexão PostgreSQL | ✅ Obrigatório |
| **pgvector** | - | Extensão Postgres para busca vetorial | ✅ Recomendado |

**⚠️ CRÍTICO:** O suporte ao SQLite foi **DESCONTINUADO**. Todo o ambiente de desenvolvimento deve rodar via Docker com PostgreSQL.

### Frontend

| Tecnologia | Versão | Uso | Status |
|------------|--------|-----|--------|
| **TailwindCSS** | 3.x | Framework de estilização utilitário | ✅ Obrigatório |
| **Jinja2** | - | Template engine oficial | ✅ Obrigatório |
| **JavaScript Vanilla**| ES6+ | Interatividade sem frameworks pesados | ✅ Obrigatório |

---

## 🚫 Tecnologias Proibidas (Legado)

| Tecnologia | Motivo | Alternativa Aprovada |
|------------|--------|---------------------|
| **SQLite** | Falta de suporte a JSONB/Vectores | PostgreSQL |
| **Vertex AI** | Migração concluída para OpenAI | OpenAI GPT-4o |
| **Google Cloud** | Infraestrutura descontinuada | Docker / On-premise |
| **jQuery** | Legacy | Vanilla JS |

---

## 📦 Estrutura de Dependências (requirements.txt)

```txt
# Core & AI
openai==1.x
langgraph
chromadb
langchain-openai

# Database
SQLAlchemy>=2.0
psycopg2-binary
langchain-postgres  # Para PostgresSaver (Memória do Grafo)

# Web & UI
Flask==2.3.3
tailwindcss
```

---

## 🔄 Processo de Adição
Siga o checklist em `docs/governance/README.md`. Qualquer nova biblioteca de IA deve ser validada quanto ao impacto na latência e custos de token.

---

**Responsável:** Lead Architect  
**Aprovado em:** 17/02/2026
