#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"

detect_lan_ip() {
  if command -v ipconfig >/dev/null 2>&1; then
    local en0_ip=""
    local en1_ip=""
    en0_ip="$(ipconfig getifaddr en0 2>/dev/null || true)"
    en1_ip="$(ipconfig getifaddr en1 2>/dev/null || true)"
    if [[ -n "$en0_ip" ]]; then
      echo "$en0_ip"
      return 0
    fi
    if [[ -n "$en1_ip" ]]; then
      echo "$en1_ip"
      return 0
    fi
  fi

  if command -v ifconfig >/dev/null 2>&1; then
    ifconfig | awk '/inet / {print $2}' | grep -v '^127\.' | head -n 1
    return 0
  fi

  return 1
}

LAN_IP="$(detect_lan_ip || true)"

if [[ -z "${LAN_IP:-}" ]]; then
  echo "Could not detect a LAN IP automatically."
  echo "Run: ifconfig | grep 'inet '"
  echo "Then open http://<your-lan-ip>:${PORT} from your phone."
else
  echo "LAN IP detected: ${LAN_IP}"
  echo "Open this URL from Android Chrome (same Wi-Fi):"
  echo "http://${LAN_IP}:${PORT}"
fi

echo
echo "Starting server on 0.0.0.0:${PORT} ..."
if [[ -x ".venv/bin/uvicorn" ]]; then
  exec .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
fi

if [[ -x ".venv/bin/python" ]]; then
  exec .venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
fi

if command -v uvicorn >/dev/null 2>&1; then
  exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
fi

if command -v python >/dev/null 2>&1; then
  exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}"
fi

echo "Could not find a Python runtime with uvicorn support in PATH."
exit 1
