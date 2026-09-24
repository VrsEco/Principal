#!/usr/bin/env bash
# Smoke pós-deploy: healthz 200 e assets críticos 200 (Chart.js com tipo JavaScript).
# Imprime o JSON de evidência em stdout; sai com 1 se qualquer verificação falhar.
set -uo pipefail

base="${APP32_PUBLIC_BASE_URL:-https://app.gestaoversus.com.br}"
base="${base%/}"
assets=(
  "/static/vendor/chartjs/chart.umd.min.js"
  "/static/vendor/chartjs/chartjs-adapter-date-fns.bundle.min.js"
)

ok=0
health="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "${base}/healthz" || echo 0)"
[ "$health" = "200" ] || ok=1

smoke='{}'
for path in "${assets[@]}"; do
  out="$(curl -sS -o /dev/null -w '%{http_code} %{content_type}' --max-time 20 "${base}${path}" || echo '0 ')"
  code="${out%% *}"
  ctype="${out#* }"
  case "$ctype" in
    *javascript*) ;;
    *) [ "$code" != "200" ] || code=415 ;;
  esac
  [ "$code" = "200" ] || ok=1
  smoke="$(jq -c --arg p "$path" --argjson c "$code" '. + {($p): $c}' <<<"$smoke")"
done

jq -cn --argjson h "$health" --argjson s "$smoke" '{health_status:$h, smoke:$s}'
exit "$ok"
