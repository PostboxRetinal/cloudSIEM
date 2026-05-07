#!/usr/bin/env python3
"""
import-dashboards.py
Importa los dashboards ejecutivo y operacional a Kibana desde NDJSON.
"""

import json
import time
import sys
import os
from pathlib import Path

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

KIBANA_URL      = os.getenv("KIBANA_HOST",     "https://localhost:5601")
ELASTIC_USER    = os.getenv("ELASTIC_USER",    "elastic")
ELASTIC_PASS    = os.getenv("ELASTIC_PASSWORD","SiemElastic2026!")
CACERT          = os.getenv("CACERT",          "./setup/certs/ca/ca.crt")
DASHBOARDS_FILE = Path(__file__).resolve().parent.parent / "setup" / "dashboards" / "executive-operational-dashboards.ndjson"

G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; B = "\033[94m"; W = "\033[1m"; X = "\033[0m"

def kibana_session():
    s = requests.Session()
    s.auth = (ELASTIC_USER, ELASTIC_PASS)
    s.headers = {"kbn-xsrf": "true"}
    s.verify = CACERT if Path(CACERT).exists() else False
    return s

def wait_for_kibana(session, url, timeout=180):
    print(f"\n{W}Esperando a que Kibana esté disponible...{X}")
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            r = session.get(f"{url}/api/status", timeout=5)
            if r.status_code == 200:
                print(f"  {G}✓{X} Kibana disponible")
                return True
        except:
            pass
        time.sleep(2)
    print(f"  {R}✗{X} Kibana no respondió en {timeout}s")
    return False

def import_dashboards():
    print(f"\n{W}=== Importando Dashboards a Kibana ==={X}")
    session = kibana_session()
    
    if not wait_for_kibana(session, KIBANA_URL):
        sys.exit(1)
    
    if not DASHBOARDS_FILE.exists():
        print(f"{R}No se encontró: {DASHBOARDS_FILE}{X}")
        sys.exit(1)
    
    print(f"  Importando desde: {B}{DASHBOARDS_FILE.name}{X}")
    
    with DASHBOARDS_FILE.open("rb") as f:
        response = session.post(
            f"{KIBANA_URL}/api/saved_objects/_import",
            params={"overwrite": "true"},
            files={"file": (DASHBOARDS_FILE.name, f, "application/x-ndjson")},
            timeout=30,
        )
    
    if response.status_code != 200:
        print(f"  {R}✗{X} Error {response.status_code}")
        print(response.text[:300])
        sys.exit(1)
    
    payload = response.json()
    imported = payload.get("success_count", 0)
    failed = payload.get("errors", [])
    
    if failed:
        print(f"  {Y}⚠{X}  Importados {imported} con {len(failed)} errores")
        for err in failed[:3]:
            print(f"     - {err.get('error', {}).get('message', 'Error desconocido')}")
    else:
        print(f"  {G}✓{X}  {imported} dashboards importados")

if __name__ == "__main__":
    import_dashboards()
