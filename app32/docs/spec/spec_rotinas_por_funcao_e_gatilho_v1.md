# SPEC — Rotinas por Função e Gatilho

**Classificação:** SPEC  
**Confidencialidade:** Uso interno e restrito ao APP Versus  
**Status:** Decisão oficial  
**Versão:** 1.0 — 2026-09-01

## 1. Objetivo

Suportar rotinas programadas, contínuas por gatilho e híbridas, vinculando responsabilidade e execução a funções organizacionais e resolvendo seus ocupantes dinamicamente.

## 2. Modos de execução

| Modo | Agenda | Gatilho | Comportamento |
|---|---:|---:|---|
| `scheduled` | obrigatório | não | o agendador cria as instâncias |
| `triggered` | não | obrigatório | um evento cria ou deixa a instância aguardando confirmação |
| `hybrid` | sim | sim | agenda e eventos podem criar instâncias |

## 3. Funções

- Uma rotina aceita no máximo uma função `responsible`.
- Uma rotina aceita N funções `executor`.
- Distribuição executora:
  - `collective`: uma instância com todos os ocupantes;
  - `individual`: uma instância para cada ocupante;
  - `pool`: uma instância sem executor individual, disponível à função.
- Vínculos diretos já existentes em `routine_collaborators` permanecem como exceção/override compatível.
- Os ocupantes ativos são obtidos de `employees.role_id`, sempre com o mesmo `company_id`.

## 4. Gatilhos

- Cada gatilho possui código canônico, nome, origem e política de ativação.
- `automatic`: processa o evento imediatamente.
- `confirmation`: registra o evento como pendente e exige confirmação humana.
- `event_key` é idempotente por empresa e gatilho.
- A instância registra código determinístico, payload do evento e fotografia de funções/ocupantes.

## 5. Modelo de dados

- `routines.execution_mode`.
- `routine_role_assignments`: empresa, rotina, função, tipo, distribuição e horas.
- `routine_triggers`: empresa, rotina, código, origem, política e configuração.
- `routine_trigger_events`: empresa, gatilho, chave idempotente, payload, status e instâncias criadas.
- Toda consulta e chave operacional inclui `company_id`; referências cruzadas entre empresas são inválidas.

## 6. Contratos HTTP

- `GET|PUT /api/companies/{company_id}/process-routines/{routine_id}/execution-rule`
- `POST /api/companies/{company_id}/routine-events`
- `POST /api/companies/{company_id}/routine-trigger-events/{event_id}/confirm`

Payload mínimo de evento:

```json
{
  "trigger_code": "novo_pedido_recebido",
  "event_key": "pedido:12345",
  "payload": {"pedido_id": 12345}
}
```

## 7. Interface

- A tela da rotina expõe `Modo de execução`.
- A aba `Regra de Execução` gerencia responsável, funções executoras, distribuição, gatilhos e eventos pendentes.
- Campos de agenda ficam ocultos no modo contínuo por gatilho.
- A listagem diferencia visualmente rotinas programadas, contínuas e híbridas.

## 8. Critérios de aceite

1. Rotina contínua não é processada pelo agendador.
2. Evento duplicado não cria nova instância.
3. Função de outra empresa é rejeitada.
4. Distribuição individual cria uma instância por ocupante ativo.
5. Evento de confirmação não cria instância antes da decisão humana.
6. Cada instância preserva a fotografia do responsável, executores e gatilho.
7. A UI permite configurar o modelo sem exigir colaborador nominal.

