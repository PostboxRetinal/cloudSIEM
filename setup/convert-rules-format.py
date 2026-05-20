#!/usr/bin/env python3
"""
convert-rules-format.py
Convierte los archivos de reglas JSON a formato compatible con Kibana 8.19.14
Renombra "id" a "rule_id" en cada regla.
"""

import json
from pathlib import Path

def convert_rules():
    rules_dir = Path(__file__).resolve().parent.parent / "rules"
    
    # Archivos de reglas individuales
    rule_files = [
        "brute-force-ssh.json",
        "login-after-hours.json", 
        "multiple-404.json",
        "port-scan.json",
        "sensitive-paths.json"
    ]
    
    all_rules = []
    
    for rule_file_name in rule_files:
        rule_path = rules_dir / rule_file_name
        if not rule_path.exists():
            print(f"WARN: {rule_file_name} no encontrado")
            continue
            
        with rule_path.open("r") as f:
            rule = json.load(f)
        
        # Renombrar "id" a "rule_id"
        if "id" in rule:
            rule["rule_id"] = rule.pop("id")
        
        all_rules.append(rule)
        print(f"✓ Convertida: {rule_file_name}")
    
    # Generar NDJSON
    output_path = rules_dir / "all-rules.ndjson"
    with output_path.open("w") as f:
        for rule in all_rules:
            f.write(json.dumps(rule, ensure_ascii=False) + "\n")
    
    print(f"\n✓ Archivo generado: {output_path}")
    print(f"  Total de reglas: {len(all_rules)}")

if __name__ == "__main__":
    convert_rules()
