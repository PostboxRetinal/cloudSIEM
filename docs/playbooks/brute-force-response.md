# Playbook de respuesta: fuerza bruta SSH

## Objetivo

Guiar la respuesta ante múltiples intentos fallidos de autenticación SSH desde una misma IP. El playbook cubre investigación, contención, erradicación y lecciones aprendidas para un incidente simulado en CloudSIEM.

## Resumen del escenario

| Dato | Valor |
| --- | --- |
| Alerta principal | `SIEM - Brute Force SSH Detectado` |
| Severidad esperada | `high` |
| Regla | `rules/brute-force-ssh.json` |
| Fuente | `logs-auth*` |
| Dataset | `event.dataset:"system.auth"` |
| Condición | 5 o más fallos de autenticación desde la misma `source.ip` en 60 segundos |
| Técnica MITRE ATT&CK | `T1110.001 - Password Guessing` |
| Script de simulación | `python3 setup/generate-test-logs.py --attack brute_force --count 35` |

## Criterios de activación

Ejecutar este playbook si se cumple al menos una condición:

1. Se genera una alerta `SIEM - Brute Force SSH Detectado` en `Kibana -> Security -> Alerts`.
2. En `Discover` se observan múltiples eventos `event.action:"authentication_failure"` desde la misma `source.ip`.
3. El dashboard operacional muestra un aumento anormal de fallos SSH.

## Roles mínimos

| Rol | Responsabilidad |
| --- | --- |
| Operador SIEM | Ejecuta la investigación y registra evidencia. |
| Responsable de infraestructura | Aplica bloqueo de IP, firewall o cambios de SSH si corresponde. |
| Responsable de identidad | Restablece credenciales o deshabilita usuarios si hubo éxito de autenticación. |

## Preparación

1. Abrir `Kibana -> Security -> Alerts`.
2. Seleccionar una ventana de tiempo de los últimos 15 minutos.
3. Confirmar que el índice `logs-auth*` contiene eventos recientes.
4. Si es una simulación, generar el escenario desde la raíz del repositorio:

```bash
python3 setup/generate-test-logs.py --attack brute_force --count 35
```

Esperar de 30 a 60 segundos para que Filebeat, Logstash y Elasticsearch procesen los eventos.

## Fase 1: identificación

1. Buscar la alerta `SIEM - Brute Force SSH Detectado`.
2. Registrar estos datos de la alerta:

| Campo | Valor a registrar |
| --- | --- |
| Hora de alerta | `@timestamp` o `kibana.alert.start` |
| Regla | `kibana.alert.rule.name` |
| Severidad | `kibana.alert.severity` |
| IP origen | `source.ip` |
| Host afectado | `host.name` |
| Usuario objetivo | `user.name` |
| Acción | `event.action` |
| Resultado | `event.outcome` |

3. Si no aparece la alerta, abrir `Discover` y usar esta consulta KQL:

```text
event.dataset:"system.auth" and event.action:"authentication_failure" and process.name:"sshd"
```

4. Confirmar que una misma `source.ip` genera 5 o más fallos en 60 segundos.

## Fase 2: investigación

### Paso 1: determinar origen y volumen

En `Discover`, filtrar por la IP origen de la alerta:

```text
event.dataset:"system.auth" and source.ip:"<IP_ORIGEN>"
```

Registrar:

| Pregunta | Evidencia esperada |
| --- | --- |
| Cuántos intentos hubo | Conteo de eventos en la ventana temporal. |
| Desde qué IP vinieron | `source.ip`. |
| Contra qué host | `host.name`. |
| Contra qué usuarios | Lista de `user.name`. |
| Eran usuarios válidos o genéricos | `root`, `admin`, `ubuntu`, `postgres`, `test`, otros. |

### Paso 2: buscar autenticación exitosa posterior

Usar la misma IP origen y ampliar la ventana a 30 minutos:

```text
event.dataset:"system.auth" and source.ip:"<IP_ORIGEN>" and event.action:"authentication_success"
```

Interpretación:

| Resultado | Clasificación |
| --- | --- |
| No hay eventos exitosos | Intento de brute force bloqueado o fallido. |
| Hay `authentication_success` después de los fallos | Compromiso probable de cuenta. |
| Hay éxito desde IP interna conocida y usuario validado | Posible falso positivo, requiere confirmación. |

### Paso 3: revisar actividad posterior del usuario

Si hubo autenticación exitosa, buscar actividad de sesión y comandos con privilegios:

