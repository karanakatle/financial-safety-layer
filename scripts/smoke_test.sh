#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "[1/5] Health"
curl -fsS "$BASE_URL/api/health" | python -m json.tool

echo "[2/5] Initial state"
curl -fsS "$BASE_URL/api/state" | python -m json.tool

echo "[3/5] Post expense transaction"
curl -fsS -X POST "$BASE_URL/api/transaction" \
  -H 'Content-Type: application/json' \
  -d '{"type":"expense","amount":200,"category":"food","note":"lunch"}' | python -m json.tool

echo "[4/5] Voice query"
curl -fsS -X POST "$BASE_URL/api/voice-query" \
  -H 'Content-Type: application/json' \
  -d '{"query":"Kitna paisa bacha hai?"}' | python -m json.tool

echo "[5/5] Alerts"
curl -fsS "$BASE_URL/api/alerts" | python -m json.tool

echo "Smoke test complete."
