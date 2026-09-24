#!/usr/bin/env bash
# Callback do workflow oficial ao ledger de deploy (autenticado por OIDC do GitHub Actions).
# Uso: deploy_callback.sh <started|stage|succeeded|failed> [stage_name]
# Entradas por ambiente: DEPLOYMENT_ID, CALLBACK_URL, OIDC_AUDIENCE, EVIDENCE_JSON, FAILURE_REASON.
# Nenhum segredo é aceito, gravado ou impresso: o token OIDC é efêmero e mascarado.
set -euo pipefail

event="${1:?evento obrigatório}"
stage="${2:-}"
: "${DEPLOYMENT_ID:?}" "${CALLBACK_URL:?}" "${OIDC_AUDIENCE:?}"
: "${ACTIONS_ID_TOKEN_REQUEST_URL:?job precisa de permissions: id-token: write}" "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:?}"

if ! [[ "$DEPLOYMENT_ID" =~ ^[0-9a-f]{32}$ ]]; then
  echo "deployment_id inválido" >&2
  exit 1
fi
case "$event" in started|stage|succeeded|failed) ;; *) echo "evento inválido" >&2; exit 1 ;; esac

evidence="${EVIDENCE_JSON:-}"
[ -n "$evidence" ] || evidence='{}'

token="$(curl -fsS -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
  "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=${OIDC_AUDIENCE}" | jq -r '.value')"
echo "::add-mask::${token}"

payload="$(jq -n --arg c "$DEPLOYMENT_ID" --arg e "$event" --arg s "$stage" \
  --arg r "${FAILURE_REASON:-}" --argjson ev "$evidence" \
  '{correlation_id:$c, event:$e, stage:(if $s=="" then null else $s end),
    failure_reason:(if $r=="" then null else $r end), evidence:$ev}')"

curl -fsS -X POST "$CALLBACK_URL" \
  -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" \
  --data "$payload"
echo
