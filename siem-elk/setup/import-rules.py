#!/usr/bin/env python3
"""
import-rules.py
Importa las 5 reglas de detección SIEM a Kibana usando la Security API.
También puede probar cada regla generando eventos sintéticos.

Uso:
    pip install requests
    python3 setup/import-rules.py --action import
    python3 setup/import-rules.py --action test
    python3 setup/import-rules.py --action status
"""

import argparse
import json
import time
import sys
import os
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# ─── Configuración ────────────────────────────────────────────────────────────
KIBANA_URL      = os.getenv("KIBANA_HOST",     "http://localhost:5601")
ES_URL          = os.getenv("ELASTIC_HOSTS",   "https://localhost:9200")
ELASTIC_USER    = os.getenv("ELASTIC_USER",    "elastic")
ELASTIC_PASS    = os.getenv("ELASTIC_PASSWORD","elastic*")
CACERT          = os.getenv("CACERT",          "./setup/certs/ca/ca.crt")
RULES_DIR       = Path("../rules")

# Colores
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"
B = "\033[94m"; W = "\033[1m";  X = "\033[0m"

def kibana_session():
    s = requests.Session()
    s.auth    = (ELASTIC_USER, ELASTIC_PASS)
    s.headers = {
        "kbn-xsrf":     "true",
        "Content-Type": "application/json",
    }
    return s

def es_session():
    s = requests.Session()
    s.auth   = (ELASTIC_USER, ELASTIC_PASS)
    s.verify = CACERT
    return s

# ─── Esperar a que Kibana esté disponible ─────────────────────────────────
def wait_for_kibana(session, kibana_url, timeout_seconds=180):
    print(f"\n{W}=== Esperando a que Kibana esté disponible en {kibana_url} ==={X}")
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = session.get(kibana_url, timeout=10)
            if response.status_code in (200, 302):
                print(f"  {G}Kibana disponible{X}")
                return True
        except requests.exceptions.RequestException:
            pass
        print("  esperando...", end="\r", flush=True)
        time.sleep(5)
    print(f"\n{R}ERROR: Kibana no respondió en {timeout_seconds} segundos{X}")
    return False

# ─── IMPORTAR REGLAS ──────────────────────────────────────────────────────────
def import_rules():
    print(f"\n{W}=== Importando reglas a Kibana SIEM ==={X}")
    session = kibana_session()

    if not wait_for_kibana(session, KIBANA_URL):
        sys.exit(1)

    rule_files = sorted(RULES_DIR.glob("*.json"))
    if not rule_files:
        print(f"{R}No se encontraron archivos .json en {RULES_DIR}{X}")
        sys.exit(1)

    results = {"ok": [], "fail": []}

    for rfile in rule_files:
        rule = json.loads(rfile.read_text())
        name = rule.get("name", rfile.name)
        print(f"\n  Importando: {B}{name}{X}")

        # Intentar crear la regla
        r = session.post(
            f"{KIBANA_URL}/api/detection_engine/rules",
            json=rule,
            verify=False,
            timeout=30,
        )

        if r.status_code == 200:
            rid = r.json().get("id", "?")
            print(f"  {G}✓{X} Creada — id: {rid}")
            results["ok"].append(name)

        elif r.status_code == 409:
            # Ya existe — actualizar con PUT
            print(f"  {Y}~{X} Ya existe — actualizando...")
            rule["rule_id"] = rule.get("id")
            r2 = session.put(
                f"{KIBANA_URL}/api/detection_engine/rules",
                json=rule, verify=False, timeout=30,
            )
            if r2.status_code == 200:
                print(f"  {G}✓{X} Actualizada")
                results["ok"].append(name)
            else:
                print(f"  {R}✗{X} Error al actualizar: {r2.status_code} — {r2.text[:200]}")
                results["fail"].append(name)
        else:
            print(f"  {R}✗{X} Error {r.status_code}: {r.text[:300]}")
            results["fail"].append(name)

    # Habilitar el motor de detección si no está activo
    print(f"\n  Habilitando motor de detección...")
    session.post(
        f"{KIBANA_URL}/api/detection_engine/index",
        json={}, verify=False, timeout=30,
    )

    print(f"\n{W}Resumen:{X}")
    print(f"  {G}✓ Exitosas:{X} {len(results['ok'])}")
    print(f"  {R}✗ Fallidas:{X} {len(results['fail'])}")
    for f in results["fail"]:
        print(f"    - {f}")

