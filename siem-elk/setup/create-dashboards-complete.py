#!/usr/bin/env python3
"""
create-dashboards-complete.py
Genera dashboards ejecutivo y operacional con visualizaciones completas para Kibana 8.3.3
"""

import json
from pathlib import Path


def build_dashboard(dashboard_id, title, description, panel_specs):
    panels = []
    references = []

    for index, panel_spec in enumerate(panel_specs, start=1):
        panel_ref_name = f"panel_{index}"
        panels.append(
            {
                "version": "8.3.3",
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

    return {
        "type": "dashboard",
        "id": dashboard_id,
        "attributes": {
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
            "refreshInterval": {"pause": True, "value": 0},
            "timeRestore": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps(
                    {
                        "query": {"language": "kuery", "query": ""},
                        "filter": [],
                    }
                )
            },
        },
        "references": references,
    }

def create_complete_dashboards():
    """Crea dashboards con visualizaciones para Kibana 8.3.3"""
    
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
    
    # ─── VISUALIZATIONS ──────────────────────────────────────────────────────
    
    # 1. Top Threats (pie chart)
    viz_top_threats = {
        "type": "visualization",
        "id": "viz-top-threats",
        "attributes": {
            "title": "Top Amenazas del Día",
            "visState": json.dumps({
                "title": "Top Amenazas del Día",
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
                            "field": "event.action",
                            "size": 5,
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
    saved_objects.append(viz_top_threats)
    
    # 2. Alert Trend (line chart)
    viz_alert_trend = {
        "type": "visualization",
        "id": "viz-alert-trend",
        "attributes": {
            "title": "Tendencia de Alertas por Semana",
            "visState": json.dumps({
                "title": "Tendencia de Alertas por Semana",
                "type": "line",
                "params": {
                    "grid": {"categoryLines": False, "valueAxis": "ValueAxis-1"},
                    "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom", "show": True, "style": {}, "scale": {"type": "linear"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value", "position": "left", "show": True, "style": {}, "scale": {"type": "linear", "mode": "normal"}, "labels": {"show": True, "truncate": 100}, "title": {"text": "Count"}}],
                    "seriesParams": [{"show": True, "type": "line", "interpolate": "linear", "valueAxis": "ValueAxis-1"}],
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
                            "interval": "day",
                            "customInterval": "2h",
                            "min_doc_count": 1,
                            "extended_bounds": {},
                            "order": "asc",
                            "orderBy": "_key"
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
    saved_objects.append(viz_alert_trend)
    
    # 3. Top IPs (horizontal bar)
    viz_top_ips = {
        "type": "visualization",
        "id": "viz-top-ips",
        "attributes": {
            "title": "Top IPs con Eventos",
            "visState": json.dumps({
                "title": "Top IPs con Eventos",
                "type": "histogram",
                "params": {
                    "grid": {"categoryLines": False, "valueAxis": "ValueAxis-1"},
                    "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "left", "show": True, "style": {}, "scale": {"type": "linear"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value", "position": "bottom", "show": True, "style": {}, "scale": {"type": "linear", "mode": "normal"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "seriesParams": [{"show": True, "type": "bars", "stacked": "none", "mode": "normal", "valueAxis": "ValueAxis-1", "drawLinesBetweenPoints": True}],
                    "addLegend": False,
                    "addTooltip": True,
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
                            "field": "source.ip",
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
    
    # 4. System Health KPI
    viz_health = {
        "type": "visualization",
        "id": "viz-system-health",
        "attributes": {
            "title": "Salud General del Sistema",
            "visState": json.dumps({
                "title": "Salud General del Sistema",
                "type": "metric",
                "params": {
                    "addLegend": False,
                    "addTooltip": True,
                    "fontSize": 60,
                    "handleNoResults": True,
                    "colorFullBackground": False,
                    "coloring": "Shades",
                    "invertColors": False,
                    "thresholdStyle": "background",
                    "thresholds": "1000,10000",
                    "sparkline": {"show": True, "full": True, "valueSparklineMode": "gray"}
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
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
    
    # 5. Real-time Events Table
    viz_events_table = {
        "type": "visualization",
        "id": "viz-events-table",
        "attributes": {
            "title": "Eventos en Tiempo Real",
            "visState": json.dumps({
                "title": "Eventos en Tiempo Real",
                "type": "table",
                "params": {
                    "perPage": 10,
                    "showPartialRows": False,
                    "showMeticsAtAllLevels": False,
                    "showTotal": False,
                    "totalFunc": "sum",
                    "percentageCol": ""
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
                            "size": 100,
                            "order": "desc",
                            "orderBy": "_key"
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
    
    # 6. Active Alerts Table
    viz_alerts_table = {
        "type": "visualization",
        "id": "viz-alerts-table",
        "attributes": {
            "title": "Alertas Activas",
            "visState": json.dumps({
                "title": "Alertas Activas",
                "type": "table",
                "params": {
                    "perPage": 20,
                    "showPartialRows": False,
                    "showMeticsAtAllLevels": False,
                    "showTotal": False,
                    "totalFunc": "sum",
                    "percentageCol": ""
                },
                "aggs": [
                    {
                        "id": "1",
                        "enabled": True,
                        "type": "count",
                        "schema": "metric",
                        "params": {}
                    }
                ]
            }),
            "uiStateJSON": "{}",
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": json.dumps({
                    "index": "logs-*",
                    "query": {
                        "bool": {
                            "must": [
                                {"term": {"event.category": "threat"}},
                                {"range": {"@timestamp": {"gte": "now-7d"}}}
                            ]
                        }
                    },
                    "filter": [],
                    "sort": [{"@timestamp": {"order": "desc"}}]
                })
            }
        }
    }
    saved_objects.append(viz_alerts_table)
    
    # 7. Top Users
    viz_top_users = {
        "type": "visualization",
        "id": "viz-top-users",
        "attributes": {
            "title": "Top Usuarios con Eventos",
            "visState": json.dumps({
                "title": "Top Usuarios con Eventos",
                "type": "histogram",
                "params": {
                    "grid": {"categoryLines": False, "valueAxis": "ValueAxis-1"},
                    "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "left", "show": True, "style": {}, "scale": {"type": "linear"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "valueAxes": [{"id": "ValueAxis-1", "name": "LeftAxis-1", "type": "value", "position": "bottom", "show": True, "style": {}, "scale": {"type": "linear", "mode": "normal"}, "labels": {"show": True, "truncate": 100}, "title": {}}],
                    "seriesParams": [{"show": True, "type": "bars", "stacked": "none", "mode": "normal", "valueAxis": "ValueAxis-1"}],
                    "addLegend": False,
                    "addTooltip": True,
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
                            "field": "user.name",
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
    
    # ─── DASHBOARDS ──────────────────────────────────────────────────────────

    executive_panels = [
        {"id": "viz-system-health", "gridData": {"x": 0, "y": 0, "w": 24, "h": 12}},
        {"id": "viz-top-threats", "gridData": {"x": 24, "y": 0, "w": 24, "h": 12}},
        {"id": "viz-alert-trend", "gridData": {"x": 0, "y": 12, "w": 48, "h": 12}},
        {"id": "viz-top-ips", "gridData": {"x": 0, "y": 24, "w": 48, "h": 15}},
    ]
    saved_objects.append(
        build_dashboard(
            "executive-security-overview",
            "Executive - Información de Seguridad",
            "Panel ejecutivo con KPIs y amenazas para audiencia no técnica",
            executive_panels,
        )
    )

    operational_panels = [
        {"id": "viz-top-users", "gridData": {"x": 0, "y": 0, "w": 24, "h": 15}},
        {"id": "viz-top-ips", "gridData": {"x": 24, "y": 0, "w": 24, "h": 15}},
        {"id": "viz-alerts-table", "gridData": {"x": 0, "y": 15, "w": 48, "h": 18}},
        {"id": "viz-events-table", "gridData": {"x": 0, "y": 33, "w": 48, "h": 20}},
    ]
    saved_objects.append(
        build_dashboard(
            "operational-triage-console",
            "Operational - Consola de Triaje",
            "Panel operacional para investigación y respuesta a incidentes",
            operational_panels,
        )
    )
    
    # Write NDJSON
    output_path = Path(__file__).resolve().parent.parent / "setup" / "dashboards" / "executive-operational-dashboards.ndjson"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w", encoding="utf-8") as f:
        for item in saved_objects:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"✓ Dashboards completos creados para Kibana 8.3.3")
    print(f"  Archivo: {output_path}")
    print(f"  Visualizaciones: {sum(1 for d in saved_objects if d['type'] == 'visualization')}")
    print(f"  Dashboards: {sum(1 for d in saved_objects if d['type'] == 'dashboard')}")

if __name__ == "__main__":
    create_complete_dashboards()
