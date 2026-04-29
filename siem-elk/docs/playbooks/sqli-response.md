# 🛡️ Playbook de Respuesta: Intento de Inyección SQL (SQLi)

## 1. Fase de Identificación

- **Alerta:** `Security Alert: SQL Injection Pattern Detected in Web Logs`.
- **Criterio:** Presencia de caracteres sospechosos (`'`, `--`, `OR 1=1`, `UNION SELECT`) en la URL o cuerpo de la petición capturada por Nginx.
- **Herramientas:** Dashboard Operacional > Logs de Nginx.

## 2. Fase de Investigación

1.  **Analizar el Payload:** Revisar el campo `url.path` o `url.query` para entender qué intentaba extraer el atacante.
2.  **Verificar Respuesta del Servidor:** ¿El servidor respondió con un `500 Internal Server Error` (malo) o con un `403 Forbidden` (bueno)?
3.  **Correlación:** Buscar si la misma IP ha realizado escaneos de vulnerabilidades previos.

## 3. Fase de Contención

1.  **Bloqueo en WAF:** Bloquear el patrón específico o la IP en el Web Application Firewall.
2.  **Aislamiento:** Si se sospecha compromiso de base de datos, poner el servicio en modo mantenimiento.

## 4. Fase de Erradicación

1.  **Parcheo de Código:** Implementar consultas preparadas (Prepared Statements) en la aplicación afectada.
2.  **Sanitización:** Revisar las reglas de validación de entrada en el servidor Logstash/Nginx.

## 5. Lecciones Aprendidas

- ¿La aplicación tiene vulnerabilidades conocidas no parcheadas?
- ¿Es necesario endurecer las reglas de ModSecurity?
