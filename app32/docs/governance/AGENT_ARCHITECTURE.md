# 🧠 Arquitetura de Agentes (v2.0 - Body-Brain)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Oficial - OpenAI / LangGraph

---

## 🎯 Filosofia "Body-Brain"
O sistema Gestão Versus opera sob a separação clara entre execução rasteira e raciocínio superior.

1.  **O Corpo (App32):** APIs, CRUDs, Tabelas SQL e Interface.
2.  **O Cérebro (Intelligence):** Lógica de grafos, memória vetorial e modelos de linguagem.

---

## 🏗️ Core Stack (Intelligence Layer)

*   **Brain:** OpenAI GPT-4o (via LangChain).
*   **Orquestração:** LangGraph (Uso de `StateGraph` para fluxos cíclicos).
*   **Checkpointer:** `PostgresSaver` (Persistência síncrona do estado do grafo no banco PostgreSQL).
*   **Vector Library:** ChromaDB (Persistência local em `/storage/vector_db`).

---

## 🧩 Tipos de Agentes

### 1. Supervisor (Roteador)
O cérebro central que analisa a intenção do usuário e decide qual Agente Expert deve ser acionado. Não executa lógica de negócio, apenas orquestra.

### 2. Experts (Executores)
Agentes especializados em domínios específicos (Financeiro, Estratégico, OKRs). Eles possuem ferramentas (`Tools`) para consultar dados do "Corpo".

---

## 💾 Memória e Estado

### Memória de Curto Prazo (Thread State)
Gerenciada pelo **LangGraph** e persistida no PostgreSQL. Permite que o agente lembre o que foi dito na conversa atual mesmo após reinicializações do servidor.

### Memória de Longo Prazo (RAG)
Gerenciada via **ChromaDB**. Documentos, históricos de anos anteriores e manuais de governança são "indexados" para consulta semântica.

---

## 🔌 Regras de Implementação

1.  **Streaming:** Todas as chamadas de IA devem suportar streaming de tokens para melhor UX.
2.  **Tool Decorators:** Funções do "Corpo" expostas para o "Cérebro" devem ser decoradas com `@tool` do LangChain e possuir docstrings extremamente descritivas.
3.  **Prompt Management:** Proibido embutir prompts em arquivos de rota. Devem residir em `src/intelligence/prompts`.

---

## 🚫 O que NÃO fazer
*   NUNCA usar Vertex AI ou Google Cloud Platform (Legacy).
*   NUNCA criar agentes que não pertençam a um Grafo de Estado (LangGraph).
*   NUNCA ignorar o `thread_id` nas conversas.

---

**Responsável:** AI Lead Designer
