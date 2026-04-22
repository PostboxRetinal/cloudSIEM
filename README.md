# CloudSIEM

Plataforma SIEM simplificada para centralizar, normalizar, correlacionar y visualizar eventos de seguridad usando Elastic Stack.

Este repositorio corresponde al **Proyecto 8: Plataforma de analisis de logs y seguridad con Elastic Stack e inteligencia de amenazas** de la asignatura **Computacion en la Nube**.

## Descripcion

El objetivo del proyecto es construir una plataforma de monitoreo y analisis de seguridad capaz de:

- centralizar logs de multiples fuentes heterogeneas;
- transformar los eventos a un esquema comun;
- detectar comportamientos sospechosos mediante reglas y analitica;
- visualizar el estado de seguridad en dashboards ejecutivos y operacionales;
- demostrar la deteccion de ataques simulados en un entorno controlado.

La solucion esta pensada como una implementacion academica de un flujo SIEM end-to-end con componentes reales del ecosistema Elastic.

## Objetivos

- Centralizar y normalizar logs de multiples fuentes.
- Implementar deteccion de anomalias y correlacion de eventos.
- Construir dashboards de seguridad ejecutivos y operacionales.
- Simular escenarios de ataque y validar su deteccion.
- Documentar procedimientos de respuesta a incidentes.

## Alcance del proyecto

La plataforma debe incluir, como minimo:

- `Elasticsearch` para almacenamiento, indexacion e ILM.
- `Logstash` para parsing, transformacion y enriquecimiento.
- `Kibana` para observabilidad, seguridad y dashboards.
- `Filebeat` y/o `Metricbeat` para recoleccion de logs y metricas.
- `Docker Compose` o `Kubernetes` para despliegue.
- Scripts en `Python` para generar trafico y eventos de prueba.
- `Wazuh` como componente opcional para deteccion adicional.

## Arquitectura propuesta

```text
Fuentes de logs
  |- Syslog
  |- auth.log
  |- Nginx/Apache
  |- Kubernetes
  `- Logs simulados por scripts

Beats / Recoleccion
  `- Filebeat / Metricbeat

Pipeline de ingesta
  `- Logstash
      |- grok
      |- mutate
      |- geoip
      `- routing de errores

Almacenamiento y gestion
  `- Elasticsearch
      |- indices ECS
      |- ILM
      `- retencion de 30 dias

Analitica y visualizacion
  `- Kibana SIEM / Dashboards / Discover

Deteccion
  |- reglas de correlacion
  `- machine learning / alertas
```

## Fuentes de logs esperadas

El proyecto debe integrar al menos 3 fuentes de logs diferentes. Las fuentes objetivo definidas para la sustentacion son:

- logs de sistema (`syslog`);
- logs de seguridad (`auth.log`);
- logs de aplicacion web (`nginx` o `apache`);
- logs de Kubernetes.

Todos los eventos deben quedar visibles en Kibana y, en la medida de lo posible, alineados con `ECS` (Elastic Common Schema).

## Requerimientos funcionales y tecnicos

| ID | Requerimiento | Tecnologias principales | Criterio de aceptacion |
| --- | --- | --- | --- |
| `R8.1` | Desplegar `Elasticsearch` con 3 nodos, `Logstash` y `Kibana` con `Docker Compose`; configurar indices con `ILM` y retencion de 30 dias. | `Elasticsearch`, `Docker Compose` | Cluster en estado `green`; ILM aplicado y verificado; evidencia de paso a `warm` y/o `cold` en prueba acelerada. |
| `R8.2` | Configurar ingesta de logs desde minimo 3 fuentes: sistema (`syslog`), aplicacion web (`nginx` o `apache`), Kubernetes y/o seguridad (`auth.log`). | `Filebeat`, `Metricbeat`, `Logstash` | Logs visibles en Kibana; campos `ECS` correctamente mapeados. |
| `R8.3` | Implementar pipeline de `Logstash` con filtros `grok`, `mutate` y `geoip`; rechazar logs malformados a un indice de errores separado. | `Logstash`, `Grok`, `GeoIP` | Tasa de parseo exitoso mayor al 95%; logs rechazados almacenados con el motivo documentado. |
| `R8.4` | Implementar minimo 5 reglas de deteccion: brute force SSH, escaneo de puertos, multiples errores `404`, login fuera de horario y acceso a rutas sensibles. | `Kibana SIEM`, `Wazuh` opcional | Cada regla debe dispararse correctamente con logs de prueba generados para ese escenario. |
| `R8.5` | Simular minimo 3 escenarios de ataque: brute force, escaneo con `nmap` e inyeccion SQL reflejada en logs. | `nmap`, `hydra`, `Python` | Los 3 escenarios deben ser detectados y generar alertas en menos de 60 segundos; incluir evidencias. |
| `R8.6` | Construir dashboard ejecutivo con top amenazas del dia, mapa geografico de IPs sospechosas, tendencia de alertas por semana y salud general del sistema. | `Kibana Dashboards` | Dashboard con actualizacion automatica y comprensible para audiencia no tecnica. |
| `R8.7` | Construir dashboard operacional con logs en tiempo real, alertas activas, top usuarios/IPs y drill-down a eventos especificos. | `Kibana Discover`, `Kibana Dashboards` | Investigacion de incidente simulado completada en menos de 5 minutos usando el dashboard. |
| `R8.8` | Documentar playbooks de respuesta para minimo 2 incidentes detectados, incluyendo investigacion, contencion, erradicacion y lecciones aprendidas. | `Markdown`, `GitHub Wiki` | Un integrante no involucrado en su creacion debe poder seguir el playbook y responder al incidente simulado. |

## Entregables

- Stack ELK desplegado con minimo 3 fuentes de logs diferentes.
- Minimo 5 reglas de deteccion de amenazas configuradas y probadas.
- Dashboard SIEM con vista ejecutiva y operacional.
- Playbook de respuesta para minimo 2 tipos de incidente.

## Escenarios de ataque a demostrar

Los escenarios sugeridos para la validacion del sistema son:

1. `Brute force SSH`
2. `Escaneo de puertos con nmap`
3. `Inyeccion SQL registrada en logs web`

Para cada escenario se recomienda documentar:

- fuente del log afectado;
- patron esperado en los eventos;
- regla o alerta asociada;
- evidencia en Kibana;
- tiempo de deteccion;
- accion de respuesta definida en el playbook.

## Estructura esperada del repositorio

A medida que avance la implementacion, este repositorio deberia incorporar una estructura similar a la siguiente:

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

## Criterios de exito

Se considerara que el proyecto cumple su objetivo si logra:

- centralizar eventos de seguridad en una sola plataforma;
- detectar ataques simulados con latencia baja;
- ofrecer visibilidad tecnica y ejecutiva;
- facilitar investigacion y respuesta mediante dashboards y playbooks.

## Estado del repositorio

Estado actual: `fase inicial de documentacion`.

Este README define el alcance, objetivos y entregables esperados del proyecto. La implementacion tecnica del stack, pipelines, dashboards y playbooks debe incorporarse progresivamente en este repositorio.
