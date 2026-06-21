package com.arthamantri.android.notify

import com.arthamantri.android.core.FinancialRiskDetection
import com.arthamantri.android.core.HumanReviewRedactor

data class HumanReviewPayload(
    val consentedForSubmission: Boolean,
    val genericSafetyGuidance: String,
    val redactedSnippet: String? = null,
    val category: String? = null,
    val riskLevel: String? = null,
    val confidenceScore: Double? = null,
    val reviewable: Boolean = false,
    val sourceType: String? = null,
    val reasonCode: String? = null,
)

data class HumanReviewSupportMetadata(
    val redactedSnippet: String,
    val category: String,
    val riskLevel: String,
    val confidenceScore: Double?,
    val reviewable: Boolean,
    val sourceType: String,
    val reasonCode: String,
)

object HumanReviewPayloadBuilder {
    private const val GENERIC_GUIDANCE =
        "FinSaathi is not fully sure. Pause, do not share OTP/UPI PIN/bank details, and verify through an official source or trusted person."

    fun build(
        rawMessage: String,
        detection: FinancialRiskDetection,
        sourceType: String,
        explicitConsentToShareRedactedContent: Boolean,
    ): HumanReviewPayload {
        if (!detection.reviewable || !explicitConsentToShareRedactedContent) {
            return HumanReviewPayload(
                consentedForSubmission = false,
                genericSafetyGuidance = GENERIC_GUIDANCE,
                reviewable = detection.reviewable,
            )
        }

        return HumanReviewPayload(
            consentedForSubmission = true,
            genericSafetyGuidance = GENERIC_GUIDANCE,
            redactedSnippet = HumanReviewRedactor.redact(rawMessage),
            category = detection.category.wireValue,
            riskLevel = detection.riskLevel.name.lowercase(),
            confidenceScore = detection.confidenceScore,
            reviewable = true,
            sourceType = sourceType,
            reasonCode = detection.reasonCode,
        )
    }

    fun buildSupportMetadata(
        rawMessage: String,
        detection: FinancialRiskDetection,
        sourceType: String,
    ): HumanReviewSupportMetadata? {
        if (!detection.reviewable) {
            return null
        }
        val redactedSnippet = HumanReviewRedactor.redact(rawMessage)
        if (redactedSnippet.isBlank()) {
            return null
        }
        return HumanReviewSupportMetadata(
            redactedSnippet = redactedSnippet,
            category = detection.category.wireValue,
            riskLevel = detection.riskLevel.name.lowercase(),
            confidenceScore = detection.confidenceScore,
            reviewable = true,
            sourceType = sourceType,
            reasonCode = detection.reasonCode,
        )
    }
}
