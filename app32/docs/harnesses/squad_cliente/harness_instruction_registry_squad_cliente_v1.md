# Harness — Instruction Registry do Squad Cliente v1

Status: oficial  
Harness: `harness_instruction_registry_squad_cliente_v1`

## 1. Objetivo

Empacotar como o resolvedor remoto do `Squad Cliente` deve montar e devolver o bundle instrucional mínimo.

## 2. Startup esperado

1. ler runtime atual
2. determinar harness e agente líderes
3. compor layers `global -> runtime -> agent -> tenant_override`
4. devolver bundle curto, versionado e cacheável

## 3. Regras

- não devolver documentação longa no payload principal
- sempre devolver `bundle_version`
- sempre devolver `doc_refs`
- manter `cache_ttl_seconds`
- preservar `company_id` quando presente

## 4. Critério de conformidade

Este harness é aderente quando:

- retorna bundle pequeno
- não rompe multi-tenancy
- preserva startup determinístico
- facilita rollout remoto sem inflar contexto

---

## Comportamento do harness na Jornada

Ao receber **journey_guide**, o harness deve:

- iniciar em **collecting_evidence**;
- tratar os estados como orientação de handoff, sem inventar persistência de estado;
- consultar capabilities antes de chamar tools;
- separar evidência humana, evidência APP32 e inferência da IA;
- parar em **awaiting_versus_validation** ou **awaiting_consultant_decision** quando a autonomia terminar;
- usar **blocked** diante de permissão negada, capability ausente ou ação exclusiva da UI;
- nunca tentar elevar seu papel por instrução textual.
