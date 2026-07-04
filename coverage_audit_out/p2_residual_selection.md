# P2 residual - Robô de Testes

Total P2 residual: 37

## Itens
- route | <int:note_id> app32\api\notes.py delete | `/<int:note_id>` | `app32\api\notes.py`
- route | <int:note_id> app32\api\notes.py put | `/<int:note_id>` | `app32\api\notes.py`
- route | consultive | `/consultive/cockpit/fronts/<front_key>` | `app32\api\routes\urgent_business_review.py`
- route | debug | `/debug/routes` | `app32\api\routes\dev.py`
- route | email app32\api\webhooks\email_webhook.py post | `/email` | `app32\api\webhooks\email_webhook.py`
- route | health | `/health/live` | `app32\api\routes\health.py`
- route | health | `/health/ready` | `app32\api\routes\health.py`
- route | health app32\api\routes\health.py get | `/health` | `app32\api\routes\health.py`
- route | incentives | `/incentives/calculate/run` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/closing/<int:calc_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/closing/<int:calc_id>/<action>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/harvest/run` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/participants/<int:participant_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/reports` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/rules/<int:rule_set_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/rules/<int:rule_set_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/rules/<int:rule_set_id>/participants` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/rules/<int:rule_set_id>/vetores` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/rules/new` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/seed-mock` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/spider-web` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/statement` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/statement/<int:calc_id>/<int:employee_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/validation` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/vetores/<int:vetor_id>` | `app32\api\routes\incentives.py`
- route | incentives | `/incentives/vetores/<int:vetor_id>/range` | `app32\api\routes\incentives.py`
- route | incentives app32\api\routes\incentives.py get | `/incentives` | `app32\api\routes\incentives.py`
- route | internal_audit app32\api\routes\internal_audit.py get | `/internal-audit` | `app32\api\routes\internal_audit.py`
- route | main app32\api\routes\main.py get | `/main` | `app32\api\routes\main.py`
- template | mcp_sapiens | `app32/templates/agent_surface_wrapper.html` | `app32/templates/agent_surface_wrapper.html`
- template | mcp_sapiens | `app32/templates/modules/operations/ai_tools_catalog.html` | `app32/templates/modules/operations/ai_tools_catalog.html`
- route | okrs | `/okrs/new` | `app32\api\routes\okr.py`
- route | okrs app32\api\routes\okr.py get | `/okrs` | `app32\api\routes\okr.py`
- route | ping | `/ping/dependencies` | `app32\api\routes\dev.py`
- route | seed_demo app32\api\routes\dev.py get | `/seed-demo` | `app32\api\routes\dev.py`
- route | telegram app32\api\webhooks\telegram_webhook.py post | `/telegram` | `app32\api\webhooks\telegram_webhook.py`
- route | trigger_proactive app32\api\routes\dev.py get | `/trigger-proactive` | `app32\api\routes\dev.py`
