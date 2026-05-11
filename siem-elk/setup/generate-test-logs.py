#!/usr/bin/env python3
"""
generate-test-logs.py
Genera logs de prueba realistas para las 4 fuentes del SIEM.
Escribe directamente en los archivos que Filebeat monitorea.

Uso:
    python3 generate-test-logs.py --source all
    python3 generate-test-logs.py --source nginx --count 100
    python3 generate-test-logs.py --source auth  --attack brute_force
"""

import argparse
import random
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# ─── IPs de muestra (mezcla pública y privada) ────────────────────────────────
EXTERNAL_IPS = [
    "185.220.101.34", "89.248.167.131", "194.165.16.11",
    "45.33.32.156",   "198.199.101.45", "104.236.246.58",
    "162.243.157.229","159.89.214.31",  "167.99.197.32",
]
INTERNAL_IPS = ["10.0.0.5", "192.168.1.20", "172.16.0.10"]
USERS        = ["root", "admin", "ubuntu", "deploy", "postgres", "www-data"]
PATHS_OK     = ["/", "/index.html", "/api/v1/status", "/api/v1/users", "/about"]
PATHS_SENS   = ["/admin", "/.env", "/wp-admin", "/phpmyadmin", "/config.php"]
PATHS_SQLI   = [
    "/api/search?q=1' OR '1'='1",
    "/users?id=1 UNION SELECT username,password FROM users--",
    "/api/data?filter=1;DROP TABLE users;--",
]
USER_AGENTS  = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "curl/7.68.0",
    "python-requests/2.28.0",
    "Nikto/2.1.6",       # scanner
    "sqlmap/1.7.2",       # SQLi tool
]


def ts_syslog():
    """Timestamp formato syslog: 'Apr 25 14:32:01'"""
    return datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")


def ts_nginx():
    """Timestamp formato nginx: '25/Apr/2024:14:32:01 +0000'"""
    return datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")


def ts_iso():
    """Timestamp ISO 8601"""
    return datetime.now(timezone.utc).isoformat()


# ─── Generadores por fuente ───────────────────────────────────────────────────

def gen_syslog(count=20):
    """Genera entradas de syslog del sistema."""
    templates = [
        "{ts} {host} kernel: [UFW BLOCK] IN=eth0 OUT= SRC={ip} DST=10.0.0.1 PROTO=TCP DPT={port}",
        "{ts} {host} systemd[1]: Started Session {sid} of user {user}.",
        "{ts} {host} cron[{pid}]: ({user}) CMD (/usr/bin/python3 /opt/monitor.py)",
        "{ts} {host} kernel: EXT4-fs (sda1): mounted filesystem",
        "{ts} {host} systemd-logind[{pid}]: New session {sid} of user {user}.",
        "{ts} {host} CRON[{pid}]: (root) CMD (test -x /usr/sbin/anacron || ...)",
        "{ts} {host} NetworkManager[{pid}]: <info>  device (eth0): state change: ip-config -> activated",
    ]
    lines = []
    for _ in range(count):
        tpl = random.choice(templates)
        lines.append(tpl.format(
            ts   = ts_syslog(),
            host = random.choice(["web-01", "db-01", "app-01"]),
            ip   = random.choice(EXTERNAL_IPS),
            port = random.choice([22, 80, 443, 3306, 5432, 8080]),
            user = random.choice(USERS),
            pid  = random.randint(1000, 9999),
            sid  = random.randint(1, 100),
        ))
    return lines


def gen_auth_normal(count=10):
    """Genera eventos de autenticación normales."""
    lines = []
    for _ in range(count):
        ip   = random.choice(INTERNAL_IPS)
        user = random.choice(["ubuntu", "deploy", "admin"])
        lines.append(
            f"{ts_syslog()} web-01 sshd[{random.randint(1000,9999)}]: "
            f"Accepted publickey for {user} from {ip} port "
            f"{random.randint(40000,65000)} ssh2: RSA SHA256:abc123"
        )
    return lines


def gen_auth_brute_force(target_ip=None, count=30):
    """Genera un ataque de brute force SSH (R8.5 — escenario 1)."""
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
        time.sleep(0.05)  # 30 intentos en ~1.5 segundos → dispara la regla
    return lines


def gen_nginx_normal(count=30):
    """Genera tráfico nginx normal."""
    codes = [200, 200, 200, 200, 301, 304, 404]
    lines = []
    for _ in range(count):
        ip   = random.choice(EXTERNAL_IPS + INTERNAL_IPS)
        path = random.choice(PATHS_OK)
        code = random.choice(codes)
        size = random.randint(100, 50000)
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" {code} {size} '
            f'"-" "{random.choice(USER_AGENTS[:3])}"'
        )
    return lines


