#!/usr/bin/env python3
"""
orchestrate-logs.py
Orquestador de generacion de logs para el SIEM.
Cumple R8.5: coordina logs de ataque (generate-test-logs.py) y
logs normales (generate-normal-logs.py) en 3 modos.

Uso:
    python3 orchestrate-logs.py --mode random   # mix aleatorio de normales + ataques
    python3 orchestrate-logs.py --mode attacks  # solo ataques
    python3 orchestrate-logs.py --mode normal   # solo logs normales
"""

import argparse
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def call_attack_script(attack_type="all_attacks", count=30):
    """Ejecuta generate-test-logs.py con el tipo de ataque indicado."""
    script = SCRIPT_DIR / "generate-test-logs.py"
    print(f"  >> Llamando: {script.name} --attack {attack_type}")
    result = subprocess.run(
        [sys.executable, str(script), "--attack", attack_type, "--count", str(count)],
        capture_output=False,
    )
    return result.returncode == 0


def call_normal_script(source="all", count=30):
    """Ejecuta generate-normal-logs.py con la fuente indicada."""
    script = SCRIPT_DIR / "generate-normal-logs.py"
    print(f"  >> Llamando: {script.name} --source {source}")
    result = subprocess.run(
        [sys.executable, str(script), "--source", source, "--count", str(count)],
        capture_output=False,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# MODO 1: Logs aleatorios (mix de normales + ataques)
# ---------------------------------------------------------------------------
def generate_random_mix():
    """Funcion 1: llama aleatoriamente a los 2 scripts para generar un mix."""
    print("\n=== MODO RANDOM: Mix aleatorio de logs normales y ataques ===\n")
    operations = []

    for _ in range(random.randint(2, 4)):
        operations.append(("normal", random.choice(["all", "syslog", "auth", "nginx", "k8s"]),
                          random.randint(10, 40)))

    attack_types = ["brute_force", "404_flood", "sqli", "port_scan"]
    random.shuffle(attack_types)
    for atk in attack_types[:random.randint(1, 3)]:
        operations.append(("attack", atk, random.randint(15, 40)))

    random.shuffle(operations)

    for op_type, target, count in operations:
        if op_type == "normal":
            call_normal_script(target, count)
        else:
            call_attack_script(target, count)

    print(f"\nMix completado: {len(operations)} operaciones ejecutadas.\n")


# ---------------------------------------------------------------------------
# MODO 2: Solo ataques
# ---------------------------------------------------------------------------
def generate_attacks():
    """Funcion 2: llama solo a generate-test-logs.py con todos los ataques."""
    print("\n=== MODO ATAQUES: Solo logs de amenazas ===\n")
    call_attack_script("all_attacks", 35)
    print("\nAtaques completados.\n")


# ---------------------------------------------------------------------------
# MODO 3: Solo logs normales
# ---------------------------------------------------------------------------
def generate_normal():
    """Funcion 3: llama solo a generate-normal-logs.py con todas las fuentes."""
    print("\n=== MODO NORMAL: Solo logs legitimos ===\n")
    call_normal_script("all", 30)
    print("\nLogs normales completados.\n")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Orquestador de logs SIEM (R8.5)")
    parser.add_argument("--mode", choices=["random", "attacks", "normal"],
                        default="random",
                        help="Modo de generacion: random (mix), attacks (solo ataques), "
                             "normal (solo logs legitimos)")
    args = parser.parse_args()

    print(f"Orquestador SIEM - {datetime.now(timezone.utc).isoformat()}")

    if args.mode == "random":
        generate_random_mix()
    elif args.mode == "attacks":
        generate_attacks()
    elif args.mode == "normal":
        generate_normal()

    print("Esperar ~30s para que Filebeat procese los logs.")
    print("Verificar en Kibana -> Discover -> indice logs-* o Security -> Alerts")


if __name__ == "__main__":
    main()
