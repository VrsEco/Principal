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

### Repetição em PostgreSQL 14 (versão de produção)

Produção roda PostgreSQL **14.24** (Ubuntu 22.04). O mesmo ensaio foi repetido com
`pgvector/pgvector:pg14` (PostgreSQL 14.24, container `knowledge-vector-test-pg14`,
`127.0.0.1:55433`): as 7 verificações `OK` e `test_knowledge_vector_skeleton.py` com 13 passando.

### Constatação em produção (25/09/2026, somente leitura)

`SELECT name, default_version, installed_version FROM pg_available_extensions WHERE name = 'vector'`
no banco `bdversusv2` de produção (phpPgAdmin, usuário `app`) retornou **nenhuma linha**: o
pacote do pgvector **não está instalado** no PostgreSQL de produção. A migration `1400` falharia
de forma segura, mas interromperia o deploy. Não publicar este PR antes da instalação.

### Resolução da infraestrutura (25/09/2026, ticket Configr #241421)

O suporte do Configr respondeu no mesmo dia:

- **pgvector 0.8.6 instalado** e a extensão `vector` **já criada** no banco `bdversusv2`, schema
  `public` (`pg_available_extensions`: `vector | 0.8.6 | 0.8.6`, segundo o suporte). Compilado a
  partir do código-fonte oficial para o PostgreSQL 14.24 do Ubuntu, porque o pacote PGDG não é
  compatível com ele.
- **Superusuário é necessário para `CREATE EXTENSION`**; o usuário `app` não consegue. Como a
  extensão já existe, a migration `1400` (`CREATE EXTENSION IF NOT EXISTS vector`) apenas segue
  adiante, sem exigir privilégio. O suporte testou tipo `vector`, operadores de distância e índices
  HNSW/IVFFlat com o usuário `app`.
- **Sem reinício** do PostgreSQL e sem indisponibilidade; nenhum outro banco foi alterado.
- **Atualização do pgvector não é automática**: exige novo pedido ao suporte.

Confirmado depois por consulta própria, somente leitura, em produção (25/09/2026):
`vector | 0.8.6 | 0.8.6` em `bdversusv2`.

## Estado em produção (25/09/2026, após o deploy `full` #1466)

- PR #34 mesclado e publicado; migrações `20260924_1400` e `1500` aplicadas em `bdversusv2`
  (`alembic_version = 20260924_1500`; tabelas `knowledge_chunk_embeddings` e
  `knowledge_embedding_usage_events` criadas). Backup manual #299 antes do deploy.
- A funcionalidade está **desligada**: sem `KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED` e sem variáveis
  `KNOWLEDGE_*` ou chave de embeddings no servidor.

## Plano de habilitação em produção (não executado)

**Lacunas de código que impedem a habilitação apenas por configuração** (verificadas em
`origin/main`, `804678278`):

1. **Nenhum provedor de embeddings era injetado em runtime** (verificado em `804678278`).
   `KnowledgeQueryService()` é criado sem `embedding_provider` em `src/core/mcp_knowledge_tools.py`,
   `src/intelligence/knowledge_tools.py` e `services/knowledge/interaction_service.py`; sem
   provedor a recuperação recua para busca textual (`embedding_provider_missing`), e nenhum
   chamador pede a estratégia `hybrid`, então ligar a flag e a chave não alterava a resposta.
   **Resolvida no branch `codex/rag-embedding-provider-wiring`** (desligada por padrão, sem mudar o
   comportamento atual): o serviço resolve o provedor do ambiente por
   `build_default_embedding_provider()` (exige, juntos, flag ligada, modelo/versão/geração e
   `OPENAI_API_KEY`; senão `None`), passar `embedding_provider=None` explícito continua significando
   "sem provedor", o SDK é criado só na primeira consulta com tempo limite de 8 s e 1 tentativa, e
   qualquer falha recua para busca textual (`vector_retrieval_failed`). Sem estratégia pedida, o
   padrão passa a ser `hybrid` **apenas** com tudo pronto e a empresa dentro do piloto
   (`KNOWLEDGE_VECTOR_PILOT_COMPANY_IDS`, ids separados por vírgula; vazio libera todas as empresas
   quando a flag está ligada, e uma lista inválida bloqueia todas). Consequência: cada pergunta
   passa a enviar o texto da pergunta ao provedor de embeddings (custo pequeno, mas recorrente).
