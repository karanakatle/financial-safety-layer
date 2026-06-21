from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def normalized_lower_text(relative_path: str) -> str:
    return re.sub(r"\s+", " ", read_text(relative_path).lower())


def test_privacy_policy_covers_sensitive_permissions_and_boundaries():
    policy = normalized_lower_text("frontend/privacy-policy.html")

    required_terms = [
        "sms data",
        "incoming sms may be locally scanned",
        "notification data",
        "non-messaging notification title/text",
        "usage access",
        "selected link-context app",
        "overlay",
        "post notifications",
        "foreground service",
        "boot",
        "local-first",
        "selected raw notification or payment-request text may be sent",
        "raw url",
        "otp",
        "upi pin",
        "aadhaar",
        "pan",
        "bank password",
        "card details",
        "exact bank balance is not required or stored",
        "we do not sell personal data",
        "https",
        "request deletion",
    ]

    missing = [term for term in required_terms if term not in policy]
    assert missing == []


def test_play_console_checklist_matches_manifest_permissions():
    checklist = read_text("ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md")
    manifest = read_text("ArthamantriAndroid/app/src/main/AndroidManifest.xml")
    checklist_lower = checklist.lower()

    manifest_permissions = set(re.findall(r'<uses-permission[^>]+android:name="([^"]+)"', manifest))
    sensitive_permission_docs = {
        "android.permission.RECEIVE_SMS": ["receive_sms", "incoming sms"],
        "android.permission.POST_NOTIFICATIONS": ["post_notifications", "fallback"],
        "android.permission.PACKAGE_USAGE_STATS": ["usage access", "selected link-context"],
        "android.permission.SYSTEM_ALERT_WINDOW": ["system_alert_window", "overlay"],
        "android.permission.FOREGROUND_SERVICE": ["foreground service"],
        "android.permission.FOREGROUND_SERVICE_DATA_SYNC": ["foreground service"],
        "android.permission.RECEIVE_BOOT_COMPLETED": ["receive_boot_completed", "reboot"],
    }
    sensitive_prefixes = (
        "android.permission.READ_",
        "android.permission.RECEIVE_",
        "android.permission.POST_",
        "android.permission.FOREGROUND_SERVICE",
        "android.permission.PACKAGE_USAGE_STATS",
        "android.permission.SYSTEM_ALERT_WINDOW",
    )
    sensitive_manifest_permissions = {
        permission
        for permission in manifest_permissions
        if any(permission.startswith(prefix) for prefix in sensitive_prefixes)
    }

    undocumented_permissions = sensitive_manifest_permissions - set(sensitive_permission_docs)
    assert undocumented_permissions == set()

    for permission, expected_terms in sensitive_permission_docs.items():
        assert permission in manifest_permissions
        for term in expected_terms:
            assert term in checklist_lower
    assert "android.permission.READ_SMS" not in manifest_permissions

    assert "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE" in manifest
    assert "notification listener service" in checklist_lower

    required_claims = [
        "data safety form draft",
        "incoming sms may be locally scanned",
        "sms sender ids",
        "notification title and text",
        "selected raw notification or payment-request text can be sent",
        "raw urls",
        "payee labels",
        "upi handles",
        "incidental personal data",
        "usage access is used to detect relevant upi/payment app opens and selected link-context app opens",
        "overlay is used for important safety warnings",
        "data is not sold",
        "support@finsaathi.app",
        "does not give loans",
        "sell investments",
        "replace banks",
    ]

    missing_claims = [claim for claim in required_claims if claim not in checklist_lower]
    assert missing_claims == []

    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", checklist_lower))
    positive_forbidden_raw_text_claims = [
        sentence
        for sentence in sentences
        if "raw text never leaves the device" in sentence
        and "avoid claiming" not in sentence
        and "do not claim" not in sentence
    ]
    assert positive_forbidden_raw_text_claims == []


def test_in_app_permission_copy_aligns_with_store_listing_claims():
    english_strings = read_text("ArthamantriAndroid/app/src/main/res/values/strings.xml")
    hindi_strings = read_text("ArthamantriAndroid/app/src/main/res/values-hi/strings.xml")
    checklist = read_text("ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md")

    for copy in (english_strings, hindi_strings):
        assert "OTP" in copy
        assert "UPI PIN" in copy
        assert "Aadhaar" in copy
        assert "PAN" in copy

    assert "financial SMS and notifications" in english_strings
    assert "selected payment-app/link moments" in english_strings
    assert "limited telemetry/feedback" in english_strings
    assert "Exact bank balance is optional only if you enter it yourself" in english_strings
    assert "SMS और सूचना" in hindi_strings
    assert "चुने हुए भुगतान-ऐप/लिंक क्षण" in hindi_strings
    assert "सीमित telemetry/feedback" in hindi_strings
    assert "stop-and-verify warnings for important safety moments" in checklist
    assert "Consent copy discloses limited telemetry/feedback" in checklist


def test_android_api_url_config_has_no_dead_render_fallback():
    build_gradle = read_text("ArthamantriAndroid/app/build.gradle.kts")
    gradle_properties = read_text("ArthamantriAndroid/gradle.properties")

    assert "https://arthamantri-api.onrender.com/" not in build_gradle
    assert "API_BASE_URL=https://arthamantri-api.onrender.com/" not in gradle_properties
    assert 'defaultDebugApiBaseUrl = "http://10.0.2.2:8765/"' in build_gradle
    assert "Release builds require an explicit API_BASE_URL" in build_gradle
    assert "API_BASE_URL must end with /" in build_gradle


def test_android_source_namespace_is_finsaathi():
    checked_roots = [
        ROOT / "ArthamantriAndroid/app/build.gradle.kts",
        ROOT / "ArthamantriAndroid/app/src/main/AndroidManifest.xml",
        ROOT / "ArthamantriAndroid/README.md",
        ROOT / "ArthamantriAndroid/PRODUCTION_SETUP.md",
    ]
    checked_roots.extend((ROOT / "ArthamantriAndroid/app/src/main/java").rglob("*.kt"))
    checked_roots.extend((ROOT / "ArthamantriAndroid/app/src/test/java").rglob("*.kt"))

    old_dot_namespace = "com." + "arthamantri.android"
    old_path_namespace = "com/" + "arthamantri/android"
    old_references = []
    for path in checked_roots:
        text = path.read_text(encoding="utf-8")
        if old_dot_namespace in text or old_path_namespace in text:
            old_references.append(str(path.relative_to(ROOT)))

    assert old_references == []

    build_gradle = read_text("ArthamantriAndroid/app/build.gradle.kts")
    assert 'namespace = "com.finsaathi.android"' in build_gradle
    assert 'applicationId = "com.finsaathi.android"' in build_gradle

    main_activity = read_text("ArthamantriAndroid/app/src/main/java/com/finsaathi/android/MainActivity.kt")
    assert main_activity.startswith("package com.finsaathi.android")


def test_backup_rules_do_not_reference_old_brand_pref_names():
    backup_rules = read_text("ArthamantriAndroid/app/src/main/res/xml/backup_rules.xml")
    data_extraction_rules = read_text("ArthamantriAndroid/app/src/main/res/xml/data_extraction_rules.xml")
    old_brand_config_prefs = "arthamantri" + "_android_prefs.xml"

    for text in (backup_rules, data_extraction_rules):
        assert old_brand_config_prefs not in text
        assert 'path="finsaathi_prefs.xml"' in text
        assert 'path="finsaathi_android_prefs.xml"' in text
