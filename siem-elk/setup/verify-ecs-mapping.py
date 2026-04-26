#!/usr/bin/env python3
"""
verify-ecs-mapping.py
Verifica que los campos ECS estén correctamente mapeados en Elasticsearch.
Comprueba las 4 fuentes de logs: syslog, nginx, auth, kubernetes.

Uso:
    pip install requests
    python3 verify-ecs-mapping.py --host https://localhost:9200 \
            --user elastic --password SiemElastic2024! \
            --cacert ./setup/certs/ca/ca.crt
"""

import argparse
import json
import sys
import urllib3
import requests
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Campos ECS obligatorios por fuente ───────────────────────────────────────
ECS_REQUIRED = {
    "logs-syslog-*": [
        "@timestamp", "host.name", "message",
        "event.dataset", "event.kind", "event.category",
        "log.type",
    ],
    "logs-auth-*": [
        "@timestamp", "host.name", "message",
        "event.dataset", "event.kind", "event.category", "event.outcome",
        "event.action", "user.name", "source.ip",
    ],
    "logs-nginx-*": [
        "@timestamp", "source.ip", "message",
        "http.request.method", "url.original",
        "http.response.status_code", "http.response.body.bytes",
        "event.dataset", "event.kind", "event.category",
    ],
    "logs-k8s-*": [
        "@timestamp", "message",
        "kubernetes.pod.name", "kubernetes.namespace",
        "kubernetes.container.name", "kubernetes.node.name",
        "orchestrator.type", "orchestrator.namespace",
        "event.dataset", "event.kind",
    ],
}

# ─── Colores para terminal ────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def check(condition, ok_msg, fail_msg):
    if condition:
        print(f"  {GREEN}✓{RESET} {ok_msg}")
        return True
    else:
        print(f"  {RED}✗{RESET} {fail_msg}")
        return False