2. **A atualização automática não gera embeddings.** `services/knowledge/auto_update_service.py`
   não referencia embeddings; trechos novos ou alterados ficam sem vetor (o checksum obsoleto é
   descartado com segurança) até alguém rodar `scripts/knowledge_embedding_backfill.py`. Decidir
   entre rodar o backfill após cada atualização ou integrá-lo ao serviço.
3. **Índice vetorial.** A migração `1400` não cria índice HNSW; ele só entra após medição no golden
   set (piloto). Com o corpus atual (cerca de 3,6 mil tokens) a busca exata basta.

**Passos, na ordem** (cada um exige aprovação do operador; o agente não manipula a chave):

1. Publicar o código da lacuna 1 (PR do branch acima, 16 testes novos com o SDK simulado; sem rede
   nem chave) por deploy `quick` (não há migrações), com a flag ainda desligada.
2. **Chave.** O app já tem uma chave OpenAI funcionando, gerida na tela de integrações (serviço
   `ai`); o mesmo resolvedor que o restante do app usa (`resolve_openai_api_key`, com o banco como
   fonte) é agora consultado pelo runtime e pelo backfill, então **não é preciso criar outra chave
   para começar**. Ordem: `KNOWLEDGE_OPENAI_API_KEY` (opcional, dedicada) > chave das integrações
   do app > `OPENAI_API_KEY` do ambiente. Consequência: o limite mensal de gasto do projeto dessa
   chave cobre o app inteiro. Para um teto só do conhecimento, o operador cria no painel do
   provedor um projeto dedicado com **limite mensal** (sugestão US$ 10) e grava a chave no `.env`
   do servidor como `KNOWLEDGE_OPENAI_API_KEY`. Trocar a chave nas integrações (desativar uma e
   ativar outra) vale para o app e para o RAG sem novo deploy, mas o runtime consulta as
   integrações uma vez por criação do serviço de consulta (uma leitura simples do banco por
   pergunta enquanto a flag estiver ligada e não houver chave dedicada). Definir
   `KNOWLEDGE_EMBEDDING_MODEL=text-embedding-3-small`, `KNOWLEDGE_EMBEDDING_VERSION=v1`,
   `KNOWLEDGE_EMBEDDING_INDEX_GENERATION=1`, `KNOWLEDGE_VECTOR_PILOT_COMPANY_IDS=<ids da empresa
   piloto>` e `KNOWLEDGE_EMBEDDING_PRICE_PER_MILLION_USD` (conferir o preço vigente no provedor).
   **Não** ligar ainda `KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED`.
3. Simulação: `python scripts/knowledge_embedding_backfill.py` (não chama o provedor). Depois
   `--execute --max-chunks 5` e conferir os tokens e o custo estimado em
   `knowledge_embedding_usage_events` e em `knowledge_index_runs.metadata_json`.
4. Backfill completo da primeira onda (`product_help`), depois de conferir o custo do passo 3.
5. Ligar `KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED=true`, reiniciar o web e o MCP e validar em empresa
   piloto, comparando a precisão com o golden set (`knowledge/golden_sets/`) contra a busca
   textual. Só então decidir o índice HNSW e a ampliação para outras fontes.
6. **Reversão:** desligar a flag e reiniciar volta à busca textual imediatamente. As tabelas podem
   ficar; o `downgrade` das migrações remove só a projeção vetorial (ensaiado nesta máquina).

## Piloto em produção e avaliação A/B (25/09/2026)

