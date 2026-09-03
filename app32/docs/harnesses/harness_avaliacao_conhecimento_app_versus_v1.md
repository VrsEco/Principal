# Harness — Avaliação da Camada de Conhecimento do APP Versus v1

**Classe documental:** Harness
**Status:** canônico inicial
**Data:** 2026-07-30
**Domínio:** `knowledge`

## Objetivo

Bloquear regressões de escopo, atualização, citação e qualidade antes de rollout.

## Suíte Fase 0

- adapter descobre catálogo publicado;
- checksum é determinístico;
- alteração muda checksum;
- draft é rejeitado;
- `product_help` rejeita `company_id`;
- source ref duplicado falha;
- sync registra run;
- erro executa rollback e registra falha;
- scheduler registra job;
- migration possui constraints e FTS;
- registry de automações expõe o job.

## Comandos

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest `
  .\app32\tests\test_knowledge_product_help_adapter.py `
  .\app32\tests\test_knowledge_auto_update_service.py `
  .\app32\tests\test_knowledge_repository_contract.py `
  .\app32\tests\test_knowledge_scheduler_contract.py `
  .\app32\tests\test_knowledge_migration_contract.py `
  -q -p no:cacheprovider
```

## Gate

- 100% dos testes da Fase 0 passam;
- zero exposição cross-tenant;
- catálogo inválido falha fechado;
- nenhuma mutação operacional;
- documentos anteriores permanecem disponíveis após falha de sincronização.

## Evolução obrigatória

Adicionar golden questions, precisão de citações, abstenção, conflitos, ACL revogada, temporalidade e prompt injection conforme novos adapters e retrieval forem habilitados.

## Suíte Árvore Estratégica P0

- feature flag é resolvida por empresa;
- árvore, nó, contribuição e auditoria são tenant-owned;
- ID de outro tenant retorna ausência controlada;
- conteúdo confidencial não é serializado para colaborador sem autorização;
- retry com a mesma idempotency key não duplica contribuição;
- API usa a empresa da sessão e rejeita override do cliente;
- escrita web exige CSRF;
- escrita MCP exige `company_id`, `idempotency_key` e confirmação humana;
- tools aparecem no domínio canônico `knowledge` e não promovem dado canônico.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest `
  .\app32\tests\test_strategic_tree_service.py `
  .\app32\tests\test_strategic_tree_routes.py `
  .\app32\tests\test_core_mcp_strategic_tree_tools.py `
  .\app32\tests\test_strategic_tree_ui_contract.py `
  -q
```

## Suíte de linguagem simples e atalho global

- orientação funcional prioriza um manual oficial e não concatena SPEC técnica;
- pergunta explicitamente técnica continua elegível a `system_documentation`;
- conteúdo estruturado preserva listas e opções;
- ações secundárias aceitam apenas rotas internas seguras;
- o atalho global usa `/api/agents/knowledge/answer` sem receber `company_id`;
- tela completa e atalho global mantêm os escopos `all`, `company` e `product`.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest `
  .\app32\tests\test_knowledge_query_service.py `
  .\app32\tests\test_knowledge_product_help_adapter.py `
  .\app32\tests\test_sapiens_knowledge_ui.py `
  .\app32\tests\test_sapiens_widget_knowledge_ui.py `
  -q
```

## Suíte de treinamento supervisionado

- feedback usa escala simples e motivos controlados;
- service de curadoria é tenant-safe;
- rotas de treinamento usam `company_id` da sessão;
- payload do cliente não injeta empresa;
- tela `/sapiens/training` expõe feedbacks, lacunas, propostas e playbooks;
- robô treinador cria propostas revisáveis sem aplicação automática.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH='app32'
python -m pytest `
  .\app32\tests\test_knowledge_feedback_training_contract.py `
  .\app32\tests\test_sapiens_knowledge_ui.py `
  -q
```

## Suíte RAG governado híbrido

- RAG não aceita `company_id` do cliente;
- ACL/grants são aplicados antes de full-text, vetor ou síntese;
- pergunta operacional atual usa MCP/Service/SQL como fonte primária;
- pergunta de uso do produto prioriza `product_help`;
- busca vetorial só roda sobre chunks tenant-safe;
- resposta factual sem citação é rejeitada;
- ausência de evidência gera abstenção;
- conflito entre fontes é exibido;
- termos técnicos de retrieval não aparecem para usuário comum;
- ChromaDB legado não recebe nova responsabilidade produtiva.

Gate mínimo antes de ativar embeddings/`pgvector`:

1. golden set por domínio;
2. teste cross-tenant;
3. teste de ACL revogada;
4. métrica de groundedness;
5. precisão e completude de citações;
6. abstenção correta;
7. custo e latência por empresa;
8. rollback para SQL + full-text.

## Suíte busca citada

- pergunta de ajuda retorna claim e citação;
- ação usa route/URI cadastrada;
- busca corporativa exige empresa ativa;
- consulta de um tenant não encontra conteúdo de outro;
- ausência de evidência gera `knowledge_gap`;
- tool MCP não expõe parâmetro `company_id`;
- capabilities usam o domínio canônico `knowledge`;
- tools organizacionais exigem contexto de empresa.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest `
  .\app32\tests\test_knowledge_query_service.py `
  .\app32\tests\test_core_mcp_knowledge_tools.py `
  -q -p no:cacheprovider
```

## Suíte adapters tenant-owned

- somente a versão publicada mais recente do processo é elegível;
- snapshot visual não entra no conteúdo textual;
- grants de empresa, usuário e colaborador são projetados;
- grant não suportado não amplia acesso;
- reunião concluída projeta ata, discussões, atividades e pauta;
- reunião sem principal identificável falha fechada;
- identificador legado/inexistente de colaborador não vira grant;
- principal divergente não recupera a fonte;
- scheduler registra atualização tenant-owned independente.

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest `
  .\app32\tests\test_knowledge_tenant_adapters.py `
  .\app32\tests\test_knowledge_query_service.py `
  .\app32\tests\test_knowledge_auto_update_service.py `
  .\app32\tests\test_knowledge_scheduler_contract.py `
  .\app32\tests\test_knowledge_migration_contract.py `
  .\app32\tests\test_core_mcp_knowledge_tools.py `
  -q -p no:cacheprovider
```
