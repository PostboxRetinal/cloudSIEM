#!/usr/bin/env python3
"""
create-dashboards-8-3-3.py
Genera dashboards para Kibana 8.3.3 directamente con formato correcto.
"""

from pathlib import Path
import runpy


def create_dashboard_ndjson():
    """Genera dashboards executive y operational para Kibana 8.3.3."""
    target = Path(__file__).with_name("create-dashboards-complete.py")
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    create_dashboard_ndjson()
