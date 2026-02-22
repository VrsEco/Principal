# Gestão Versus - Backend v2.0
> **Status**: Produção / Stable  
> **Arquitetura**: OpenAI + LangGraph + PostgreSQL (Body-Brain Separation)

Esta versão representa o estado da arte do sistema Gestão Versus, consolidando a migração para uma arquitetura moderna, escalável e resiliente. 

**AVISO DE DEPRECIAÇÃO**: Esta versão v2.0 substitui integralmente e deprecia permanentemente a arquitetura anterior baseada em Google Vertex AI e SQLite local. O uso dessas tecnologias é proibido neste núcleo.

---

## 🧠 Visão Arquitetural

O sistema adota o padrão **Body-Brain Separation**, garantindo que a lógica de negócio e a inteligência de orquestração operem em harmonia, mas com responsabilidades claras:

- **The Body (O Corpo)**: Desenvolvido em **Flask** e **PostgreSQL**, gerencia as rotas, APIs, persistência de dados transacionais e a interface de usuário.
- **The Brain (O Cérebro)**: Desenvolvido com **LangGraph** e **OpenAI (GPT-4o)**, gerencia o raciocínio dos agentes, a memória de curto/longo prazo e a orquestração de ferramentas.
- **RAG (Knowledge Base)**: Base de conhecimento vetorial utilizando **ChromaDB** para recuperação de regras de negócio em tempo real.

---

## 🛠️ Stack Tecnológica

- **Linguagem**: Python 3.10+
- **Web**: Flask + Flask-CORS
- **Inteligência**: OpenAI Chat Completions (GPT-4o / GPT-4o-mini)
- **Orquestração**: LangGraph (StateGraph + Supervisor Pattern)
- **Banco de Dados**: PostgreSQL (Persistência via psycopg2 / SQLAlchemy)
- **Vetores (RAG)**: ChromaDB + OpenAI Embeddings (text-embedding-3-small)

---

## ⚙️ Configuração de Ambiente

### Pré-requisitos
- Python 3.10 ou superior.
- Instância do PostgreSQL rodando (Docker ou Local).

### Instalação
1. Clone o repositório.
2. Crie e ative seu ambiente virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
3. Instale as dependências:
   ```powershell
   pip install -r requirements.txt
   ```

### Variáveis de Ambiente (.env)
Crie um arquivo `.env` na raiz do projeto com as seguintes chaves:
```env
# Flask
FLASK_APP=main.py
FLASK_ENV=development
DEBUG=True

# Banco de Dados (PostgreSQL)
DATABASE_URL=postgresql://usuário:senha@localhost:5432/bd_app_versus

# Inteligência Artificial
OPENAI_API_KEY=sk-sua-chave-aqui
```

---

## 🚀 Inicialização Passo a Passo

### Passo 1: Banco de Dados
O `DatabaseManager` do sistema está configurado para o modo *Auto-Provisioning*. Certifique-se apenas de que a `DATABASE_URL` aponta para um banco já criado no Postgres. As tabelas de sistema e de memória do LangGraph serão criadas automaticamente na primeira execução.

### Passo 2: Carga de Conhecimento (RAG)
Para que o agente conheça as regras de negócio (aprovações, limites, procedimentos), é necessário popular o banco de vetores:
```powershell
python src/intelligence/seed_knowledge.py
```

### Passo 3: Inicializar o Servidor
Com o ambiente configurado, inicie o backend:
```powershell
python main.py
```
O servidor estará disponível em `http://localhost:5010`.

---

## ⌨️ Uso do Sistema

### Interface Web (Chat)
Acesse a nova interface de chat diretamente pelo navegador:
> [http://localhost:5010/chat](http://localhost:5010/chat)

### API de Chat (v2.0)
Para integrações externas ou frontends customizados:
- **Endpoint**: `POST /api/v2/chat`
- **Payload**:
  ```json
  {
    "message": "Qual a regra para notas fiscais acima de 10k?",
    "thread_id": "sessao-do-usuario-001"
  }
  ```

---

## 📁 Estrutura de Pastas

```text
c:\GestaoVersus\app32\
├── main.py                 # Entry point do servidor Flask
├── requirements.txt         # Dependências limpas (Sem Vertex/SQLite)
├── src/
│   ├── core/               # "The Body": Rotas, DB e lógicas base
│   │   ├── database.py     # Gestão Postgres
│   │   └── routes.py       # Definição dos endpoints e views
│   ├── intelligence/       # "The Brain": Agentes e RAG
│   │   ├── graph.py        # Orquestração LangGraph
│   │   ├── rag.py          # Interface com ChromaDB
│   │   ├── agents/         # Especialistas (Supervisor-Worker)
│   │   └── tools.py        # Ferramentas (DB Query, RAG Search)
│   └── templates/          # Frontend Web (TailwindCSS)
└── data/
    └── chroma_db/          # Persistência local do banco de vetores
```

---

## 🛡️ Segurança e Complacência
1. **SELECT Only**: As ferramentas de banco de dados do agente são restritas a operações de leitura para evitar corrupção de dados via Prompt Injection.
2. **Postgres Checkpoints**: Toda a memória de conversa é persistida de forma ACID diretamente no PostgreSQL, garantindo que o agente nunca "esqueça" o contexto mesmo após reinicializações.
3. **Zero SQLite Policy**: Nenhum banco de dados local `.db` ou `.sqlite` é permitido para armazenamento de estado ou lógica de negócio (exceto o motor interno do ChromaDB).

---
*Documentação gerada automaticamente para Gestão Versus v2.0 - 2026.*
