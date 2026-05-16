# Microsoft Sentinel para CloudSIEM

Esta integración agrega una capa cloud de detección con Microsoft Sentinel. El stack local sigue usando Elastic para ingesta, parsing y dashboards; un forwarder continuo consulta `logs-*` en Elasticsearch y envía eventos normalizados a una tabla custom de Log Analytics llamada `CloudSIEM_CL`.

## Región sugerida

Usar `eastus`. Tiene buena disponibilidad para Log Analytics, Data Collection Rules, Data Collection Endpoints y Microsoft Sentinel en cuentas de estudiante. Si hay restricción de cuota, usar `eastus2`.

## Comandos Azure CLI

Instalar o actualizar Azure CLI y Bicep si hace falta:

```bash
az version
az bicep upgrade
```

Iniciar sesión y seleccionar la suscripción Student:

```bash
az login
az account list --output table
az account set --subscription "<student-subscription-id>"
```

Registrar providers requeridos:

```bash
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.OperationsManagement
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.SecurityInsights
az provider register --namespace Microsoft.Authorization
```

Crear el resource group:

```bash
az group create \
  --name rg-cloudsiem-sentinel \
  --location eastus
```

Crear una app registration y service principal para el forwarder:

```bash
FORWARDER_APP_NAME=sp-cloudsiem-sentinel-forwarder

AZURE_CLIENT_ID=$(az ad app create \
  --display-name "$FORWARDER_APP_NAME" \
  --query appId \
  --output tsv)

AZURE_CLIENT_SECRET=$(az ad app credential reset \
  --id "$AZURE_CLIENT_ID" \
  --display-name cloudsiem-forwarder \
  --years 1 \
  --query password \
  --output tsv)

AZURE_TENANT_ID=$(az account show --query tenantId --output tsv)

AZURE_OBJECT_ID=$(az ad sp create \
  --id "$AZURE_CLIENT_ID" \
  --query id \
  --output tsv)
```

Desplegar Sentinel, la tabla custom, DCR/DCE y las reglas:

```bash
az deployment group create \
  --name cloudsiem-sentinel \
  --resource-group rg-cloudsiem-sentinel \
  --template-file azure/bicep/main.bicep \
  --parameters azure/bicep/parameters.example.json \
  --parameters forwarderPrincipalObjectId="$AZURE_OBJECT_ID"
```

Obtener las salidas necesarias para el forwarder:

```bash
SENTINEL_DCE_ENDPOINT=$(az deployment group show \
  --name cloudsiem-sentinel \
  --resource-group rg-cloudsiem-sentinel \
  --query properties.outputs.dataCollectionEndpoint.value \
  --output tsv)

SENTINEL_DCR_IMMUTABLE_ID=$(az deployment group show \
  --name cloudsiem-sentinel \
  --resource-group rg-cloudsiem-sentinel \
  --query properties.outputs.dataCollectionRuleImmutableId.value \
  --output tsv)
```

Crear `.env.sentinel` local:

```bash
cat > .env.sentinel <<EOF
AZURE_TENANT_ID=$AZURE_TENANT_ID
AZURE_CLIENT_ID=$AZURE_CLIENT_ID
AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET
SENTINEL_DCE_ENDPOINT=$SENTINEL_DCE_ENDPOINT
SENTINEL_DCR_IMMUTABLE_ID=$SENTINEL_DCR_IMMUTABLE_ID
SENTINEL_STREAM_NAME=Custom-CloudSIEM
SENTINEL_POLL_SECONDS=10
SENTINEL_BATCH_SIZE=500
SENTINEL_LOOKBACK_MINUTES=15
EOF
```

## Ejecutar streaming continuo con Podman

Instalar `podman-compose` en un entorno local del proyecto si no existe en el sistema:

```bash
python3 -m venv .venv-tools/podman-compose
.venv-tools/podman-compose/bin/pip install podman-compose
```

Arrancar el stack con el launcher por etapas:

```bash
bash setup/run-podman-sentinel-stack.sh --build --force-recreate
```

El script carga `.env` y `.env.sentinel`, ejecuta los jobs one-shot con `--no-deps`, añade el override Podman de Sentinel para el relabeling SELinux y arranca `sentinel-forwarder` al final. Esto evita el error de Podman Compose `container state improper` cuando una dependencia terminó correctamente pero ya no está corriendo.

Para usar Docker Compose sin el override de Podman:

```bash
docker compose \
  --env-file .env \
  --env-file .env.sentinel \
  -f docker-compose.yml \
  -f docker-compose-sentinel.yml \
  up --build
```

## Validar ingesta y reglas

```bash
python3 setup/verify-sentinel.py \
  --resource-group rg-cloudsiem-sentinel \
  --workspace law-cloudsiem
```

Consulta rápida por CLI:

```bash
WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group rg-cloudsiem-sentinel \
  --workspace-name law-cloudsiem \
  --query customerId \
  --output tsv)

az monitor log-analytics query \
  --workspace "$WORKSPACE_ID" \
  --analytics-query "CloudSIEM_CL | summarize Count=count() by EventDataset | order by Count desc" \
  --output table
```

## Generar eventos de prueba

```bash
python3 setup/orchestrate-logs.py --mode attacks
```

Esperar unos minutos. Las reglas scheduled corren cada 5 minutos y crean alertas/incidentes si la consulta devuelve resultados.

## Control de costos

- El forwarder envía solo índices `logs-*`.
- La tabla tiene retención de 30 días.
- El batch por defecto es de 500 eventos cada 10 segundos.
- Para pausar el costo de ingesta, detener `sentinel-forwarder`.

Eliminar todos los recursos Azure del laboratorio:

```bash
az group delete \
  --name rg-cloudsiem-sentinel \
  --yes
```
