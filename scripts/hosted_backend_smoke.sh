#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-}}"
PILOT_ADMIN_KEY="${PILOT_ADMIN_KEY:-}"

if [[ -z "$BASE_URL" ]]; then
  echo "Usage: BASE_URL=https://your-backend.example.com PILOT_ADMIN_KEY=... scripts/hosted_backend_smoke.sh"
  echo "   or: PILOT_ADMIN_KEY=... scripts/hosted_backend_smoke.sh https://your-backend.example.com"
  exit 2
fi

BASE_URL="${BASE_URL%/}"

echo "[1/5] Public health"
curl -fsS "$BASE_URL/api/health" | python -m json.tool

echo "[2/5] Pilot meta"
curl -fsS "$BASE_URL/api/pilot/meta?language=en" | python -m json.tool

echo "[3/5] Literacy status"
curl -fsS "$BASE_URL/api/literacy/status?participant_id=hosted_sit_smoke" | python -m json.tool

echo "[4/5] SMS ingest contract"
curl -fsS -X POST "$BASE_URL/api/literacy/sms-ingest" \
  -H 'Content-Type: application/json' \
  -d '{"participant_id":"hosted_sit_smoke","message":"Pay Rs 499 registration fee to earn Rs 30000 monthly. Click http://fake-example.test now.","source":"sms","timestamp":"2026-06-22T00:00:00Z"}' \
  | python -m json.tool

echo "[5/5] Storage health"
if [[ -z "$PILOT_ADMIN_KEY" ]]; then
  echo "Skipped storage health because PILOT_ADMIN_KEY is not set."
  echo "Set PILOT_ADMIN_KEY to verify durable DB path before SIT/UAT."
else
  curl -fsS "$BASE_URL/api/literacy/storage-health" \
    -H "x-pilot-admin-key: $PILOT_ADMIN_KEY" \
    | python -m json.tool
fi

echo "Hosted backend smoke complete."
