targetScope = 'resourceGroup'

@description('Azure region for all Microsoft Sentinel resources.')
param location string = resourceGroup().location

@description('Log Analytics workspace name.')
param workspaceName string = 'law-cloudsiem'

@description('Data Collection Endpoint name used by the forwarder.')
param dataCollectionEndpointName string = 'dce-cloudsiem'

@description('Data Collection Rule name used by the forwarder.')
param dataCollectionRuleName string = 'dcr-cloudsiem'

@description('Object ID of the forwarder service principal. Leave empty to skip role assignment.')
param forwarderPrincipalObjectId string = ''

@minValue(4)
@maxValue(730)
@description('Interactive retention for the custom CloudSIEM table.')
param retentionInDays int = 30

@description('Deploy CloudSIEM scheduled analytics rules in Microsoft Sentinel.')
param deployAnalyticsRules bool = true

var customTableName = 'CloudSIEM_CL'
var streamName = 'Custom-CloudSIEM'
var workspaceDestinationName = 'cloudsiem-workspace'
var monitoringMetricsPublisherRoleId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '3913510d-42f4-4e42-8a64-420c390055eb')

var cloudSiemColumns = [
  {
    name: 'TimeGenerated'
    type: 'datetime'
  }
  {
    name: 'EventId'
    type: 'string'
  }
  {
    name: 'ElasticIndex'
    type: 'string'
  }
  {
    name: 'EventDataset'
    type: 'string'
  }
  {
    name: 'EventCategory'
    type: 'string'
  }
  {
    name: 'EventType'
    type: 'string'
  }
  {
    name: 'EventAction'
    type: 'string'
  }
  {
    name: 'EventOutcome'
    type: 'string'
  }
  {
    name: 'EventSeverity'
    type: 'long'
  }
  {
    name: 'SiemSeverity'
    type: 'string'
  }
  {
    name: 'SourceIp'
    type: 'string'
  }
  {
    name: 'SourcePort'
    type: 'long'
  }
  {
    name: 'DestinationIp'
    type: 'string'
  }
  {
    name: 'DestinationPort'
    type: 'long'
  }
  {
    name: 'NetworkTransport'
    type: 'string'
  }
  {
    name: 'UserName'
    type: 'string'
  }
  {
    name: 'HostName'
    type: 'string'
  }
  {
    name: 'ProcessName'
    type: 'string'
  }
  {
    name: 'HttpMethod'
    type: 'string'
  }
  {
    name: 'HttpStatusCode'
    type: 'long'
  }
  {
    name: 'HttpResponseBytes'
    type: 'long'
  }
  {
    name: 'UrlPath'
    type: 'string'
  }
  {
    name: 'UrlOriginal'
    type: 'string'
  }
  {
    name: 'UserAgent'
    type: 'string'
  }
  {
    name: 'Tags'
    type: 'dynamic'
  }
  {
    name: 'BruteForceAttempt'
    type: 'boolean'
  }
  {
    name: 'AfterHoursLogin'
    type: 'boolean'
  }
  {
    name: 'SensitivePath'
    type: 'boolean'
  }
  {
    name: 'SqliDetected'
    type: 'boolean'
  }
  {
    name: 'XssDetected'
    type: 'boolean'
  }
  {
    name: 'PathTraversal'
    type: 'boolean'
  }
  {
    name: 'ScannerDetected'
    type: 'boolean'
  }
  {
    name: 'Message'
    type: 'string'
  }
]

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: retentionInDays
    features: {
      searchVersion: 1
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource cloudSiemTable 'Microsoft.OperationalInsights/workspaces/tables@2022-10-01' = {
  parent: workspace
  name: customTableName
  properties: {
    retentionInDays: retentionInDays
    totalRetentionInDays: retentionInDays
    schema: {
      name: customTableName
      columns: cloudSiemColumns
    }
  }
}

resource sentinelOnboarding 'Microsoft.SecurityInsights/onboardingStates@2023-02-01-preview' = {
  scope: workspace
  name: 'default'
  properties: {}
}

resource dataCollectionEndpoint 'Microsoft.Insights/dataCollectionEndpoints@2022-06-01' = {
  name: dataCollectionEndpointName
  location: location
  properties: {
    networkAcls: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource dataCollectionRule 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: dataCollectionRuleName
  location: location
  kind: 'Direct'
  properties: {
    dataCollectionEndpointId: dataCollectionEndpoint.id
    streamDeclarations: {
      'Custom-CloudSIEM': {
        columns: cloudSiemColumns
      }
    }
    destinations: {
      logAnalytics: [
        {
          name: workspaceDestinationName
          workspaceResourceId: workspace.id
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          streamName
        ]
        destinations: [
          workspaceDestinationName
        ]
        transformKql: 'source'
        outputStream: 'Custom-${customTableName}'
      }
    ]
  }
  dependsOn: [
    cloudSiemTable
  ]
}

resource dcrPublisherRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (forwarderPrincipalObjectId != '') {
  name: guid(dataCollectionRule.id, forwarderPrincipalObjectId, 'cloudsiem-monitoring-metrics-publisher')
  scope: dataCollectionRule
  properties: {
    roleDefinitionId: monitoringMetricsPublisherRoleId
    principalId: forwarderPrincipalObjectId
    principalType: 'ServicePrincipal'
  }
}

resource authAnomalyRule 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = if (deployAnalyticsRules) {
  scope: workspace
  name: guid(workspace.id, 'cloudsiem-auth-failed-login-anomaly')
  kind: 'Scheduled'
  properties: {
    displayName: 'CloudSIEM - ML SSH Failed Login Spike'
    description: 'Detecta picos anomalos de fallos de autenticacion SSH por IP origen usando series_decompose_anomalies en Microsoft Sentinel.'
    severity: 'High'
    enabled: true
    query: loadTextContent('../sentinel/queries/auth-failed-login-anomaly.kql')
    queryFrequency: 'PT5M'
    queryPeriod: 'PT24H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT1H'
    suppressionEnabled: false
    tactics: [
      'CredentialAccess'
    ]
    entityMappings: [
      {
        entityType: 'IP'
        fieldMappings: [
          {
            identifier: 'Address'
            columnName: 'SourceIp'
          }
        ]
      }
    ]
    customDetails: {
      FailedLogins: 'FailedLogins'
      AnomalyScore: 'AnomalyScore'
      Baseline: 'Baseline'
    }
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: true
        reopenClosedIncident: false
        lookbackDuration: 'PT1H'
        matchingMethod: 'Selected'
        groupByEntities: [
          'IP'
        ]
        groupByAlertDetails: []
        groupByCustomDetails: []
      }
    }
    eventGroupingSettings: {
      aggregationKind: 'SingleAlert'
    }
  }
  dependsOn: [
    sentinelOnboarding
  ]
}

