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
import sys
import urllib3
from datetime import datetime, timezone

try:
    import requests
    import urllib3
except ImportError:
    print("Error: requiere 'requests' y 'urllib3'. Instalar con: pip install requests urllib3")
    sys.exit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

THRESHOLD = 95.0

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

EXIT_INDICES = [
    "logs-nginx-*",
    "logs-auth-*",
    "logs-syslog-*",
    "logs-k8s-*",
]
ERROR_INDEX = "logs-errors-*"


def count_docs(session, host, index_pattern, cacert):
    """Cuenta documentos en un patron de indice."""
    url = f"{host}/{index_pattern}/_count"
    try:
        r = session.get(url, verify=cacert, timeout=10)
        if r.status_code == 404:
            return 0
        r.raise_for_status()
        return r.json().get("count", 0)
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(description="Verificar tasa de parseo Logstash > 95% (R8.3)")
    parser.add_argument("--host",     default="https://localhost:9200")
    parser.add_argument("--user",     default="elastic")
    parser.add_argument("--password", default="SiemElastic2026!")
    parser.add_argument("--cacert",   default=None)
    parser.add_argument("--insecure", action="store_true",
                        help="Deshabilitar verificacion de certificado")
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  Verificacion de Tasa de Parseo - R8.3{RESET}")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"  Host Elasticsearch: {args.host}")
    print(f"  Umbral requerido:   > {THRESHOLD}%\n")

    session = requests.Session()
    session.auth = (args.user, args.password)
    cacert = False if args.insecure else args.cacert

    total_exit = 0
    counts_by_index = {}

    print(f"{CYAN}--- Conteo de documentos por indice ---{RESET}")

    for pattern in EXIT_INDICES:
        count = count_docs(session, args.host, pattern, cacert)
        counts_by_index[pattern] = count
        total_exit += count
        status = f"{GREEN}{count:>8,}{RESET}"
        print(f"  {pattern:20s} {status} docs (parseo exitoso)")

    errors = count_docs(session, args.host, ERROR_INDEX, cacert)
    counts_by_index[ERROR_INDEX] = errors
    status = f"{RED if errors > 0 else GREEN}{errors:>8,}{RESET}"
    print(f"  {'logs-errors-*':20s} {status} docs (parseo FALLIDO)")

    total_all = total_exit + errors

    if total_all == 0:
        print(f"\n{YELLOW}  No hay datos en Elasticsearch.{RESET}")
        print("  Genera logs primero: python3 setup/generate-normal-logs.py --source all")
        sys.exit(0)

    parse_rate = (total_exit / total_all) * 100

    print(f"\n{CYAN}--- Resultado ---{RESET}")
    print(f"  Total documentos procesados:  {total_all:>8,}")
    print(f"  Parseo exitoso:               {total_exit:>8,}")
    print(f"  Parseo fallido (errores):     {errors:>8,}")
    print(f"")

    if parse_rate >= THRESHOLD:
        print(f"  Tasa de parseo: {GREEN}{parse_rate:.2f}%{RESET} >= {THRESHOLD}% -> {GREEN}OK{RESET}")
    else:
        print(f"  Tasa de parseo: {RED}{parse_rate:.2f}%{RESET} < {THRESHOLD}% -> {RED}FALLIDO{RESET}")
        print(f"\n  {YELLOW}Revision recomendada:{RESET}")
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
        print(f"  {GREEN}CONCLUSION: R8.3 CUMPLE (tasa {parse_rate:.2f}% > {THRESHOLD}%){RESET}")
    else:
        print(f"  {RED}CONCLUSION: R8.3 NO CUMPLE (tasa {parse_rate:.2f}% < {THRESHOLD}%){RESET}")
    print(f"{BOLD}{'='*55}{RESET}\n")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
