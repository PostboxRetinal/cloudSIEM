#!/usr/bin/env python3
"""
create-dashboards-complete.py
Genera dashboards ejecutivo y operacional con visualizaciones completas para Kibana 8.19.14
"""

import json
from pathlib import Path

DASHBOARD_VERSION = "8.19.14"
LOGS_INDEX = "logs-*"

RISK_QUERY = {
    "bool": {
        "filter": [
            {"terms": {"siem.severity.keyword": ["high", "medium"]}}
        ]
    }
}

HIGH_RISK_QUERY = {"term": {"siem.severity.keyword": "high"}}
MEDIUM_RISK_QUERY = {"term": {"siem.severity.keyword": "medium"}}
AUTH_FAILURE_QUERY = {"term": {"event.action.keyword": "authentication_failure"}}
FIREWALL_BLOCK_QUERY = {"term": {"event.action.keyword": "firewall_block"}}
WEB_EVENTS_QUERY = {"term": {"event.dataset.keyword": "nginx.access"}}
AUTH_USER_QUERY = {
    "bool": {
        "filter": [
            {"term": {"event.dataset.keyword": "system.auth"}},
            {"exists": {"field": "user.name.keyword"}},
        ],
        "must_not": [{"term": {"user.name.keyword": ""}}],
    }
}

THREAT_TAGS_REGEX = (
    "sqli_detected|path_traversal|security_scanner|sensitive_path_access|"
    "auth_failure|firewall_block|after_hours_login|high_risk_sudo|"
    "xss_detected|max_attempts_exceeded|http_404"
)
WEB_INDICATOR_TAGS_REGEX = (
    "sqli_detected|path_traversal|security_scanner|sensitive_path_access|"
    "xss_detected|http_404"
)


def search_source(query=None, sort=None):
    source = {
        "index": LOGS_INDEX,
        "query": query or {"match_all": {}},
        "filter": [],
    }
    if sort:
        source["sort"] = sort
    return {"searchSourceJSON": json.dumps(source, ensure_ascii=False)}