resource webAnomalyRule 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = if (deployAnalyticsRules) {
  scope: workspace
  name: guid(workspace.id, 'cloudsiem-web-suspicious-pattern-anomaly')
  kind: 'Scheduled'
  properties: {
    displayName: 'CloudSIEM - ML Web Suspicious Pattern Spike'
    description: 'Detecta picos anomalos de patrones web sospechosos: 404 masivos, scanners, SQLi, XSS, path traversal y rutas sensibles.'
    severity: 'Medium'
    enabled: true
    query: loadTextContent('../sentinel/queries/web-suspicious-pattern-anomaly.kql')
    queryFrequency: 'PT5M'
    queryPeriod: 'PT24H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT1H'
    suppressionEnabled: false
    tactics: [
      'Reconnaissance'
      'InitialAccess'
    ]
    entityMappings: [
      {
        entityType: 'IP'
        fieldMappings: [
          {
            identifier: 'Address'
            columnName: 'SourceIp'
          }
        ]
      }
    ]
    customDetails: {
      SuspiciousRequests: 'SuspiciousRequests'
      AnomalyScore: 'AnomalyScore'
      Baseline: 'Baseline'
    }
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: true
        reopenClosedIncident: false
        lookbackDuration: 'PT1H'
        matchingMethod: 'Selected'
        groupByEntities: [
          'IP'
        ]
        groupByAlertDetails: []
        groupByCustomDetails: []
      }
    }
    eventGroupingSettings: {
      aggregationKind: 'SingleAlert'
    }
  }
  dependsOn: [
    sentinelOnboarding
  ]
}

