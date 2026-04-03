package com.arthamantri.android.core

object AppConstants {
    object Locale {
        const val DEFAULT_LANGUAGE = "en"
        const val HINDI_LANGUAGE = "hi"
    }

    object Prefs {
        const val PILOT_PREFS = "pilot_prefs"
        const val KEY_APP_LANGUAGE = "app_lang"
        const val KEY_LANGUAGE_SELECTED = "language_selected"
        const val KEY_CONSENT_ACCEPTED = "consent_accepted"
        const val KEY_CONSENT_DEFERRED = "consent_deferred"
        const val KEY_MONEY_SETUP_DONE = "money_setup_done"
        const val KEY_MONEY_SETUP_SKIPPED = "money_setup_skipped"
        const val KEY_MONEY_SETUP_COHORT = "money_setup_cohort"
        const val KEY_MONEY_SETUP_GOALS = "money_setup_goals"
        const val KEY_MONEY_SETUP_BUCKET = "money_setup_bucket"
        const val KEY_MONEY_SETUP_SELECTION_SOURCE = "money_setup_selection_source"
        const val KEY_PERMISSION_ONBOARDING_DONE = "permission_onboarding_done"
        const val KEY_GUIDED_PERMISSION_FLOW_ACTIVE = "guided_permission_flow_active"
        const val KEY_MONITORING_ACTIVE = "monitoring_active"
        const val KEY_SETUP_VERIFICATION_SHOWN = "setup_verification_shown"
        const val KEY_PENDING_PERMISSION_SETTINGS_STEP = "pending_permission_settings_step"
        const val KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH = "reopen_help_after_locale_switch"
        const val KEY_MANAGE_ACCESS_EXPANDED = "manage_access_expanded"
        const val KEY_DRAWER_OPEN = "drawer_open"
        const val KEY_RESTORE_DRAWER_ON_RETURN = "restore_drawer_on_return"
        const val KEY_OFFLINE_TELEMETRY_QUEUE = "offline_telemetry_queue"
        const val KEY_PAYMENT_APP_SETUP_STATE = "payment_app_setup_state"
        const val KEY_PAYMENT_APP_SETUP_SOURCE_APP = "payment_app_setup_source_app"
        const val KEY_PAYMENT_APP_SETUP_UPDATED_AT_MS = "payment_app_setup_updated_at_ms"
        const val KEY_RECENT_LINK_URL = "recent_link_url"
        const val KEY_RECENT_LINK_SCHEME = "recent_link_scheme"
        const val KEY_RECENT_LINK_HOST = "recent_link_host"
        const val KEY_RECENT_LINK_RESOLVED_DOMAIN = "recent_link_resolved_domain"
        const val KEY_RECENT_LINK_SOURCE_APP = "recent_link_source_app"
        const val KEY_RECENT_LINK_CAPTURED_AT_MS = "recent_link_captured_at_ms"

        const val APP_CONFIG_PREFS = "arthamantri_android_prefs"
        const val KEY_BASE_URL = "base_url"
    }

    object RequestCodes {
        const val RUNTIME_PERMISSIONS = 1001
        const val POST_NOTIFICATIONS = 2001
    }

    object Notifications {
        const val SAFETY_CHANNEL_ID = "arthamantri_safety_alerts"
        const val FOREGROUND_SERVICE_ID = 3201
        const val FULL_SCREEN_INTENT_ID = 4201
    }

    object Timing {
        const val MONITOR_LOOP_DELAY_MS = 3000L
        const val FOREGROUND_QUERY_WINDOW_MS = 15_000L
        const val UPI_SIGNAL_DEBOUNCE_MS = 60_000L
        const val NOTIFICATION_DEDUPE_WINDOW_MS = 15_000L
        const val PAYMENT_DECISION_PAUSE_SECONDS = 3
        const val OFFLINE_QUEUE_MAX_ITEMS = 30
        const val RECENT_LINK_CONTEXT_WINDOW_MS = 10 * 60 * 1000L
    }

    object IntentExtras {
        const val ALERT_TITLE = "extra_title"
        const val ALERT_MESSAGE = "extra_message"
        const val ALERT_ID = "extra_alert_id"
        const val ALERT_PAUSE_SECONDS = "extra_alert_pause_seconds"
        const val ALERT_SEVERITY = "extra_alert_severity"
        const val ALERT_WHY_THIS_ALERT = "extra_alert_why_this_alert"
        const val ALERT_NEXT_SAFE_ACTION = "extra_next_safe_action"
        const val ALERT_ESSENTIAL_GOAL_IMPACT = "extra_essential_goal_impact"
        const val ALERT_PRIMARY_ACTION_LABEL = "extra_alert_primary_action_label"
        const val ALERT_FOCUSED_ACTION_LABELS = "extra_alert_focused_action_labels"
        const val ALERT_PROCEED_CONFIRMATION_LABEL = "extra_alert_proceed_confirmation_label"
        const val ALERT_USE_FOCUSED_PAYMENT_ACTIONS = "extra_alert_use_focused_payment_actions"
        const val ALERT_FAMILY = "extra_alert_family"
        const val ALERT_SHOW_USEFULNESS_FEEDBACK = "extra_alert_show_usefulness_feedback"
        const val ALERT_OPEN_SUPPORT_PATH = "extra_alert_open_support_path"
        const val INBOUND_LINK_CAPTURED = "extra_inbound_link_captured"
    }

