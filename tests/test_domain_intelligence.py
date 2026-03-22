from backend.literacy.domain_intelligence import classify_domain, enrich_domain_context, load_official_domains


def test_classify_domain_supports_expected_classes():
    assert classify_domain(link_scheme="upi", url_host="pay", resolved_domain="pay") == "payment_link"
    assert classify_domain(url_host="secure.icicibank.com", resolved_domain="icicibank.com") == "official"
    assert classify_domain(url_host="offers-fastloan.example", resolved_domain="offers-fastloan.example") == "loan"
    assert classify_domain(url_host="secure-card-verify.example", resolved_domain="secure-card-verify.example") == "card"
    assert classify_domain(url_host="m.axisbank.example", resolved_domain="axisbank.example") == "bank"
    assert classify_domain(url_host="tinyurl.com", resolved_domain="tinyurl.com") == "suspicious"
    assert classify_domain(url_host="community.example", resolved_domain="community.example") == "unknown"


def test_enrich_domain_context_parses_raw_url_when_host_is_missing():
    context = enrich_domain_context(raw_url="https://secure.icicibank.com/login")
    assert context.link_scheme == "https"
    assert context.url_host == "secure.icicibank.com"
    assert context.resolved_domain == "icicibank.com"
    assert context.domain_class == "official"


def test_classify_domain_can_load_extra_official_domains_from_config_env(monkeypatch):
    monkeypatch.setenv("ARTHAMANTRI_OFFICIAL_DOMAINS", "grameenbank.co.in")
    load_official_domains.cache_clear()
    try:
        assert classify_domain(
            url_host="secure.grameenbank.co.in",
            resolved_domain="grameenbank.co.in",
        ) == "official"
    finally:
        load_official_domains.cache_clear()
