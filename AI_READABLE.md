# Protocolo Gestão Versus Monorepo (AI-Readable)

Este documento orienta Agentes de IA sobre a nova estrutura do projeto e como interagir com o sistema.

## 📁 Estrutura do Repositório
- `/app31/`: Legado do sistema (Referência técnica).
- `/app32/`: Core do sistema v2.0 (Produção).
- `.gitignore`: Configurado para ignorar ambientes virtuais e arquivos de IDE recursivamente.

## 🤖 Protocolo MCP (Model Context Protocol)
O sistema expõe o "Cérebro" do negócio via MCP para garantir que IAs operem com dados em tempo real.

### Como Conectar (Cursor/Claude):
Adicione um novo servidor MCP:
- **Command**: `C:\GestaoVersus\.venv\Scripts\python.exe C:\GestaoVersus\app32\src\core\mcp_server.py`

### Ferramentas Disponíveis:
1.  **`query_database`**: Executa SQL com injeção automática de `company_id`.
2.  **`consult_business_rules`**: Consulta a base RAG de regras de negócio.
3.  **`list_plans` / `get_plan_diagnostics`**: Gestão estratégica.
4.  **`get_system_health`**: Monitoramento de infraestrutura.
5.  **`get_database_schema`**: Descoberta de tabelas e colunas.

## 🛡️ Regras de Ouro para Agentes
1.  **Multi-tenancy**: Toda query ou alteração de dados deve OBRIGATORIAMENTE filtrar por `company_id`.
2.  **Early Return**: Código limpo com retornos antecipados para evitar aninhamento excessivo.
3.  **AI-Readable Context**: Sempre use as ferramentas MCP para validar o estado do banco antes de sugerir mudanças.

**Squad de Engenharia de Elite - Gestão Versus**
