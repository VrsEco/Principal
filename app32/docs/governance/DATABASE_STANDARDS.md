# 🗄️ Padrões de Banco de Dados (v2.0)

**Última Atualização:** 17/02/2026  
**Versão:** 2.0  
**Status:** ✅ Obrigatório

---

## 🎯 Princípios

1. **PostgreSQL Only** - Fim da compatibilidade com SQLite.
2. **Persistence by JSONB** - Uso intensivo de JSONB para estados do LangGraph.
3. **Vector Support** - Integração com ChromaDB e pgvector para RAG.
4. **Docker Mandatory** - O ambiente de dev deve espelhar o de prod via containers.

---

## 🏗️ Infraestrutura

### PostgreSQL
*   **Versão Mínima:** 15 (Suporte a extensões modernas).
*   **Obrigatório:** Instalação local ou via Docker. O uso de arquivos `.db` ou `sqlite3` está **TERMINANTEMENTE PROIBIDO**.
*   **Extensões:** `pgvector` deve estar habilitado para futuras migrações de vetores do Chroma para o banco principal.

### ChromaDB
*   **Uso:** Persistência de embeddings para a Camada de Inteligência.
*   **Modo:** Execução local (Persistent Client) vinculada ao diretório `/storage/vector_db`.

---

## 🏗️ Padrões de Modelagem

### JSONB vs JSON
Sempre prefira `JSONB` (PostgreSQL native) para colunas que requerem indexação ou consultas complexas dentro do JSON. Colunas de "Checkpoint" do LangGraph devem usar o driver `PostgresSaver`.

### Nomenclatura
Mantenha o padrão `snake_case` no plural para tabelas e `snake_case` no singular para colunas.

---

## 🔄 Migrations
Utilize o **Flask-Migrate (Alembic)**.
1. `flask db migrate -m "descricao"`
2. `flask db upgrade`

**Nota:** Migrations que tocam em estados de IA (grafos) devem ser tratadas com cautela para não corromper memórias de curto prazo ativas.

---

## 🚀 Performance
*   **Indexação JSONB:** Use índices GIN em colunas de metadados.
*   **Eager Loading:** Obrigatório para evitar N+1 em serviços de IA que leem contexto de múltiplas tabelas.
*   **Materialized Views:** Obrigatórias para consolidação de dados pesados (ex: progresso de planos, históricos financeiros) consumidos por dashboards ou IAs. Devem ser atualizadas via triggers ou workers de engenharia.

---

**Responsável:** Technical Writer / DBA  
