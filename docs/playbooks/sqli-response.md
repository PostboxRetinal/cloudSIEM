# Playbook de respuesta: SQLi y rutas web sensibles

## Objetivo

Guiar la respuesta ante intentos de inyección SQL y accesos a rutas web sensibles observados en logs de Nginx. El playbook está orientado a confirmar el intento, estimar impacto, contener el origen y definir acciones de erradicación.

## Resumen del escenario

| Dato | Valor |
| --- | --- |
| Alerta principal | `SIEM - Acceso a Rutas Web Sensibles` |
| Indicador SQLi | `siem.sqli_detected:true` o tag `sqli_detected` |
| Severidad esperada | `high` para rutas sensibles, variable para SQLi según respuesta HTTP |
| Regla | `rules/sensitive-paths.json` |
| Fuente | `logs-nginx*` |
| Dataset | `event.dataset:"nginx.access"` |
| Técnicas MITRE ATT&CK | `T1190 - Exploit Public-Facing Application`, `T1552.001 - Credentials In Files` |
| Script de simulación | `python3 setup/generate-test-logs.py --attack sqli` |

## Criterios de activación

Ejecutar este playbook si se cumple al menos una condición:

1. Se genera la alerta `SIEM - Acceso a Rutas Web Sensibles`.
2. En `Discover` aparecen eventos con `siem.sqli_detected:true` o tag `sqli_detected`.
3. Una IP externa solicita rutas como `/admin`, `/.env`, `/wp-admin`, `/phpmyadmin`, `/config.php` o rutas equivalentes.
4. El `user_agent.original` muestra herramientas como `sqlmap`, `nikto`, `curl`, `nmap`, `gobuster` o `dirbuster`.

## Roles mínimos

| Rol | Responsabilidad |
| --- | --- |
| Operador SIEM | Investiga la alerta y recolecta evidencia. |
| Responsable de aplicación | Valida impacto en endpoint, código y datos. |
| Responsable de infraestructura | Aplica bloqueo de IP, rate limit o reglas WAF. |
| Responsable de seguridad | Decide rotación de secretos y escalamiento. |

## Preparación

1. Abrir `Kibana -> Security -> Alerts` y `Discover`.
2. Seleccionar una ventana de tiempo de los últimos 15 minutos.
3. Confirmar que el índice `logs-nginx*` contiene eventos recientes.
4. Si es una simulación, generar el escenario desde la raíz del repositorio:

```bash
python3 setup/generate-test-logs.py --attack sqli
```

Esperar de 30 a 60 segundos para que los eventos lleguen a Kibana.

## Fase 1: identificación

1. Buscar la alerta `SIEM - Acceso a Rutas Web Sensibles` en `Kibana -> Security -> Alerts`.
2. En paralelo, abrir `Discover` y usar esta consulta para detectar SQLi:

```text
event.dataset:"nginx.access" and (siem.sqli_detected:true or tags:"sqli_detected")
```

3. Si la alerta no aparece, buscar rutas sensibles:

```text
event.dataset:"nginx.access" and (siem.sensitive_path:true or tags:"sensitive_path_access")
```

4. Registrar estos datos:

| Campo | Valor a registrar |
| --- | --- |
| Hora del evento | `@timestamp` |
| IP origen | `source.ip` |
| Host o servicio | `host.name`, `service.name` si existe |
| Método HTTP | `http.request.method` |
| URL completa | `url.original` |
| Ruta | `url.path` |
| Query string | `url.query` |
| Código HTTP | `http.response.status_code` |
| User agent | `user_agent.original` |
| Tags SIEM | `tags` |

## Fase 2: investigación

### Paso 1: confirmar patrón de SQLi

Revisar `url.original` y `url.query` buscando patrones como:

| Patrón | Interpretación |
| --- | --- |
| `' OR '1'='1` | Bypass de autenticación o condición siempre verdadera. |
| `UNION SELECT` | Intento de extracción de columnas o tablas. |
| `DROP TABLE` | Intento destructivo contra base de datos. |
| `--` | Comentario SQL para alterar la consulta. |
| User agent `sqlmap` | Automatización de prueba o ataque SQLi. |

Consulta KQL recomendada:

```text
event.dataset:"nginx.access" and source.ip:"<IP_ORIGEN>" and (url.original:*UNION* or url.original:*SELECT* or url.original:*DROP* or url.original:*1\=1* or user_agent.original:*sqlmap*)
```

### Paso 2: evaluar respuesta del servidor

Clasificar impacto según `http.response.status_code`:

| Código | Interpretación | Severidad operativa |
| --- | --- | --- |
| `200` | La aplicación respondió correctamente al payload o ruta sensible. Puede haber exposición. | Alta |
| `301` o `302` | Redirección. Revisar destino y si redirige a login. | Media |
| `403` | Bloqueado por aplicación, WAF o control de acceso. | Media |
| `404` | Ruta inexistente. Puede ser reconocimiento. | Baja a media |
| `500` | Error interno. Puede indicar vulnerabilidad o fallo de manejo de entrada. | Alta |

### Paso 3: identificar rutas sensibles solicitadas

Buscar todas las solicitudes de la misma IP en la ventana de investigación:

```text
event.dataset:"nginx.access" and source.ip:"<IP_ORIGEN>"
```

Registrar si aparecen rutas como:

| Ruta | Riesgo |
| --- | --- |
| `/.env` | Exposición de secretos. |
| `/config.php` o `/config` | Exposición de configuración. |
| `/.git` | Exposición de código fuente. |
| `/phpmyadmin` | Administración de base de datos expuesta. |
| `/admin` o `/api/admin` | Panel administrativo expuesto. |
| `/etc/passwd` o `/proc/` | Intento de lectura de archivos del sistema. |

