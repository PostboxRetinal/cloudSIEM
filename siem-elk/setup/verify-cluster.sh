#!/bin/bash
# ── Verificar estado del cluster ELK ─────────────────────────────────────────
set -e
source ../.env

ES_URL="https://localhost:9200"
AUTH="elastic:${ELASTIC_PASSWORD}"

echo "╔══════════════════════════════════════════╗"
echo "║   Verificación del cluster SIEM ELK      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

echo "── Estado del cluster ─────────────────────"
curl -s -k -u $AUTH "$ES_URL/_cluster/health?pretty"

echo ""
echo "── Nodos activos ──────────────────────────"
curl -s -k -u $AUTH "$ES_URL/_cat/nodes?v"

echo ""
echo "── ILM Policy ─────────────────────────────"
curl -s -k -u $AUTH "$ES_URL/_ilm/policy/siem-logs-policy?pretty" | head -30

echo ""
echo "── Índices existentes ──────────────────────"
curl -s -k -u $AUTH "$ES_URL/_cat/indices?v&s=index"

echo ""
echo "── Fase ILM de cada índice ─────────────────"
curl -s -k -u $AUTH "$ES_URL/*/_ilm/explain?pretty" | (python3 -c "
import json, sys
data = json.load(sys.stdin)
for idx, info in data.get('indices', {}).items():
    phase = info.get('phase', 'N/A')
    age   = info.get('age',   'N/A')
    print(f'  {idx:40s} phase={phase:6s} age={age}')
" 2>/dev/null || cat)
