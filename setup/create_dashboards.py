#!/usr/bin/env python3

import argparse
import base64
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "https://localhost:5601"
DEFAULT_USER = "elastic"
DEFAULT_PASSWORD = "SiemElastic2026!"
DEFAULT_SOURCE_QUERY = "CyberArk"
DEFAULT_OUTPUT = Path("setup/dashboards/executive-operational-dashboards.ndjson")


def _build_request(base_url, path, user, password, method="GET", body=None):
    url = base_url.rstrip("/") + path
    headers = {"kbn-xsrf": "true"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    headers["Authorization"] = f"Basic {token}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def request_json(base_url, path, user, password, method="GET", body=None, insecure=False):
    context = ssl._create_unverified_context() if insecure else None
    request = _build_request(base_url, path, user, password, method=method, body=body)
    with urllib.request.urlopen(request, context=context) as response:
        payload = response.read().decode("utf-8")
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type or payload.startswith("{") or payload.startswith("["):
            return json.loads(payload)
        return payload


def request_text(base_url, path, user, password, method="GET", body=None, insecure=False):
    context = ssl._create_unverified_context() if insecure else None
    request = _build_request(base_url, path, user, password, method=method, body=body)
    with urllib.request.urlopen(request, context=context) as response:
        return response.read().decode("utf-8")


def find_source_dashboard(base_url, user, password, search_text, insecure=False):
    result = request_json(
        base_url,
        f"/api/saved_objects/_find?type=dashboard&search={urllib.parse.quote(search_text)}&search_fields=title&per_page=1",
        user,
        password,
        insecure=insecure,
    )
    objects = result.get("saved_objects", [])
    if not objects:
        raise RuntimeError(f"No dashboard found matching {search_text!r}")
    return objects[0]


def clone_dashboard(source, new_id, new_title, new_description):
    clone = {
        "type": "dashboard",
        "id": new_id,
        "attributes": json.loads(json.dumps(source["attributes"])),
        "references": json.loads(json.dumps(source.get("references", []))),
    }
    clone["attributes"]["title"] = new_title
    clone["attributes"]["description"] = new_description
    clone["attributes"]["timeRestore"] = False
    return clone


def export_dashboards(base_url, user, password, dashboard_ids, output_path, insecure=False):
    body = {"objects": [{"type": "dashboard", "id": dashboard_id} for dashboard_id in dashboard_ids], "includeReferencesDeep": True}
    payload = request_text(base_url, "/api/saved_objects/_export", user, password, method="POST", body=body, insecure=insecure)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(payload, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Clone a working Kibana dashboard into executive and operational views.")
    parser.add_argument("--kibana", default=os.getenv("KIBANA_HOST", DEFAULT_BASE_URL), help="Kibana base URL")
    parser.add_argument("--user", default=os.getenv("KIBANA_USER", DEFAULT_USER), help="Kibana username")
    parser.add_argument("--password", default=os.getenv("KIBANA_PASSWORD", DEFAULT_PASSWORD), help="Kibana password")
    parser.add_argument("--search", default=DEFAULT_SOURCE_QUERY, help="Dashboard title search text")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="NDJSON export path")
    parser.add_argument("--insecure", action="store_true", help="Skip TLS certificate validation")
    args = parser.parse_args()

    source = find_source_dashboard(args.kibana, args.user, args.password, args.search, insecure=args.insecure)
    executive = clone_dashboard(
        source,
        "executive-security-overview",
        "Executive Security Overview",
        "Resumen ejecutivo de actividad, autenticaciones y señales de riesgo.",
    )
    operational = clone_dashboard(
        source,
        "operational-triage-console",
        "Operational Triage Console",
        "Vista operacional para investigación, triage y respuesta.",
    )

    request_json(args.kibana, "/api/saved_objects/_bulk_create?overwrite=true", args.user, args.password, method="POST", body=[executive, operational], insecure=args.insecure)
    export_dashboards(args.kibana, args.user, args.password, [executive["id"], operational["id"]], Path(args.output), insecure=args.insecure)

    print(f"Created dashboards: {executive['id']}, {operational['id']}")
    print(f"Exported NDJSON to: {args.output}")


if __name__ == "__main__":
    main()