# 🚫 Padrões Proibidos e Anti-Patterns (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ OBRIGATÓRIO

---

## 🔐 SEGURANÇA E STACK

### 🔴 NUNCA: Usar SQLite ou Banco de Arquivo
*   ❌ `import sqlite3`
*   ❌ Arquivos `.db` ou `.sqlite` no repositório.
*   ✅ Use apenas PostgreSQL oficial via SQLAlchemy/psycopg2.

### 🔴 NUNCA: Usar Stack de IA Legada
*   ❌ `import google.cloud.aiplatform` ou `import vertexai`.
*   ❌ Referências a modelos "Bison", "Gecko" ou "Gemini 1.0".
*   ✅ Use OpenAI GPT-4o e LangGraph.

---

## 🏗️ ARQUITETURA

### 🟡 NUNCA: IA em Controllers/Rotas
*   A lógica de chamadas ao `openai.chat.completions` ou execução de `graph.invoke()` **NUNCA** deve estar dentro de arquivos de rota (`api/routes`).
*   **Onde colocar:** Deve estar isolada em `src/intelligence/`.

### 🟡 NUNCA: Bypass da Camada de Serviço
*   Rotas não devem chamar a Camada de Inteligência diretamente.
*   Fluxo obrigatório: `Route -> Service -> Intelligence`.

---

## 💾 DADOS E PERSISTÊNCIA

### 🟡 NUNCA: Ignorar pgvector no Planejamento
*   Não crie tabelas de "mensagens" manuais sem prever a integração com a persistência do LangGraph.

### 🟡 NUNCA: Deletar Logs de Auditoria
*   O uso de `@auto_log_crud` é obrigatório em todas as rotas de escrita.

---

## 🌐 FRONTEND

### 🟡 NUNCA: Z-Index Aleatório
*   ❌ `z-index: 9999` ou `z-index: 999999`.
*   ✅ Siga a hierarquia de `MODAL_STANDARDS.md`.

---

**Consequência:** Violações destes padrões bloqueiam o Merge e requerem refatoração imediata.

**Responsável:** Tech Lead
