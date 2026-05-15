#!/usr/bin/env python3
"""
verify-parse-rate.py
Verifica que la tasa de parseo del pipeline Logstash sea superior al 95% (R8.3).
Conecta a Elasticsearch, cuenta documentos en indices exitosos vs errores.

Uso:
    python3 verify-parse-rate.py
    python3 verify-parse-rate.py --host https://localhost:9200 --insecure
    python3 verify-parse-rate.py --host https://localhost:9200 --user elastic --password <pass>
"""

import argparse
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

urllib3_disable_warnings = False
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# ─── Configuración ────────────────────────────────────────────────────────────────
THRESHOLD = 95.0
EXIT_INDICES = [
    "logs-syslog-*",
    "logs-auth-*",
    "logs-nginx-*",
    "logs-k8s-*",
]
ERROR_INDEX = "logs-errors-*"

# Colores
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
B = "\033[94m"; W = "\033[1m";  X = "\033[0m"; CYAN = "\033[36m"
BOLD = "\033[1m"; RESET = "\033[0m"

def count_docs(session, host, index_pattern, cacert):
    """Cuenta documentos en un patrón de índices."""
    url = f"{host}/{index_pattern}/_count"
    try:
        r = session.get(url, verify=cacert, timeout=10)
        if r.status_code == 404:
            return 0
        r.raise_for_status()
        return r.json().get("count", 0)
    except Exception as e:
        raise RuntimeError(f"Error consultando {index_pattern}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Verificar tasa de parseo de logs")
    parser.add_argument("--host",     default="https://localhost:9200")
    parser.add_argument("--user",     default="elastic")
    parser.add_argument("--password", default="SiemElastic2026!")
    parser.add_argument("--cacert",   default=os.getenv("CACERT", "./setup/certs/ca/ca.crt"))
    parser.add_argument("--insecure", action="store_true", help="Deshabilitar verificación TLS")
    args = parser.parse_args()

    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Verificacion de Tasa de Parseo - R8.3")
    print(f"  {datetime.now(timezone(timedelta(hours=-5))).strftime('%Y-%m-%d %H:%M:%S UTC-5')}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Host Elasticsearch: {args.host}")
    print(f"  Umbral requerido:   > {THRESHOLD}%\n")

    session = requests.Session()
    session.auth = (args.user, args.password)
    cacert = False if args.insecure else (args.cacert or True)

    total_exit = 0
    counts_by_index = {}

    print(f"{CYAN}--- Conteo de documentos por indice ---{RESET}")

    try:
        for pattern in EXIT_INDICES:
            count = count_docs(session, args.host, pattern, cacert)
            counts_by_index[pattern] = count
            total_exit += count
            status = f"{G}{count:>8,}{RESET}"
            print(f"  {pattern:20s} {status} docs (parseo exitoso)")

        errors = count_docs(session, args.host, ERROR_INDEX, cacert)
    except RuntimeError as exc:
        print(f"\n{R}  Error verificando Elasticsearch:{RESET} {exc}")
        sys.exit(2)

    counts_by_index[ERROR_INDEX] = errors
    status = f"{R if errors > 0 else G}{errors:>8,}{RESET}"
    print(f"  {'logs-errors-*':20s} {status} docs (errores de parseo)")

    total_all = total_exit + errors

    if total_all == 0:
        print(f"\n{Y}  No hay datos en Elasticsearch.{RESET}")
        print("  Genera logs primero: python3 setup/generate-normal-logs.py --source all")
        sys.exit(0)

    parse_rate = (total_exit / total_all) * 100

    print(f"\n{CYAN}--- Resultado ---{RESET}")
    print(f"  Total documentos procesados:  {total_all:>8,}")
    print(f"  Parseo exitoso:               {total_exit:>8,}")
    print(f"  Parseo fallido (errores):     {errors:>8,}")
    print(f"")

    if parse_rate >= THRESHOLD:
        print(f"  Tasa de parseo: {G}{parse_rate:.2f}%{RESET} >= {THRESHOLD}% -> {G}OK{RESET}")
    else:
        print(f"  Tasa de parseo: {R}{parse_rate:.2f}%{RESET} < {THRESHOLD}% -> {R}FALLIDO{RESET}")
        print(f"\n  {Y}Revision recomendada:{RESET}")
        print(f"  - Verificar patrones grok en logstash/pipeline/")
        print(f"  - Revisar logs de Logstash: docker logs siem-logstash | tail -50")
        print(f"  - Verificar indice de errores: curl -k {args.host}/{ERROR_INDEX}/_search?pretty")

    print(f"\n{CYAN}--- Detalle por fuente ---{RESET}")
    for pattern, count in counts_by_index.items():
        pct = (count / total_all * 100) if total_all > 0 else 0
        bar_len = 40
        filled = int(bar_len * pct / 100)
        bar = f"{'#' * filled}{'-' * (bar_len - filled)}"
        print(f"  {pattern:20s} [{bar}] {pct:5.1f}%")

    passed = parse_rate >= THRESHOLD
    print(f"\n{BOLD}{'='*55}{RESET}")
    if passed:
        print(f"  {G}CONCLUSION: R8.3 CUMPLE (tasa {parse_rate:.2f}% > {THRESHOLD}%){RESET}")
    else:
        print(f"  {R}CONCLUSION: R8.3 NO CUMPLE (tasa {parse_rate:.2f}% < {THRESHOLD}%){RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")

    sys.exit(0 if passed else 1)

if __name__ == "__main__":
    main()
