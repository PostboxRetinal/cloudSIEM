# Guia de generacion de logs - SIEM Platform

## Estructura de los scripts

```
setup/
  generate-test-logs.py      # Script 1: genera logs de ATAQUE (R8.5)
  generate-normal-logs.py    # Script 2: genera logs LEGITIMOS (R8.2)
  orchestrate-logs.py        # Script 3: orquestador que coordina ambos
```

---

## Script 1: generate-test-logs.py

Genera logs de ataque simulado para probar las reglas de deteccion del SIEM.

### Ataques disponibles

| Argumento | Ataque | Fuente de log | Regla que dispara |
|---|---|---|---|
| `brute_force` | Fuerza bruta SSH | `auth.log` | SIEM - Brute Force SSH Detectado |
| `404_flood` | Enumeracion web (404 flood) | `nginx/access.log` | SIEM - Flood de Errores HTTP 404 |
| `sqli` | Inyeccion SQL + rutas sensibles | `nginx/access.log` | SIEM - Acceso a Rutas Web Sensibles |
| `port_scan` | Escaneo nmap (SYN scan) | `syslog` | SIEM - Escaneo de Puertos Detectado |
| `all_attacks` | Todos los anteriores | -- | Todas las reglas |

### Ejemplos

```bash
# Todos los ataques (por defecto)
python setup/generate-test-logs.py

# Solo brute force SSH con 50 intentos
python setup/generate-test-logs.py --attack brute_force --count 50

# Solo escaneo nmap
python setup/generate-test-logs.py --attack port_scan
```

---

## Script 2: generate-normal-logs.py

Genera logs legitimios (sin actividad maliciosa) para las 4 fuentes del pipeline.

### Fuentes

| Argumento | Fuente | Contenido |
|---|---|---|
| `syslog` | Sistema | systemd, cron, kernel, NetworkManager, rsyslog, ntpd |
| `auth` | Autenticacion | SSH Accepted, session open/close, sudo commands |
| `nginx` | Web | Trafico HTTP normal (200, 301, 304) |
| `k8s` | Kubernetes | Logs de pods frontend, backend, redis, postgres |
| `all` | Todas las anteriores | Mix de las 4 fuentes |

### Ejemplos

```bash
# Todas las fuentes (por defecto)
python setup/generate-normal-logs.py

# Solo syslog con 50 lineas
python setup/generate-normal-logs.py --source syslog --count 50

# Solo logs de nginx
python setup/generate-normal-logs.py --source nginx --count 30
```

---

## Script 3: orchestrate-logs.py

Orquestador que coordina los dos scripts anteriores. Proporciona 3 modos de operacion.

### Modos

| Modo | Descripcion | Funcion |
|---|---|---|
| `random` | Mix aleatorio de logs normales y ataques | `generate_random_mix()` |
| `attacks` | Solo logs de ataque (llama Script 1) | `generate_attacks()` |
| `normal` | Solo logs legitimios (llama Script 2) | `generate_normal()` |

### Ejemplos

```bash
# Mix aleatorio de logs normales + ataques
python setup/orchestrate-logs.py --mode random

# Solo ataques (todos los escenarios)
python setup/orchestrate-logs.py --mode attacks

# Solo logs normales (las 4 fuentes)
python setup/orchestrate-logs.py --mode normal
```

---

## Flujo de trabajo recomendado

### 1. Generar logs normales (R8.2)

```bash
python setup/generate-normal-logs.py --source all --count 30
```

Verificar en Kibana -> Discover que los indices `logs-syslog-*`, `logs-auth-*`,
`logs-nginx-*` y `logs-k8s-*` tienen documentos.

### 2. Verificar tasa de parseo (R8.3)

```bash
python setup/verify-parse-rate.py
```

Debe reportar > 95%.

### 3. Generar ataques y verificar deteccion (R8.4, R8.5)

```bash
# Opcion A: orquestador modo ataques
python setup/orchestrate-logs.py --mode attacks

# Opcion B: script individual
python setup/generate-test-logs.py --attack all_attacks
```

Esperar ~30-60s y verificar en Kibana -> Security -> Alerts:

- `SIEM - Brute Force SSH Detectado`
- `SIEM - Escaneo de Puertos Detectado`
- `SIEM - Flood de Errores HTTP 404`
- `SIEM - Login SSH Exitoso Fuera de Horario Laboral`
- `SIEM - Acceso a Rutas Web Sensibles`

### 4. Demostracion completa (mix)

```bash
python setup/orchestrate-logs.py --mode random
```

Esto genera una mezcla realista de trafico normal y ataques, simulando un
entorno de produccion real.

---

## Solucion de problemas

**Los logs no aparecen en Kibana:**
```bash
# Verificar que Filebeat esta corriendo
docker ps | grep filebeat

# Verificar que los archivos existen
ls -la logs/

# Verificar conexion Logstash
curl -s http://localhost:9600/ | python3 -m json.tool
```

**La tasa de parseo es baja:**
```bash
# Revisar logs de Logstash
docker logs siem-logstash --tail 50

# Verificar contenido del indice de errores
curl -sk https://localhost:9200/logs-errors-*/_search?pretty \
  -u elastic:${ELASTIC_PASSWORD}
```
