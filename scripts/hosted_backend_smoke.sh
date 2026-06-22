#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-}}"
PILOT_ADMIN_KEY="${PILOT_ADMIN_KEY:-}"
EXPECTED_DB_PATH_PREFIX="${EXPECTED_DB_PATH_PREFIX:-/var/data}"

if [[ -z "$BASE_URL" ]]; then
  echo "Usage: BASE_URL=https://your-backend.example.com PILOT_ADMIN_KEY=... scripts/hosted_backend_smoke.sh"
  echo "   or: PILOT_ADMIN_KEY=... scripts/hosted_backend_smoke.sh https://your-backend.example.com"
  exit 2
fi

if [[ -z "$PILOT_ADMIN_KEY" ]]; then
  echo "PILOT_ADMIN_KEY is required for hosted SIT smoke."
  echo "Storage health must be verified before SIT/UAT so ephemeral storage cannot slip through."
  exit 2
fi

BASE_URL="${BASE_URL%/}"
SMOKE_PARTICIPANT_ID="hosted_sit_smoke_$(date -u +%s)"
SMOKE_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
SMS_RESPONSE="$(mktemp)"
STORAGE_RESPONSE="$(mktemp)"
trap 'rm -f "$SMS_RESPONSE" "$STORAGE_RESPONSE"' EXIT

echo "[1/5] Public health"
curl -fsS "$BASE_URL/api/health" | python -m json.tool

echo "[2/5] Pilot meta"
curl -fsS "$BASE_URL/api/pilot/meta?language=en" | python -m json.tool

echo "[3/5] Literacy status"
curl -fsS "$BASE_URL/api/literacy/status?participant_id=hosted_sit_smoke" | python -m json.tool

echo "[4/5] SMS ingest contract"
curl -fsS -X POST "$BASE_URL/api/literacy/sms-ingest" \
  -H 'Content-Type: application/json' \
  -d "{\"participant_id\":\"$SMOKE_PARTICIPANT_ID\",\"language\":\"en\",\"signal_type\":\"expense\",\"signal_confidence\":\"confirmed\",\"amount\":6000,\"category\":\"upi\",\"note\":\"registration fee payment requested for earn 30000 monthly offer\",\"timestamp\":\"$SMOKE_TIMESTAMP\"}" \
  -o "$SMS_RESPONSE"
python -m json.tool "$SMS_RESPONSE"
python - "$SMS_RESPONSE" <<'PY'
import json
import sys

path = sys.argv[1]
payload = json.load(open(path, encoding="utf-8"))
alerts = payload.get("literacy_alerts") or []
if not alerts:
    raise SystemExit("Expected at least one literacy alert from contract-valid risky SMS smoke payload.")

alert = alerts[0]
required_fields = ["risk_level", "severity", "why_this_alert", "next_best_action"]
missing = [field for field in required_fields if not alert.get(field)]
if missing:
    raise SystemExit(f"SMS alert is missing expected guidance fields: {', '.join(missing)}")

if payload.get("deduplicated") is not False:
    raise SystemExit("Expected fresh smoke participant to produce deduplicated=false.")

print("SMS ingest assertion passed.")
PY

echo "[5/5] Storage health"
curl -fsS "$BASE_URL/api/literacy/storage-health" \
  -H "x-pilot-admin-key: $PILOT_ADMIN_KEY" \
  -o "$STORAGE_RESPONSE"
python -m json.tool "$STORAGE_RESPONSE"
python - "$STORAGE_RESPONSE" "$EXPECTED_DB_PATH_PREFIX" <<'PY'
import json
import os
import sys

path = sys.argv[1]
expected_prefix = sys.argv[2]
payload = json.load(open(path, encoding="utf-8"))
db_path = str(payload.get("db_path") or "")
real_db_path = os.path.realpath(db_path)
real_expected_prefix = os.path.realpath(expected_prefix)

if payload.get("ok") is not True:
    raise SystemExit("Storage health did not return ok=true.")
if payload.get("db_exists") is not True:
    raise SystemExit("Storage health did not confirm db_exists=true.")
if expected_prefix and not real_db_path.startswith(real_expected_prefix.rstrip("/") + "/"):
    raise SystemExit(
        f"Storage DB path must start with durable prefix {expected_prefix!r}; got {db_path!r}."
    )

print("Storage health assertion passed.")
PY

echo "Hosted backend smoke complete."