def build_metric_visualization(viz_id, title, sub_text, query=None, agg_type="count", agg_params=None):
    return {
        "type": "visualization",
        "id": viz_id,
        "attributes": {
            "title": title,
            "visState": json.dumps(
                {
                    "title": title,
                    "type": "metric",
                    "params": {
                        "addTooltip": True,
                        "addLegend": False,
                        "type": "metric",
                        "metric": {
                            "percentageMode": False,
                            "useRanges": False,
                            "colorSchema": "Green to Red",
                            "metricColorMode": "None",
                            "colorsRange": [{"from": 0, "to": 10000}],
                            "labels": {"show": False},
                            "invertColors": False,
                            "style": {
                                "bgFill": "#000",
                                "bgColor": False,
                                "labelColor": False,
                                "subText": sub_text,
                                "fontSize": 48,
                            },
                        },
                    },
                    "aggs": [
                        {
                            "id": "1",
                            "enabled": True,
                            "type": agg_type,
                            "schema": "metric",
                            "params": agg_params or {},
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(query),
        },
    }


def build_pie_visualization(viz_id, title, field, query=None, size=8, include=None):
    bucket_params = {
        "field": field,
        "size": size,
        "order": "desc",
        "orderBy": "1",
    }
    if include:
        bucket_params["include"] = include

    return {
        "type": "visualization",
        "id": viz_id,
        "attributes": {
            "title": title,
            "visState": json.dumps(
                {
                    "title": title,
                    "type": "pie",
                    "params": {
                        "addLegend": True,
                        "addTooltip": True,
                        "isDonut": True,
                        "legendPosition": "right",
                    },
                    "aggs": [
                        {
                            "id": "1",
                            "enabled": True,
                            "type": "count",
                            "schema": "metric",
                            "params": {},
                        },
                        {
                            "id": "2",
                            "enabled": True,
                            "type": "terms",
                            "schema": "segment",
                            "params": bucket_params,
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(query),
        },
    }


def build_table_visualization(viz_id, title, buckets, query=None, per_page=10, sort=None):
    aggs = [
        {
            "id": "1",
            "enabled": True,
            "type": "count",
            "schema": "metric",
            "params": {},
        }
    ]

    for index, bucket in enumerate(buckets, start=2):
        params = {
            "field": bucket["field"],
            "size": bucket.get("size", 10),
            "order": bucket.get("order", "desc"),
            "orderBy": bucket.get("orderBy", "1"),
        }
        if "include" in bucket:
            params["include"] = bucket["include"]
        aggs.append(
            {
                "id": str(index),
                "enabled": True,
                "type": "terms",
                "schema": "bucket",
                "params": params,
            }
        )

    return {
        "type": "visualization",
        "id": viz_id,
        "attributes": {
            "title": title,
            "visState": json.dumps(
                {
                    "title": title,
                    "type": "table",
                    "params": {
                        "perPage": per_page,
                        "showTotal": False,
                    },
                    "aggs": aggs,
                },
                ensure_ascii=False,
            ),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(query, sort=sort),
        },
    }


def build_line_visualization(viz_id, title, query=None, interval="m", custom_interval="1m"):
    return {
        "type": "visualization",
        "id": viz_id,
        "attributes": {
            "title": title,
            "visState": json.dumps(
                {
                    "title": title,
                    "type": "line",
                    "params": {
                        "grid": {"categoryLines": False, "valueAxis": "ValueAxis-1"},
                        "categoryAxes": [
                            {
                                "id": "CategoryAxis-1",
                                "type": "category",
                                "position": "bottom",
                                "show": True,
                                "style": {},
                                "scale": {"type": "linear"},
                                "labels": {"show": True, "truncate": 100},
                                "title": {},
                            }
                        ],
                        "valueAxes": [
                            {
                                "id": "ValueAxis-1",
                                "name": "LeftAxis-1",
                                "type": "value",
                                "position": "left",
                                "show": True,
                                "style": {},
                                "scale": {"type": "linear", "mode": "normal"},
                                "labels": {"show": True, "truncate": 100},
                                "title": {"text": "Count"},
                            }
                        ],
                        "seriesParams": [
                            {
                                "show": True,
                                "type": "line",
                                "mode": "normal",
                                "data": {"label": "Count", "id": "1"},
                                "interpolate": "linear",
                                "drawLinesBetweenPoints": True,
                                "showCircles": True,
                                "valueAxis": "ValueAxis-1",
                            }
                        ],
                        "addLegend": True,
                        "addTooltip": True,
                        "legendPosition": "bottom",
                    },
                    "aggs": [
                        {
                            "id": "1",
                            "enabled": True,
                            "type": "count",
                            "schema": "metric",
                            "params": {},
                        },
                        {
                            "id": "2",
                            "enabled": True,
                            "type": "date_histogram",
                            "schema": "segment",
                            "params": {
                                "field": "@timestamp",
                                "interval": interval,
                                "customInterval": custom_interval,
                                "min_doc_count": 1,
                                "extended_bounds": {},
                                "order": "asc",
                                "orderBy": "_key",
                            },
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(query),
        },
    }


def build_dashboard(
    dashboard_id,
    title,
    description,
    panel_specs,
    refresh_interval={"pause": True, "value": 0},
    time_from=None,
    time_to=None,
):
    panels = []
    references = []

    for index, panel_spec in enumerate(panel_specs, start=1):
        panel_ref_name = f"panel_{index}"
        panels.append(
            {
                "version": DASHBOARD_VERSION,
                "type": "visualization",
                "gridData": panel_spec["gridData"],
                "panelIndex": str(index),
                "embeddableConfig": {},
                "panelRefName": panel_ref_name,
            }
        )
        references.append(
            {
                "type": "visualization",
                "id": panel_spec["id"],
                "name": panel_ref_name,
            }
        )

    attributes = {
        "title": title,
        "description": description,
        "optionsJSON": json.dumps(
            {
                "useMargins": True,
                "syncColors": False,
                "syncCursor": True,
                "syncTooltips": False,
                "hidePanelTitles": False,
            }
        ),
        "panelsJSON": json.dumps(panels, ensure_ascii=False),
        "refreshInterval": refresh_interval,
        "timeRestore": bool(time_from or time_to),
        "kibanaSavedObjectMeta": {
            "searchSourceJSON": json.dumps(
                {
                    "query": {"language": "kuery", "query": ""},
                    "filter": [],
                }
            )
        },
    }
    if time_from:
        attributes["timeFrom"] = time_from
    if time_to:
        attributes["timeTo"] = time_to

    return {
        "type": "dashboard",
        "id": dashboard_id,
        "attributes": attributes,
        "references": references,
    }

def create_complete_dashboards():
    """Crea dashboards con visualizaciones para Kibana 8.19.14"""
    
    saved_objects = []
    
    # Index pattern para logs
    index_pattern = {
        "type": "index-pattern",
        "id": "logs-*",
        "attributes": {
            "title": "logs-*",
            "timeFieldName": "@timestamp"
        }
    }
    saved_objects.append(index_pattern)
    saved_objects.extend(
        [
            build_metric_visualization(
                "viz-exec-total-events",
                "Eventos Observados",
                "últimas 24h",
            ),
            build_metric_visualization(
                "viz-exec-high-risk",
                "Riesgo Alto",
                "eventos críticos",
                query=HIGH_RISK_QUERY,
            ),
            build_metric_visualization(
                "viz-exec-medium-risk",
                "Riesgo Medio",
                "eventos relevantes",
                query=MEDIUM_RISK_QUERY,
            ),
            build_metric_visualization(
                "viz-exec-risk-sources",
                "IPs Sospechosas",
                "orígenes únicos",
                query=RISK_QUERY,
                agg_type="cardinality",
                agg_params={"field": "source.ip.keyword"},
            ),
        ]
    )
    
    # ─── VISUALIZATIONS ──────────────────────────────────────────────────────
    
    # 1. Top Threats (pie chart)
    viz_top_threats = {
        "type": "visualization",
        "id": "viz-top-threats",
        "attributes": {
            "title": "Top Señales de Riesgo del Día",
            "visState": json.dumps({
                "title": "Top Señales de Riesgo del Día",
                "type": "pie",
                "params": {
                    "addLegend": True,
                    "addTooltip": True,
                    "isDonut": True,
                    "legendPosition": "right"
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "segment",
                        "params": {
                            "field": "tags.keyword",
                            "size": 8,
                            "include": THREAT_TAGS_REGEX,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(RISK_QUERY)
        }
    }
    saved_objects.append(viz_top_threats)
    
    # 2. Alert Trend (line chart)
    viz_alert_trend = {
        "type": "visualization",
        "id": "viz-alert-trend",
        "attributes": {
            "title": "Tendencia de Riesgo por Hora",
            "visState": json.dumps({
                "title": "Tendencia de Riesgo por Hora",
                "type": "line",
                "params": {
                    "grid": {"categoryLines": False, "valueAxis": "ValueAxis-1"},
                    "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom", "show": True, "style": {}, "scale": {"type": "linear"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value", "position": "left", "show": True, "style": {}, "scale": {"type": "linear", "mode": "normal"}, "labels": {"show": True, "truncate": 100}, "title": {"text": "Count"}}],
                    "seriesParams": [
                        {
                            "show": True,
                            "type": "line",
                            "mode": "normal",
                            "data": {"label": "Count", "id": "1"},
                            "interpolate": "linear",
                            "drawLinesBetweenPoints": True,
                            "showCircles": True,
                            "valueAxis": "ValueAxis-1",
                        }
                    ],
                    "addLegend": True,
                    "addTooltip": True,
                    "legendPosition": "bottom"
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "date_histogram",
                        "schema": "segment",
                        "params": {
                            "field": "@timestamp",
                            "interval": "h",
                            "customInterval": "1h",
                            "min_doc_count": 1,
                            "extended_bounds": {},
                            "order": "asc",
                            "orderBy": "_key"
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(RISK_QUERY)
        }
    }
    saved_objects.append(viz_alert_trend)

    # 3. Top IPs (Table)
    viz_top_ips = {
        "type": "visualization",
        "id": "viz-top-ips",
        "attributes": {
            "title": "Top IPs con más Eventos",
            "visState": json.dumps({
                "title": "Top IPs con más Eventos",
                "type": "table",
                "params": {
                    "perPage": 10,
                    "showTotal": False,
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "source.ip.keyword",
                            "size": 10,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {"match_all": {}},
                    "filter": []
                })
            }
        }
    }
    saved_objects.append(viz_top_ips)
    
    # 4. System Health KPI (Gauge)
    viz_health = {
        "type": "visualization",
        "id": "viz-system-health",
        "attributes": {
            "title": "Salud General: Hosts Monitoreados",
            "visState": json.dumps({
                "title": "Salud General: Hosts Monitoreados",
                "type": "gauge",
                "params": {
                    "type": "gauge",
                    "addTooltip": True,
                    "addLegend": False,
                    "isDonut": True,
                    "gauge": {
                        "verticalSplit": False,
                        "extendRange": True,
                        "percentageMode": False,
                        "gaugeType": "Arc",
                        "gaugeStyle": "Full",
                        "backStyle": "Full",
                        "orientation": "vertical",
                        "colorSchema": "Green to Red",
                        "gaugeColorMode": "Labels",
                        "colorsRange": [
                            {"from": 0, "to": 1},
                            {"from": 1, "to": 3},
                            {"from": 3, "to": 10}
                        ],
                        "invertColors": True,
                        "labels": {"show": True, "color": "black"},
                        "scale": {"show": True, "labels": False, "color": "#333"},
                        "type": "meter",
                        "style": {
                            "bgWidth": 0.9,
                            "width": 0.9,
                            "mask": False,
                            "bgMask": False,
                            "maskBars": 50,
                            "bgFill": "#eee",
                            "bgColor": False,
                            "subText": "Hosts",
                            "fontSize": 60
                        }
                    }
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "cardinality",
                        "schema": "metric",
                        "params": {"field": "host.name.keyword"}
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {"match_all": {}},
                    "filter": []
                })
            }
        }
    }
    saved_objects.append(viz_health)
    
    # Map
    viz_geoip_map = {
        "type": "visualization",
        "id": "viz-geoip-map",
        "attributes": {
            "title": "Mapa Geográfico de IPs Sospechosas",
            "visState": json.dumps({
                "title": "Mapa Geográfico de IPs Sospechosas",
                "type": "tile_map",
                "params": {
                    "addTooltip": True,
                    "mapType": "Scaled Circle Markers",
                    "isDesaturated": True,
                    "colorSchema": "Yellow to Red",
                    "heatMaxZoom": 16,
                    "heatMinOpacity": 0.1,
                    "heatRadius": 25,
                    "heatBlur": 15,
                    "heatNormalizeData": True
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "geohash_grid",
                        "schema": "segment",
                        "params": {
                            "field": "source.geo.location",
                            "autoPrecision": True
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(RISK_QUERY)
        }
    }
    saved_objects.append(viz_geoip_map)
    
    # 5. Real-time Events Table (Detailed)
    viz_events_table = {
        "type": "visualization",
        "id": "viz-events-table",
        "attributes": {
            "title": "Logs en Tiempo Real (Detalle)",
            "visState": json.dumps({
                "title": "Logs en Tiempo Real (Detalle)",
                "type": "table",
                "params": {
                    "perPage": 20,
                    "showTotal": False,
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "@timestamp",
                            "size": 50,
                            "order": "desc",
                            "orderBy": "_key"
                        }
                    },
                    {
                        "id": "3",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "event.dataset.keyword",
                            "size": 5
                        }
                    },
                    {
                        "id": "4",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "message.keyword",
                            "size": 5
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {"match_all": {}},
                    "filter": [],
                    "sort": [{"@timestamp": {"order": "desc"}}]
                })
            }
        }
    }
    saved_objects.append(viz_events_table)
    
    # 6. Active Alerts Table (Detailed)
    viz_alerts_table = {
        "type": "visualization",
        "id": "viz-alerts-table",
        "attributes": {
            "title": "Alertas Activas Detalladas",
            "visState": json.dumps({
                "title": "Alertas Activas Detalladas",
                "type": "table",
                "params": {
                    "perPage": 10,
                    "showTotal": False,
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "siem.severity.keyword",
                            "size": 5
                        }
                    },
                    {
                        "id": "3",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "event.action.keyword",
                            "size": 10
                        }
                    },
                    {
                        "id": "4",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "event.dataset.keyword",
                            "size": 5
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {
                        "bool": {
                            "should": [
                                {"term": {"siem.severity.keyword": "high"}},
                                {"term": {"siem.severity.keyword": "medium"}},
                                {"term": {"siem.severity.keyword": "low"}}
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "filter": [],
                    "sort": [{"@timestamp": {"order": "desc"}}]
                })
            }
        }
    }
    saved_objects.append(viz_alerts_table)
    
    # 7. Top Users (Table)
    viz_top_users = {
        "type": "visualization",
        "id": "viz-top-users",
        "attributes": {
            "title": "Top Usuarios con más Eventos",
            "visState": json.dumps({
                "title": "Top Usuarios con más Eventos",
                "type": "table",
                "params": {
                    "perPage": 10,
                    "showTotal": False,
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "user.name.keyword",
                            "size": 10,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {"match_all": {}},
                    "filter": []
                })
            }
        }
    }
    saved_objects.append(viz_top_users)

    # 8. Executive severity distribution
    viz_exec_severity = {
        "type": "visualization",
        "id": "viz-exec-severity-distribution",
        "attributes": {
            "title": "Distribución por Severidad",
            "visState": json.dumps({
                "title": "Distribución por Severidad",
                "type": "pie",
                "params": {
                    "addLegend": True,
                    "addTooltip": True,
                    "isDonut": True,
                    "legendPosition": "right"
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "segment",
                        "params": {
                            "field": "siem.severity.keyword",
                            "size": 4,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }, ensure_ascii=False),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source()
        }
    }
    saved_objects.append(viz_exec_severity)

    # 9. Executive source coverage
    viz_exec_source_coverage = {
        "type": "visualization",
        "id": "viz-exec-source-coverage",
        "attributes": {
            "title": "Cobertura por Fuente de Log",
            "visState": json.dumps({
                "title": "Cobertura por Fuente de Log",
                "type": "pie",
                "params": {
                    "addLegend": True,
                    "addTooltip": True,
                    "isDonut": True,
                    "legendPosition": "right"
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "segment",
                        "params": {
                            "field": "event.dataset.keyword",
                            "size": 8,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }, ensure_ascii=False),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source()
        }
    }
    saved_objects.append(viz_exec_source_coverage)

    # 10. Executive suspicious IPs table
    viz_exec_risk_ips = {
        "type": "visualization",
        "id": "viz-exec-risk-ips",
        "attributes": {
            "title": "Top IPs Sospechosas",
            "visState": json.dumps({
                "title": "Top IPs Sospechosas",
                "type": "table",
                "params": {
                    "perPage": 10,
                    "showTotal": False,
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    },
                    {
                        "id": "2",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "source.ip.keyword",
                            "size": 10,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    },
                    {
                        "id": "3",
                        "enabled": True,
                        "type": "terms",
                        "schema": "bucket",
                        "params": {
                            "field": "event.action.keyword",
                            "size": 5,
                            "order": "desc",
                            "orderBy": "1"
                        }
                    }
                ]
            }, ensure_ascii=False),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": search_source(RISK_QUERY)
        }
    }
    saved_objects.append(viz_exec_risk_ips)

    # ─── OPERATIONAL TRIAGE VISUALIZATIONS ──────────────────────────────────
    saved_objects.extend(
        [
            build_metric_visualization(
                "viz-op-events-recent",
                "Eventos Recientes",
                "últimas 2h",
            ),
            build_metric_visualization(
                "viz-op-risk-events",
                "Eventos de Riesgo",
                "high + medium",
                query=RISK_QUERY,
            ),
            build_metric_visualization(
                "viz-op-ssh-failures",
                "Fallos SSH",
                "authentication_failure",
                query=AUTH_FAILURE_QUERY,
            ),
            build_metric_visualization(
                "viz-op-firewall-blocks",
                "Bloqueos Firewall",
                "firewall_block",
                query=FIREWALL_BLOCK_QUERY,
            ),
            build_pie_visualization(
                "viz-op-actions",
                "Acciones Detectadas",
                "event.action.keyword",
                query=RISK_QUERY,
                size=8,
            ),
            build_pie_visualization(
                "viz-op-web-indicators",
                "Indicadores Web",
                "tags.keyword",
                query=WEB_EVENTS_QUERY,
                size=8,
                include=WEB_INDICATOR_TAGS_REGEX,
            ),
            build_line_visualization(
                "viz-op-risk-trend",
                "Tendencia de Riesgo por Minuto",
                query=RISK_QUERY,
                interval="m",
                custom_interval="1m",
            ),
            build_table_visualization(
                "viz-op-top-auth-users",
                "Top Usuarios Auth",
                [
                    {"field": "user.name.keyword", "size": 10},
                    {"field": "event.action.keyword", "size": 5},
                    {"field": "source.ip.keyword", "size": 5},
                ],
                query=AUTH_USER_QUERY,
                per_page=10,
            ),
            build_table_visualization(
                "viz-op-blocked-ports",
                "Puertos Destino Bloqueados",
                [
                    {"field": "destination.port", "size": 12},
                    {"field": "source.ip.keyword", "size": 5},
                ],
                query=FIREWALL_BLOCK_QUERY,
                per_page=12,
            ),
            build_table_visualization(
                "viz-op-investigation-events",
                "Eventos de Investigación",
                [
                    {"field": "@timestamp", "size": 50, "orderBy": "_key"},
                    {"field": "siem.severity.keyword", "size": 4},
                    {"field": "event.dataset.keyword", "size": 6},
                    {"field": "event.action.keyword", "size": 8},
                    {"field": "source.ip.keyword", "size": 10},
                    {"field": "message.keyword", "size": 5},
                ],
                query=RISK_QUERY,
                per_page=20,
                sort=[{"@timestamp": {"order": "desc"}}],
            ),
        ]
    )
    
    # ─── DASHBOARDS ──────────────────────────────────────────────────────────

    executive_panels = [
        {"id": "viz-exec-total-events", "gridData": {"x": 0, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-exec-high-risk", "gridData": {"x": 12, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-exec-medium-risk", "gridData": {"x": 24, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-exec-risk-sources", "gridData": {"x": 36, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-system-health", "gridData": {"x": 0, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-exec-severity-distribution", "gridData": {"x": 16, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-exec-source-coverage", "gridData": {"x": 32, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-top-threats", "gridData": {"x": 0, "y": 24, "w": 24, "h": 15}},
        {"id": "viz-alert-trend", "gridData": {"x": 24, "y": 24, "w": 24, "h": 15}},
        {"id": "viz-geoip-map", "gridData": {"x": 0, "y": 39, "w": 24, "h": 18}},
        {"id": "viz-exec-risk-ips", "gridData": {"x": 24, "y": 39, "w": 24, "h": 18}},
    ]
    saved_objects.append(
        build_dashboard(
            "executive-security-overview",
            "Executive - Resumen de Seguridad",
            "Panel ejecutivo con KPIs, amenazas, cobertura y tendencia de riesgo para audiencia no técnica",
            executive_panels,
            refresh_interval={"pause": False, "value": 10000},
            time_from="now-24h",
            time_to="now",
        )
    )

    operational_panels = [
        {"id": "viz-op-events-recent", "gridData": {"x": 0, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-op-risk-events", "gridData": {"x": 12, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-op-ssh-failures", "gridData": {"x": 24, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-op-firewall-blocks", "gridData": {"x": 36, "y": 0, "w": 12, "h": 10}},
        {"id": "viz-exec-severity-distribution", "gridData": {"x": 0, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-op-actions", "gridData": {"x": 16, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-op-web-indicators", "gridData": {"x": 32, "y": 10, "w": 16, "h": 14}},
        {"id": "viz-op-risk-trend", "gridData": {"x": 0, "y": 24, "w": 24, "h": 15}},
        {"id": "viz-op-blocked-ports", "gridData": {"x": 24, "y": 24, "w": 24, "h": 15}},
        {"id": "viz-exec-risk-ips", "gridData": {"x": 0, "y": 39, "w": 24, "h": 18}},
        {"id": "viz-op-top-auth-users", "gridData": {"x": 24, "y": 39, "w": 24, "h": 18}},
        {"id": "viz-op-investigation-events", "gridData": {"x": 0, "y": 57, "w": 48, "h": 22}},
    ]
    saved_objects.append(
        build_dashboard(
            "operational-triage-console",
            "Operational - Consola de Triaje",
            "Panel operacional para investigación y respuesta a incidentes",
            operational_panels,
            refresh_interval={"pause": False, "value": 10000},
            time_from="now-2h",
            time_to="now",
        )
    )
    
    # Write NDJSON
    output_path = Path(__file__).resolve().parent.parent / "setup" / "dashboards" / "executive-operational-dashboards.ndjson"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        for item in saved_objects:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✓ Dashboards completos creados para Kibana 8.19.14")
    print(f"  Archivo: {output_path}")
    print(f"  Visualizaciones: {sum(1 for d in saved_objects if d['type'] == 'visualization')}")
    print(f"  Dashboards: {sum(1 for d in saved_objects if d['type'] == 'dashboard')}")

if __name__ == "__main__":
    create_complete_dashboards()
