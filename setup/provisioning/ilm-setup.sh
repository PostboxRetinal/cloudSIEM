#!/usr/bin/env sh
set -e

echo "Esperando que el cluster este listo..."
sleep 15

echo "=== Configurando contrasena de kibana_system ==="
curl -s -X POST --cacert /certs/ca/ca.crt \
  -u "elastic:${ELASTIC_PASSWORD}" \
  "https://es01:9200/_security/user/kibana_system/_password" \
  -H "Content-Type: application/json" \
  -d "{\"password\":\"${KIBANA_PASSWORD}\"}"

echo ""
echo "=== Creando ILM policy: siem-logs-policy (30 dias) ==="
curl -s -X PUT --cacert /certs/ca/ca.crt \
  -u "elastic:${ELASTIC_PASSWORD}" \
  "https://es01:9200/_ilm/policy/siem-logs-policy" \
  -H "Content-Type: application/json" \
  -d @/setup/ilm-policy.json

if [ -f /setup/component-settings.json ]; then
  echo ""
  echo "=== Creando component templates ==="
  curl -s -X PUT --cacert /certs/ca/ca.crt \
    -u "elastic:${ELASTIC_PASSWORD}" \
    "https://es01:9200/_component_template/siem-settings" \
    -H "Content-Type: application/json" \
    -d @/setup/component-settings.json
else
  echo "=== Omitiendo component template: /setup/component-settings.json no existe ==="
fi

echo ""
echo "=== Creando ingest pipelines ==="
if [ -f /setup/geoip-pipeline.json ]; then
  curl -s -X PUT --cacert /certs/ca/ca.crt \
    -u "elastic:${ELASTIC_PASSWORD}" \
    "https://es01:9200/_ingest/pipeline/geoip-pipeline" \
    -H "Content-Type: application/json" \
    -d @/setup/geoip-pipeline.json
  echo " Ingest pipeline: geoip-pipeline creado"
fi

echo ""
echo "=== Creando index templates ==="
for tpl in siem-syslog siem-nginx siem-auth siem-k8s siem-errors logs-mapping; do
  template_file="/setup/template-${tpl}.json"
  if [ -f "$template_file" ]; then
    curl -s -X PUT --cacert /certs/ca/ca.crt \
      -u "elastic:${ELASTIC_PASSWORD}" \
      "https://es01:9200/_index_template/${tpl}" \
      -H "Content-Type: application/json" \
      -d @"$template_file"
  else
    echo "Skipping missing index template: $template_file"
  fi
  echo ""
done

echo "=== ILM y templates configurados correctamente ==="
curl -s --cacert /certs/ca/ca.crt \
  -u "elastic:${ELASTIC_PASSWORD}" \
  "https://es01:9200/_cluster/health?pretty"
