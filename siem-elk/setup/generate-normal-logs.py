#!/usr/bin/env python3
"""
generate-normal-logs.py
Genera logs LEGITIMOS (no ataques) para las 4 fuentes del SIEM.
Cumple R8.2: syslog, auth.log, nginx/apache, kubernetes.

Escribe directamente en los archivos que Filebeat monitorea.

Uso:
    python3 generate-normal-logs.py --source all --count 30
    python3 generate-normal-logs.py --source nginx --count 50
    python3 generate-normal-logs.py --source auth
"""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

INTERNAL_IPS = ["10.0.0.5", "192.168.1.20", "172.16.0.10"]
USERS        = ["ubuntu", "deploy", "admin", "www-data", "gitlab"]
PATHS_OK     = ["/", "/index.html", "/api/v1/status", "/api/v1/users", "/about",
                "/api/health", "/login", "/css/style.css", "/js/app.js", "/favicon.ico"]


def ts_syslog():
    return datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")


def ts_nginx():
    return datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")


def ts_iso():
    return datetime.now(timezone.utc).isoformat()


def write_logs(lines, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"  -> {len(lines)} lineas escritas en {path}")


# ---------------------------------------------------------------------------
# FUENTE 1: SYSLOG - mensajes normales del sistema
# ---------------------------------------------------------------------------
def gen_syslog(count=20):
    """Genera entradas de syslog del sistema (eventos normales)."""
    templates = [
        "{ts} {host} systemd[1]: Started Session {sid} of user {user}.",
        "{ts} {host} systemd[1]: Stopped Session {sid} of user {user}.",
        "{ts} {host} cron[{pid}]: ({user}) CMD (/usr/bin/python3 /opt/monitor.py)",
        "{ts} {host} kernel: EXT4-fs (sda1): mounted filesystem with writeback timezone.",
        "{ts} {host} systemd-logind[{pid}]: New session {sid} of user {user}.",
        "{ts} {host} CRON[{pid}]: (root) CMD (test -x /usr/sbin/anacron || exit 0)",
        "{ts} {host} NetworkManager[{pid}]: <info>  device (eth0): state change: ip-config -> activated",
        "{ts} {host} rsyslogd[{pid}]: [origin software=\"rsyslogd\"] start",
        "{ts} {host} ntpd[{pid}]: time sync resumed, clock offset 0.003 sec",
        "{ts} {host} sshd[{pid}]: Server listening on 0.0.0.0 port 22.",
    ]
    lines = []
    for _ in range(count):
        tpl = random.choice(templates)
        lines.append(tpl.format(
            ts   = ts_syslog(),
            host = random.choice(["web-01", "db-01", "app-01"]),
            user = random.choice(USERS),
            pid  = random.randint(1000, 9999),
            sid  = random.randint(1, 100),
        ))
    return lines


# ---------------------------------------------------------------------------
# FUENTE 2: AUTH.LOG - autenticaciones exitosas y operaciones normales
# ---------------------------------------------------------------------------
def gen_auth_normal(count=10):
    """Genera eventos de autenticacion normales (exitosos)."""
    lines = []
    for _ in range(count):
        ip   = random.choice(INTERNAL_IPS)
        user = random.choice(["ubuntu", "deploy", "admin"])
        pid  = random.randint(1000, 9999)
        event_type = random.choice(["accepted", "session_open", "sudo", "session_close"])

        if event_type == "accepted":
            lines.append(
                f"{ts_syslog()} web-01 sshd[{pid}]: "
                f"Accepted publickey for {user} from {ip} port "
                f"{random.randint(40000,65000)} ssh2: RSA SHA256:def456"
            )

        elif event_type == "session_open":
            lines.append(
                f"{ts_syslog()} web-01 sshd[{pid}]: "
                f"pam_unix(sshd:session): session opened for user {user} by (uid=0)"
            )

        elif event_type == "sudo":
            cmd = random.choice(["/bin/bash", "/usr/bin/git pull", "/bin/systemctl restart nginx",
                                 "/usr/bin/apt update", "/bin/journalctl -xe", "/usr/sbin/ufw status"])
            lines.append(
                f"{ts_syslog()} web-01 sudo: {user} : TTY=pts/0 ; "
                f"PWD=/home/{user} ; USER=root ; COMMAND={cmd}"
            )

        else:
            lines.append(
                f"{ts_syslog()} web-01 sshd[{pid}]: "
                f"pam_unix(sshd:session): session closed for user {user}"
            )

    return lines


# ---------------------------------------------------------------------------
# FUENTE 3: NGINX - trafico web normal
# ---------------------------------------------------------------------------
def gen_nginx_normal(count=30):
    """Genera trafico nginx normal (codigos 200, 301, 304, 404 aislados)."""
    codes  = [200, 200, 200, 200, 301, 304, 200, 200, 200, 404]
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "curl/7.68.0",
        "python-requests/2.28.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    ]
    lines = []
    for _ in range(count):
        ip   = random.choice(INTERNAL_IPS + ["104.236.246.58", "45.33.32.156"])
        path = random.choice(PATHS_OK)
        code = random.choice(codes)
        size = random.randint(100, 50000)
        ua   = random.choice(agents)
        lines.append(
            f'{ip} - - [{ts_nginx()}] '
            f'"GET {path} HTTP/1.1" {code} {size} '
            f'"-" "{ua}"'
        )
    return lines


# ---------------------------------------------------------------------------
# FUENTE 4: KUBERNETES - logs de contenedores
# ---------------------------------------------------------------------------
def gen_k8s_logs(count=15):
    """Genera logs de contenedores Kubernetes (eventos normales)."""
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
        msg_type = random.choice(["info", "info", "info", "warn"])
        messages = {
            "info": f"Request processed in {random.randint(10,500)}ms",
            "warn": f"Connection pool at {random.randint(70,85)}% capacity",
        }
        lines.append(json.dumps({
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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generador de logs normales SIEM (R8.2)")
    parser.add_argument("--source", choices=["all", "syslog", "auth", "nginx", "k8s"],
                        default="all", help="Fuente de logs a generar")
    parser.add_argument("--count",  type=int, default=30,
                        help="Numero de entradas de log por fuente")
    parser.add_argument("--syslog-path", default=str(BASE_LOG_DIR / "syslog"))
    parser.add_argument("--auth-path",   default=str(BASE_LOG_DIR / "auth.log"))
    parser.add_argument("--nginx-path",  default=str(BASE_LOG_DIR / "nginx" / "access.log"))
    parser.add_argument("--k8s-path",    default=str(BASE_LOG_DIR / "containers" / "test-pod.log"))
    args = parser.parse_args()

    print(f"\nGenerador de logs normales SIEM - {ts_iso()}\n")

    if args.source in ("all", "syslog"):
        print("Generando syslog normal...")
        write_logs(gen_syslog(args.count), args.syslog_path)

    if args.source in ("all", "auth"):
        print("Generando auth.log normal...")
        write_logs(gen_auth_normal(max(args.count // 2, 5)), args.auth_path)

    if args.source in ("all", "nginx"):
        print("Generando nginx access normal...")
        write_logs(gen_nginx_normal(args.count), args.nginx_path)

    if args.source in ("all", "k8s"):
        print("Generando logs Kubernetes normales...")
        write_logs(gen_k8s_logs(max(args.count // 2, 10)), args.k8s_path)

    print("\nLogs normales generados. Esperar ~15s para que Filebeat los procese.")


if __name__ == "__main__":
    main()
