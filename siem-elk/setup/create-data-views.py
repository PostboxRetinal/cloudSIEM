#!/usr/bin/env python3
"""Crea los data views necesarios en Kibana si no existen."""

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
WAIT_KIBANA_TIMEOUT = int(os.getenv("WAIT_KIBANA_TIMEOUT", "600"))
DATA_VIEW_RETRIES = int(os.getenv("DATA_VIEW_RETRIES", "5"))
DATA_VIEW_RETRY_WAIT = int(os.getenv("DATA_VIEW_RETRY_WAIT", "10"))

DATA_VIEWS = [
    {"id": "logs-*",       "title": "logs-*",       "description": "Todos los logs"},
    {"id": "logs-auth-*",  "title": "logs-auth-*",  "description": "Logs de autenticacion"},
    {"id": "logs-nginx-*", "title": "logs-nginx-*", "description": "Logs de nginx/apache"},
    {"id": "logs-syslog-*","title": "logs-syslog-*","description": "Logs de sistema"},
    {"id": "logs-k8s-*",   "title": "logs-k8s-*",   "description": "Logs de Kubernetes"},
]

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[94m"
W = "\033[1m"
X = "\033[0m"


def kibana_session():
    client = requests.Session()
    client.auth = (ELASTIC_USER, ELASTIC_PASS)
    client.headers = {"kbn-xsrf": "true"}
    client.verify = CACERT if Path(CACERT).exists() else False
    return client


def wait_for_kibana(client, timeout=WAIT_KIBANA_TIMEOUT):
    print(f"\n{W}Esperando a que Kibana este disponible...{X}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = client.get(f"{KIBANA_URL}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                overall = data.get("status", {}).get("overall", {})
                level = overall.get("level")
                if level in ("available", "green"):
                    print(f"  {G}✓{X} Kibana disponible")
                    return True
        except Exception:
            pass
        time.sleep(5)
    print(f"  {R}✗{X} Kibana no respondio en {timeout}s")
    return False


def ensure_data_view(client, data_view_id, title):
    get_url = f"{KIBANA_URL}/api/data_views/data_view/{data_view_id}"
    create_url = f"{KIBANA_URL}/api/data_views/data_view"

    for attempt in range(1, DATA_VIEW_RETRIES + 1):
        try:
            response = client.get(get_url, timeout=10)
            if response.status_code == 200:
                print(f"  {G}✓{X} Data view existe: {data_view_id}")
                return True
            if response.status_code not in (404, 400):
                print(f"  {R}✗{X} Error consultando data view: {response.status_code}")
                print(response.text[:500])
                return False

            payload = {
                "data_view": {
                    "id": data_view_id,
                    "title": title,
                    "timeFieldName": "@timestamp",
                }
            }
            created = client.post(create_url, json=payload, timeout=20)
            if created.status_code in (200, 201):
                print(f"  {G}✓{X} Data view creado: {data_view_id}")
                return True

            print(f"  {Y}⚠{X} Error creando data view (intento {attempt}/{DATA_VIEW_RETRIES})")
            print(created.text[:300])
        except Exception:
            print(f"  {Y}⚠{X} Error temporal creando data view (intento {attempt}/{DATA_VIEW_RETRIES})")

        time.sleep(DATA_VIEW_RETRY_WAIT)

    return False


def main():
    print(f"\n{W}=== Creando Data Views en Kibana ==={X}")
    client = kibana_session()

    if not wait_for_kibana(client):
        sys.exit(1)

    all_ok = True
    for dv in DATA_VIEWS:
        print(f"\n  {B}-- {dv['description']}{X}")
        if not ensure_data_view(client, dv["id"], dv["title"]):
            print(f"  {R}✗{X} Fallo al crear data view: {dv['id']}")
            all_ok = False

    if all_ok:
        print(f"\n  {G}✓{X} Todos los data views listos")
    else:
        print(f"\n  {Y}⚠{X} Algunos data views no se crearon correctamente")


if __name__ == "__main__":
    main()