    object NotificationExtras {
        const val TITLE = "android.title"
        const val TEXT = "android.text"
        const val BIG_TEXT = "android.bigText"
    }

    object SecureSettings {
        const val ENABLED_NOTIFICATION_LISTENERS = "enabled_notification_listeners"
    }

    object Domain {
        const val CATEGORY_BANK_SMS = "bank_sms"
        const val CATEGORY_UPI = "upi"
        const val CATEGORY_CARD = "card"
        const val CATEGORY_ATM = "atm"
        const val SMS_SIGNAL_EXPENSE = "expense"
        const val SMS_SIGNAL_INCOME = "income"
        const val SMS_SIGNAL_PARTIAL = "partial"
        const val SMS_SIGNAL_CONFIRMED = "confirmed"
        const val SMS_SIGNAL_PARTIAL_CONFIDENCE = "partial"

        const val PILOT_LOG_LEVEL_INFO = "info"
        const val NOTE_ANDROID_SMS_LISTENER = "Android SMS listener"
        const val NOTE_SMS_UNKNOWN_SENDER = "unknown"
        const val NOTE_SMS_PREFIX = "SMS from"
        const val NOTE_NOTIFICATION_PREFIX = "Notification from"
        const val UNKNOWN_PARTICIPANT_ID = "unknown_participant"
        const val ALERT_ACTION_USEFUL = "useful"
        const val ALERT_ACTION_NOT_USEFUL = "not_useful"
        const val ALERT_ACTION_DISMISSED = "dismissed"
        const val ALERT_ACTION_PAUSE = "pause"
        const val ALERT_ACTION_DECLINE = "decline"
        const val ALERT_ACTION_PROCEED = "proceed"
        const val ALERT_ACTION_BACKED_OUT = "backed_out"
        const val ALERT_ACTION_BACKGROUNDED = "backgrounded"
        const val ALERT_ACTION_REPLACED = "replaced"
        const val ALERT_ACTION_TRUSTED_PERSON_REQUESTED = "trusted_person_requested"
        const val ALERT_ACTION_TRUSTED_PERSON_LAUNCHED = "trusted_person_launched"
        const val ALERT_ACTION_TRUSTED_PERSON_FAILED = "trusted_person_failed"
        const val ALERT_ACTION_SUPPORT_REQUESTED = "support_requested"
        const val ALERT_ACTION_SUPPORT_OPENED = "support_opened"
        const val ALERT_ACTION_SUPPORT_FAILED = "support_failed"
        const val APP_LOG_LEVEL_WARN = "warn"
        const val OFFLINE_QUEUE_KIND_ALERT_FEEDBACK = "alert_feedback"
        const val OFFLINE_QUEUE_KIND_APP_LOG = "app_log"
        const val ALERT_FAMILY_PAYMENT = "payment"
        const val ALERT_FAMILY_ACCOUNT_ACCESS = "account_access"
        const val ALERT_FAMILY_CASHFLOW = "cashflow"
        const val LOCAL_FALLBACK_ALERT_PREFIX = "local-cashflow-fallback"
        const val LOCAL_PAYMENT_FALLBACK_ALERT_PREFIX = "local-payment-fallback"
    }

    object ContextEvents {
        const val EVENT_NOTIFICATION_OBSERVED = "notification_observed"
        const val EVENT_SMS_OBSERVED = "sms_observed"
        const val EVENT_APP_OPEN = "app_open"
        const val EVENT_PAYMENT_CANDIDATE = "payment_candidate"
        const val EVENT_ACCOUNT_ACCESS_CANDIDATE = "account_access_candidate"
        const val EVENT_SETUP_STATE_TRANSITION = "setup_state_transition"
        const val EVENT_LINK_CLICK = "link_click"
        const val EVENT_ALERT_ACTION = "alert_action"

        const val CLASSIFICATION_OBSERVED = "observed"
        const val CLASSIFICATION_SUPPRESSED = "suppressed"
        const val CLASSIFICATION_PAYMENT_CANDIDATE = "payment_candidate"
        const val CLASSIFICATION_ACCOUNT_ACCESS_CANDIDATE = "account_access_candidate"

        const val SETUP_STATE_UNKNOWN = "unknown"
    }

