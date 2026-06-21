package com.arthamantri.android.core

enum class FinancialRiskLevel {
    GREEN,
    YELLOW,
    RED,
}

enum class FinancialRiskCategory(val wireValue: String) {
    BENIGN_OR_ROUTINE("benign_or_routine"),
    GENERIC_PROMOTION("generic_promotion"),
    UPFRONT_FEE_RISK("upfront_fee_risk"),
    SENSITIVE_DATA_REQUEST("sensitive_data_request"),
    KYC_ACCOUNT_BLOCK_PRESSURE("kyc_account_block_pressure"),
    GUARANTEED_RETURN_SCHEME("guaranteed_return_scheme"),
    UNKNOWN_LINK_MONEY_PRESSURE("unknown_link_money_pressure"),
}

data class FinancialRiskDetection(
    val riskLevel: FinancialRiskLevel,
    val category: FinancialRiskCategory,
    val reasonCode: String,
    val confidenceScore: Double = 1.0,
    val reviewable: Boolean = false,
) {
    val shouldAlert: Boolean
        get() = riskLevel != FinancialRiskLevel.GREEN
}

object FinancialRiskMessageDetector {
    fun detect(
        message: String,
        recentLinkContext: LinkContextSignals? = null,
    ): FinancialRiskDetection {
        val normalized = normalize(message)
        if (normalized.isBlank()) {
            return green("blank")
        }

        val signals = StructuredMessageSignalExtractor.extract(message)
        if (isRecentSuspiciousAccessFlow(normalized, signals, recentLinkContext)) {
            return detection(
                FinancialRiskLevel.RED,
                FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE,
                "recent_link_account_access",
                confidenceScore = 0.78,
                reviewable = true,
            )
        }

        if (isSensitiveDataRequest(normalized)) {
            return red(FinancialRiskCategory.SENSITIVE_DATA_REQUEST, "sensitive_data_requested")
        }

        if (isUpfrontFeeRisk(normalized)) {
            return red(FinancialRiskCategory.UPFRONT_FEE_RISK, "pay_before_benefit")
        }

        if (isKycOrAccountBlockPressure(normalized)) {
            val level = if (hasUrl(normalized) || hasUrgency(normalized) || hasPaymentRequest(normalized)) {
                FinancialRiskLevel.RED
            } else {
                FinancialRiskLevel.YELLOW
            }
            return detection(
                level,
                FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE,
                "kyc_or_account_pressure",
                confidenceScore = if (level == FinancialRiskLevel.RED) 0.82 else 0.7,
            )
        }

        if (isUnknownLinkMoneyPressure(normalized)) {
            return detection(
                FinancialRiskLevel.RED,
                FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE,
                "link_with_money_pressure",
                confidenceScore = 0.62,
                reviewable = true,
            )
        }

        if (isGuaranteedReturnScheme(normalized)) {
            val level = if (hasPaymentRequest(normalized) || hasUrgency(normalized)) {
                FinancialRiskLevel.RED
            } else {
                FinancialRiskLevel.YELLOW
            }
            return detection(
                level,
                FinancialRiskCategory.GUARANTEED_RETURN_SCHEME,
                "unrealistic_return_promise",
                confidenceScore = if (level == FinancialRiskLevel.RED) 0.82 else 0.7,
            )
        }

        if (isRoutineOrBenign(signals, normalized)) {
            return green("routine_financial_message")
        }

        if (isGenericFinancialPromotion(normalized)) {
            return yellow(FinancialRiskCategory.GENERIC_PROMOTION, "generic_financial_promotion")
        }

        return green("no_risk_pattern")
    }

    private fun isSensitiveDataRequest(text: String): Boolean {
        val hasRequest = hasAny(text, requestVerbs)
        val hasSensitiveTerm = hasAny(text, sensitiveTerms)
        if (!hasRequest || !hasSensitiveTerm) {
            return false
        }
        if (!hasAny(text, safetyEducationPhrases)) {
            return true
        }
        return hasExplicitSensitiveRequest(text)
    }

    private fun isUpfrontFeeRisk(text: String): Boolean {
        val benefitPromise = hasAny(text, benefitTerms)
        val feeDemand = hasAny(text, upfrontFeeTerms) || (hasPaymentRequest(text) && hasMoneyMarker(text))
        return benefitPromise && feeDemand
    }

    private fun isUnknownLinkMoneyPressure(text: String): Boolean {
        return hasUrl(text) &&
            hasAny(text, moneyOrAccountTerms) &&
            (hasUrgency(text) || hasPaymentRequest(text) || hasAny(text, requestVerbs))
    }

    private fun isKycOrAccountBlockPressure(text: String): Boolean {
        val kycOrAccount = hasAny(text, kycTerms) || hasAny(text, accountBlockTerms)
        val actionPressure = hasAny(text, actionTerms) || hasUrgency(text) || hasUrl(text)
        return kycOrAccount && actionPressure
    }

    private fun isGuaranteedReturnScheme(text: String): Boolean {
        return hasAny(text, guaranteedReturnTerms)
    }

