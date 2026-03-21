#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "${backend_pid:-}" ]]; then
    kill "${backend_pid}" 2>/dev/null || true
  fi

  if [[ -n "${frontend_pid:-}" ]]; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi

  wait 2>/dev/null || true
  exit "${exit_code}"
}

trap cleanup EXIT INT TERM

cd "${ROOT_DIR}"

python3 backend/manage.py runserver &
backend_pid=$!

(
  cd "${ROOT_DIR}/frontend"
  npm run dev -- --host 127.0.0.1
) &
frontend_pid=$!

while kill -0 "${backend_pid}" 2>/dev/null && kill -0 "${frontend_pid}" 2>/dev/null; do
  sleep 1
done
