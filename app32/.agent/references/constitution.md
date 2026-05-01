# Constituição Técnica — Gestão Versus

## Stack oficial
- Python 3.10+
- Flask
- PostgreSQL com `psycopg2`
- OpenAI / LangGraph quando aplicável
- Jinja2 + TailwindCSS no frontend server-rendered

## Guardrails globais
1. Multi-tenancy obrigatório: toda leitura e escrita deve escopar `company_id`.
2. Não confiar apenas no id do objeto.
3. Não colocar lógica de negócio em rotas.
4. Validar payloads com schema rigoroso.
5. MCP First para leitura operacional e integração com agentes.
6. SQLite proibido.
7. Vertex AI proibido.

## Comunicação
- responder em Português-Brasil
- exigência técnica alta
- respostas curtas e objetivas, com alvo de leitura entre 1 e 5 minutos, salvo quando o usuário pedir aprofundamento
- priorizar clareza arquitetural e evolução sustentável
