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
        const val KEY_PERMISSION_ONBOARDING_DONE = "permission_onboarding_done"
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
    }

    object IntentExtras {
        const val ALERT_TITLE = "extra_title"
        const val ALERT_MESSAGE = "extra_message"
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

        const val PILOT_LOG_LEVEL_INFO = "info"
        const val NOTE_ANDROID_SMS_LISTENER = "Android SMS listener"
        const val NOTE_SMS_UNKNOWN_SENDER = "unknown"
        const val NOTE_SMS_PREFIX = "SMS from"
        const val NOTE_NOTIFICATION_PREFIX = "Notification from"
        const val UNKNOWN_PARTICIPANT_ID = "unknown_participant"
    }

    object Parsing {
        const val AMOUNT_REGEX_PATTERN = "(?:INR|Rs\\\\.?|₹)\\\\s*([0-9]+(?:\\\\.[0-9]{1,2})?)"
        const val NORMALIZE_WHITESPACE_REGEX = "\\\\s+"
        const val DEDUPE_PAYLOAD_MAX_LENGTH = 180

        val SMS_DEBIT_KEYWORDS = listOf(
            "debited", "debit", "spent", "withdrawn", "upi txn", "paid",
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
