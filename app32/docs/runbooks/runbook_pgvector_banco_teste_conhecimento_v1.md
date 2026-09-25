# Runbook — pgvector em banco de TESTE descartável (Conhecimento Corporativo)

**Objetivo:** provar, fora de produção e fora do banco de desenvolvimento (porta 5432), que a
migration `20260924_1400`/`1500`, o isolamento por tenant na consulta vetorial e o rollback
funcionam. **Não** aplica nada em produção e **não** chama a OpenAI.

Pré-requisitos desta máquina (verificados em 2026-09-24): PostgreSQL 14 em
`C:\Program Files\PostgreSQL\14`, Visual Studio 2022 instalado, sem Docker, `git` disponível.
O PostgreSQL 14 local **não** traz os arquivos do pgvector; é preciso instalá-los uma vez.

## Opção A — compilar o pgvector no PostgreSQL 14 local (sem Docker)

Abra o **"x64 Native Tools Command Prompt for VS 2022" como Administrador** e execute:

```bat
set "PGROOT=C:\Program Files\PostgreSQL\14"
cd %TEMP%
git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

- Use a tag estável mais recente listada em <https://github.com/pgvector/pgvector/releases>
  (a `v0.8.0` acima é um exemplo; se a tag não existir, troque).
- Se `nmake` não for encontrado, falta o componente **"Desenvolvimento para desktop com C++"**
  do Visual Studio (Visual Studio Installer → Modificar).
- A instalação apenas copia arquivos para a pasta do PostgreSQL. **Nenhum banco existente é
  alterado**: a extensão só passa a existir num banco quando alguém executa `CREATE EXTENSION`.

## Opção B — Docker (padrão dos DATABASE_STANDARDS)

Instale o Docker Desktop e suba um PostgreSQL com pgvector já incluído, em porta própria:

```bash
docker run --name knowledge-vector-test -e POSTGRES_PASSWORD=teste -p 127.0.0.1:55432:5432 -d pgvector/pgvector:pg16
docker exec knowledge-vector-test psql -U postgres -c "CREATE DATABASE knowledge_vector_test"
```

Nesse caso pule a criação do cluster abaixo e use a senha `teste`.

## Cluster descartável (Opção A) — porta 55432

No PowerShell (o cluster fica numa pasta temporária, separada do banco de desenvolvimento):

```powershell
$pg = "C:\Program Files\PostgreSQL\14\bin"
$dir = "$env:TEMP\pgvector_teste"
Set-Content -Path "$env:TEMP\pgvector_pw.txt" -Value "teste" -NoNewline
& "$pg\initdb.exe" -D $dir -U postgres --pwfile="$env:TEMP\pgvector_pw.txt" -A md5 -E UTF8
& "$pg\pg_ctl.exe" -D $dir -o "-p 55432 -c listen_addresses=127.0.0.1" -l "$env:TEMP\pgvector_teste.log" start
$env:PGPASSWORD = "teste"
& "$pg\psql.exe" -h 127.0.0.1 -p 55432 -U postgres -c "CREATE DATABASE knowledge_vector_test"
& "$pg\psql.exe" -h 127.0.0.1 -p 55432 -U postgres -d knowledge_vector_test -c "SELECT * FROM pg_available_extensions WHERE name='vector'"
```

A última consulta deve retornar **uma linha**. Se vier vazia, a Opção A não foi instalada.

## Ensaio

```powershell
cd C:\GestaoVersus\app32\app32
$env:APP32_KNOWLEDGE_VECTOR_TEST_DATABASE_URL = "postgresql+psycopg2://postgres:teste@127.0.0.1:55432/knowledge_vector_test"
python scripts/knowledge_vector_rehearsal.py
python -m pytest tests/test_knowledge_vector_skeleton.py -p no:flask -q
```

O script recusa qualquer banco que não seja local, em porta diferente de 5432 e com nome
terminado em `_test`. Resultado esperado (todas as linhas `OK`):

- upgrade `1400` + `1500` aplicado;
- consulta vetorial da empresa 1 enxerga só o dado da empresa 1 (e a 2 só o da 2), mesmo com
  vetores idênticos;
- vetor com checksum obsoleto é descartado;
- rollback remove só a projeção; `knowledge_sources`/`knowledge_chunks` e a extensão permanecem.

## Backfill de ponta a ponta com custo mínimo (opcional, exige sua chave)

Só depois do ensaio acima. Simulação primeiro (não chama a OpenAI):

```powershell
$env:KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED = "true"
$env:KNOWLEDGE_EMBEDDING_MODEL = "text-embedding-3-small"
$env:KNOWLEDGE_EMBEDDING_VERSION = "v1"
$env:KNOWLEDGE_EMBEDDING_INDEX_GENERATION = "1"
python scripts/knowledge_embedding_backfill.py
```

Para gravar de verdade use `--execute --max-chunks 5` e `OPENAI_API_KEY` **definida por você**
no ambiente da sessão (não a coloque em arquivos versionados). O job só envia trechos do
manual do produto (`product_help`).

## Encerrar e limpar

```powershell
& "C:\Program Files\PostgreSQL\14\bin\pg_ctl.exe" -D "$env:TEMP\pgvector_teste" -m fast stop
Remove-Item -Recurse -Force "$env:TEMP\pgvector_teste", "$env:TEMP\pgvector_pw.txt"
```

## Evidência do ensaio (25/09/2026)

Executado pela Opção B (Docker) com o container descartável `knowledge-vector-test`
(`pgvector/pgvector:pg16`, `127.0.0.1:55432`, banco `knowledge_vector_test`), sem chamar a OpenAI:

- `scripts/knowledge_vector_rehearsal.py`: todas as 7 verificações `OK` (upgrade `1400` + `1500`;
  isolamento por tenant com vetores idênticos; checksum obsoleto descartado; rollback remove só a
  projeção e preserva `knowledge_sources`/`knowledge_chunks` e a extensão).
- `tests/test_knowledge_vector_skeleton.py`: 13 passam.
- Suíte `*knowledge*`: 141 passam; 4 falham em `test_sapiens_knowledge_ui.py` e
  `test_sapiens_widget_knowledge_ui.py`, falhas que já ocorrem na `main` sem este PR (leem
  `app32/static/js/...`, hoje em `static/` na raiz).

## Limites

- O ensaio provou migration, isolamento e rollback em PostgreSQL 16 com pgvector. Não provou
  desempenho, custo de embeddings nem o comportamento no PostgreSQL de **produção** (versão e
  extensões podem diferir).
- Pendente antes de mesclar/publicar: confirmar que o PostgreSQL de produção tem a extensão
  `vector` disponível (`pg_available_extensions`), decisão de modelo e orçamento de embeddings
  e exportar `KnowledgeEmbeddingUsageEvent` em `models/__init__.py`.
- A migration em **produção** só com a extensão instalada pelo responsável da infraestrutura e
  aprovação explícita; a `1400` falha de forma segura se a extensão estiver ausente.
