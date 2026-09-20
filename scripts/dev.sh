#!/usr/bin/env bash
set -euo pipefail

api_port="${API_PORT:-8000}"
web_host="${WEB_HOST:-127.0.0.1}"
api_pid=""

cleanup() {
  if [[ -n "${api_pid}" ]] && kill -0 "${api_pid}" 2>/dev/null; then
    kill "${api_pid}" 2>/dev/null || true
    wait "${api_pid}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

uv run uvicorn apps.api.main:app --host 127.0.0.1 --port "${api_port}" &
api_pid=$!

echo "Waiting for API on http://127.0.0.1:${api_port} ..."
until curl --fail --silent "http://127.0.0.1:${api_port}/health" >/dev/null; do
  if ! kill -0 "${api_pid}" 2>/dev/null; then
    wait "${api_pid}"
    exit 1
  fi
  sleep 0.5
done

echo "API is ready. Starting Vite on http://${web_host}:5173 ..."
npm --prefix apps/web run dev -- --host "${web_host}"