# ─── ESTADO DE REGLAS ─────────────────────────────────────────────────────────
def check_status():
    print(f"\n{W}=== Estado de las reglas SIEM ==={X}")
    session  = kibana_session()
    r = session.get(
        f"{KIBANA_URL}/api/detection_engine/rules/_find?per_page=20&filter=alert.attributes.tags:%22SIEM%22",
        verify=False, timeout=30,
    )
    if r.status_code != 200:
        print(f"{R}Error conectando a Kibana: {r.status_code}{X}")
        return

    data  = r.json()
    rules = data.get("data", [])
    print(f"  Reglas SIEM encontradas: {len(rules)}\n")

    headers = ["Nombre", "Habilitada", "Severidad", "Último run", "Alertas totales"]
    print(f"  {'Nombre':<45} {'Habilitada':<12} {'Sev':<8} {'Alertas'}")
    print(f"  {'-'*45} {'-'*12} {'-'*8} {'-'*8}")

    for rule in rules:
        name    = rule.get("name", "?")[:44]
        enabled = f"{G}Sí{X}" if rule.get("enabled") else f"{R}No{X}"
        sev     = rule.get("severity", "?")
        sev_col = G if sev == "low" else (Y if sev == "medium" else R)
        alerts  = rule.get("execution_summary", {}).get("last_execution", {}).get("metrics", {}).get("total_alerts_created", "?")

        print(f"  {name:<45} {enabled:<12} {sev_col}{sev:<8}{X} {alerts}")

