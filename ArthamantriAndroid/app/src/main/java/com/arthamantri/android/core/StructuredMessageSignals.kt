package com.arthamantri.android.core

data class StructuredMessageSignals(
    val normalizedText: String,
    val hasOtpCode: Boolean,
    val hasUpiHandle: Boolean,
    val hasUpiDeepLink: Boolean,
    val hasUrl: Boolean,
    val isCallMetadata: Boolean,
    val isSetupOrRegistration: Boolean,
    val isOtpVerification: Boolean,
    val isReceiveOnly: Boolean,
    val isPostTransactionConfirmation: Boolean,
    val isStatementOrReport: Boolean,
    val isEmiStatus: Boolean,
    val isPortfolioInfo: Boolean,
    val isMarketingOrProductStatus: Boolean,
    val isSensitiveAccessSignal: Boolean,
    val hasStrongPaymentSignal: Boolean,
)

object StructuredMessageSignalExtractor {
    private val otpCodeRegex = Regex("""\b\d{4,8}\b""")
    private val upiHandleRegex = Regex("""\b[a-z0-9.\-_]{2,}@[a-z]{2,}\b""", RegexOption.IGNORE_CASE)
    private val upiDeepLinkRegex = Regex("""upi://pay\b""", RegexOption.IGNORE_CASE)
    private val urlRegex = Regex("""https?://\S+""", RegexOption.IGNORE_CASE)
    private val messageBundleRegex = Regex("""\b\d+\s+messages?\s+from\s+\d+\s+chats?\b""", RegexOption.IGNORE_CASE)

    fun extract(text: String): StructuredMessageSignals {
        val normalized = normalize(text)
        val hasOtpCode = otpCodeRegex.containsMatchIn(text)
        val hasUpiHandle = upiHandleRegex.containsMatchIn(text)
        val hasUpiDeepLink = upiDeepLinkRegex.containsMatchIn(text)
        val hasUrl = urlRegex.containsMatchIn(text)
        val isCallMetadata = hasPhrase(normalized, "missed call") ||
            hasPhrase(normalized, "voice call") ||
            hasPhrase(normalized, "available for calls") ||
            messageBundleRegex.containsMatchIn(normalized)
        val isSetupOrRegistration = (
            hasAnyWord(normalized, "register", "registered", "registration", "verify", "verified", "verification") &&
                hasAnyWord(normalized, "device", "mobile", "phone", "account")
            ) ||
            hasAllWords(normalized, "set", "upi", "pin") ||
            hasAllWords(normalized, "link", "bank", "account") ||
            hasAllWords(normalized, "bank", "account", "fetch") ||
            hasAllWords(normalized, "current", "device")
        val isOtpVerification = hasOtpCode &&
            (
                hasWord(normalized, "otp") ||
                    hasAllWords(normalized, "verification", "code") ||
                    hasPhrase(normalized, "one time password")
                )
        val hasCollectSignal = hasAnyWord(normalized, "collect", "mandate", "autopay") ||
            hasPhrase(normalized, "request money") ||
            hasPhrase(normalized, "approve request") ||
            hasPhrase(normalized, "approve collect")
        val hasSendSignal = hasPhrase(normalized, "send money") ||
            hasPhrase(normalized, "approve payment") ||
            hasPhrase(normalized, "payment request") ||
            hasPhrase(normalized, "pay to") ||
            hasPhrase(normalized, "payment to") ||
            hasPhrase(normalized, "scan and pay")
        val isReceiveOnly = (
            hasAnyWord(normalized, "credited", "received") &&
                !hasCollectSignal &&
                !hasSendSignal &&
                !hasUpiDeepLink
            ) ||
            hasAllWords(normalized, "payment", "received")
        val isPostTransactionConfirmation = (
            hasAllWords(normalized, "payment", "successful")
            ) ||
            hasAllWords(normalized, "updated", "balance") ||
            (
                hasWord(normalized, "processed") &&
                    hasAnyWord(normalized, "purchase", "request", "investment")
                ) ||
            hasAllWords(normalized, "units", "allotted") ||
            hasAllWords(normalized, "unit", "allotment") ||
            hasAllWords(normalized, "thank", "investment")
        val isStatementOrReport = (
            hasWord(normalized, "statement") &&
                hasAnyWord(normalized, "account", "folio", "transaction", "view")
            ) ||
            (hasWord(normalized, "pan") && hasWord(normalized, "password"))
        val isEmiStatus = hasWord(normalized, "emi") &&
            hasAnyWord(normalized, "due", "deducted", "received", "repayment", "presentation")
        val isPortfolioInfo = (
            hasAnyWord(normalized, "passbook", "portfolio", "valuation", "securities")
            && hasAnyWord(normalized, "balance", "bal", "value")
            ) ||
            hasAllWords(normalized, "fund", "bal")
        val isMarketingOrProductStatus = hasAllWords(normalized, "card", "status", "updated") ||
            (
                hasWord(normalized, "loan") &&
                    hasAnyWord(normalized, "offer", "approved", "pre-approved", "preapproved", "exclusive")
                )
        val isSensitiveAccessSignal = (
            hasWord(normalized, "pan") && hasWord(normalized, "password")
            ) ||
            hasAllWords(normalized, "data", "sharing") ||
            hasWord(normalized, "aadhaar") ||
            hasWord(normalized, "passport") ||
            hasAllWords(normalized, "net", "banking", "login") ||
            hasAllWords(normalized, "mobile", "banking") ||
            (hasWord(normalized, "email") && hasWord(normalized, "changed")) ||
            (hasWord(normalized, "authorising") || hasWord(normalized, "authorizing"))

        return StructuredMessageSignals(
            normalizedText = normalized,
            hasOtpCode = hasOtpCode,
            hasUpiHandle = hasUpiHandle,
            hasUpiDeepLink = hasUpiDeepLink,
            hasUrl = hasUrl,
            isCallMetadata = isCallMetadata,
            isSetupOrRegistration = isSetupOrRegistration,
            isOtpVerification = isOtpVerification,
            isReceiveOnly = isReceiveOnly,
            isPostTransactionConfirmation = isPostTransactionConfirmation,
            isStatementOrReport = isStatementOrReport,
            isEmiStatus = isEmiStatus,
            isPortfolioInfo = isPortfolioInfo,
            isMarketingOrProductStatus = isMarketingOrProductStatus,
            isSensitiveAccessSignal = isSensitiveAccessSignal,
            hasStrongPaymentSignal = hasCollectSignal || hasSendSignal || hasUpiHandle || hasUpiDeepLink,
        )
    }

    private fun normalize(text: String): String = " ${text.lowercase().replace(Regex("\\s+"), " ").trim()} "

    private fun hasPhrase(text: String, phrase: String): Boolean = text.contains(" ${phrase.lowercase()} ")

    private fun hasWord(text: String, word: String): Boolean = wordRegex(word).containsMatchIn(text)

    private fun hasAnyWord(text: String, vararg words: String): Boolean = words.any { hasWord(text, it) || hasPhrase(text, it) }

    private fun hasAllWords(text: String, vararg words: String): Boolean = words.all { hasWord(text, it) || hasPhrase(text, it) }
}
    private fun wordRegex(word: String): Regex =
        Regex("""(^|[^\p{L}\p{N}])${Regex.escape(word.lowercase())}([^\p{L}\p{N}]|$)""")
