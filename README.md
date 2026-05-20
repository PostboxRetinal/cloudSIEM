# CloudSIEM

Guía del proyecto y del trabajo en `develop`.

## Resumen

CloudSIEM es una plataforma SIEM académica basada en Elastic Stack para centralizar, normalizar, correlacionar y visualizar eventos de seguridad. El repositorio corresponde al Proyecto 8 de la asignatura Computación en la Nube.

## Objetivos

- Centralizar y normalizar logs de múltiples fuentes.
- Detectar amenazas y patrones sospechosos.
- Visualizar el estado de seguridad en dashboards.
- Documentar respuesta a incidentes.
- Demostrar la detección de ataques simulados en un entorno controlado.

## Alcance del proyecto

- `Elasticsearch` para almacenamiento, indexación e `ILM`.
- `Logstash` para parsing, transformación y enriquecimiento.
- `Kibana` para observabilidad, seguridad y dashboards.
- `Filebeat` para recolección de logs.
- `Docker Compose` como despliegue principal; `Kubernetes` como ruta complementaria.
- `Python` para generadores de logs y utilidades.

## Despliegue local con Podman en Linux

El despliegue en Linux con Podman usa el launcher por etapas del repositorio:

```bash
systemctl --user start podman.socket
bash setup/run-podman-sentinel-stack.sh --build --force-recreate --no-sentinel
```

Para incluir la integración opcional con Microsoft Sentinel:

```bash
bash setup/run-podman-sentinel-stack.sh --build --force-recreate
```

Para detener el stack local:

```bash
podman-compose -f docker-compose.yml -f docker-compose-podman.yml down
```

Para detener el stack con Sentinel:

```bash
podman-compose -f docker-compose.yml -f docker-compose-podman.yml -f docker-compose-sentinel.yml -f docker-compose-sentinel-podman.yml down
```

El override `docker-compose-podman.yml` configura `userns_mode: keep-id` en Filebeat, relabeling SELinux para bind mounts y el socket rootless de Podman desde `$XDG_RUNTIME_DIR/podman/podman.sock`.

El launcher ejecuta los jobs one-shot con el orden correcto y evita los fallos de Podman Compose con servicios one-shot (`setup`, `cleanup-indices`, `ilm-setup`, `data-views-setup` y `dashboards-import`) que terminan correctamente pero no quedan en estado `running`. En Sentinel, el relabeling SELinux queda en `docker-compose-sentinel-podman.yml` para que `docker-compose-sentinel.yml` siga siendo portable en Windows y Docker Desktop.

Para Windows, Docker Desktop o WSL2 con Sentinel, usar:

```bash
docker compose -f docker-compose.yml -f docker-compose-sentinel.yml up --build
```

## Arquitectura propuesta

```text
Fuentes de logs
  |- Syslog
  |- auth.log
  |- Nginx/Apache
  |- Kubernetes
  `- Logs simulados por scripts

Filebeat / Recolección
  `- Filebeat

Pipeline de ingesta
  `- Logstash
      |- grok
      |- mutate
      |- geoip
      `- routing de errores

Almacenamiento y gestión
  `- Elasticsearch
      |- índices ECS
      |- ILM
      `- retención de 30 días

Analítica y visualización
  `- Kibana SIEM / Dashboards / Discover

Detección
  |- reglas de correlación
  `- alertas
```

## Fuentes de logs esperadas

El proyecto debe integrar al menos 3 fuentes de logs diferentes. Las fuentes objetivo definidas para la sustentación son:

- logs de sistema (`syslog`);
- logs de seguridad (`auth.log`);
- logs de aplicación web (`nginx` o `apache`);
- logs de Kubernetes.

Todos los eventos deben quedar visibles en Kibana y, en la medida de lo posible, alineados con `ECS` (Elastic Common Schema).

## Requerimientos funcionales y técnicos

| ID | Requerimiento | Tecnologías principales | Criterio de aceptación |
| --- | --- | --- | --- |
| `R8.1` | Desplegar `Elasticsearch` con 3 nodos, `Logstash` y `Kibana` con `Docker Compose`; configurar índices con `ILM` y retención de 30 días. | `Elasticsearch`, `Docker Compose` | Clúster en estado `green`; `ILM` aplicado y verificado; evidencia de paso a `warm` y/o `cold` en prueba acelerada. |
| `R8.2` | Configurar ingesta de logs desde mínimo 3 fuentes: sistema (`syslog`), aplicación web (`nginx` o `apache`), Kubernetes y/o seguridad (`auth.log`). | `Filebeat`, `Logstash` | Logs visibles en Kibana; campos `ECS` correctamente mapeados. |
| `R8.3` | Implementar pipeline de `Logstash` con filtros `grok`, `mutate` y `geoip`; rechazar logs malformados a un índice de errores separado. | `Logstash`, `Grok`, `GeoIP` | Tasa de parseo exitoso mayor al 95%; logs rechazados almacenados con el motivo documentado. |
| `R8.4` | Implementar mínimo 5 reglas de detección: brute force SSH, escaneo de puertos, múltiples errores `404`, login fuera de horario y acceso a rutas sensibles. | `Kibana SIEM` | Cada regla debe dispararse correctamente con logs de prueba generados para ese escenario. |
| `R8.5` | Simular mínimo 3 escenarios de ataque: brute force, escaneo con `nmap` e inyección SQL reflejada en logs. | `nmap`, `hydra`, `Python` | Los 3 escenarios deben ser detectados y generar alertas en menos de 60 segundos; incluir evidencias. |
| `R8.6` | Construir dashboard ejecutivo con top amenazas del día, mapa geográfico de IPs sospechosas, tendencia de alertas por semana y salud general del sistema. | `Kibana Dashboards` | Dashboard con actualización automática y comprensible para audiencia no técnica. |
| `R8.7` | Construir dashboard operacional con logs en tiempo real, alertas activas, top usuarios/IPs y drill-down a eventos específicos. | `Kibana Discover`, `Kibana Dashboards` | Investigación de incidente simulado completada en menos de 5 minutos usando el dashboard. |
| `R8.8` | Documentar playbooks de respuesta para mínimo 2 incidentes detectados, incluyendo investigación, contención, erradicación y lecciones aprendidas. | `Markdown`, `GitHub Wiki` | Un integrante no involucrado en su creación debe poder seguir el playbook y responder al incidente simulado. |

