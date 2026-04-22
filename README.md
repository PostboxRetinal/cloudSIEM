# CloudSIEM
## Plataforma SIEM simplificada para centralizar, normalizar, correlacionar y visualizar eventos de seguridad usando Elastic Stack.

Este repositorio corresponde al **Proyecto 8: Plataforma de análisis de logs y seguridad con Elastic Stack e inteligencia de amenazas** de la asignatura **Computación en la Nube**.

## Descripción

El objetivo del proyecto es construir una plataforma de monitoreo y análisis de seguridad capaz de:

- centralizar logs de múltiples fuentes heterogéneas;
- transformar los eventos a un esquema común;
- detectar comportamientos sospechosos mediante reglas y analítica;
- visualizar el estado de seguridad en dashboards ejecutivos y operacionales;
- demostrar la detección de ataques simulados en un entorno controlado.

La solución está pensada como una implementación académica de un flujo SIEM end-to-end con componentes reales del ecosistema Elastic.

## Objetivos

- Centralizar y normalizar logs de múltiples fuentes.
- Implementar detección de anomalías y correlación de eventos.
- Construir dashboards de seguridad ejecutivos y operacionales.
- Simular escenarios de ataque y validar su detección.
- Documentar procedimientos de respuesta a incidentes.

## Alcance del proyecto

La plataforma debe incluir, como mínimo:

- `Elasticsearch` para almacenamiento, indexación e ILM.
- `Logstash` para parsing, transformación y enriquecimiento.
- `Kibana` para observabilidad, seguridad y dashboards.
- `Filebeat` y/o `Metricbeat` para recolección de logs y métricas.
- `Docker Compose` o `Kubernetes` para despliegue.
- Scripts en `Python` para generar tráfico y eventos de prueba.
- `Wazuh` como componente opcional para detección adicional.

## Arquitectura propuesta

```text
Fuentes de logs
  |- Syslog
  |- auth.log
  |- Nginx/Apache
  |- Kubernetes
  `- Logs simulados por scripts

Beats / Recolección
  `- Filebeat / Metricbeat

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
  `- machine learning / alertas
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
| `R8.1` | Desplegar `Elasticsearch` con 3 nodos, `Logstash` y `Kibana` con `Docker Compose`; configurar índices con `ILM` y retención de 30 días. | `Elasticsearch`, `Docker Compose` | Cluster en estado `green`; ILM aplicado y verificado; evidencia de paso a `warm` y/o `cold` en prueba acelerada. |
| `R8.2` | Configurar ingesta de logs desde mínimo 3 fuentes: sistema (`syslog`), aplicación web (`nginx` o `apache`), Kubernetes y/o seguridad (`auth.log`). | `Filebeat`, `Metricbeat`, `Logstash` | Logs visibles en Kibana; campos `ECS` correctamente mapeados. |
| `R8.3` | Implementar pipeline de `Logstash` con filtros `grok`, `mutate` y `geoip`; rechazar logs malformados a un índice de errores separado. | `Logstash`, `Grok`, `GeoIP` | Tasa de parseo exitoso mayor al 95%; logs rechazados almacenados con el motivo documentado. |
| `R8.4` | Implementar mínimo 5 reglas de detección: brute force SSH, escaneo de puertos, múltiples errores `404`, login fuera de horario y acceso a rutas sensibles. | `Kibana SIEM`, `Wazuh` opcional | Cada regla debe dispararse correctamente con logs de prueba generados para ese escenario. |
| `R8.5` | Simular mínimo 3 escenarios de ataque: brute force, escaneo con `nmap` e inyección SQL reflejada en logs. | `nmap`, `hydra`, `Python` | Los 3 escenarios deben ser detectados y generar alertas en menos de 60 segundos; incluir evidencias. |
| `R8.6` | Construir dashboard ejecutivo con top amenazas del día, mapa geográfico de IPs sospechosas, tendencia de alertas por semana y salud general del sistema. | `Kibana Dashboards` | Dashboard con actualización automática y comprensible para audiencia no técnica. |
| `R8.7` | Construir dashboard operacional con logs en tiempo real, alertas activas, top usuarios/IPs y drill-down a eventos específicos. | `Kibana Discover`, `Kibana Dashboards` | Investigación de incidente simulado completada en menos de 5 minutos usando el dashboard. |
| `R8.8` | Documentar playbooks de respuesta para mínimo 2 incidentes detectados, incluyendo investigación, contención, erradicación y lecciones aprendidas. | `Markdown`, `GitHub Wiki` | Un integrante no involucrado en su creación debe poder seguir el playbook y responder al incidente simulado. |

## Entregables

- Stack ELK desplegado con mínimo 3 fuentes de logs diferentes.
- Mínimo 5 reglas de detección de amenazas configuradas y probadas.
- Dashboard SIEM con vista ejecutiva y operacional.
- Playbook de respuesta para mínimo 2 tipos de incidente.

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

## Estructura esperada del repositorio

A medida que avance la implementación, este repositorio debería incorporar una estructura similar a la siguiente:

```text
.
├── README.md
├── docker-compose.yml
├── elasticsearch/
├── logstash/
│   ├── pipeline/
│   └── config/
├── kibana/
│   ├── dashboards/
│   └── alerts/
├── beats/
│   ├── filebeat/
│   └── metricbeat/
├── generators/
│   └── python/
├── playbooks/
└── docs/
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

## Criterios de éxito

Se considerará que el proyecto cumple su objetivo si logra:

- centralizar eventos de seguridad en una sola plataforma;
- detectar ataques simulados con latencia baja;
- ofrecer visibilidad técnica y ejecutiva;
- facilitar investigación y respuesta mediante dashboards y playbooks.

## Estado del repositorio

Estado actual: `fase inicial de documentación`.

Este README define el alcance, objetivos y entregables esperados del proyecto. La implementación técnica del stack, pipelines, dashboards y playbooks debe incorporarse progresivamente en este repositorio.