def gen_nginx_404_flood(source_ip=None, count=20):
    """Genera flood de errores 404 (R8.5 — detectado por regla de múltiples 404)."""
    ip     = source_ip or random.choice(EXTERNAL_IPS)
    paths  = [f"/wp-includes/{i}.php" for i in range(50)] + \
             [f"/.git/config", "/.env", "/backup.zip", "/admin/config"]
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


def gen_nginx_sqli(source_ip=None, count=10):
    """Genera intentos de inyección SQL en logs nginx (R8.5 — escenario 3)."""
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


def gen_nginx_sensitive_paths(source_ip=None, count=8):
    """Genera acceso a rutas sensibles (regla R8.4 — acceso a rutas sensibles)."""
    ip    = source_ip or random.choice(EXTERNAL_IPS)
    lines = []
    for path in PATHS_SENS[:count]:
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" 403 287 '
            f'"-" "Mozilla/5.0"'
        )
    return lines


def gen_k8s_logs(count=15):
    """Genera logs de contenedores Kubernetes en formato JSON."""
    pods = [
        ("frontend-7d9b8c-xk2p9", "frontend", "default"),
        ("backend-api-5f6b-mn3q1", "api",      "default"),
        ("db-primary-0",           "postgres",  "database"),
        ("redis-master-0",         "redis",     "cache"),
        ("nginx-ingress-abc12",    "nginx",     "kube-system"),
    ]
    lines = []
    for _ in range(count):
        pod, ctr, ns = random.choice(pods)
        msg_type = random.choice(["info", "warn", "error"])
        messages  = {
            "info":  f"Request processed in {random.randint(10,500)}ms",
            "warn":  f"Connection pool at {random.randint(80,95)}% capacity",
            "error": f"Failed to connect to {random.choice(['postgres', 'redis'])}: timeout",
        }
        import json as _json
        lines.append(_json.dumps({
            "time":    ts_iso(),
            "level":   msg_type,
            "message": messages[msg_type],
            "kubernetes": {
                "pod": {"name": pod},
                "namespace": ns,
                "container": {"name": ctr},
            }
        }))
    return lines


# ─── Escritura a archivos ─────────────────────────────────────────────────────

def write_logs(lines, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"  → {len(lines)} líneas escritas en {path}")


def main():
    parser = argparse.ArgumentParser(description="Generador de logs de prueba SIEM")
    parser.add_argument("--source", choices=["all", "syslog", "auth", "nginx", "k8s"],
                        default="all", help="Fuente de logs a generar")
    parser.add_argument("--attack", choices=["none", "brute_force", "404_flood", "sqli", "all_attacks"],
                        default="none", help="Tipo de ataque a simular")
    parser.add_argument("--count",  type=int, default=30,
                        help="Número de entradas de log normales")
    parser.add_argument("--syslog-path", default=str(BASE_LOG_DIR / "syslog"))
    parser.add_argument("--auth-path",   default=str(BASE_LOG_DIR / "auth.log"))
    parser.add_argument("--nginx-path",  default=str(BASE_LOG_DIR / "nginx" / "access.log"))
    parser.add_argument("--k8s-path",    default=str(BASE_LOG_DIR / "containers" / "test-pod.log"))
    args = parser.parse_args()

    attacker_ip = random.choice(EXTERNAL_IPS)
    print(f"\nGenerador de logs SIEM — {ts_iso()}")
    print(f"IP atacante para simulaciones: {attacker_ip}\n")

    # Logs normales
    if args.source in ("all", "syslog"):
        print("Generando syslog...")
        write_logs(gen_syslog(args.count), args.syslog_path)

    if args.source in ("all", "auth"):
        print("Generando auth.log (normal)...")
        write_logs(gen_auth_normal(5), args.auth_path)

    if args.source in ("all", "nginx"):
        print("Generando nginx access (normal)...")
        write_logs(gen_nginx_normal(args.count), args.nginx_path)

    if args.source in ("all", "k8s"):
        print("Generando logs Kubernetes...")
        write_logs(gen_k8s_logs(args.count), args.k8s_path)

    # Ataques
    if args.attack in ("brute_force", "all_attacks"):
        print("\nSimulando brute force SSH...")
        write_logs(gen_auth_brute_force(attacker_ip, 35), args.auth_path)

    if args.attack in ("404_flood", "all_attacks"):
        print("\nSimulando 404 flood...")
        write_logs(gen_nginx_404_flood(attacker_ip, 25), args.nginx_path)

    if args.attack in ("sqli", "all_attacks"):
        print("\nSimulando inyección SQL...")
        write_logs(gen_nginx_sqli(attacker_ip, 12), args.nginx_path)
        write_logs(gen_nginx_sensitive_paths(attacker_ip), args.nginx_path)

    print("\nLogs generados. Esperar ~30s para que Filebeat los procese.")
    print("Verificar en Kibana → Discover → índice logs-*")


if __name__ == "__main__":
    main()