    private fun isGenericFinancialPromotion(text: String): Boolean {
        return hasAny(text, genericPromotionTerms) && !hasPaymentRequest(text)
    }

    private fun isRecentSuspiciousAccessFlow(
        text: String,
        signals: StructuredMessageSignals,
        recentLinkContext: LinkContextSignals?,
    ): Boolean {
        if (recentLinkContext?.linkClicked != true || !isHighRiskRecentLink(recentLinkContext)) {
            return false
        }

        return signals.isOtpVerification ||
            signals.isSensitiveAccessSignal ||
            hasAny(text, accountAccessContextTerms)
    }

    private fun isHighRiskRecentLink(linkContext: LinkContextSignals): Boolean {
        val host = linkContext.urlHost.orEmpty()
        val resolvedDomain = linkContext.resolvedDomain.orEmpty()
        return isSuspiciousHost(host) ||
            isSuspiciousHost(resolvedDomain) ||
            hasAnyDomainMarker(host, highRiskFinancialDomainMarkers) ||
            hasAnyDomainMarker(resolvedDomain, highRiskFinancialDomainMarkers)
    }

    private fun isSuspiciousHost(value: String): Boolean {
        val normalized = value.trim().trim('.').lowercase().removePrefix("www.")
        if (normalized.isBlank()) {
            return false
        }
        return normalized in suspiciousDomains ||
            normalized.startsWith("xn--") ||
            suspiciousTlds.any { normalized.endsWith(it) } ||
            isIpv4Address(normalized)
    }

    private fun hasAnyDomainMarker(value: String, markers: Collection<String>): Boolean {
        val normalized = value.trim().trim('.').lowercase().removePrefix("www.")
        return normalized.isNotBlank() && markers.any { marker -> normalized.contains(marker) }
    }

    private fun isIpv4Address(value: String): Boolean =
        Regex("""\b(?:\d{1,3}\.){3}\d{1,3}\b""").matches(value) &&
            value.split('.').all { part -> part.toIntOrNull()?.let { it in 0..255 } == true }

    private fun isRoutineOrBenign(signals: StructuredMessageSignals, text: String): Boolean {
        if (
            signals.isCallMetadata ||
            signals.isSetupOrRegistration ||
            signals.isOtpVerification ||
            signals.isReceiveOnly ||
            signals.isPostTransactionConfirmation ||
            signals.isStatementOrReport ||
            signals.isEmiStatus ||
            signals.isPortfolioInfo
        ) {
            return true
        }

        return hasAny(text, routineTerms) && !hasUrl(text) && !hasUrgency(text) && !hasPaymentRequest(text)
    }

    private fun hasPaymentRequest(text: String): Boolean = hasAny(text, paymentRequestTerms)

    private fun hasMoneyMarker(text: String): Boolean =
        AppConstants.Parsing.MONEY_MARKERS.any { text.contains(" ${it.lowercase()} ") } ||
            text.contains(" ₹") ||
            text.contains(" rs.") ||
            text.contains(" rupees ") ||
            text.contains(" rupay") ||
            Regex("""\b\d{2,}(?:,\d{3})*(?:\.\d{1,2})?\b""").containsMatchIn(text)

    private fun hasUrl(text: String): Boolean =
        text.contains(" http://") ||
            text.contains(" https://") ||
            text.contains(" www.") ||
            Regex("""\b[a-z0-9][a-z0-9-]{1,62}\.[a-z]{2,12}\b""").containsMatchIn(text)

    private fun hasUrgency(text: String): Boolean = hasAny(text, urgencyTerms)

    private fun hasAny(text: String, phrases: Collection<String>): Boolean =
        phrases.any { phrase ->
            Regex("""(?<![a-z0-9])${Regex.escape(phrase.lowercase())}(?![a-z0-9])""")
                .containsMatchIn(text)
        }

    private fun hasExplicitSensitiveRequest(text: String): Boolean {
        val requestText = safetyEducationPhrases.fold(text) { current, phrase ->
            current.replace(Regex("""(?<![a-z0-9])${Regex.escape(phrase.lowercase())}(?![a-z0-9])"""), " ")
        }
        val sensitivePattern = Regex("""\b(otp|upi\s*pin|pin|password|bank\s*password|cvv|aadhaar|aadhar|pan)\b""")
        return requestVerbs.any { verb ->
            Regex("""(?<![a-z0-9])${Regex.escape(verb.lowercase())}(?![a-z0-9]).{0,48}${sensitivePattern.pattern}""")
                .containsMatchIn(requestText)
        } || sensitivePattern.findAll(requestText).any { match ->
            val afterSensitive = requestText.substring(match.range.last + 1).take(64)
            hasAny(" $afterSensitive ", requestVerbs)
        }
    }

    private fun normalize(message: String): String =
        " ${message.lowercase().replace(Regex("\\s+"), " ").trim()} "

    private fun green(reasonCode: String): FinancialRiskDetection =
        detection(FinancialRiskLevel.GREEN, FinancialRiskCategory.BENIGN_OR_ROUTINE, reasonCode, confidenceScore = 0.92)