### Paso 4: correlacionar actividad relacionada

Buscar si la misma IP también generó otros indicadores:

```text
source.ip:"<IP_ORIGEN>" and (tags:"http_404" or tags:"security_scanner" or siem.sensitive_path:true or siem.sqli_detected:true)
```

Si existen muchos `404`, revisar también el playbook de enumeración web cuando esté disponible. Si existen intentos de SSH desde la misma IP, aplicar el playbook de fuerza bruta SSH.

### Paso 5: clasificar el incidente

| Evidencia | Clasificación |
| --- | --- |
| SQLi con `403` o `404`, sin otros eventos | Intento bloqueado o reconocimiento. |
| SQLi con `200` | Explotación posible, requiere revisión de aplicación. |
| SQLi con `500` | Vulnerabilidad probable o manejo inseguro de entrada. |
| Acceso `200` a `/.env`, `/config`, `/.git` o similar | Compromiso probable de secretos o información. |
| User agent de scanner autorizado desde IP interna documentada | Posible falso positivo, requiere evidencia de autorización. |

## Fase 3: contención

### Acciones para laboratorio

1. Registrar IP origen, URL completa, código HTTP y user agent.
2. Marcar la alerta como `acknowledged` o `in progress` si Kibana lo permite.
3. No cambiar reglas de firewall productivas durante la simulación.
4. Documentar la acción que se aplicaría si fuera un entorno real.

### Acciones para entorno real

Aplicar según la clasificación:

| Condición | Acción de contención |
| --- | --- |
| Scanner externo con múltiples intentos | Bloquear `source.ip` en firewall, WAF o reverse proxy. |
| Payload SQLi con respuesta `200` | Bloquear IP y poner endpoint afectado en revisión urgente. |
| Ruta sensible con respuesta `200` | Bloquear acceso público, retirar archivo/ruta y rotar secretos expuestos. |
| Error `500` provocado por payload | Activar modo mantenimiento del endpoint si hay riesgo de explotación. |
| Scanner interno autorizado | Confirmar ventana de prueba y excluir solo si está documentado. |

Ejemplos de referencia:

```bash
sudo ufw deny from <IP_ORIGEN> to any port 80
sudo ufw deny from <IP_ORIGEN> to any port 443
```

Para Nginx, una contención temporal podría ser bloquear la IP en el bloque `server` o aplicar rate limiting. Implementar cambios solo con aprobación del responsable del servicio.

## Fase 4: erradicación

1. Revisar el endpoint afectado y confirmar que usa consultas preparadas o parametrizadas.
2. Validar entrada en servidor para parámetros usados en búsqueda, filtros, IDs y formularios.
3. Corregir manejo de errores para evitar respuestas `500` con payloads maliciosos.
4. Remover o proteger rutas sensibles como `/.env`, `/.git`, `/config.php`, `/phpmyadmin` y `/server-status`.
5. Rotar secretos si una ruta sensible respondió `200` o si existe duda razonable de exposición.
6. Agregar pruebas de seguridad para payloads SQLi comunes.
7. Revisar reglas WAF o controles equivalentes para bloquear patrones repetidos.
8. Confirmar que nuevos intentos similares generan alerta y no devuelven `200`.

Consulta de verificación:

```text
event.dataset:"nginx.access" and source.ip:"<IP_ORIGEN>" and @timestamp >= "<HORA_CONTENCION>"
```

## Fase 5: recuperación y monitoreo

1. Monitorear durante 30 minutos después de aplicar contención.
2. Confirmar que no hay nuevos `200` para payloads SQLi o rutas sensibles.
3. Revisar que el tráfico legítimo al servicio continúa funcionando.
4. Cerrar la alerta solo cuando la causa raíz esté documentada o el evento esté clasificado como falso positivo.

## Lecciones aprendidas

Completar estas preguntas al cierre:

| Pregunta | Respuesta |
| --- | --- |
| La detección apareció en menos de 60 segundos |  |
| La regla o indicador mostró la URL completa |  |
| El código HTTP permitió clasificar impacto |  |
| Hubo respuesta `200` a payload SQLi o ruta sensible |  |
| Se identificó el endpoint vulnerable o expuesto |  |
| Se requiere WAF, validación adicional o cambio de código |  |
| Se requiere rotación de secretos |  |
| Qué ajuste se hará a reglas, dashboards o documentación |  |

## Checklist de cierre

| Ítem | Estado |
| --- | --- |
| Indicador SQLi o alerta de ruta sensible identificado |  |
| IP origen registrada |  |
| URL y payload registrados |  |
| Código HTTP evaluado |  |
| User agent registrado |  |
| Se revisaron otros eventos de la misma IP |  |
| Se clasificó el impacto |  |
| Se definió contención |  |
| Se definió erradicación |  |
| Se documentaron lecciones aprendidas |  |
| Otro integrante pudo seguir el procedimiento |  |

## Resultado esperado en simulación

Para considerar exitosa la prueba, un operador no involucrado en la creación del playbook debe poder concluir:

1. La IP atacante generó payloads compatibles con SQLi y accesos a rutas sensibles.
2. Los campos `siem.sqli_detected`, `siem.sensitive_path`, `url.original` y `http.response.status_code` permiten explicar el incidente.
3. La severidad se justifica con la respuesta HTTP y el tipo de ruta solicitada.
4. La contención propuesta reduce nuevos intentos desde el origen observado.
5. Las acciones de erradicación apuntan a la causa raíz y no solo a la alerta.