# ─── GENERAR EVENTOS DE PRUEBA ────────────────────────────────────────────────
def generate_test_events():
    """
    Inserta documentos directamente en Elasticsearch para disparar cada regla.
    Útil para demostrar R8.4 sin necesidad de ataques reales.
    """
    print(f"\n{W}=== Generando eventos de prueba para las 5 reglas ==={X}")
    es = es_session()
    now = datetime.now(timezone.utc)
    attacker_ip = "185.220.101.34"

    tests = [
        # ── Regla 1: Brute Force SSH ─────────────────────────────────────────
        {
            "rule": "Brute Force SSH",
            "index": "logs-auth",
            "count": 8,
            "doc_template": {
                "@timestamp":       None,  # se rellena en el bucle
                "event.dataset":    "system.auth",
                "event.outcome":    "failure",
                "event.action":     "authentication_failure",
                "event.kind":       "event",
                "event.category":   "authentication",
                "process.name":     "sshd",
                "host.name":        "web-01",
                "source.ip":        attacker_ip,
                "user.name":        "root",
                "tags":             ["auth_failure", "ssh_failure"],
                "siem.brute_force_attempt": True,
                "siem.severity":    "high",
                "message":          f"Failed password for root from {attacker_ip} port 54321 ssh2",
            }
        },
        # ── Regla 2: Port Scan ───────────────────────────────────────────────
        {
            "rule": "Port Scan",
            "index": "logs-syslog",
            "count": 25,
            "doc_template": {
                "@timestamp":        None,
                "event.dataset":     "system.syslog",
                "event.category":    "network",
                "event.action":      "firewall_block",
                "event.kind":        "event",
                "event.outcome":     "failure",
                "network.transport": "tcp",
                "host.name":         "web-01",
                "source.ip":         attacker_ip,
                "destination.ip":    "10.0.0.1",
                "tags":              ["firewall_block"],
                "siem.severity":     "medium",
                "message":           f"[UFW BLOCK] SRC={attacker_ip} PROTO=TCP",
            },
            "vary_field": "destination.port",
            "vary_values": list(range(20, 45))
        },
        # ── Regla 3: Múltiples 404 ───────────────────────────────────────────
        {
            "rule": "Múltiples 404",
            "index": "logs-nginx",
            "count": 20,
            "doc_template": {
                "@timestamp":                  None,
                "event.dataset":               "nginx.access",
                "event.category":              "web",
                "event.type":                  "denied",
                "event.kind":                  "event",
                "http.request.method":         "GET",
                "http.response.status_code":   404,
                "http.response.body.bytes":    162,
                "http.version":                "1.1",
                "source.ip":                   attacker_ip,
                "user_agent.original":         "gobuster/3.1.0",
                "tags":                        ["http_404"],
                "siem.severity":               "medium",
                "message":                     f"{attacker_ip} - - \"GET /wp-admin HTTP/1.1\" 404 162",
            },
            "vary_field": "url.path",
            "vary_values": [
                "/wp-admin", "/.env", "/config.php", "/backup.zip",
                "/.git/config", "/admin", "/phpmyadmin", "/setup.php",
                "/install.php", "/wp-login.php", "/administrator",
                "/db.sql", "/dump.sql", "/admin/login", "/console",
                "/actuator", "/.aws/credentials", "/server-info",
                "/server-status", "/robots.txt", "/sitemap.xml"
            ]
        },
        # ── Regla 4: Login fuera de horario ──────────────────────────────────
        {
            "rule": "Login Fuera de Horario",
            "index": "logs-auth",
            "count": 1,
            "doc_template": {
                "@timestamp":                  (now.replace(hour=2, minute=30)).isoformat(),
                "event.dataset":               "system.auth",
                "event.outcome":               "success",
                "event.action":                "authentication_success",
                "event.kind":                  "event",
                "event.category":              "authentication",
                "process.name":                "sshd",
                "host.name":                   "web-01",
                "source.ip":                   attacker_ip,
                "source.geo.country_iso_code": "RU",
                "source.geo.country_name":     "Russia",
                "user.name":                   "deploy",
                "auth.method":                 "password",
                "siem.after_hours_login":      True,
                "siem.severity":               "medium",
                "tags":                        ["auth_success", "ssh_login", "after_hours_login"],
                "message":                     f"Accepted password for deploy from {attacker_ip} port 54321 ssh2",
            }
        },
        # ── Regla 5: Rutas sensibles ─────────────────────────────────────────
        {
            "rule": "Acceso a Rutas Sensibles",
            "index": "logs-nginx",
            "count": 5,
            "doc_template": {
                "@timestamp":                None,
                "event.dataset":             "nginx.access",
                "event.category":            "web",
                "event.kind":                "event",
                "http.request.method":       "GET",
                "http.response.status_code": 200,
                "http.response.body.bytes":  4096,
                "source.ip":                 attacker_ip,
                "user_agent.original":       "curl/7.68.0",
                "siem.sensitive_path":       True,
                "siem.severity":             "high",
                "tags":                      ["sensitive_path_access"],
                "message":                   f"{attacker_ip} - - \"GET /.env HTTP/1.1\" 200 4096",
            },
            "vary_field": "url.path",
            "vary_values": ["/.env", "/admin", "/.git/config", "/phpmyadmin", "/backup.zip"]
        },
    ]

    total_inserted = 0

    for test in tests:
        rule_name = test["rule"]
        index     = f"{test['index']}-{now.strftime('%Y.%m.%d')}"
        count     = test["count"]
        template  = test["doc_template"].copy()
        vary      = test.get("vary_field")
        values    = test.get("vary_values", [])

        print(f"\n  {B}── {rule_name}{X} → {index}")

        inserted = 0
        for i in range(count):
            doc = template.copy()
            # Timestamp dinámico (distribuido en últimos 45 segundos)
            if doc.get("@timestamp") is None or isinstance(doc["@timestamp"], type(None)):
                doc["@timestamp"] = (
                    now - timedelta(seconds=random.randint(0, 45))
                ).isoformat()
            # Variar campo si aplica
            if vary and values:
                doc[vary] = values[i % len(values)]

            r = es.post(
                f"{ES_URL}/{index}/_doc",
                json=doc,
                timeout=10,
            )
            if r.status_code in (200, 201):
                inserted += 1
            else:
                print(f"    {Y}⚠{X} Doc {i}: {r.status_code} — {r.text[:100]}")

        print(f"  {G}✓{X} {inserted}/{count} documentos insertados")
        total_inserted += inserted

    print(f"\n  {W}Total insertado: {total_inserted} documentos{X}")
    print(f"\n  {Y}Esperar ~60 segundos y verificar alertas en:{X}")
    print(f"  Kibana → Security → Alerts")
    print(f"  O ejecutar: python3 setup/import-rules.py --action status")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Gestión de reglas SIEM en Kibana"
    )
    parser.add_argument(
        "--action",
        choices=["import", "test", "status"],
        default="import",
        help="import: carga reglas | test: inserta eventos | status: muestra estado"
    )
    parser.add_argument("--kibana",   default=KIBANA_URL, help="URL de Kibana")
    parser.add_argument("--es",       default=ES_URL,     help="URL de Elasticsearch")
    parser.add_argument("--user",     default=ELASTIC_USER)
    parser.add_argument("--password", default=ELASTIC_PASS)
    parser.add_argument("--cacert",   default=CACERT)
    args = parser.parse_args()

    print(f"{W}SIEM Rules Manager{X} — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Kibana: {args.kibana} | ES: {args.es}")

    global KIBANA_URL, ES_URL, ELASTIC_USER, ELASTIC_PASS, CACERT
    KIBANA_URL = args.kibana
    ES_URL       = args.es
    ELASTIC_USER = args.user
    ELASTIC_PASS = args.password
    CACERT       = args.cacert

    if args.action == "import":
        import_rules()
    elif args.action == "test":
        generate_test_events()
    elif args.action == "status":
        check_status()

if __name__ == "__main__":
    main()