## Entregables

- Stack ELK desplegado con mínimo 3 fuentes de logs diferentes.
- Mínimo 5 reglas de detección de amenazas configuradas y probadas.
- Dashboard SIEM con vista ejecutiva y operacional.
- Playbook de respuesta para mínimo 2 tipos de incidente en [`docs/playbooks/`](docs/playbooks/README.md).

## Escenarios de ataque a demostrar

Los escenarios sugeridos para la validación del sistema son:

1. `Brute force SSH`
2. `Escaneo de puertos con nmap`
3. `Inyección SQL registrada en logs web`

Para cada escenario se recomienda documentar:

- fuente del log afectado;
- patrón esperado en los eventos;
- regla o alerta asociada;
- evidencia en Kibana;
- tiempo de detección;
- acción de respuesta definida en el playbook.

## Integración opcional con Microsoft Sentinel

El repositorio incluye una ruta cloud para detección continua con Microsoft Sentinel. La integración mantiene Elastic como SIEM local y agrega un forwarder que envía eventos normalizados de `logs-*` a una tabla `CloudSIEM_CL` en Log Analytics mediante Azure Monitor Logs Ingestion API.

Los recursos Azure, reglas KQL y comandos CLI están documentados en [`azure/sentinel/README.md`](azure/sentinel/README.md). Esta ruta agrega reglas programadas de Sentinel para anomalías de autenticación SSH, patrones web sospechosos, escaneo de puertos, login fuera de horario y rutas sensibles.

## Estructura esperada del repositorio

A medida que avance la implementación, este repositorio debería incorporar una estructura similar a la siguiente:

```text
.
├── .editorconfig
├── .gitattributes
├── README.md
├── .github/
│   ├── AGENTS.md
│   └── copilot-instructions.md
├── docker-compose.yml
├── docker-compose-podman.yml
├── docker-compose-sentinel.yml
├── docker-compose-sentinel-podman.yml
├── filebeat/
├── logstash/
├── kibana/
├── setup/
├── rules/
├── docs/
└── logs/
```

## Flujo de ramas

Este repositorio usa `develop` como rama principal de integración del equipo.

### Rama `develop`

- Todo el trabajo del equipo debe integrarse primero en `develop`.
- Los miembros del equipo deben hacer push a `develop` antes de pruebas integradas, validaciones funcionales y despliegues.
- `develop` es la rama donde se consolidan cambios de documentación, configuración, pipelines, dashboards, reglas y scripts de simulación.

### Rama `main`

- `main` debe mantenerse estable y lista para entregas o demostraciones.
- No deben hacerse commits directos a `main`.
- Todo cambio hacia `main` debe entrar mediante un `Pull Request` preaprobado.
- Un `Pull Request` a `main` solo debe abrirse cuando los cambios ya hayan sido revisados y validados previamente en `develop`.

### Flujo recomendado

1. Crear una rama de trabajo desde `develop`.
2. Implementar y validar cambios en la rama de trabajo.
3. Abrir `Pull Request` hacia `develop` o integrar el cambio según la dinámica acordada por el equipo.
4. Probar en `develop` antes de cualquier despliegue o demostración.
5. Abrir `Pull Request` preaprobado hacia `main` solo cuando el cambio esté listo para publicación o entrega.

## Antes de abrir PR a `main`

Verificar que:

- el cambio ya fue integrado en `develop`;
- las pruebas o validaciones necesarias ya se ejecutaron;
- la documentación relevante fue actualizada;
- el `Pull Request` a `main` tiene aprobación previa.

## Criterios de éxito

Se considerará que el proyecto cumple su objetivo si logra:

- centralizar eventos de seguridad en una sola plataforma;
- detectar ataques simulados con latencia baja;
- ofrecer visibilidad técnica y ejecutiva;
- facilitar investigación y respuesta mediante dashboards y playbooks.

## Estado del repositorio

Estado actual: `implementación en curso`.

Este README define el alcance, objetivos y entregables esperados del proyecto, junto con la guía operativa para trabajar en `develop`.

## Nota

La documentación del proyecto no debe usar emojis.
