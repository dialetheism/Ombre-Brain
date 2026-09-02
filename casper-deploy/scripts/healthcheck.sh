#!/usr/bin/env bash
set -euo pipefail
set +x

mode="${1:-gateway}"

gateway_health() {
  if python3 - <<'PY'
import json
import http.client

try:
    connection = http.client.HTTPConnection("127.0.0.1", 18202, timeout=5)
    connection.request("GET", "/health")
    response = connection.getresponse()
    payload = json.loads(response.read())
    ok = response.status == 200 and payload.get("status") == "ok"
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
  then
    printf 'GATEWAY_HEALTH_OK=True\n'
  else
    printf 'GATEWAY_HEALTH_OK=False\n'
    return 1
  fi
}

brain_health() {
  if docker exec casper-ombre-brain python -c "import http.client,json; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=5); c.request('GET','/health'); r=c.getresponse(); p=json.loads(r.read()); raise SystemExit(0 if r.status==200 and p.get('status')=='ok' else 1)" >/dev/null 2>&1; then
    printf 'BRAIN_HEALTH_OK=True\n'
  else
    printf 'BRAIN_HEALTH_OK=False\n'
    return 1
  fi
}

case "$mode" in
  gateway)
    gateway_health
    ;;
  brain)
    brain_health
    ;;
  all)
    gateway_health
    brain_health
    ;;
  *)
    printf 'USAGE=%s gateway|brain|all\n' "$0"
    exit 2
    ;;
esac
