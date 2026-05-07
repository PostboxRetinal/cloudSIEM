#!/bin/bash
# add-panels.sh - Agrega paneles a los dashboards

KIBANA_URL="https://kibana:5601"
AUTH="elastic:SiemElastic2026!"
CACERT="/certs/ca/ca.crt"
XSRF="true"

wait_kibana() {
  echo "Esperando a Kibana..."
  for i in {1..30}; do
    if curl -s -u "$AUTH" --cacert "$CACERT" "$KIBANA_URL/api/status" >/dev/null 2>&1; then
      echo "✓ Kibana disponible"
      return 0
    fi
    sleep 2
  done
  echo "✗ Kibana no respondió"
  return 1
}

add_panels() {
  local dashboard_id="$1"
  local panels_json="$2"
  
  echo "Agregando paneles a: $dashboard_id"
  
  curl -X PUT \
    -u "$AUTH" \
    -H "Content-Type: application/json" \
    -H "kbn-xsrf: $XSRF" \
    --cacert "$CACERT" \
    -d "{\"attributes\": {\"panels\": $panels_json}}" \
    "$KIBANA_URL/api/saved_objects/dashboard/$dashboard_id" \
    2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'error' in data:
  print(f'  ✗ {data[\"error\"][\"message\"]}')
  sys.exit(1)
else:
  print(f'  ✓ Paneles agregados')
"
}

main() {
  wait_kibana || exit 1
  
  echo ""
  echo "=== Agregando Paneles a Dashboards ==="
  echo ""
  
  # Paneles ejecutivo
  exec_panels='[
    {"version":"8.3.3","gridData":{"x":0,"y":0,"w":24,"h":12},"type":"visualization","id":"viz-system-health","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":24,"y":0,"w":24,"h":12},"type":"visualization","id":"viz-top-threats","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":0,"y":12,"w":48,"h":12},"type":"visualization","id":"viz-alert-trend","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":0,"y":24,"w":48,"h":15},"type":"visualization","id":"viz-top-ips","embeddableConfig":{}}
  ]'
  
  add_panels "executive-security-overview" "$exec_panels"
  
  # Paneles operacional
  ops_panels='[
    {"version":"8.3.3","gridData":{"x":0,"y":0,"w":24,"h":15},"type":"visualization","id":"viz-top-users","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":24,"y":0,"w":24,"h":15},"type":"visualization","id":"viz-top-ips","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":0,"y":15,"w":48,"h":18},"type":"visualization","id":"viz-alerts-table","embeddableConfig":{}},
    {"version":"8.3.3","gridData":{"x":0,"y":33,"w":48,"h":20},"type":"visualization","id":"viz-events-table","embeddableConfig":{}}
  ]'
  
  add_panels "operational-triage-console" "$ops_panels"
  
  echo ""
  echo "✓ Dashboards configurados"
}

main "$@"