resource portscanAnomalyRule 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = if (deployAnalyticsRules) {
  scope: workspace
  name: guid(workspace.id, 'cloudsiem-portscan-anomaly')
  kind: 'Scheduled'
  properties: {
    displayName: 'CloudSIEM - ML Port Scan Spike'
    description: 'Detecta picos anomalos de puertos destino distintos bloqueados por IP origen.'
    severity: 'High'
    enabled: true
    query: loadTextContent('../sentinel/queries/portscan-anomaly.kql')
    queryFrequency: 'PT5M'
    queryPeriod: 'PT24H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT1H'
    suppressionEnabled: false
    tactics: [
      'Discovery'
      'Reconnaissance'
    ]
    entityMappings: [
      {
        entityType: 'IP'
        fieldMappings: [
          {
            identifier: 'Address'
            columnName: 'SourceIp'
          }
        ]
      }
    ]
    customDetails: {
      DistinctPorts: 'DistinctPorts'
      AnomalyScore: 'AnomalyScore'
      Baseline: 'Baseline'
    }
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: true
        reopenClosedIncident: false
        lookbackDuration: 'PT1H'
        matchingMethod: 'Selected'
        groupByEntities: [
          'IP'
        ]
        groupByAlertDetails: []
        groupByCustomDetails: []
      }
    }
    eventGroupingSettings: {
      aggregationKind: 'SingleAlert'
    }
  }
  dependsOn: [
    sentinelOnboarding
  ]
}

resource afterHoursRule 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = if (deployAnalyticsRules) {
  scope: workspace
  name: guid(workspace.id, 'cloudsiem-after-hours-login')
  kind: 'Scheduled'
  properties: {
    displayName: 'CloudSIEM - Login SSH Fuera de Horario'
    description: 'Detecta logins exitosos fuera del horario laboral America/Bogota o eventos marcados por Logstash como after_hours_login.'
    severity: 'Medium'
    enabled: true
    query: loadTextContent('../sentinel/queries/after-hours-login.kql')
    queryFrequency: 'PT5M'
    queryPeriod: 'PT2H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT1H'
    suppressionEnabled: false
    tactics: [
      'InitialAccess'
      'Persistence'
    ]
    entityMappings: [
      {
        entityType: 'IP'
        fieldMappings: [
          {
            identifier: 'Address'
            columnName: 'SourceIp'
          }
        ]
      }
      {
        entityType: 'Account'
        fieldMappings: [
          {
            identifier: 'Name'
            columnName: 'UserName'
          }
        ]
      }
    ]
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: true
        reopenClosedIncident: false
        lookbackDuration: 'PT2H'
        matchingMethod: 'AllEntities'
        groupByEntities: []
        groupByAlertDetails: []
        groupByCustomDetails: []
      }
    }
    eventGroupingSettings: {
      aggregationKind: 'SingleAlert'
    }
  }
  dependsOn: [
    sentinelOnboarding
  ]
}

resource sensitivePathRule 'Microsoft.SecurityInsights/alertRules@2023-02-01-preview' = if (deployAnalyticsRules) {
  scope: workspace
  name: guid(workspace.id, 'cloudsiem-sensitive-path-access')
  kind: 'Scheduled'
  properties: {
    displayName: 'CloudSIEM - Acceso a Rutas Web Sensibles'
    description: 'Detecta acceso a rutas web sensibles como admin, phpMyAdmin, .env, .git y endpoints internos.'
    severity: 'High'
    enabled: true
    query: loadTextContent('../sentinel/queries/sensitive-path-access.kql')
    queryFrequency: 'PT5M'
    queryPeriod: 'PT2H'
    triggerOperator: 'GreaterThan'
    triggerThreshold: 0
    suppressionDuration: 'PT1H'
    suppressionEnabled: false
    tactics: [
      'InitialAccess'
      'CredentialAccess'
    ]
    entityMappings: [
      {
        entityType: 'IP'
        fieldMappings: [
          {
            identifier: 'Address'
            columnName: 'SourceIp'
          }
        ]
      }
      {
        entityType: 'URL'
        fieldMappings: [
          {
            identifier: 'Url'
            columnName: 'UrlPath'
          }
        ]
      }
    ]
    incidentConfiguration: {
      createIncident: true
      groupingConfiguration: {
        enabled: true
        reopenClosedIncident: false
        lookbackDuration: 'PT2H'
        matchingMethod: 'AllEntities'
        groupByEntities: []
        groupByAlertDetails: []
        groupByCustomDetails: []
      }
    }
    eventGroupingSettings: {
      aggregationKind: 'SingleAlert'
    }
  }
  dependsOn: [
    sentinelOnboarding
  ]
}

output workspaceName string = workspace.name
output workspaceResourceId string = workspace.id
output customTableName string = customTableName
output dataCollectionEndpoint string = dataCollectionEndpoint.properties.logsIngestion.endpoint
output dataCollectionRuleId string = dataCollectionRule.id
output dataCollectionRuleImmutableId string = dataCollectionRule.properties.immutableId
output streamName string = streamName