def get_index_stats(session, host, index_pattern, cacert):
    """Obtiene estadísticas básicas del índice."""
    url = f"{host}/{index_pattern}/_stats/docs"
    try:
        r = session.get(url, verify=cacert, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data    = r.json()
        indices = data.get("indices", {})
        total_docs = sum(
            v["primaries"]["docs"]["count"]
            for v in indices.values()
        )
        return {"doc_count": total_docs, "index_count": len(indices)}
    except Exception as e:
        return {"error": str(e)}


def get_sample_doc(session, host, index_pattern, cacert):
    """Obtiene un documento de muestra del índice."""
    url  = f"{host}/{index_pattern}/_search"
    body = {"size": 1, "sort": [{"@timestamp": {"order": "desc"}}]}
    try:
        r = session.post(url, json=body, verify=cacert, timeout=10)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
        return hits[0]["_source"] if hits else None
    except Exception as e:
        return None


def flatten_doc(doc, prefix=""):
    """Aplana un documento anidado para verificar campos ECS."""
    result = {}
    for k, v in doc.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(flatten_doc(v, full_key))
        else:
            result[full_key] = v
    return result


def verify_index(session, host, index_pattern, required_fields, cacert):
    """Verifica un índice completo."""
    print(f"\n{BOLD}{BLUE}── {index_pattern}{RESET}")

    stats = get_index_stats(session, host, index_pattern, cacert)
    if stats is None:
        print(f"  {YELLOW}⚠{RESET}  Índice no encontrado (aún no hay logs)")
        return {"status": "not_found", "pattern": index_pattern}

    if "error" in stats:
        print(f"  {RED}✗{RESET} Error: {stats['error']}")
        return {"status": "error", "pattern": index_pattern}

    print(f"  Documentos: {stats['doc_count']:,} en {stats['index_count']} índice(s)")

    if stats["doc_count"] == 0:
        print(f"  {YELLOW}⚠{RESET}  Sin documentos — genera logs de prueba primero")
        return {"status": "empty", "pattern": index_pattern}

    doc = get_sample_doc(session, host, index_pattern, cacert)
    if not doc:
        print(f"  {YELLOW}⚠{RESET}  No se pudo obtener muestra")
        return {"status": "no_sample", "pattern": index_pattern}

    flat = flatten_doc(doc)
    missing   = []
    present   = []

    for field in required_fields:
        if field in flat:
            present.append(field)
        else:
            missing.append(field)

    # Mostrar resultado por campo
    for f in required_fields:
        val = flat.get(f, "MISSING")
        if val != "MISSING":
            display = str(val)[:60] + "..." if len(str(val)) > 60 else str(val)
            check(True, f"{f} = {YELLOW}{display}{RESET}", "")
        else:
            check(False, "", f"{f} — campo ausente")

    coverage = len(present) / len(required_fields) * 100
    color    = GREEN if coverage == 100 else (YELLOW if coverage >= 80 else RED)
    print(f"\n  Cobertura ECS: {color}{coverage:.0f}%{RESET} "
          f"({len(present)}/{len(required_fields)} campos)")

    return {
        "status":   "ok" if not missing else "partial",
        "pattern":  index_pattern,
        "coverage": coverage,
        "missing":  missing,
        "doc_count": stats["doc_count"],
    }


def check_cluster_health(session, host, cacert):
    """Verifica el estado del cluster."""
    print(f"\n{BOLD}=== Estado del cluster ==={RESET}")
    try:
        r = session.get(f"{host}/_cluster/health", verify=cacert, timeout=10)
        r.raise_for_status()
        h     = r.json()
        color = h.get("status", "unknown")
        emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(color, "⚪")
        print(f"  Estado:  {emoji} {color.upper()}")
        print(f"  Nodos:   {h.get('number_of_nodes', 0)} total, "
              f"{h.get('number_of_data_nodes', 0)} data")
        print(f"  Shards:  {h.get('active_shards', 0)} activos, "
              f"{h.get('unassigned_shards', 0)} sin asignar")
        return color == "green"
    except Exception as e:
        print(f"  {RED}Error conectando al cluster: {e}{RESET}")
        return False


def check_ilm_policy(session, host, cacert):
    """Verifica que el ILM policy esté activo."""
    print(f"\n{BOLD}=== ILM Policy: siem-logs-policy ==={RESET}")
    try:
        r = session.get(
            f"{host}/_ilm/policy/siem-logs-policy",
            verify=cacert, timeout=10
        )
        if r.status_code == 404:
            check(False, "", "ILM policy 'siem-logs-policy' no encontrada — ejecutar init-ilm.sh")
            return False
        r.raise_for_status()
        policy = r.json().get("siem-logs-policy", {}).get("policy", {})
        phases  = policy.get("phases", {})
        for phase in ["hot", "warm", "cold", "delete"]:
            check(phase in phases, f"Fase '{phase}' configurada", f"Fase '{phase}' ausente")
        delete_age = (
            phases.get("delete", {})
            .get("actions", {})
            .get("delete", {})
        )
        age = phases.get("delete", {}).get("min_age", "?")
        check(True, f"Retención configurada a {age}", "")
        return True
    except Exception as e:
        print(f"  {RED}Error: {e}{RESET}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verificar mapeo ECS en índices SIEM")
    parser.add_argument("--host",     default="https://localhost:9200")
    parser.add_argument("--user",     default="elastic")
    parser.add_argument("--password", default="SiemElastic2024!")
    parser.add_argument("--cacert",   default="./setup/certs/ca/ca.crt")
    parser.add_argument("--insecure", action="store_true",
                        help="Deshabilitar verificación de certificado")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*50}")
    print("  Verificación ECS — SIEM Elastic Stack")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*50}{RESET}")
    print(f"  Host:   {args.host}")
    print(f"  Usuario: {args.user}")

    session = requests.Session()
    session.auth = (args.user, args.password)
    cacert = False if args.insecure else args.cacert

    # 1. Cluster health
    cluster_ok = check_cluster_health(session, args.host, cacert)

    # 2. ILM policy
    ilm_ok = check_ilm_policy(session, args.host, cacert)

    # 3. Verificar cada fuente de logs
    print(f"\n{BOLD}=== Verificación de campos ECS por fuente ==={RESET}")
    results = []
    for pattern, fields in ECS_REQUIRED.items():
        result = verify_index(session, args.host, pattern, fields, cacert)
        results.append(result)

    # 4. Resumen
    print(f"\n{BOLD}{'='*50}")
    print("  Resumen")
    print(f"{'='*50}{RESET}")
    print(f"  Cluster:    {'🟢 green' if cluster_ok else '🔴 problema'}")
    print(f"  ILM:        {'✓ ok' if ilm_ok else '✗ no configurado'}")
    print()

    all_ok    = True
    coverages = []
    for r in results:
        status   = r.get("status", "unknown")
        pattern  = r.get("pattern", "")
        coverage = r.get("coverage", 0)
        coverages.append(coverage)

        if status == "ok":
            print(f"  {GREEN}✓{RESET} {pattern:30s} 100% ECS")
        elif status == "partial":
            missing = ", ".join(r.get("missing", []))
            print(f"  {YELLOW}~{RESET} {pattern:30s} {coverage:.0f}% — falta: {missing}")
            all_ok = False
        elif status in ("not_found", "empty"):
            print(f"  {YELLOW}⚠{RESET} {pattern:30s} sin datos aún")
        else:
            print(f"  {RED}✗{RESET} {pattern:30s} error")
            all_ok = False

    avg = sum(coverages) / len(coverages) if coverages else 0
    print(f"\n  Cobertura promedio: {avg:.0f}%")

    # Exit code para CI/CD
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
