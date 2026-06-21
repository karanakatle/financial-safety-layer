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
        "exact bank balance is not required",
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
        "android.permission.READ_SMS": ["read_sms", "incoming sms"],
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
