#!/bin/bash
# ── Probar el pipeline con líneas de muestra ──────────────────────────────────
# Uso: bash logstash/test-pipeline.sh

echo "=== Test de patrones grok contra líneas de muestra ==="

# Líneas de prueba
NGINX_LINE='185.220.101.34 - - [25/Apr/2024:14:32:01 +0000] "GET /api/v1/users?id=1 HTTP/1.1" 200 1842 "-" "curl/7.68.0"'
AUTH_FAIL='Apr 25 14:32:01 web-01 sshd[12345]: Failed password for root from 185.220.101.34 port 54321 ssh2'
AUTH_OK='Apr 25 14:32:01 web-01 sshd[12345]: Accepted publickey for ubuntu from 192.168.1.20 port 52341 ssh2'
SYSLOG_UFW='Apr 25 14:32:01 web-01 kernel: [123456.789] [UFW BLOCK] IN=eth0 OUT= SRC=185.220.101.34 DST=10.0.0.1 LEN=60 TTL=47 PROTO=TCP SPT=54321 DPT=22'
SQLI_LINE='185.220.101.34 - - [25/Apr/2024:14:32:01 +0000] "GET /api?id=1'"'"' OR '"'"'1'"'"'='"'"'1 HTTP/1.1" 200 512 "-" "sqlmap/1.7.2"'

echo ""
echo "Verificando que Logstash esté levantado..."
curl -s http://localhost:9600/ | python3 -m json.tool | grep -E '"status"|"version"' || echo "ERROR: Logstash no responde en :9600"

echo ""
echo "=== Estadísticas del pipeline ==="
curl -s http://localhost:9600/_node/stats/pipelines/main | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d.get('pipelines', {}).get('main', {}).get('events', {})
print(f'  Eventos in:       {p.get(\"in\", 0):,}')
print(f'  Eventos out:      {p.get(\"out\", 0):,}')
print(f'  Eventos filtrados:{p.get(\"filtered\", 0):,}')
print(f'  Duración (ms):    {p.get(\"duration_in_millis\", 0):,}')
" 2>/dev/null || echo "  No se pudo obtener estadísticas"

echo ""
echo "=== Verificar índices creados ==="
curl -s --cacert ../setup/certs/ca/ca.crt \
  -u "elastic:${ELASTIC_PASSWORD:-SiemElastic2024!}" \
  "https://localhost:9200/_cat/indices/logs-*?v&s=index" 2>/dev/null || \
  echo "  No se puede conectar a ES (ejecutar desde el host con el stack levantado)"

echo ""
echo "=== Tasa de parseo por índice ==="
for idx in logs-nginx logs-auth logs-syslog logs-k8s logs-errors; do
  COUNT=$(curl -s --cacert ../setup/certs/ca/ca.crt \
    -u "elastic:${ELASTIC_PASSWORD:-SiemElastic2024!}" \
    "https://localhost:9200/${idx}-*/_count" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo 0)
  printf "  %-20s %s documentos\n" "${idx}-*:" "$COUNT"
done
