#!/usr/bin/env python3
"""
sentinel-forwarder.py
Continuously forwards normalized CloudSIEM events from Elasticsearch to
Microsoft Sentinel through the Azure Monitor Logs Ingestion API.
"""

import argparse
import base64
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_INDEX = "logs-*"
TOKEN_SCOPE = "https://monitor.azure.com//.default"
INGEST_API_VERSION = "2023-01-01"
MAX_STRING_LENGTH = 16000
MAX_INGEST_BYTES = 900000


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


def getenv(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def parse_args():
    parser = argparse.ArgumentParser(description="Forward CloudSIEM logs to Microsoft Sentinel")
    parser.add_argument("--once", action="store_true", help="Run one polling iteration and exit")
    parser.add_argument("--dry-run", action="store_true", help="Read and normalize events without sending to Azure")
    return parser.parse_args()


def utc_now():
    return datetime.now(timezone.utc)


def iso_z(dt):
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_timestamp(value):
    parsed = parse_datetime(value)
    return iso_z(parsed or utc_now())


def load_checkpoint(path):
    checkpoint_path = Path(path)
    if not checkpoint_path.exists():
        return {"timestamp": None, "ids": []}
    try:
        with checkpoint_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"timestamp": None, "ids": []}
    return {
        "timestamp": data.get("timestamp"),
        "ids": data.get("ids", []),
    }


def save_checkpoint(path, checkpoint):
    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = checkpoint_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(checkpoint, handle, sort_keys=True)
    tmp_path.replace(checkpoint_path)


def ssl_context(cacert=None, insecure=False):
    if insecure:
        return ssl._create_unverified_context()  # noqa: S323 - explicit opt-in for local dev only
    if cacert and Path(cacert).exists():
        return ssl.create_default_context(cafile=cacert)
    return ssl.create_default_context()


