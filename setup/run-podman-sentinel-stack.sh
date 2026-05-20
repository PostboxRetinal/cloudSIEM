#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"
SENTINEL_ENV_FILE="${SENTINEL_ENV_FILE:-$ROOT_DIR/.env.sentinel}"
WITH_SENTINEL=true
BUILD=false
FORCE_RECREATE=false
PODMAN_COMPOSE_BIN="${PODMAN_COMPOSE:-}"

usage() {
  cat <<'EOF'
Usage: bash setup/run-podman-sentinel-stack.sh [--build] [--force-recreate] [--no-sentinel] [--compose-bin PATH]

Starts CloudSIEM on rootless Podman in explicit stages. This avoids Podman
Compose failures with service_completed_successfully dependencies.

Options:
  --build             Build images before starting long-running services.
  --force-recreate    Recreate long-running containers without deleting named volumes.
  --no-sentinel       Start only the local Elastic stack.
  --compose-bin PATH  Path to podman-compose binary.
  -h, --help          Show this help.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --build)
      BUILD=true
      ;;
    --force-recreate)
      FORCE_RECREATE=true
      ;;
    --no-sentinel)
      WITH_SENTINEL=false
      ;;
    --compose-bin)
      shift
      PODMAN_COMPOSE_BIN="${1:-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

find_podman_compose() {
  if [ -n "$PODMAN_COMPOSE_BIN" ]; then
    printf '%s\n' "$PODMAN_COMPOSE_BIN"
    return
  fi
  if command -v podman-compose >/dev/null 2>&1; then
    command -v podman-compose
    return
  fi
  if [ -x "$ROOT_DIR/.venv-tools/podman-compose/bin/podman-compose" ]; then
    printf '%s\n' "$ROOT_DIR/.venv-tools/podman-compose/bin/podman-compose"
    return
  fi
  if [ -x "/tmp/opencode/podman-compose-venv/bin/podman-compose" ]; then
    printf '%s\n' "/tmp/opencode/podman-compose-venv/bin/podman-compose"
    return
  fi
  return 1
}

load_env_file() {
  local file="$1"
  local line=""
  local key=""
  local value=""

  if [ ! -f "$file" ]; then
    echo "ERROR: required env file not found: $file" >&2
    exit 1
  fi

  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
      continue
    fi
    line="${line#export }"
    key="${line%%=*}"
    value="${line#*=}"

    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      echo "ERROR: invalid env key in $file: $key" >&2
      exit 1
    fi

    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi

    export "$key=$value"
  done < "$file"
}

ensure_podman_socket() {
  local socket_path="${XDG_RUNTIME_DIR}/podman/podman.sock"
  if [ -S "$socket_path" ]; then
    return 0
  fi

  mkdir -p "${XDG_RUNTIME_DIR}/podman"

  if [ -d "$socket_path" ]; then
    echo "Found stale Podman socket directory: $socket_path"
    if rmdir "$socket_path" 2>/dev/null; then
      echo "  Removed stale empty directory so podman.socket can bind."
    else
      cat >&2 <<EOF
ERROR: $socket_path is a directory and is not empty.

Inspect it before removing:
  ls -la "$socket_path"

Then remove it and restart the socket:
  rmdir "$socket_path"
  systemctl --user start podman.socket
EOF
      exit 1
    fi
  elif [ -e "$socket_path" ]; then
    echo "Found stale Podman socket path: $socket_path"
    rm -f "$socket_path"
    echo "  Removed stale file so podman.socket can bind."
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user reset-failed podman.socket podman.service >/dev/null 2>&1 || true
    systemctl --user start podman.socket >/dev/null 2>&1 || true
  fi

  if [ ! -S "$socket_path" ]; then
    cat >&2 <<EOF
ERROR: Podman API socket not found: $socket_path

Start it with:
  systemctl --user start podman.socket

If systemd reports "Address already in use", recover with:
  systemctl --user stop podman.socket podman.service
  rm -f "\$XDG_RUNTIME_DIR/podman/podman.sock"
  systemctl --user start podman.socket
EOF
    exit 1
  fi
}

