#!/usr/bin/env python3
"""Importa dashboards a Kibana desde NDJSON."""

import os
import sys
import time
from pathlib import Path

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

KIBANA_URL = os.getenv("KIBANA_HOST", "https://localhost:5601")
ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")
ELASTIC_PASS = os.getenv("ELASTIC_PASSWORD", "SiemElastic2026!")
CACERT = os.getenv("CACERT", "./setup/certs/ca/ca.crt")
FILE = Path(__file__).resolve().parent / "dashboards" / "executive-operational-dashboards.ndjson"
WAIT_KIBANA_TIMEOUT = int(os.getenv("WAIT_KIBANA_TIMEOUT", "300"))
IMPORT_TIMEOUT = int(os.getenv("IMPORT_TIMEOUT", "120"))
IMPORT_RETRIES = int(os.getenv("IMPORT_RETRIES", "3"))

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
W = "\033[1m"
X = "\033[0m"


def kibana_session():
    client = requests.Session()
    client.auth = (ELASTIC_USER, ELASTIC_PASS)
    client.headers = {"kbn-xsrf": "true"}
    client.verify = CACERT if Path(CACERT).exists() else False
    return client


def wait_for_kibana(client, timeout=WAIT_KIBANA_TIMEOUT):
    print(f"\n{W}Esperando a que Kibana esté disponible...{X}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = client.get(f"{KIBANA_URL}/api/status", timeout=5)
            if response.status_code == 200:
                print(f"  {G}✓{X} Kibana disponible")
                return True
        except Exception:
            pass
        time.sleep(2)
    print(f"  {R}✗{X} Kibana no respondió en {timeout}s")
    return False


def import_dashboards():
    print(f"\n{W}=== Importando Dashboards a Kibana ==={X}")
    client = kibana_session()

    if not wait_for_kibana(client):
        sys.exit(1)

    if not FILE.exists():
        print(f"{R}No se encontró: {FILE}{X}")
        sys.exit(1)

    print(f"  Importando desde: {W}{FILE.name}{X}")

    response = None
    for attempt in range(1, IMPORT_RETRIES + 1):
        with FILE.open("rb") as file_handle:
            response = client.post(
                f"{KIBANA_URL}/api/saved_objects/_import",
                params={"overwrite": "true"},
                files={"file": (FILE.name, file_handle, "application/x-ndjson")},
                timeout=IMPORT_TIMEOUT,
            )

        if response.status_code == 200:
            break

        if attempt < IMPORT_RETRIES:
            print(f"  {Y}⚠{X}  Reintentando importacion ({attempt}/{IMPORT_RETRIES})...")
            time.sleep(5)

    if response.status_code != 200:
        print(f"  {R}✗{X} Error {response.status_code}")
        print(response.text[:500])
        sys.exit(1)

    payload = response.json()
    imported = payload.get("success_count", payload.get("successCount", 0))
    success_results = payload.get("successResults", [])
    dashboard_count = sum(1 for item in success_results if item.get("type") == "dashboard")
    errors = payload.get("errors", payload.get("errorResults", []))

    if errors:
        print(f"  {Y}⚠{X}  Importados {dashboard_count} dashboards y {imported} objetos con {len(errors)} errores")
        for error in errors[:5]:
            print(f"     - {error.get('type', 'N/A')}: {error.get('id', 'N/A')}")
    else:
        print(f"  {G}✓{X}  {dashboard_count} dashboards importados")


if __name__ == "__main__":
    import_dashboards()
