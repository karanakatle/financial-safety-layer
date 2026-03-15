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
        const val KEY_PERMISSION_ONBOARDING_DONE = "permission_onboarding_done"
        const val KEY_GUIDED_PERMISSION_FLOW_ACTIVE = "guided_permission_flow_active"
        const val KEY_MONITORING_ACTIVE = "monitoring_active"
        const val KEY_SETUP_VERIFICATION_SHOWN = "setup_verification_shown"
        const val KEY_PENDING_PERMISSION_SETTINGS_STEP = "pending_permission_settings_step"
        const val KEY_REOPEN_HELP_AFTER_LOCALE_SWITCH = "reopen_help_after_locale_switch"
        const val KEY_MANAGE_ACCESS_EXPANDED = "manage_access_expanded"
        const val KEY_DRAWER_OPEN = "drawer_open"
        const val KEY_RESTORE_DRAWER_ON_RETURN = "restore_drawer_on_return"

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
        const val ALERT_USE_FOCUSED_PAYMENT_ACTIONS = "extra_alert_use_focused_payment_actions"
        const val ALERT_OPEN_SUPPORT_PATH = "extra_alert_open_support_path"
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

        val MONEY_MARKERS = listOf("inr", "rs", "₹")
    }

    object LogTags {
        const val MAIN_ACTIVITY = "MainActivity"
        const val BANK_SMS_RECEIVER = "BankSmsReceiver"
        const val APP_USAGE_SERVICE = "AppUsageService"
        const val TXN_NOTIFICATION_LISTENER = "TxnNotifListener"
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
