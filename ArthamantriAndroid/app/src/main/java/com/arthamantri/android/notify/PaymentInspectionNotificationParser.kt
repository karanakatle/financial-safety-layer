package com.arthamantri.android.notify

import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.StructuredMessageSignalExtractor
import com.arthamantri.android.sms.SmsParser
import com.arthamantri.android.usage.PaymentAppSetupState
import com.arthamantri.android.usage.isActiveOnboardingState

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
    private val upiDeepLinkRegex = Regex("""upi://pay\b""", RegexOption.IGNORE_CASE)
    private val sendMoneyKeywords = listOf(
        "send money",
        "approve payment",
        "payment request",
        "pay to",
        "payment to",
        "scan and pay",
    )
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
        setupState: PaymentAppSetupState = PaymentAppSetupState.IDLE,
    ): PaymentInspectionNotificationSignal? {
        val rawText = listOf(title, text, bigText)
            .filter { it.isNotBlank() }
            .joinToString(" ")
            .replace(Regex(AppConstants.Parsing.NORMALIZE_WHITESPACE_REGEX), " ")
            .trim()

        if (rawText.isBlank()) {
            return null
        }

        val signals = StructuredMessageSignalExtractor.extract(rawText)
        if (
            signals.isCallMetadata ||
            signals.isSetupOrRegistration ||
            signals.isOtpVerification ||
            signals.isReceiveOnly ||
            signals.isPostTransactionConfirmation ||
            signals.isStatementOrReport ||
            signals.isEmiStatus ||
            signals.isPortfolioInfo ||
            signals.isMarketingOrProductStatus ||
            signals.isSensitiveAccessSignal
        ) {
            return null
        }

        val lower = signals.normalizedText
        val hasCollectKeyword = AppConstants.PaymentInspection.NOTIFICATION_REQUEST_KEYWORDS.any { lower.contains(it) }
        val hasRefundKeyword = AppConstants.PaymentInspection.NOTIFICATION_REFUND_KEYWORDS.any { lower.contains(it) }
        val hasSendKeyword = sendMoneyKeywords.any { lower.contains(it) }
        val hasUpiHandle = payeeHandleRegex.containsMatchIn(rawText)
        val hasUpiDeepLink = upiDeepLinkRegex.containsMatchIn(rawText)
        val hasStrongPaymentSignal = hasCollectKeyword || hasRefundKeyword || hasSendKeyword || hasUpiHandle || hasUpiDeepLink
        val hasExplicitPaymentSignal = hasCollectKeyword || hasRefundKeyword || hasSendKeyword || hasUpiDeepLink
        if (!hasStrongPaymentSignal) {
            return null
        }
        if (setupState.isActiveOnboardingState() && !hasExplicitPaymentSignal) {
            return null
        }

        val requestKind = when {
            hasRefundKeyword ->
                AppConstants.PaymentInspection.REQUEST_KIND_REFUND
            hasCollectKeyword ->
                AppConstants.PaymentInspection.REQUEST_KIND_COLLECT
            hasSendKeyword || hasUpiDeepLink ->
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