    private fun yellow(category: FinancialRiskCategory, reasonCode: String): FinancialRiskDetection =
        detection(FinancialRiskLevel.YELLOW, category, reasonCode, confidenceScore = 0.72)

    private fun red(category: FinancialRiskCategory, reasonCode: String): FinancialRiskDetection =
        detection(FinancialRiskLevel.RED, category, reasonCode, confidenceScore = 0.86)

    private fun detection(
        level: FinancialRiskLevel,
        category: FinancialRiskCategory,
        reasonCode: String,
        confidenceScore: Double,
        reviewable: Boolean = false,
    ): FinancialRiskDetection =
        FinancialRiskDetection(
            riskLevel = level,
            category = category,
            reasonCode = reasonCode,
            confidenceScore = confidenceScore.coerceIn(0.0, 1.0),
            reviewable = reviewable || (level == FinancialRiskLevel.RED && confidenceScore < 0.7),
        )

    private val safetyEducationPhrases = setOf(
        "do not share",
        "don't share",
        "never share",
        "not share",
        "share nahi",
    )

    private val requestVerbs = setOf(
        "share",
        "send",
        "tell",
        "give",
        "provide",
        "submit",
        "enter",
        "type",
        "confirm",
        "upload",
        "forward",
        "bhejo",
        "bheje",
        "bataye",
        "batana",
        "dijiye",
        "de do",
        "photo",
    )

    private val sensitiveTerms = setOf(
        "otp",
        "upi pin",
        "pin",
        "bank password",
        "password",
        "card detail",
        "card details",
        "card number",
        "cvv",
        "aadhaar",
        "aadhar",
        "pan",
        "net banking",
        "mobile banking",
        "remote access",
        "screen share",
        "anydesk",
        "teamviewer",
    )

    private val benefitTerms = setOf(
        "job",
        "work from home",
        "packing job",
        "earn",
        "earning",
        "income",
        "salary",
        "monthly",
        "loan",
        "approved loan",
        "reward",
        "cashback",
        "bonus",
    )

    private val upfrontFeeTerms = setOf(
        "registration fee",
        "processing fee",
        "joining fee",
        "activation fee",
        "service charge",
        "security deposit",
        "deposit first",
        "advance payment",
        "fee first",
    )

    private val paymentRequestTerms = setOf(
        "pay",
        "pay now",
        "payment",
        "transfer",
        "send money",
        "deposit",
        "fee",
        "charges",
        "jama",
        "bharo",
    )

    private val moneyOrAccountTerms = setOf(
        "money",
        "payment",
        "account",
        "bank",
        "kyc",
        "refund",
        "reward",
        "cashback",
        "loan",
        "upi",
        "card",
    )

    private val kycTerms = setOf(
        "kyc",
        "re-kyc",
        "update kyc",
        "verify kyc",
        "account verification",
        "verify account",
        "update account",
    )

    private val accountBlockTerms = setOf(
        "account blocked",
        "account block",
        "account suspended",
        "account suspend",
        "block your account",
        "bank account blocked",
        "expire",
        "expired",
        "deactivate",
        "freeze",
    )

    private val accountAccessContextTerms = setOf(
        "login",
        "verify account",
        "account verification",
        "update account",
        "customer id",
        "net banking",
        "internet banking",
        "mobile banking",
        "kyc",
    )

    private val actionTerms = setOf(
        "click",
        "open link",
        "verify",
        "update",
        "complete",
        "continue",
        "act",
    )

    private val urgencyTerms = setOf(
        "urgent",
        "immediately",
        "today",
        "now",
        "within 24 hours",
        "last chance",
        "limited time",
        "offer ends",
        "avoid block",
        "will be blocked",
        "final notice",
    )

    private val guaranteedReturnTerms = setOf(
        "double money",
        "double your money",
        "guaranteed return",
        "guaranteed income",
        "guaranteed profit",
        "fixed profit",
        "daily profit",
        "risk free return",
        "risk-free return",
        "earn fixed profit",
        "profit daily",
        "return guarantee",
    )

    private val genericPromotionTerms = setOf(
        "loan offer",
        "pre-approved loan",
        "preapproved loan",
        "exclusive loan",
        "apply now",
        "credit card offer",
    )

    private val highRiskFinancialDomainMarkers = setOf(
        "loan",
        "loans",
        "credit",
        "lending",
        "emi",
        "borrow",
        "finance",
        "card",
        "cards",
        "creditcard",
        "debitcard",
        "rupay",
        "visa",
        "mastercard",
        "amex",
    )

    private val suspiciousDomains = setOf(
        "bit.ly",
        "tinyurl.com",
        "goo.gl",
        "is.gd",
        "cutt.ly",
        "lnk.to",
    )

    private val suspiciousTlds = setOf(
        ".top",
        ".xyz",
        ".click",
        ".support",
        ".live",
        ".work",
        ".zip",
        ".mov",
    )

    private val routineTerms = setOf(
        "debited",
        "credited",
        "payment successful",
        "paid",
        "received",
        "balance",
        "statement",
        "bill due",
        "due date",
    )
}
