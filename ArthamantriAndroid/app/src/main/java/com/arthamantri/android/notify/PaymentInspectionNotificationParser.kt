package com.arthamantri.android.notify

import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.sms.SmsParser

data class PaymentInspectionNotificationSignal(
    val appName: String,
    val requestKind: String,
    val amount: Double?,
    val payeeLabel: String,
    val payeeHandle: String,
    val rawText: String,
    val source: String = AppConstants.PaymentInspection.SOURCE_NOTIFICATION,
)

object PaymentInspectionNotificationParser {
    private val payeeHandleRegex = Regex("""([A-Za-z0-9.\-_]{2,})@([A-Za-z]{2,})""")
    private val labelPrefixRegex = Regex(
        """(?:from|to|by|for)\s+([A-Za-z][A-Za-z0-9 .&\-_]{2,40})""",
        RegexOption.IGNORE_CASE,
    )

    fun parse(
        packageName: String,
        appName: String,
        title: String,
        text: String,
        bigText: String,
        isUpiPackage: Boolean,
    ): PaymentInspectionNotificationSignal? {
        val rawText = listOf(title, text, bigText)
            .filter { it.isNotBlank() }
            .joinToString(" ")
            .replace(Regex(AppConstants.Parsing.NORMALIZE_WHITESPACE_REGEX), " ")
            .trim()

        if (rawText.isBlank()) {
            return null
        }

        val lower = rawText.lowercase()
        val looksRelevant = isUpiPackage ||
            AppConstants.PaymentInspection.NOTIFICATION_REQUEST_KEYWORDS.any { lower.contains(it) } ||
            AppConstants.PaymentInspection.NOTIFICATION_REFUND_KEYWORDS.any { lower.contains(it) }
        if (!looksRelevant) {
            return null
        }

        val requestKind = when {
            AppConstants.PaymentInspection.NOTIFICATION_REFUND_KEYWORDS.any { lower.contains(it) } ->
                AppConstants.PaymentInspection.REQUEST_KIND_REFUND
            AppConstants.PaymentInspection.NOTIFICATION_REQUEST_KEYWORDS.any { lower.contains(it) } ->
                AppConstants.PaymentInspection.REQUEST_KIND_COLLECT
            lower.contains("send money") || lower.contains("pay ") ->
                AppConstants.PaymentInspection.REQUEST_KIND_SEND
            else -> AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN
        }

        val handleMatch = payeeHandleRegex.find(rawText)
        val payeeHandle = handleMatch?.value.orEmpty()
        val payeeLabel = when {
            title.isNotBlank() && title.lowercase() != packageName.lowercase() -> title.trim()
            handleMatch != null -> handleMatch.groupValues.getOrNull(1).orEmpty()
            else -> labelPrefixRegex.find(rawText)?.groupValues?.getOrNull(1)?.trim().orEmpty()
        }

        return PaymentInspectionNotificationSignal(
            appName = appName,
            requestKind = requestKind,
            amount = SmsParser.extractAmountValue(rawText),
            payeeLabel = payeeLabel,
            payeeHandle = payeeHandle,
            rawText = rawText,
        )
    }
}
