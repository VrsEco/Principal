# Triagem SE-COORD v1

Classe: **Playbook**. Status: implementação local, sem rollout remoto.
Fonte: `docs/spec/squad_engenharia_orquestracao_contexto_modelos_v1.md`, seção 16.

1. Receber objetivo, referências mínimas e escopo explícito. Não carregar catálogo/documentação inteira.
2. Consultar a entrada local `scripts/assess_engineering_task.py` com JSON validado.
3. Conferir `requires_clarification`, `unknowns` e `reasons`; dúvida relevante permanece no SE-COORD.
4. Usar o especialista recomendado apenas dentro da autorização existente. A recomendação não abre sessão, troca modelo, dispara agente ou amplia permissões.
5. Segurança/tenant: Arquiteto obrigatório; migração: DBA obrigatório; implementação: evidência QA.
6. Para ação operacional, resolver identidade, empresa e discovery MCP antes de agir. `company_id` do assessment não concede acesso.
7. Encerrar somente a fase autorizada com resultados dos testes e limites explícitos. Sem deploy nesta fase.

Na ativação de `Sapiens Engenharia`, consumir o manifesto do bootstrap canônico ou de `SapiensActivationService`, sem criar catálogo/tool paralelo. Ele é orientação local: encaminha para o entrypoint já existente, mantém a escolha do modelo manual e não executa especialista nem lê dados operacionais.

Para interação guiada pelo MCP, após selecionar `engineering`, enviar `engineering_task` ao `resolve_app32_sapiens_activation_tool`. Informar somente `task_id`, `objective` e os opcionais técnicos permitidos. O retorno `guided_triage` orienta o próximo contexto; não contém especialista selecionado e rejeita campos de autoridade ou contexto empresarial declarados pelo chamador.

## Sapiens Engenharia — complexidade e economia de contexto

Ao enviar a tarefa, usar opcionalmente `task_intent`: `execution`, `correction` ou `planning`. O SE-COORD informa complexidade e a estratégia de contexto; não escolhe Astra, Terra, 5.5, provider ou esforço. Segurança, tenant, migração e incidente prevalecem sobre uma intenção baixa declarada.

- Baixa: objetivo + fonte/função afetada + teste/evidência direta; continuidade por delta.
- Média: símbolo/contrato + dependências diretas + regressão; expandir uma dependência por vez.
- Alta: resumo arquitetural versionado + decisões + invariantes; só então carregar trechos necessários.
- Ambígua: esclarecer domínio/arquivo antes de anexar material adicional.

Manter ACTIVE no mínimo necessário, WARM como referência recuperável e DROPPED fora do pacote. Para dados empresariais, só obter evidência via adapter MCP autenticado e com escopo `company_id`; a triagem não autentica nem concede permissão.

Caso desconhecido ou misto sem prioridade clara: perguntar pelo domínio líder ou reunir evidência; não inferir certeza. Regras lexicais são conservadoras, inclusive com negações; revisar a razão antes de agir. Dados operacionais antigos não impedem testes unitários, mas não sustentam validação de integração.

## Context Governor — Fase 2 local

1. Fixar tarefa e identidade do Working Set; obter bundle confiável do registry. Contexto de outra empresa, usuário, permissão, harness ou surface não é reaproveitável.
2. Adicionar somente snapshots necessários, com motivo, origem, versão e dependências. ACTIVE participa do pacote; WARM/DROPPED não são reinjetados.
3. Antes da composição, revalidar fingerprints das fontes. Mudança de bundle exige refresh; mudança de fonte invalida o item e dependentes. Reativação exige motivo e fingerprint atual.
4. Conferir pacote: `ready=false` bloqueia envio; `ready=true` ainda exige revisar `deferred_ids`, `stale_ids`, razões e pendências da triagem. Orçamento não pode remover governança.
5. Usar delta somente sobre o pacote anterior indicado; não afirmar que ele limpa a memória do modelo. Não iniciar nova sessão ou handoff nesta fase.

O limite é estimado por bytes UTF-8/4, não pelo tokenizer do provider. A CLI conhece snapshots fornecidos, não os arquivos reais; para contexto empresarial a futura integração deve autenticar e autorizar a leitura das fontes antes de usar o service.

## Fase 3 — lifecycle local

Complemento Fase 4: aplicar Quality Gate programático após composição e coleta de evidências. Não transformar checks desconhecidos em PASS. Segurança/tenant ou efeitos incertos interrompem; ambiente não justifica escalada de modelo. Retries e revisões especializadas são recomendações limitadas, nunca execução automática. Validação local não encerra pendência operacional.

Usar `scripts/squad_engineering.py` para status/context/why/model/handoff e auxiliares decide/resume, conforme runbook. SAME preserva tarefa; EXTEND exige dependência explícita; ROTATE recomenda separação, sem criar tarefa automaticamente. Handoff exporta apenas referências e notas explicitamente revisadas; retomada valida identidade, registry e fontes, mas não executa nada. Checksum não autentica autoria; não persistir contexto empresarial neste adapter. Fases 4–6 permanecem pendentes.
