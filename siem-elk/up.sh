#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

COMPOSE_CMD=()
COMPOSE_FILES=(-f docker-compose.yml)
if [[ -f docker-compose.linux.yml ]]; then
  COMPOSE_FILES+=(-f docker-compose.linux.yml)
fi
if command -v podman >/dev/null 2>&1 && podman info >/dev/null 2>&1; then
  if podman compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(podman compose)
  elif command -v podman-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(podman-compose)
  fi
  if [[ -f docker-compose.podman.yml ]]; then
    COMPOSE_FILES+=(-f docker-compose.podman.yml)
  fi
fi

if [[ ${#COMPOSE_CMD[@]} -eq 0 ]] && command -v docker >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
fi

if [[ ${#COMPOSE_CMD[@]} -eq 0 ]]; then
  printf '%s\n' "No Docker or Podman compose runtime found." >&2
  exit 1
fi

ACTION=up
if [[ ${1:-} == up || ${1:-} == down ]]; then
  ACTION="$1"
  shift
fi

ensure_podman_socket() {
  local socket_path="$1"

  if [[ -S "$socket_path" ]]; then
    return 0
  fi

  if command -v systemctl >/dev/null 2>&1; then
    systemctl --user start podman.socket >/dev/null 2>&1 || true
  fi

  for _ in 1 2 3 4 5; do
    if [[ -S "$socket_path" ]]; then
      return 0
    fi
    sleep 1
  done

  return 1
}

if [[ ${COMPOSE_CMD[0]} == podman* ]]; then
  HOST_SOCKET_PATH="${HOST_SOCKET_PATH:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/podman/podman.sock}"
  if ! ensure_podman_socket "$HOST_SOCKET_PATH"; then
    printf '%s\n' "Podman socket unavailable at $HOST_SOCKET_PATH. Start it with: systemctl --user start podman.socket" >&2
    exit 1
  fi
else
  HOST_SOCKET_PATH="${HOST_SOCKET_PATH:-/var/run/docker.sock}"
fi
export HOST_SOCKET_PATH

if [[ "$ACTION" == up ]]; then
  exec "${COMPOSE_CMD[@]}" "${COMPOSE_FILES[@]}" up --build "$@"
fi

exec "${COMPOSE_CMD[@]}" "${COMPOSE_FILES[@]}" down "$@"