Estado: backfill do `product_help` executado pelo operador (76 de 76 trechos, `run_id` 131902 e
131903, 10.891 tokens reais; o estimador da simulação subestima cerca de 1,8×), flag ligada e piloto
na empresa 9. O catálogo `product_help` inclui as entradas de navegação compiladas do menu
(`manual_catalog_compiler`), não só os arquivos JSON de `knowledge/product_help/`.

Primeira comparação (2 perguntas, empresa 8 em busca textual × empresa 9 em híbrida, mesmo
universo de fontes; dados de `knowledge_interactions`): "como faço um lançamento financeiro?" citou
"Acessar Lançamento Rápido" na textual e "Realizar uma conciliação bancária" na híbrida (a textual
foi a resposta mais direta); "como cadastro um projeto?" deu 0 citações nas duas. Amostra pequena:
é um sinal, não uma prova.

**Como decidir com dados:** `scripts/knowledge_strategy_ab.py` roda as mesmas perguntas em cada
estratégia para uma empresa e compara a fonte citada com a esperada (acerto no 1º resultado, no
top-k e MRR), listando as divergências. No servidor, a flag vale só para o processo:

```text
KNOWLEDGE_VECTOR_RETRIEVAL_ENABLED=true FLASK_CONFIG=production APP_BOOTSTRAP_DB_SCHEMA=0 \
APP_BOOTSTRAP_RUNTIME_SERVICES=0 <python do virtualenv> scripts/knowledge_strategy_ab.py --company-id 9
```

- Casos: o golden set (`knowledge/golden_sets/sapiens_fase1_product_help_pt_br.json`) mais
  `knowledge/golden_sets/ab_perguntas_pt_br.tsv` (`pergunta<TAB>esperado1|esperado2`; esperado
  `-` = a resposta correta é a abstenção; sem esperado = só compara as estratégias). Amplie o TSV
  com as perguntas reais dos usuários antes de decidir.
- Modo `answer` (padrão) mede o que o usuário vê; `--mode search` mede só o ranking. `--json` dá
  a saída completa. Só lê; cada consulta híbrida registra 1 evento `query` (~10 tokens).
- Regra sugerida: ampliar o piloto somente se, em pelo menos 30 perguntas com esperado, o híbrido
  for igual ou melhor que a textual em acerto@1 e MRR. Se for pior, ajustar o ranking (por exemplo
  mais peso ao textual, ou vetor apenas como reserva quando a busca textual vem vazia) ou desligar.

## Limites

- O ensaio provou migration, isolamento e rollback em PostgreSQL 14 e 16 com pgvector, e a
  migração já roda em produção. O piloto provou que a busca vetorial executa e custa centavos de
  milésimo; **ainda não provou ganho de qualidade** (ver a avaliação A/B acima).
- Atualizações do pgvector exigem novo pedido ao suporte do Configr.

## Resultado do A/B de 25/09/2026 e correção da fusão híbrida

Primeira medição em produção (empresa 9, 10 perguntas com esperado, modo `answer`): `full_text` acerto@1 = 9, MRR 0,90, 2 abstenções; `hybrid` acerto@1 = 6, MRR 0,60, 5 abstenções. Regra de decisão não atendida; piloto não ampliado.

Causas confirmadas na reprodução local: (1) sem limiar de similaridade, o vizinho mais próximo era devolvido mesmo sem relação; (2) trechos sem vetor recebiam pesos redistribuídos e podiam superar artigos indexados. Os "sem resultado" de produção não reproduziram localmente.

Correção: a estratégia `hybrid` agora preserva a ordem do FTS e o vetor só **resgata** trechos que o FTS não trouxe, com similaridade ≥ `KNOWLEDGE_VECTOR_MIN_SIMILARITY` (padrão 0,35; valor inválido volta ao padrão). Consequência: o híbrido nunca fica abaixo do FTS em abstenção. A soma ponderada (`HybridRankingPolicy`) segue no código, sem uso na fusão.

Reavaliar após o deploy com `python scripts/knowledge_strategy_ab.py --company-id 9`; para inspecionar candidatos e similaridades, `--mode search --json`. Calibrar o limiar com esses números antes de ampliar o piloto.
