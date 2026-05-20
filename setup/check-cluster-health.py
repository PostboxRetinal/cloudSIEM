import requests
import os
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def get_env_var(var_name, default_value):
    try:
        with open(".env", "r") as f:
            for line in f:
                if line.startswith(var_name):
                    return line.split("=")[1].strip().replace('"', '').replace("'", "")
    except:
        pass
    return os.getenv(var_name, default_value)

ELASTIC_PASSWORD = get_env_var('ELASTIC_PASSWORD', 'SiemElastic2024!')
ELASTIC_HOST = "https://es01:9200"

def run_diagnostic():
    print("="*70)
    print(f"SIEM MASTER DIAGNOSTIC - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # --- 1. ELASTICSEARCH (R8.1) ---
    print("\n[1/4] ELASTICSEARCH CLUSTER")
    try:
        health = requests.get(f"{ELASTIC_HOST}/_cluster/health", auth=('elastic', ELASTIC_PASSWORD), verify=False, timeout=5).json()
        status = health['status']
        color = "OK" if status == "green" else "WARN" if status == "yellow" else "FAIL"
        print(f"   Salud: {color} {status.upper()}")
        
        nodes_info = requests.get(f"{ELASTIC_HOST}/_cat/nodes?h=name,ip,node.role,ram.percent,cpu&format=json", auth=('elastic', ELASTIC_PASSWORD), verify=False).json()
        print(f"   Nodos Activos ({len(nodes_info)}):")
        for n in nodes_info:
            print(f"   - {n['name'].ljust(15)} | IP: {n['ip'].ljust(12)} | CPU: {n['cpu']}% | RAM: {n['ram.percent']}%")
            
        # Verificar ILM (R8.1)
        ilm = requests.get(f"{ELASTIC_HOST}/_ilm/policy/siem-logs-policy", auth=('elastic', ELASTIC_PASSWORD), verify=False)
        ilm_status = "APLICADA (30 días)" if ilm.status_code == 200 else "NO ENCONTRADA"
        print(f"   Política ILM: {ilm_status}")
    except Exception as e:
        print(f"   Error conectando a Elasticsearch: {e}")

    # --- 2. SERVICIOS ELK (Logstash / Kibana) ---
    print("\n[2/4] ESTADO DE SERVICIOS")
    services = {
        "Kibana": "https://kibana:5601/api/status",
        "Logstash": "http://logstash:9600/_node/stats"
    }
    for name, url in services.items():
        try:
            res = requests.get(url, timeout=3, verify=False)
            status = "LIVE" if res.status_code == 200 else "STARTING"
            print(f"   └─ {name.ljust(10)}: {status}")
        except:
            print(f"   └─ {name.ljust(10)}: DOWN / NOT REACHABLE")

    # --- 3. REGLAS DE SEGURIDAD (R8.4) ---
    print("\n[3/4] REGLAS DE DETECCIÓN (SIEM)")
    try:
        # Consultar reglas vía API de Kibana
        rules = requests.get("https://kibana:5601/api/detection_engine/rules/_find",
                            auth=('elastic', ELASTIC_PASSWORD), 
                            headers={"kbn-xsrf": "true"}, timeout=5, verify=False).json()
        total_rules = rules.get('total', 0)
        mark = "OK" if total_rules >= 5 else "WARN"
        print(f"   {mark} Reglas Activas: {total_rules} (Mínimo requerido: 5)")
    except:
        print("   No se pudo conectar a la API de Reglas de Kibana.")

    # --- 4. INGESTA DE DATOS (R8.2) ---
    print("\n[4/4] VOLUMEN DE DATOS")
    sources = {"siem-auth": "Auth Logs", "siem-nginx": "Web Logs", "siem-syslog": "Syslogs"}
    for idx, name in sources.items():
        try:
            count = requests.get(f"{ELASTIC_HOST}/{idx}*/_count", auth=('elastic', ELASTIC_PASSWORD), verify=False).json().get('count', 0)
            print(f"   └─ {name.ljust(10)}: {count} docs")
        except:
            print(f"   └─ {name.ljust(10)}: 0 docs")

    print("\n" + "="*70)
    print("SUGERENCIA: Si los docs están en 0, ejecuta el generador de logs.")
    print("="*70)

if __name__ == "__main__":
    run_diagnostic()
