# Constituição Técnica — Gestão Versus

## Arquitetura obrigatória
- Python 3.10+, Flask, PostgreSQL com `psycopg2`, Jinja2 + Tailwind; OpenAI/LangGraph quando aplicável.
- SQLite e Vertex AI são proibidos.
- Toda operação lê e grava com `company_id`; id de objeto isolado não é autorização.
- Regras vivem em services, não em rotas. Payloads são validados por schema rigoroso.
- MCP é a superfície prioritária para leitura operacional e integrações de agentes.

## Comunicação e eficiência
- PT-BR, decisão primeiro, 3–7 bullets e profundidade proporcional ao risco.
- Contexto é recurso finito: carregue apenas o necessário, limite saídas de ferramentas e evite reexplicar contexto já disponível.