def basic_auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def request_json(method, url, headers=None, body=None, context=None, timeout=30):
    data = None
    request_headers = headers or {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers = {"Content-Type": "application/json", **request_headers}

    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            response_body = response.read()
            if not response_body:
                return response.status, None
            return response.status, json.loads(response_body.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {response_body[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


class AzureTokenProvider:
    def __init__(self, tenant_id, client_id, client_secret):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.expires_at = 0

    def get_token(self):
        if self.access_token and time.time() < self.expires_at - 120:
            return self.access_token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": TOKEN_SCOPE,
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                token_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Azure token request failed: HTTP {exc.code}: {response_body[:500]}") from exc

        self.access_token = token_payload["access_token"]
        self.expires_at = time.time() + int(token_payload.get("expires_in", 3600))
        return self.access_token


def get_path(document, path, default=None):
    if path in document:
        return document[path]
    current = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def first_value(value, default=None):
    if isinstance(value, list):
        for item in value:
            if item not in (None, ""):
                return item
        return default
    if value in (None, ""):
        return default
    return value


def as_string(value):
    value = first_value(value, "")
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text[:MAX_STRING_LENGTH]


def as_long(value):
    value = first_value(value)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_bool(value):
    value = first_value(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value) if value is not None else False


def tags_value(document):
    tags = get_path(document, "tags", [])
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(tag) for tag in tags]
    return [str(tags)]


def normalize_hit(hit):
    document = hit.get("_source", {})
    timestamp = canonical_timestamp(get_path(document, "@timestamp"))

    return {
        "TimeGenerated": timestamp,
        "EventId": as_string(hit.get("_id")),
        "ElasticIndex": as_string(hit.get("_index")),
        "EventDataset": as_string(get_path(document, "event.dataset")),
        "EventCategory": as_string(get_path(document, "event.category")),
        "EventType": as_string(get_path(document, "event.type")),
        "EventAction": as_string(get_path(document, "event.action")),
        "EventOutcome": as_string(get_path(document, "event.outcome")),
        "EventSeverity": as_long(get_path(document, "event.severity")),
        "SiemSeverity": as_string(get_path(document, "siem.severity")),
        "SourceIp": as_string(get_path(document, "source.ip")),
        "SourcePort": as_long(get_path(document, "source.port")),
        "DestinationIp": as_string(get_path(document, "destination.ip")),
        "DestinationPort": as_long(get_path(document, "destination.port")),
        "NetworkTransport": as_string(get_path(document, "network.transport")),
        "UserName": as_string(get_path(document, "user.name")),
        "HostName": as_string(get_path(document, "host.name")),
        "ProcessName": as_string(get_path(document, "process.name")),
        "HttpMethod": as_string(get_path(document, "http.request.method")),
        "HttpStatusCode": as_long(get_path(document, "http.response.status_code")),
        "HttpResponseBytes": as_long(get_path(document, "http.response.body.bytes")),
        "UrlPath": as_string(get_path(document, "url.path")),
        "UrlOriginal": as_string(get_path(document, "url.original")),
        "UserAgent": as_string(get_path(document, "user_agent.original")),
        "Tags": tags_value(document),
        "BruteForceAttempt": as_bool(get_path(document, "siem.brute_force_attempt")),
        "AfterHoursLogin": as_bool(get_path(document, "siem.after_hours_login")),
        "SensitivePath": as_bool(get_path(document, "siem.sensitive_path")),
        "SqliDetected": as_bool(get_path(document, "siem.sqli_detected")),
        "XssDetected": as_bool(get_path(document, "siem.xss_detected")),
        "PathTraversal": as_bool(get_path(document, "siem.path_traversal")),
        "ScannerDetected": as_bool(get_path(document, "siem.scanner_detected")),
        "Message": as_string(get_path(document, "message")),
    }


def fetch_elasticsearch_batch(es_url, es_auth, es_context, index_pattern, checkpoint, batch_size, lookback_minutes):
    last_ts = checkpoint.get("timestamp")
    seen_ids = set(checkpoint.get("ids", []))
    start_time = last_ts or f"now-{lookback_minutes}m"
    search_size = min(max(batch_size + len(seen_ids) + 100, batch_size), 10000)
    search_body = {
        "size": search_size,
        "sort": [
            {"@timestamp": {"order": "asc", "unmapped_type": "date"}}
        ],
        "query": {
            "range": {
                "@timestamp": {
                    "gte": start_time
                }
            }
        },
    }
    endpoint = f"{es_url.rstrip('/')}/{index_pattern}/_search?ignore_unavailable=true&allow_no_indices=true"
    _, payload = request_json(
        "POST",
        endpoint,
        headers={"Authorization": es_auth},
        body=search_body,
        context=es_context,
        timeout=30,
    )
    hits = payload.get("hits", {}).get("hits", []) if payload else []
    records = []
    event_ids = []
    for hit in hits:
        record = normalize_hit(hit)
        event_id = record["EventId"]
        if last_ts and record["TimeGenerated"] == last_ts and event_id in seen_ids:
            continue
        records.append(record)
        event_ids.append(event_id)
        if len(records) >= batch_size:
            break
    return records, event_ids


def send_to_sentinel(token_provider, dce_endpoint, dcr_immutable_id, stream_name, records):
    url = (
        f"{dce_endpoint.rstrip('/')}/dataCollectionRules/{dcr_immutable_id}"
        f"/streams/{stream_name}?api-version={INGEST_API_VERSION}"
    )
    headers = {
        "Authorization": f"Bearer {token_provider.get_token()}",
        "Content-Type": "application/json",
    }
    data = json.dumps(records).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"Unexpected Sentinel response status {response.status}")
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Sentinel ingestion failed: HTTP {exc.code}: {response_body[:500]}") from exc


def record_chunks(records, max_bytes=MAX_INGEST_BYTES):
    chunk = []
    chunk_bytes = 2
    for record in records:
        record_bytes = len(json.dumps(record).encode("utf-8")) + 1
        if chunk and chunk_bytes + record_bytes > max_bytes:
            yield chunk
            chunk = []
            chunk_bytes = 2
        chunk.append(record)
        chunk_bytes += record_bytes
    if chunk:
        yield chunk


def update_checkpoint(previous, records, event_ids):
    if not records:
        return previous

    max_ts = max(record["TimeGenerated"] for record in records)
    max_ids = [event_id for record, event_id in zip(records, event_ids) if record["TimeGenerated"] == max_ts]
    if previous.get("timestamp") == max_ts:
        max_ids.extend(previous.get("ids", []))
    return {
        "timestamp": max_ts,
        "ids": sorted(set(max_ids))[-10000:],
    }


def main():
    args = parse_args()
    try:
        tenant_id = getenv("AZURE_TENANT_ID", required=not args.dry_run)
        client_id = getenv("AZURE_CLIENT_ID", required=not args.dry_run)
        client_secret = getenv("AZURE_CLIENT_SECRET", required=not args.dry_run)
        dce_endpoint = getenv("SENTINEL_DCE_ENDPOINT", required=not args.dry_run)
        dcr_immutable_id = getenv("SENTINEL_DCR_IMMUTABLE_ID", required=not args.dry_run)
    except ConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    stream_name = getenv("SENTINEL_STREAM_NAME", "Custom-CloudSIEM")
    es_url = getenv("ES_URL", getenv("ELASTIC_HOSTS", "https://localhost:9200"))
    es_url = es_url.split(",")[0]
    es_user = getenv("ELASTIC_USER", "elastic")
    es_password = getenv("ELASTIC_PASSWORD", required=True)
    cacert = getenv("CACERT", "./setup/certs/ca/ca.crt")
    checkpoint_file = getenv("SENTINEL_CHECKPOINT_FILE", "./sentinel-forwarder-checkpoint.json")
    poll_seconds = int(getenv("SENTINEL_POLL_SECONDS", "10"))
    batch_size = int(getenv("SENTINEL_BATCH_SIZE", "500"))
    lookback_minutes = int(getenv("SENTINEL_LOOKBACK_MINUTES", "15"))
    index_pattern = getenv("SENTINEL_INDEX_PATTERN", DEFAULT_INDEX)
    insecure_es = getenv("SENTINEL_INSECURE_ES", "false").lower() == "true"

    es_context = ssl_context(cacert, insecure=insecure_es)
    es_auth = basic_auth_header(es_user, es_password)
    token_provider = None if args.dry_run else AzureTokenProvider(tenant_id, client_id, client_secret)

    print("CloudSIEM Sentinel forwarder started", flush=True)
    print(f"  Elasticsearch: {es_url}/{index_pattern}", flush=True)
    print(f"  Stream: {stream_name}", flush=True)
    print(f"  Checkpoint: {checkpoint_file}", flush=True)

    while True:
        checkpoint = load_checkpoint(checkpoint_file)
        try:
            records, event_ids = fetch_elasticsearch_batch(
                es_url,
                es_auth,
                es_context,
                index_pattern,
                checkpoint,
                batch_size,
                lookback_minutes,
            )
            if records:
                if args.dry_run:
                    print(f"Dry run: normalized {len(records)} records", flush=True)
                else:
                    for chunk in record_chunks(records):
                        send_to_sentinel(token_provider, dce_endpoint, dcr_immutable_id, stream_name, chunk)
                    print(f"Forwarded {len(records)} records to Microsoft Sentinel", flush=True)
                save_checkpoint(checkpoint_file, update_checkpoint(checkpoint, records, event_ids))
            else:
                print("No new records to forward", flush=True)
        except Exception as exc:  # noqa: BLE001 - keep daemon alive after transient failures
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)

        if args.once:
            break
        time.sleep(poll_seconds)

    return 0


if __name__ == "__main__":
    sys.exit(main())
