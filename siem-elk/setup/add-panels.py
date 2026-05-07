#!/usr/bin/env python3
"""
add-dashboard-panels.py (v2)
Agrega los paneles de visualizaciones a los dashboards después de la importación.
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

def kibana_session():
    s = requests.Session()
    s.auth = (ELASTIC_USER, ELASTIC_PASS)
    s.headers = {"kbn-xsrf": "true", "Content-Type": "application/json"}
    s.verify = CACERT if Path(CACERT).exists() else False
    return s

def wait_for_kibana(timeout=180):
    print("Esperando a que Kibana esté disponible...")
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            s = kibana_session()
            r = s.get(f"{KIBANA_URL}/api/status", timeout=5)
            if r.status_code == 200:
                print("  ✓ Kibana disponible")
                return True
        except:
            pass
        time.sleep(2)
    print(f"  ✗ Kibana no respondió")
    return False

def add_panels_to_dashboard(dashboard_id, panels):
    """Agrega paneles a un dashboard existente"""
    session = kibana_session()
    
    # Actualizar dashboard con paneles usando PATCH
    update_payload = json.dumps({
        "attributes": {
            "panels": panels
        }
    })
    
    # Intentar con PATCH
    r = session.patch(
        f"{KIBANA_URL}/api/saved_objects/dashboard/{dashboard_id}",
        data=update_payload,
        timeout=10
    )
    
    if r.status_code not in [200, 201]:
        print(f"  ✗ Error {r.status_code}: {r.text[:150]}")
        return False
    
    return True

def main():
    if not wait_for_kibana():
        sys.exit(1)
    
    print("\n=== Agregando Paneles a Dashboards ===\n")
    
    # Paneles para dashboard ejecutivo
    exec_panels = [
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 0, "w": 24, "h": 12},
            "type": "visualization",
            "id": "viz-system-health",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 24, "y": 0, "w": 24, "h": 12},
            "type": "visualization",
            "id": "viz-top-threats",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 12, "w": 48, "h": 12},
            "type": "visualization",
            "id": "viz-alert-trend",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 24, "w": 48, "h": 15},
            "type": "visualization",
            "id": "viz-top-ips",
            "embeddableConfig": {}
        }
    ]
    
    # Paneles para dashboard operacional
    ops_panels = [
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 0, "w": 24, "h": 15},
            "type": "visualization",
            "id": "viz-top-users",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 24, "y": 0, "w": 24, "h": 15},
            "type": "visualization",
            "id": "viz-top-ips",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 15, "w": 48, "h": 18},
            "type": "visualization",
            "id": "viz-alerts-table",
            "embeddableConfig": {}
        },
        {
            "version": "8.3.3",
            "gridData": {"x": 0, "y": 33, "w": 48, "h": 20},
            "type": "visualization",
            "id": "viz-events-table",
            "embeddableConfig": {}
        }
    ]
    
    # Agregar paneles
    if add_panels_to_dashboard("executive-security-overview", exec_panels):
        print("  ✓ Paneles agregados a Executive Dashboard")
    
    if add_panels_to_dashboard("operational-triage-console", ops_panels):
        print("  ✓ Paneles agregados a Operational Dashboard")
    
    print("\n✓ Dashboards configurados completamente")

if __name__ == "__main__":
    main()
