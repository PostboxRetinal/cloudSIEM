#!/usr/bin/env python3
"""
generate-test-logs.py
Genera logs de ATAQUE simulados para el SIEM.
Cumple R8.5: brute force SSH, 404 flood, SQL injection, port scan (nmap).

Escribe directamente en los archivos que Filebeat monitorea.

Uso:
    python3 generate-test-logs.py --attack all_attacks
    python3 generate-test-logs.py --attack brute_force --count 50
    python3 generate-test-logs.py --attack port_scan
"""

import argparse
import random
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

EXTERNAL_IPS = [
    "185.220.101.34", "89.248.167.131", "194.165.16.11",
    "45.33.32.156",   "198.199.101.45", "104.236.246.58",
    "162.243.157.229","159.89.214.31",  "167.99.197.32",
]
USERS        = ["root", "admin", "ubuntu", "deploy", "postgres", "www-data"]
PATHS_SENS   = ["/admin", "/.env", "/wp-admin", "/phpmyadmin", "/config.php"]
PATHS_SQLI   = [
    "/api/search?q=1' OR '1'='1",
    "/users?id=1 UNION SELECT username,password FROM users--",
    "/api/data?filter=1;DROP TABLE users;--",
]


def ts_syslog():
    return datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")


def ts_nginx():
    return datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")


def write_logs(lines, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"  -> {len(lines)} lineas escritas en {path}")


# ---------------------------------------------------------------------------
# ATAQUE 1: Brute Force SSH
# ---------------------------------------------------------------------------
def gen_auth_brute_force(target_ip=None, count=30):
    """Genera un ataque de brute force SSH (R8.5 - escenario 1)."""
    ip    = target_ip or random.choice(EXTERNAL_IPS)
    users = ["root", "admin", "ubuntu", "user", "test", "postgres"]
    lines = []
    print(f"  [brute_force] IP atacante: {ip}, {count} intentos")
    for i in range(count):
        user = random.choice(users)
        pid  = random.randint(1000, 9999)
        lines.append(
            f"{ts_syslog()} web-01 sshd[{pid}]: "
            f"Failed password for {'invalid user ' if random.random() > 0.5 else ''}"
            f"{user} from {ip} port {random.randint(40000,65000)} ssh2"
        )
        time.sleep(0.05)
    return lines


# ---------------------------------------------------------------------------
# ATAQUE 2: 404 Flood (enumeracion web)
# ---------------------------------------------------------------------------
def gen_nginx_404_flood(source_ip=None, count=20):
    """Genera flood de errores 404 (R8.5 - escenario 2)."""
    ip     = source_ip or random.choice(EXTERNAL_IPS)
    paths  = [f"/wp-includes/{i}.php" for i in range(50)] + \
             ["/.git/config", "/.env", "/backup.zip", "/admin/config"]
    lines  = []
    print(f"  [404_flood] IP atacante: {ip}, {count} peticiones")
    for _ in range(count):
        path = random.choice(paths)
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" 404 162 '
            f'"-" "python-requests/2.28.0"'
        )
        time.sleep(0.02)
    return lines


# ---------------------------------------------------------------------------
# ATAQUE 3: SQL Injection
# ---------------------------------------------------------------------------
def gen_nginx_sqli(source_ip=None, count=10):
    """Genera intentos de inyeccion SQL en logs nginx (R8.5 - escenario 3)."""
    ip    = source_ip or random.choice(EXTERNAL_IPS)
    lines = []
    print(f"  [sqli] IP atacante: {ip}, {count} intentos")
    for _ in range(count):
        path = random.choice(PATHS_SQLI)
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" 200 1024 '
            f'"-" "sqlmap/1.7.2#stable (https://sqlmap.org)"'
        )
        time.sleep(0.1)
    return lines


