# CloudSIEM

Guia interna del equipo para trabajar en la rama `develop`.

## Proyecto

CloudSIEM es una plataforma SIEM academica basada en Elastic Stack para:

- centralizar logs de multiples fuentes;
- detectar amenazas y patrones sospechosos;
- visualizar el estado de seguridad en dashboards;
- documentar respuesta a incidentes.

Stack objetivo del proyecto:

- `Elasticsearch`
- `Logstash`
- `Kibana`
- `Filebeat` y/o `Metricbeat`
- `Docker Compose`
- `Python` para generadores de logs
- `Wazuh` opcional

## Objetivo de esta rama

La rama `develop` es la rama principal de trabajo del equipo.

Todo cambio debe pasar primero por `develop` antes de:

- pruebas integradas;
- validaciones del proyecto;
- despliegues;
- paso a `main`.

## Reglas de ramas

### `develop`

- Es la rama de integracion del equipo.
- Aqui se consolidan cambios de configuracion, pipelines, dashboards, reglas, scripts y documentacion.
- El equipo debe hacer push a `develop` antes de probar o desplegar.

### `main`

- Debe mantenerse estable.
- No se hacen commits directos a `main`.
- Todo cambio a `main` debe entrar por `Pull Request` preaprobado.
- Solo se envia a `main` lo que ya fue revisado y validado en `develop`.

## Flujo de trabajo

1. Crear una rama desde `develop`.
2. Implementar el cambio.
3. Probar el cambio localmente.
4. Integrar el cambio en `develop`.
5. Validar en equipo dentro de `develop`.
6. Abrir `Pull Request` preaprobado hacia `main` solo cuando el cambio este listo.

## Alcance minimo del proyecto

El proyecto debe cubrir como minimo:

- 3 fuentes de logs diferentes;
- pipeline de `Logstash` con `grok`, `mutate` y `geoip`;
- indice separado para logs malformados;
- 5 reglas de deteccion;
- 3 escenarios de ataque simulados;
- dashboard ejecutivo;
- dashboard operacional;
- 2 playbooks de respuesta a incidentes.

## Reglas de deteccion requeridas

- brute force SSH
- escaneo de puertos
- multiples errores `404`
- login fuera de horario
- acceso a rutas sensibles

## Escenarios de prueba requeridos

- brute force
- escaneo con `nmap`
- inyeccion SQL en logs

## Antes de abrir PR a `main`

Verificar que:

- el cambio ya fue integrado en `develop`;
- el equipo reviso el cambio;
- las pruebas o validaciones necesarias ya se ejecutaron;
- la documentacion relevante fue actualizada;
- el `Pull Request` a `main` tiene aprobacion previa.

## Nota

Este README esta pensado como guia operativa interna del equipo en `develop`.
La rama `main` debe conservar una version mas orientada a presentacion o entrega final.
