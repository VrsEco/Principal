# Paper — Motor Corporativo de Eventos + BPMS + Catálogo Unificado de Automações

Status: em evolução  
Classe: Paper

## 1. Tese

O APP32 não deve ter um “super motor de faturamento”.

Deve ter:

- um **motor corporativo de eventos e regras**;
- **serviços de domínio** por módulo;
- o **BPMS** como camada de jornada humana, exceção e aprovação;
- um **catálogo unificado de automações** visível no mesmo lugar para BPMS e motor.

## 2. Problema

Sem essa separação, surgem dois erros:

1. colocar regra estrutural de domínio dentro do BPMS;
2. espalhar automações em lugares diferentes, sem visão única operacional.

## 3. Direção proposta

### 3.1. Motor corporativo

Responsável por:

- receber eventos;
- avaliar regras;
- disparar ações;
- registrar execuções;
- garantir idempotência e reversão.

### 3.2. Serviços de domínio

Responsáveis por executar a regra real:

- contratos;
- faturamento;
- financeiro;
- fiscal.

### 3.3. BPMS

Responsável por:

- aprovações;
- exceções;
- tarefas humanas;
- SLA;
- trilha operacional visual.

## 4. Catálogo unificado de automações

O usuário deve enxergar tudo no mesmo lugar.

Cada automação deve ter:

- `automation_origin`: `bpms` | `event_engine`
- `domain_key`
- `trigger_type`
- `action_type`
- `execution_mode`: `automatic` | `manual_release` | `approval_required`
- `status`

## 5. Princípio de integração

> BPMS e motor compartilham visibilidade, mas não se confundem.

O motor executa automação determinística.  
O BPMS governa jornada, exceção e decisão humana.

## 6. Exemplo

### Faturamento contratual

- evento: `CONTRACT_BILLING_DUE`
- motor avalia regra
- serviço de faturamento gera competência
- automação aparece no catálogo unificado como origem `event_engine`

### Aprovação excepcional

- evento gera necessidade de revisão
- motor abre processo no BPMS
- automação aparece no mesmo catálogo, agora com origem `bpms`