# ---------------------------------------------------------------------------
# ATAQUE 4: Port Scan (nmap)
# ---------------------------------------------------------------------------
def gen_port_scan_nmap(target_ip=None, count=30):
    """Genera eventos UFW BLOCK simulando un escaneo nmap SYN a multiples puertos
    (R8.5 - escenario nmap). Dispara la regla 'SIEM - Escaneo de Puertos Detectado'
    cuando una misma IP contacta 20+ puertos distintos en 30s."""
    ip     = target_ip or random.choice(EXTERNAL_IPS)
    ports  = [22, 80, 443, 3306, 5432, 8080, 8443, 9200, 5601, 5044,
              6379, 27017, 1433, 1521, 11211, 25, 53, 161, 389, 636,
              993, 995, 2082, 2083, 8888, 9090, 3000, 5000, 9000, 10000]
    host   = random.choice(["web-01", "app-01", "db-01"])
    lines  = []
    print(f"  [port_scan_nmap] IP atacante: {ip}, {count} puertos escaneados")
    for i in range(min(count, len(ports))):
        port = ports[i]
        d_ip = f"10.0.0.{random.randint(1, 20)}"
        pid  = random.randint(1000, 9999)
        lines.append(
            f"{ts_syslog()} {host} kernel: [{random.randint(100000, 999999)}.{random.randint(100, 999)}] "
            f"[UFW BLOCK] IN=eth0 OUT= SRC={ip} DST={d_ip} "
            f"LEN={random.randint(40, 120)} TTL={random.randint(40, 128)} "
            f"PROTO=TCP SPT={random.randint(40000, 65000)} DPT={port}"
        )
        time.sleep(0.08)
    return lines


# ---------------------------------------------------------------------------
# Complementario: Acceso a rutas sensibles (se genera con sqli)
# ---------------------------------------------------------------------------
def gen_nginx_sensitive_paths(source_ip=None, count=8):
    """Genera acceso a rutas sensibles."""
    ip    = source_ip or random.choice(EXTERNAL_IPS)
    lines = []
    for path in PATHS_SENS[:count]:
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" 403 287 '
            f'"-" "Mozilla/5.0"'
        )
    return lines


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generador de logs de ataque SIEM (R8.5)")
    parser.add_argument("--attack", choices=["brute_force", "404_flood", "sqli", "port_scan", "all_attacks"],
                        default="all_attacks", help="Tipo de ataque a simular")
    parser.add_argument("--count",  type=int, default=30,
                        help="Numero de entradas de log por ataque")
    parser.add_argument("--auth-path",   default=str(BASE_LOG_DIR / "auth.log"))
    parser.add_argument("--nginx-path",  default=str(BASE_LOG_DIR / "nginx" / "access.log"))
    parser.add_argument("--syslog-path", default=str(BASE_LOG_DIR / "syslog"))
    args = parser.parse_args()

    attacker_ip = random.choice(EXTERNAL_IPS)
    print(f"\nGenerador de ataques SIEM - {datetime.now(timezone.utc).isoformat()}")
    print(f"IP atacante para simulaciones: {attacker_ip}\n")

    if args.attack in ("brute_force", "all_attacks"):
        print("Simulando brute force SSH...")
        write_logs(gen_auth_brute_force(attacker_ip, max(args.count, 35)), args.auth_path)

    if args.attack in ("404_flood", "all_attacks"):
        print("Simulando 404 flood...")
        write_logs(gen_nginx_404_flood(attacker_ip, max(args.count, 25)), args.nginx_path)

    if args.attack in ("sqli", "all_attacks"):
        print("Simulando inyeccion SQL...")
        write_logs(gen_nginx_sqli(attacker_ip, 12), args.nginx_path)
        write_logs(gen_nginx_sensitive_paths(attacker_ip), args.nginx_path)

    if args.attack in ("port_scan", "all_attacks"):
        print("Simulando escaneo de puertos (nmap)...")
        write_logs(gen_port_scan_nmap(attacker_ip, 30), args.syslog_path)

    print("\nAtaques generados. Esperar ~30s para que Filebeat los procese.")
    print("Verificar en Kibana -> Security -> Alerts")


if __name__ == "__main__":
    main()