```text
event.dataset:"system.auth" and user.name:"<USUARIO>" and (event.action:"session_opened" or event.action:"sudo_command" or tags:"privilege_escalation")
```

Registrar cualquier `process.command_line`, `host.name`, `user.name` y `@timestamp` observado.

### Paso 4: descartar falsos positivos

Considerar falso positivo solo si se puede demostrar una de estas condiciones:

| Condición | Evidencia requerida |
| --- | --- |
| Usuario legítimo olvidó su clave | Confirmación del usuario y origen esperado. |
| Servicio interno tiene credencial vencida | IP interna documentada y owner identificado. |
| Prueba autorizada | Ventana de prueba aprobada y origen conocido. |

Si no existe evidencia suficiente, tratar el evento como incidente real o simulación maliciosa confirmada.

## Fase 3: contención

### Acciones para laboratorio

1. Marcar la alerta como `acknowledged` o `in progress` en Kibana si la opción está disponible.
2. Documentar la IP atacante y el usuario objetivo.
3. No modificar servicios productivos durante la simulación.
4. Si se requiere demostrar contención, registrar el comando que se aplicaría:

```bash
sudo ufw deny from <IP_ORIGEN> to any port 22
```

### Acciones para entorno real

Aplicar según el resultado de investigación:

| Condición | Acción de contención |
| --- | --- |
| Solo fallos, sin éxito | Bloquear `source.ip` en firewall o security group. |
| Éxito posterior desde la misma IP | Bloquear IP, revocar sesiones y deshabilitar usuario afectado. |
| Múltiples usuarios atacados | Bloquear IP y revisar políticas de lockout. |
| Usuario privilegiado afectado | Escalar a incidente crítico y revocar credenciales de inmediato. |

Comandos de referencia para Linux:

```bash
sudo ufw deny from <IP_ORIGEN> to any port 22
sudo pkill -u <USUARIO>
sudo passwd -l <USUARIO>
```

Usar estos comandos solo con aprobación del responsable del sistema.

## Fase 4: erradicación

1. Forzar cambio de contraseña del usuario afectado si hubo éxito de autenticación.
2. Revocar llaves SSH no reconocidas en `~/.ssh/authorized_keys`.
3. Revisar cuentas con permisos elevados y accesos recientes.
4. Habilitar MFA donde aplique.
5. Validar que `PasswordAuthentication` esté deshabilitado si la política exige solo llaves SSH.
6. Ajustar `MaxAuthTries`, `AllowUsers` o controles equivalentes en `sshd_config`.
7. Confirmar que no vuelven a aparecer eventos desde la misma `source.ip` después de la contención.

Consulta de verificación:

```text
event.dataset:"system.auth" and source.ip:"<IP_ORIGEN>" and @timestamp >= "<HORA_CONTENCION>"
```

## Fase 5: recuperación y monitoreo

1. Mantener monitoreo por 30 minutos después de la contención.
2. Verificar que no existan nuevos `authentication_success` sospechosos.
3. Validar que los usuarios legítimos puedan autenticarse con el método permitido.
4. Cerrar la alerta solo cuando el origen esté bloqueado o clasificado como benigno.

## Lecciones aprendidas

Completar estas preguntas al cierre:

| Pregunta | Respuesta |
| --- | --- |
| La detección se generó en menos de 60 segundos |  |
| La alerta mostró la IP origen correctamente |  |
| Hubo autenticación exitosa posterior |  |
| La política de bloqueo de cuentas fue suficiente |  |
| El firewall bloqueó automáticamente o requirió acción manual |  |
| Se requiere MFA, allowlist o deshabilitar contraseñas SSH |  |
| Qué ajuste se hará a reglas, dashboards o documentación |  |

## Checklist de cierre

| Ítem | Estado |
| --- | --- |
| Alerta identificada |  |
| IP origen registrada |  |
| Usuarios objetivo registrados |  |
| Se buscó autenticación exitosa posterior |  |
| Se clasificó el incidente |  |
| Se definió contención |  |
| Se definió erradicación |  |
| Se documentaron lecciones aprendidas |  |
| Otro integrante pudo seguir el procedimiento |  |

## Resultado esperado en simulación

Para considerar exitosa la prueba, un operador no involucrado en la creación del playbook debe poder concluir:

1. La IP atacante generó múltiples fallos SSH.
2. La regla `SIEM - Brute Force SSH Detectado` corresponde al comportamiento observado.
3. No hubo acceso exitoso, o si lo hubo, se trató como compromiso probable.
4. La acción de contención elegida coincide con la evidencia.
5. Las lecciones aprendidas quedaron registradas.
