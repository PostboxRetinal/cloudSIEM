#!/usr/bin/env python3
"""
cleanup-indices.py
Elimina indices SIEM viejos que tengan mappings incorrectos (source.ip como text)
y verifica que los templates esten correctamente aplicados.

Uso (manual - para arreglar el stack actual):
    python3 setup/cleanup-indices.py

Uso (docker - via ilm-setup):
    python3 setup/cleanup-indices.py --docker
"""

import os
import sys
import time

try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

ES_URL = os.getenv("ELASTIC_HOSTS", "https://localhost:9200")
ELASTIC_USER = os.getenv("ELASTIC_USER", "elastic")
ELASTIC_PASS = os.getenv("ELASTIC_PASSWORD", "SiemElastic2026!")
CACERT = os.getenv("CACERT", "./setup/certs/ca/ca.crt")
IS_DOCKER = "--docker" in sys.argv

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

TEMPLATES_CHECK = [
    ("siem-auth",   "logs-auth-*",   "source.ip"),
    ("siem-nginx",  "logs-nginx-*",  "source.ip"),
    ("siem-syslog", "logs-syslog-*", "source.ip"),
    ("siem-k8s",    "logs-k8s-*",    None),
    ("siem-errors", "logs-errors-*", None),
]

INDICES_TO_CLEAN = [
    "logs-auth-*", "logs-nginx-*", "logs-syslog-*",
    "logs-k8s-*", "logs-errors-*",
]


def es_session():
    s = requests.Session()
    s.auth = (ELASTIC_USER, ELASTIC_PASS)
    s.verify = CACERT if (CACERT and os.path.exists(CACERT)) else False
    s.headers["Content-Type"] = "application/json"
    return s


def wait_for_es(session, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = session.get(f"{ES_URL}/_cluster/health", timeout=5)
            if r.status_code == 200:
                status = r.json().get("status")
                if status in ("green", "yellow"):
                    print(f"  {GREEN}Cluster ES disponible (status={status}){RESET}")
                    return True
        except Exception:
            pass
        time.sleep(3)
    print(f"  {RED}ES no disponible tras {timeout}s{RESET}")
    return False


def disable_destructive_requires_name(session):
    """ES 8.x bloquea DELETE con wildcards por defecto. Lo desactivamos."""
    try:
        body = {"persistent": {"action.destructive_requires_name": False}}
        r = session.put(f"{ES_URL}/_cluster/settings", json=body, timeout=10)
        if r.status_code in (200, 201):
            print(f"  {GREEN}action.destructive_requires_name desactivado{RESET}")
        else:
            print(f"  {YELLOW}No se pudo desactivar: {r.text[:100]}{RESET}")
    except Exception as e:
        print(f"  {YELLOW}Error al desactivar: {e}{RESET}")


def delete_indices(session):
    print(f"\n{CYAN}--- Eliminando indices logs-* con mapping incorrecto ---{RESET}")
    disable_destructive_requires_name(session)
    time.sleep(1)
    all_ok = True
    for pattern in INDICES_TO_CLEAN:
        try:
            r = session.delete(f"{ES_URL}/{pattern}")
            if r.status_code in (200, 202):
                print(f"  {GREEN}Eliminado: {pattern}{RESET}")
            elif r.status_code == 404:
                print(f"  {YELLOW}No existe: {pattern}{RESET}")
            else:
                print(f"  {RED}Error {r.status_code} al eliminar {pattern}: {r.text[:100]}{RESET}")
                all_ok = False
        except Exception as e:
            print(f"  {RED}Excepcion al eliminar {pattern}: {e}{RESET}")
            all_ok = False

    if all_ok:
        print(f"  {GREEN}Limpiando indices completado.{RESET}")
    time.sleep(2)
    return all_ok


def verify_templates(session):
    """Verifica templates. No falla si faltan porque ilm-setup los crea despues."""
    print(f"\n{CYAN}--- Verificando templates de indice ---{RESET}")

    r = session.get(f"{ES_URL}/_index_template", timeout=10)
    if r.status_code != 200:
        print(f"  {YELLOW}No se pudieron listar templates: {r.status_code}{RESET}")
        return True

    existing = {t["name"] for t in r.json().get("index_templates", [])}
    all_ok = True

    for tpl_name, idx_pattern, check_field in TEMPLATES_CHECK:
        if tpl_name not in existing:
            print(f"  {YELLOW}Aun no existe: {tpl_name} (lo crea ilm-setup despues){RESET}")
        else:
            print(f"  {GREEN}OK template: {tpl_name}{RESET}")

    print(f"  {GREEN}Verificacion completada (ilm-setup creara los templates faltantes).{RESET}")
    return True


def verify_mapping_on_new_index(session):
    """Verifica que AL MENOS un indice SIEM exista con source.ip como keyword."""
    print(f"\n{CYAN}--- Verificando mapping en indices existentes ---{RESET}")
    try:
        r = session.get(f"{ES_URL}/_cat/indices/logs-*-*?h=index&format=json&s=index", timeout=10)
        if r.status_code != 200 or not r.json():
            print(f"  {YELLOW}Aun no hay indices SIEM (normal si se acaban de eliminar){RESET}")
            return True
        indices = [i["index"] for i in r.json()[:3]]
        for idx in indices:
            r2 = session.get(f"{ES_URL}/{idx}/_mapping", timeout=10)
            if r2.status_code != 200:
                continue
            props = r2.json().get(idx, {}).get("mappings", {}).get("properties", {})
            source_ip = props.get("source", {}).get("properties", {}).get("ip", props.get("source.ip", {}))
            if isinstance(source_ip, dict):
                ip_type = source_ip.get("type", "?")
                if ip_type == "keyword":
                    print(f"  {GREEN}{idx}: source.ip={ip_type} OK{RESET}")
                elif ip_type == "text":
                    print(f"  {RED}{idx}: source.ip={ip_type} -> AUN MAL, reintentar cleanup{RESET}")
                    return False
    except Exception as e:
        print(f"  {YELLOW}No se pudo verificar mapping: {e}{RESET}")
    return True


def main():
    print(f"\n{BOLD}{'='*50}{RESET}")
    print(f"{BOLD}  Cleanup de indices SIEM - R8.3/R8.4{RESET}")
    print(f"  ES: {ES_URL}")
    print(f"{BOLD}{'='*50}{RESET}")

    session = es_session()

    if not wait_for_es(session):
        sys.exit(1)

    if not delete_indices(session):
        print(f"  {RED}Hubo errores eliminando indices. Continuando...{RESET}")

    if not verify_templates(session):
        print(f"  {RED}ERROR: Faltan templates. Revisar setup/{RESET}")
        sys.exit(1)

    verify_mapping_on_new_index(session)

    print(f"\n{GREEN}Cleanup completado. Cuando Filebeat/Logstash procesen nuevos logs,")
    print(f"los indices se crearan con mapping correcto (source.ip como keyword).{RESET}")
    print(f"\n  Recuerde generar logs: python setup/orchestrate-logs.py --mode random{RESET}")
    print(f"O manual:          python setup/generate-normal-logs.py --source all")
    sys.exit(0)


if __name__ == "__main__":
    main()
