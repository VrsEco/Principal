# ORM Standards (APP30)

Este guia complementa `CODING_STANDARDS.md` e detalha práticas obrigatórias ao
trabalhar com SQLAlchemy no GestaoVersus (APP30). O objetivo é evitar falhas do
mapper (erros `InvalidRequestError`, `NoReferencedTableError`) e inconsistências
de conexão que já impactaram APIs como `/pev/api/implantacao/<plan_id>/products`.

## 1. Carregamento explícito de dependências

Sempre que um módulo de serviço importar um `db.Model` fora do pacote
`models/`, importe também as entidades relacionadas *antes* de criar instâncias
ou executar queries:

```python
from models import db
from models.product import Product

# Importações apenas para registrar metadata e relacionamentos
from models import company as _company  # noqa: F401
from models import participant as _participant  # noqa: F401
from models.plan import Plan  # noqa: F401
```

- O objetivo é garantir que o metadata da tabela (`foreign keys`,
  `relationship()`) já esteja registrado quando `Product()` for instanciado ou
  quando `db.session` montar a query.
- Não confie na importação indireta via `models/__init__.py`. Serviços carregam
  em momentos diferentes e isso tem gerado 500 intermitentes em produção.

## 2. Proibido criar tabelas em runtime

- Não invoque `Model.__table__.create()` ou `db.create_all()` dentro da
  aplicação. A migração oficial (`migrations/*.sql`) é a única responsável pelo
  schema.
- Funções auxiliares como `ensure_products_table()` devem ser um no-op. Use-as
  apenas para validações ou logging.

## 3. Checagens de existência

Preferir SQL direto para validações simples quando o mapper ainda não pode ser
carregado com segurança:

```python
from sqlalchemy import text

exists = db.session.execute(
    text("SELECT 1 FROM plans WHERE id = :plan_id LIMIT 1"),
    {"plan_id": plan_id},
).first()
if not exists:
    raise ProductValidationError("Plano informado não existe.")
```

Isso evita inicializar o mapper `Plan` cedo demais e gera mensagens claras.

## 4. Conexões de banco consistentes

- Sempre normalize URLs/hosts com os helpers em `utils/env_helpers.py`.
- `normalize_database_url()` e `normalize_docker_host()` resolvem o
  `host.docker.internal` automaticamente fora de containers, eliminando
  `UnicodeDecodeError` do psycopg2 no Windows.
- Novos scripts ou services que montarem `create_engine`/`psycopg2.connect`
  devem reutilizar esses helpers.

## 5. Checklist para novos services ORM

1. Importar o `db.Model` principal **e** os modelos relacionados.
2. Validar entidades por SQL direto quando a checagem for simples.
3. Nunca criar/alterar schema em runtime.
4. Reutilizar helpers de conexão ao compor `DATABASE_URL`/`POSTGRES_HOST`.
5. Cobrir o caminho crítico com teste de integração (`app.test_client`) antes
   de subir para QA.

> Qualquer desvio destas regras precisa ser registrado no
> `docs/governance/DECISION_LOG.md` com justificativa explícita.