wait_container_health() {
  local container="$1"
  local timeout_seconds="$2"
  local deadline=$((SECONDS + timeout_seconds))
  local status=""

  echo "Waiting for $container to become healthy..."
  while [ "$SECONDS" -lt "$deadline" ]; do
    status="$(podman inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container" 2>/dev/null || true)"
    if [ "$status" = "healthy" ] || { [ "$status" = "running" ] && [ "$container" = "siem-filebeat" ]; }; then
      echo "  $container is $status"
      return 0
    fi
    sleep 5
  done

  echo "ERROR: $container did not become healthy within ${timeout_seconds}s (last status: ${status:-unknown})" >&2
  podman logs --tail 120 "$container" >&2 || true
  exit 1
}

wait_es_green() {
  local timeout_seconds="$1"
  local deadline=$((SECONDS + timeout_seconds))

  echo "Waiting for Elasticsearch cluster green..."
  while [ "$SECONDS" -lt "$deadline" ]; do
    if podman exec siem-es01 curl -fsS \
      --cacert config/certs/ca/ca.crt \
      -u "elastic:${ELASTIC_PASSWORD}" \
      "https://localhost:9200/_cluster/health?wait_for_status=green&timeout=5s" \
      >/dev/null 2>&1; then
      echo "  Elasticsearch cluster is green"
      return 0
    fi
    sleep 5
  done

  echo "ERROR: Elasticsearch did not become green within ${timeout_seconds}s" >&2
  podman logs --tail 120 siem-es01 >&2 || true
  exit 1
}

compose() {
  "$PODMAN_COMPOSE_BIN" "${COMPOSE_FILES[@]}" "$@"
}

run_job() {
  local service="$1"
  echo "Running one-shot service: $service"
  compose run --rm --no-deps -T "$service"
}

up_services() {
  local fresh_services=()
  local existing_services=()
  local service=""
  local args=()

  for service in "$@"; do
    if podman inspect "$service" >/dev/null 2>&1; then
      existing_services+=("$service")
    else
      fresh_services+=("$service")
    fi
  done

  if [ "${#fresh_services[@]}" -gt 0 ]; then
    args=(up -d --no-deps)
    if [ "$BUILD" = true ]; then
      args+=(--build)
    fi
    echo "Starting services: ${fresh_services[*]}"
    compose "${args[@]}" "${fresh_services[@]}"
  fi

  if [ "${#existing_services[@]}" -gt 0 ]; then
    args=(up -d --no-deps)
    if [ "$BUILD" = true ]; then
      args+=(--build)
    fi
    if [ "$FORCE_RECREATE" = true ]; then
      args+=(--force-recreate)
    fi
    echo "Recreating services: ${existing_services[*]}"
    compose "${args[@]}" "${existing_services[@]}"
  fi
}

cd "$ROOT_DIR"

if ! command -v podman >/dev/null 2>&1; then
  echo "ERROR: podman is required" >&2
  exit 1
fi

PODMAN_COMPOSE_BIN="$(find_podman_compose || true)"
if [ -z "$PODMAN_COMPOSE_BIN" ]; then
  cat >&2 <<'EOF'
ERROR: podman-compose was not found.

Install it locally with:
  python3 -m venv .venv-tools/podman-compose
  .venv-tools/podman-compose/bin/pip install podman-compose

Then rerun this script.
EOF
  exit 1
fi

if [ -z "${XDG_RUNTIME_DIR:-}" ]; then
  echo "ERROR: XDG_RUNTIME_DIR must be set for rootless Podman" >&2
  exit 1
fi
ensure_podman_socket

load_env_file "$ENV_FILE"
if [ "$WITH_SENTINEL" = true ]; then
  load_env_file "$SENTINEL_ENV_FILE"
fi

: "${ELASTIC_PASSWORD:?ELASTIC_PASSWORD must be set in .env}"

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose-podman.yml)
if [ "$WITH_SENTINEL" = true ]; then
  COMPOSE_FILES+=(-f docker-compose-sentinel.yml -f docker-compose-sentinel-podman.yml)
fi

echo "Using podman-compose: $PODMAN_COMPOSE_BIN"
echo "Using compose files: ${COMPOSE_FILES[*]}"

run_job setup
up_services es01 es02 es03
wait_es_green 240

run_job cleanup-indices
run_job ilm-setup

up_services kibana
wait_container_health siem-kibana 240

up_services logstash
wait_container_health siem-logstash 180

up_services filebeat
wait_container_health siem-filebeat 60

run_job rules-import
run_job data-views-setup
run_job dashboards-import
run_job log-generator

if [ "$WITH_SENTINEL" = true ]; then
  up_services sentinel-forwarder
fi

echo "CloudSIEM Podman stack started successfully."
