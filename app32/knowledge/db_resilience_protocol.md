# Protocolo de Resiliência de Banco de Dados (v2.0)

## 1. O Problema: Desvio de Schema (Schema Drift)
O erro `ProgrammingError: (psycopg2.errors.UndefinedColumn)` ocorre quando o código Python (Modelos SQLAlchemy) está mais atualizado que a estrutura real das tabelas no PostgreSQL. Isso é comum quando mudamos nomes de colunas (ex: `name` -> `title`) e não aplicamos a migration.

## 2. Diagnóstico Rápido
Sempre que ocorrer um erro de coluna inexistente:
1.  **Não assuma** que o modelo está errado.
2.  Use o script `check_pev_diag.py` (ou comando `psql \d nome_tabela`) para ver o que o banco REALMENTE tem.
3.  Compare com o arquivo `models/*.py`.

## 3. Estratégia de Correção (Dev Mode)
Em ambiente de desenvolvimento, se o usuário autorizar "recomeçar do zero":
1.  Drop das tabelas conflitantes com `CASCADE`.
2.  Uso de `db.create_all()` para recriar com o schema atual.
3.  *Script de referência:* `fix_db_schema.py`.

## 4. Prevenção por Disciplina
- **Regra de Ouro:** Toda nova funcionalidade de banco deve vir acompanhada de um script de validação de schema.
- **Alembic:** Use `flask db migrate` e `flask db upgrade` como padrão, mesmo em dev, para manter o histórico.
- **Check-in de Agente:** Ao iniciar uma tarefa de banco, o Agente @DBA deve primeiro ler o schema real do banco para confirmar se o ponto de partida é o esperado.

## 5. Serialização JSON (v2.0)
Modelos SQLAlchemy **não são serializáveis por padrão** via Jinja `| tojson`.
- **Erro comum:** `TypeError: Object of type Company is not JSON serializable`.
- **Correção:** Sempre chame `.to_dict()` antes de usar o filtro.
- **Exemplo:** `window.company = {{ company.to_dict() | tojson }};`
- **Padrão:** Todo modelo v2.0 deve implementar o método `to_dict()` de forma abrangente.
