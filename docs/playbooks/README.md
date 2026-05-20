# Guía operativa de playbooks de respuesta

Esta carpeta contiene los playbooks de respuesta a incidentes del proyecto CloudSIEM. Su objetivo es que una persona que no participó en la creación del playbook pueda investigar, contener, erradicar y documentar un incidente simulado usando Kibana y los logs generados por el laboratorio.

## Alcance

| Escenario | Playbook | Alerta o indicador principal | Fuente |
| --- | --- | --- | --- |
| Fuerza bruta SSH | [brute-force-response.md](brute-force-response.md) | `SIEM - Brute Force SSH Detectado` | `logs-auth*` |
| SQLi y rutas web sensibles | [sqli-response.md](sqli-response.md) | `SIEM - Acceso a Rutas Web Sensibles`, `siem.sqli_detected:true` | `logs-nginx*` |

## Requisitos previos

Antes de ejecutar cualquier playbook, verificar que:

1. El stack ELK esté levantado y Kibana sea accesible.
2. Las reglas de detección estén importadas y habilitadas.
3. Filebeat esté enviando eventos hacia Logstash y Elasticsearch.
4. El operador tenga acceso a `Kibana -> Security -> Alerts`, `Discover` y al dashboard `Operational - Consola de Triaje`, si fue importado.
5. La hora de Kibana cubra al menos los últimos 15 minutos durante simulaciones.

## Flujo común de respuesta

Cada playbook sigue el mismo flujo operativo:

1. Identificar la alerta o indicador.
2. Reunir evidencia mínima: hora, regla, severidad, `source.ip`, host afectado, usuario o URL, cantidad de eventos y resultado de la petición o autenticación.
3. Investigar eventos relacionados en la misma ventana temporal.
4. Clasificar el incidente como falso positivo, intento bloqueado o compromiso probable.
5. Ejecutar contención según el nivel de impacto.
6. Ejecutar erradicación y corrección de causa raíz.
7. Registrar lecciones aprendidas y mejoras de detección.

## Evidencia mínima por incidente

| Campo | Por qué importa |
| --- | --- |
| `@timestamp` | Define la ventana de investigación. |
| `kibana.alert.rule.name` | Confirma que se disparó la regla esperada. |
| `event.dataset` | Identifica la fuente de logs. |
| `event.action` | Resume la acción observada. |
| `event.outcome` | Distingue intentos fallidos de accesos exitosos. |
| `source.ip` | Identifica el origen del ataque o simulación. |
| `host.name` | Identifica el activo afectado. |
| `user.name` | Aplica a autenticación SSH. |
| `url.path`, `url.query`, `url.original` | Aplica a ataques web. |
| `http.response.status_code` | Indica si el intento web fue bloqueado o exitoso. |

## Criterio de aceptación del playbook

El playbook se considera útil si un integrante no involucrado en su creación puede:

1. Generar o recibir el incidente simulado.
2. Encontrar la alerta o indicador correcto en Kibana.
3. Completar la sección de investigación con evidencia concreta.
4. Tomar una decisión de contención justificada.
5. Ejecutar o describir la acción de erradicación adecuada.
6. Registrar al menos tres lecciones aprendidas o mejoras.
7. Cerrar el incidente con una conclusión reproducible.

## Cómo simular los escenarios

Desde la raíz del repositorio:

```bash
python3 setup/generate-test-logs.py --attack brute_force --count 35
python3 setup/generate-test-logs.py --attack sqli
```

Después de generar los logs, esperar de 30 a 60 segundos y revisar `Kibana -> Security -> Alerts` o `Discover` con los filtros indicados en cada playbook.

## Formato de cierre

Registrar el cierre con este resumen:

| Dato | Valor |
| --- | --- |
| Playbook usado |  |
| Fecha y hora de inicio |  |
| Fecha y hora de cierre |  |
| Alerta o indicador |  |
| IP origen |  |
| Activo afectado |  |
| Impacto confirmado |  |
| Contención aplicada |  |
| Erradicación aplicada |  |
| Evidencia guardada |  |
| Lecciones aprendidas |  |
