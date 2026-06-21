package com.arthamantri.android.notify

import com.arthamantri.android.core.FinancialRiskCategory
import com.arthamantri.android.core.FinancialRiskDetection
import com.arthamantri.android.core.FinancialRiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class HumanReviewPayloadBuilderTest {
    @Test
    fun `without consent review payload contains generic guidance only`() {
        val payload = HumanReviewPayloadBuilder.build(
            rawMessage = "Claim refund today at https://bad.example and share OTP 123456",
            detection = reviewableDetection(),
            sourceType = "sms",
            explicitConsentToShareRedactedContent = false,
        )

        assertFalse(payload.consentedForSubmission)
        assertTrue(payload.genericSafetyGuidance.contains("Pause"))
        assertNull(payload.redactedSnippet)
        assertNull(payload.category)
    }

    @Test
    fun `with consent review payload redacts sensitive content`() {
        val payload = HumanReviewPayloadBuilder.build(
            rawMessage = (
                "Claim refund at https://bad.example. 123456 is OTP. UPI PIN 12 34. " +
                    "Aadhaar 1234-5678-9012. CVV 123. Avl Bal Rs. 1,234.56. PAN ABCDE1234F"
                ),
            detection = reviewableDetection(),
            sourceType = "notification",
            explicitConsentToShareRedactedContent = true,
        )

        assertTrue(payload.consentedForSubmission)
        assertEquals("unknown_link_money_pressure", payload.category)
        assertEquals("red", payload.riskLevel)
        assertEquals(0.62, payload.confidenceScore ?: 0.0, 0.001)
        assertEquals("notification", payload.sourceType)
        assertEquals("link_with_money_pressure", payload.reasonCode)
        assertTrue(payload.redactedSnippet.orEmpty().contains("[redacted_url]"))
        assertTrue(payload.redactedSnippet.orEmpty().contains("[redacted]"))
        assertTrue(payload.redactedSnippet.orEmpty().contains("[redacted_pan]"))
        assertTrue(payload.redactedSnippet.orEmpty().contains("[redacted_aadhaar]"))
        assertTrue(payload.redactedSnippet.orEmpty().contains("[redacted_balance]"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("123456"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("12 34"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("1234-5678-9012"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("CVV 123"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("1,234.56"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("ABCDE1234F"))
        assertFalse(payload.redactedSnippet.orEmpty().contains("https://bad.example"))
    }

    @Test
    fun `support metadata carries only redacted candidate for reviewable alerts`() {
        val metadata = HumanReviewPayloadBuilder.buildSupportMetadata(
            rawMessage = "Open bit.ly/pay-help and confirm 123456 is OTP. Balance Rs. 9,999.00",
            detection = reviewableDetection(),
            sourceType = "sms",
        )

        assertEquals("unknown_link_money_pressure", metadata?.category)
        assertEquals("red", metadata?.riskLevel)
        assertEquals("sms", metadata?.sourceType)
        assertEquals("link_with_money_pressure", metadata?.reasonCode)
        assertEquals(true, metadata?.reviewable)
        assertFalse(metadata?.redactedSnippet.orEmpty().contains("123456"))
        assertFalse(metadata?.redactedSnippet.orEmpty().contains("9,999.00"))
        assertTrue(metadata?.redactedSnippet.orEmpty().contains("[redacted_balance]"))
    }

    @Test
    fun `non reviewable detection is not submitted even with consent`() {
        val payload = HumanReviewPayloadBuilder.build(
            rawMessage = "Pay processing fee today",
            detection = FinancialRiskDetection(
                riskLevel = FinancialRiskLevel.RED,
                category = FinancialRiskCategory.UPFRONT_FEE_RISK,
                reasonCode = "pay_before_benefit",
                confidenceScore = 0.86,
                reviewable = false,
            ),
            sourceType = "sms",
            explicitConsentToShareRedactedContent = true,
        )

        assertFalse(payload.consentedForSubmission)
        assertNull(payload.redactedSnippet)
    }

    private fun reviewableDetection(): FinancialRiskDetection {
        return FinancialRiskDetection(
            riskLevel = FinancialRiskLevel.RED,
            category = FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE,
            reasonCode = "link_with_money_pressure",
            confidenceScore = 0.62,
            reviewable = true,
        )
    }
}
