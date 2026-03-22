from __future__ import annotations

import ipaddress
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class DomainContext:
    link_scheme: str | None = None
    url_host: str | None = None
    resolved_domain: str | None = None
    domain_class: str | None = None


_BANK_MARKERS = ("bank", "banking", "ifsc", "sbi", "icici", "hdfc", "axis", "kotak", "yesbank", "federal")
_CARD_MARKERS = ("card", "cards", "creditcard", "debitcard", "rupay", "visa", "mastercard", "amex")
_LOAN_MARKERS = ("loan", "loans", "credit", "lending", "emi", "borrow", "finance")
_PAYMENT_MARKERS = ("pay", "payment", "collect", "upi", "merchant", "gateway", "checkout")
_SUSPICIOUS_DOMAINS = {"bit.ly", "tinyurl.com", "goo.gl", "is.gd", "cutt.ly", "lnk.to"}
_SUSPICIOUS_TLDS = (".top", ".xyz", ".click", ".support", ".live", ".work", ".zip", ".mov")
_SECOND_LEVEL_SUFFIXES = ("co.in", "co.uk", "com.au", "com.br", "com.sg", "co.za")
_DEFAULT_OFFICIAL_DOMAINS_PATH = Path(__file__).with_name("official_domains.json")


def enrich_domain_context(
    *,
    link_scheme: str | None = None,
    url_host: str | None = None,
    resolved_domain: str | None = None,
    raw_url: str | None = None,
    domain_class: str | None = None,
) -> DomainContext:
    scheme = _normalize_scheme(link_scheme)
    host = normalize_host(url_host)

    if (scheme is None or host is None) and raw_url:
        parsed = urlparse(raw_url)
        scheme = scheme or _normalize_scheme(parsed.scheme)
        host = host or normalize_host(parsed.hostname or ("pay" if parsed.scheme.lower() == "upi" else None))

    resolved = normalize_host(resolved_domain) or resolve_domain(host)
    classified = (domain_class or "").strip().lower() or classify_domain(
        link_scheme=scheme,
        url_host=host,
        resolved_domain=resolved,
    )
    return DomainContext(
        link_scheme=scheme,
        url_host=host,
        resolved_domain=resolved,
        domain_class=classified,
    )


def classify_domain(*, link_scheme: str | None = None, url_host: str | None = None, resolved_domain: str | None = None) -> str | None:
    scheme = _normalize_scheme(link_scheme)
    host = normalize_host(url_host)
    resolved = normalize_host(resolved_domain) or resolve_domain(host)

    if scheme is None and host is None and resolved is None:
        return None
    if scheme == "upi":
        return "payment_link"
    if _is_suspicious_host(host) or _is_suspicious_host(resolved):
        return "suspicious"
    official_domains = load_official_domains()
    if resolved in official_domains or host in official_domains:
        return "official"
    if _contains_marker(host, _CARD_MARKERS) or _contains_marker(resolved, _CARD_MARKERS):
        return "card"
    if _contains_marker(host, _LOAN_MARKERS) or _contains_marker(resolved, _LOAN_MARKERS):
        return "loan"
    if _contains_marker(host, _BANK_MARKERS) or _contains_marker(resolved, _BANK_MARKERS):
        return "bank"
    if _contains_marker(host, _PAYMENT_MARKERS) or _contains_marker(resolved, _PAYMENT_MARKERS):
        return "payment_link"
    return "unknown"


def normalize_host(value: str | None) -> str | None:
    normalized = (value or "").strip().strip(".").lower().removeprefix("www.")
    return normalized or None


def resolve_domain(host: str | None) -> str | None:
    normalized = normalize_host(host)
    if not normalized:
        return None
    labels = [label for label in normalized.split(".") if label]
    if len(labels) <= 2:
        return normalized
    if any(normalized.endswith(f".{suffix}") for suffix in _SECOND_LEVEL_SUFFIXES) and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def is_high_risk_domain_class(domain_class: str | None) -> bool:
    return (domain_class or "").strip().lower() in {"suspicious", "loan", "card"}


@lru_cache(maxsize=1)
def load_official_domains() -> set[str]:
    configured: set[str] = set()
    if _DEFAULT_OFFICIAL_DOMAINS_PATH.exists():
        loaded = json.loads(_DEFAULT_OFFICIAL_DOMAINS_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            configured.update(normalize_host(item) for item in loaded if normalize_host(item))

    extra_domains = os.getenv("ARTHAMANTRI_OFFICIAL_DOMAINS", "")
    if extra_domains.strip():
        configured.update(
            normalize_host(item)
            for item in extra_domains.split(",")
            if normalize_host(item)
        )
    return {item for item in configured if item}


def _normalize_scheme(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def _contains_marker(value: str | None, markers: tuple[str, ...]) -> bool:
    normalized = normalize_host(value) or ""
    return any(marker in normalized for marker in markers)


def _is_suspicious_host(value: str | None) -> bool:
    normalized = normalize_host(value)
    if not normalized:
        return False
    if normalized in _SUSPICIOUS_DOMAINS:
        return True
    if normalized.startswith("xn--"):
        return True
    if any(normalized.endswith(tld) for tld in _SUSPICIOUS_TLDS):
        return True
    try:
        ipaddress.ip_address(normalized)
        return True
    except ValueError:
        return False
