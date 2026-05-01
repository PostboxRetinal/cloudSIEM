# Playbook de Respuesta: Ataque de Fuerza Bruta (SSH/Auth)

## 1. Fase de Identificación
*   **Alerta:** `Security Alert: Potential SSH Brute Force Detected`.
*   **Criterio:** Más de 10 intentos de login fallidos en menos de 1 minuto desde la misma IP de origen.
*   **Herramientas:** Kibana SIEM / Dashboard Operacional.

## 2. Fase de Investigación
1.  **Verificar IP de Origen:** Consultar en el Dashboard el campo `source.geo.country_name`. ¿Es una ubicación inusual para la organización?
2.  **Impacto:** Verificar si hay algún evento `authentication_success` posterior a los fallos desde la misma IP.
3.  **Usuario Objetivo:** Identificar si el ataque es contra un usuario real o usuarios genéricos (`root`, `admin`).

## 3. Fase de Contención
1.  **Bloqueo de IP:** Agregar la IP atacante a la lista negra del Firewall o Security Group de la nube (Azure/AWS).
2.  **Desactivación de Usuario:** Si el ataque fue exitoso, deshabilitar la cuenta de usuario comprometida inmediatamente.

## 4. Fase de Erradicación
1.  **Reset de Contraseña:** Forzar cambio de contraseña con política de complejidad.
2.  **MFA:** Implementar autenticación de dos factores si no estaba activa.

## 5. Lecciones Aprendidas
*   ¿Por qué el firewall no bloqueó la IP automáticamente?
*   ¿Es necesario cambiar el puerto estándar de SSH (22)?
