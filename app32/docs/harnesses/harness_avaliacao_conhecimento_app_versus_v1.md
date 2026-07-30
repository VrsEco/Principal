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