    object PaymentInspection {
        const val SOURCE_FOREGROUND_APP = "foreground_app"
        const val SOURCE_NOTIFICATION = "notification"

        const val REQUEST_KIND_UNKNOWN = "unknown_request"
        const val REQUEST_KIND_COLLECT = "collect_request"
        const val REQUEST_KIND_REFUND = "refund_request"
        const val REQUEST_KIND_SEND = "send_money"

        val NOTIFICATION_REQUEST_KEYWORDS = listOf(
            "collect",
            "request money",
            "payment request",
            "approve request",
            "upi request",
            "mandate",
            "autopay",
            "collect request",
        )

        val NOTIFICATION_REFUND_KEYWORDS = listOf(
            "refund",
            "cashback",
            "claim refund",
            "receive refund",
        )
    }

    object Parsing {
        val AMOUNT_REGEX_PATTERNS = listOf(
            // Prefix currency marker: "INR 1,100", "Rs. 1100", "₹1100.50"
            "(?:INR|Rs\\.?|₹)\\s*[:\\-]?\\s*([0-9][0-9,]*(?:\\.[0-9]{1,2})?)",
            // Suffix currency marker: "1100 INR"
            "([0-9][0-9,]*(?:\\.[0-9]{1,2})?)\\s*(?:INR|Rs\\.?|₹)",
            // Verb-led form: "debited by 1100", "spent for Rs 250"
            "(?:debited|debit|spent|paid|withdrawn)\\s*(?:by|for)?\\s*(?:INR|Rs\\.?|₹)?\\s*([0-9][0-9,]*(?:\\.[0-9]{1,2})?)",
        )
        const val NORMALIZE_WHITESPACE_REGEX = "\\s+"
        const val DEDUPE_PAYLOAD_MAX_LENGTH = 180

        val SMS_DEBIT_KEYWORDS = listOf(
            "debited", "debit", "spent", "withdrawn", "upi txn", "paid", "purchase", "dr",
        )

        val SMS_CREDIT_KEYWORDS = listOf(
            "credited", "credit", "received", "deposited", "salary", "refund", "cashback", "reversal", "cr",
        )

        val SMS_FINANCIAL_KEYWORDS = listOf(
            "debited", "debit", "spent", "withdrawn", "credited", "credit", "received", "deposited",
            "salary", "refund", "cashback", "reversal", "upi", "account", "a/c", "txn", "transaction",
            "imps", "neft", "rtgs", "payment", "transfer",
        )

        val NOTIFICATION_TXN_KEYWORDS = listOf(
            "debited", "debit", "spent", "upi", "paid", "withdrawn", "transaction",
        )

        val MESSAGING_APP_PACKAGES = setOf(
            "com.google.android.apps.messaging",
            "com.android.mms",
            "com.samsung.android.messaging",
        )

        val SMS_DEBIT_CONFIRMATION_MARKERS = listOf(
            "via upi", "from a/c", "from ac", "from account", "account ending", "card ending",
            "atm", "imps", "neft", "rtgs", "avl bal", "available bal", "utr", "txn id", "ref no",
        )

        val SMS_CREDIT_CONFIRMATION_MARKERS = listOf(
            "to a/c", "to ac", "to your account", "credited to a/c", "credited to your account",
            "deposited in a/c", "deposited in your account", "salary", "refund", "reversal",
            "imps", "neft", "rtgs", "utr", "txn id", "ref no",
        )

        val SMS_NON_CASH_PROMOTIONAL_KEYWORDS = listOf(
            "wallet", "voucher", "gift voucher", "gift card", "store credit", "coupon",
            "promo", "promotional", "offer", "reward points", "loyalty", "pay balance",
        )

        val SMS_ADVISORY_DISCLAIMER_KEYWORDS = listOf(
            "can be avoided", "avoid this", "save more", "click here", "apply now",
            "know more", "learn more", "offer ends", "limited time",
        )

        val MONEY_MARKERS = listOf("inr", "rs", "₹")
    }

    object LogTags {
        const val MAIN_ACTIVITY = "MainActivity"
        const val BANK_SMS_RECEIVER = "BankSmsReceiver"
        const val APP_USAGE_SERVICE = "AppUsageService"
        const val TXN_NOTIFICATION_LISTENER = "TxnNotifListener"
        const val DEBUG_OBSERVABILITY = "DebugObservability"
    }

    object LogMessages {
        const val APP_USAGE_MONITOR_LOOP_ERROR = "Error in monitor loop"
        const val APP_USAGE_NOTIFY_UPI_FAILED = "Failed to notify UPI open"
        const val BANK_SMS_PROCESS_FAILED = "Failed to process SMS"
        const val TXN_NOTIFICATION_PROCESS_FAILED = "Failed to process notification"
    }

    object UiDefaults {
        const val FEEDBACK_DEFAULT_RATING = 4
    }
}
