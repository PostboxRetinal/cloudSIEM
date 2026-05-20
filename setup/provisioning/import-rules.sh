#!/usr/bin/env sh
set -e

apk add --no-cache curl > /dev/null

echo "Actualizando all-rules.ndjson..."
python /setup/convert-rules-format.py

echo "Esperando a que Kibana este disponible..."
until curl -s --cacert "${CACERT}" -o /dev/null -w "%{http_code}" "${KIBANA_HOST}" | grep -qE "^(200|302)$"; do
  echo "  esperando a Kibana..."
  sleep 5
done

if [ "${SKIP_PREFLIGHT:-false}" = "true" ]; then
  echo "  SKIP_PREFLIGHT=true, omitiendo comprobacion de Security Solution..."
else
  privileges_code=$(curl -s --cacert "${CACERT}" -o /tmp/detection-privileges.txt -w "%{http_code}" \
    -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
    -H "kbn-xsrf: true" \
    -H "Elastic-Api-Version: 2023-10-31" \
    "${KIBANA_HOST}/api/detection_engine/privileges")
  if [ "${privileges_code}" != "200" ]; then
    echo "  Security Solution APIs are not available (HTTP ${privileges_code}); skipping rule import."
    cat /tmp/detection-privileges.txt
    exit 0
  fi
fi

http_code=$(curl -s --cacert "${CACERT}" -o /tmp/response.txt -w "%{http_code}" \
  -X POST "${KIBANA_HOST}/api/detection_engine/rules/_import?overwrite=true" \
  -H "kbn-xsrf: true" \
  -H "Elastic-Api-Version: 2023-10-31" \
  -u "${ELASTIC_USER}:${ELASTIC_PASSWORD}" \
  --form "file=@/rules/all-rules.ndjson;type=application/x-ndjson")

if [ "${http_code}" != "200" ] || ! grep -q '"success"[[:space:]]*:[[:space:]]*true' /tmp/response.txt; then
  echo "  Error importando reglas"
  cat /tmp/response.txt
  exit 1
fi

echo "  Reglas importadas"
