from __future__ import annotations

import os

from fastapi import HTTPException, Request

DEFAULT_PILOT_ADMIN_HEADER = "x-pilot-admin-key"
DEFAULT_PILOT_ADMIN_API_KEY = "pilot-admin-local"


def pilot_admin_header_name() -> str:
    return (os.getenv("PILOT_ADMIN_HEADER_NAME") or DEFAULT_PILOT_ADMIN_HEADER).strip().lower()


def pilot_admin_api_key() -> str:
    return (os.getenv("PILOT_ADMIN_API_KEY") or DEFAULT_PILOT_ADMIN_API_KEY).strip()


def require_pilot_admin(request: Request) -> None:
    header_name = pilot_admin_header_name()
    expected_value = pilot_admin_api_key()
    provided_value = request.headers.get(header_name)
    if provided_value != expected_value:
        raise HTTPException(status_code=401, detail="unauthorized")
