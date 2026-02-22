# 🏗️ Arquitetura do Sistema (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Documentação Oficial

---

## 🎯 Visão Geral
O sistema Gestão Versus segue uma arquitetura modular de 6 camadas, agora reforçada pela **Camada de Inteligência (The Brain)**.

## 🌐 Fluxo de Requisições v2.0
```
Cliente → Layer 2 (Routes) → Layer 3 (Services) → Layer 3.5 (Intelligence) → LLM/VectorDB
                                     ↓
                               Layer 4 (Models) → Layer 5 (Database)
```

---

## 📁 Estrutura de Diretórios Atualizada
```
/app32
├── src/
│   ├── intelligence/         # 🧠 Layer 3.5: Intelligence (Brain)
│   │   ├── agents/           # Definições de Agentes (Expert, Supervisor)
│   │   ├── graphs/           # Grafos de Estado (LangGraph)
│   │   └── memory/           # Implementação de RAG e Vetores (ChromaDB)
│   ├── services/             # Layer 3: Orquestração e Lógica
│   └── models/               # Layer 4: Dados
├── api/
│   └── routes/               # Layer 2: Endpoints
├── templates/                # Layer 1: UI (Tailwind + Jinja2)
└── storage/
    └── vector_db/            # Banco de vetores local
```

---

## 🧩 Detalhamento das Camadas

### Layer 2: Rotas (Blueprints)
**Regra de Ouro:** NUNCA acessa a Layer 3.5 diretamente e EVITA lógica de negócio.
As rotas devem servir apenas como gatekeepers (Auth/Validation), invocando obrigatoriamente um `Service` (Layer 3) para toda lógica de escrita ou leitura complexa.

### Layer 3: Serviços (Services)
A camada de inteligência (`Intelligence`) é consumida aqui. Centraliza toda a regra de negócio determinística.
**Padronização:** Toda funcionalidade de planejamento deve estar no `PlanService`, servindo tanto às rotas Flask quanto às ferramentas MCP de IA.

### Layer 3.5: Inteligência (The Brain) ✨ NOVO
Responsável por:
*   Raciocínio via LLM (GPT-4o).
*   Manutenção de estado via LangGraph.
*   Recuperação de contexto via RAG.
*   **Isolamento:** Esta camada não deve conter lógica de commit de banco de dados SQL tradicional; ela retorna sugestões ou estados que os Services aplicam.

---

## 👥 Acesso a Dados
A Camada de Inteligência acessa o banco via Layer 4 (Models) para contexto, mas persiste sua própria memória técnica (checkpoints) via `PostgresSaver`.

---

**Próxima revisão:** Junho/2026  
**Responsável:** Lead Architect
