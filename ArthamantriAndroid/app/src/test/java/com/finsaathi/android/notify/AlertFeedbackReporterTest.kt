package com.finsaathi.android.notify

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertFeedbackReporterTest {
    @Test
    fun `detector feedback replaces raw-looking message with safe metadata summary`() {
        val rawLookingMessage = "Pay Rs. 499 registration fee now. OTP 123456. PAN ABCDE1234F."
        val metadata = AlertFeedbackMetadata(
            category = "upfront_fee_risk",
            riskLevel = "red",
            sourceType = "sms",
            reasonCode = "upfront_fee_with_income_promise",
        )

        val reportMessage = AlertFeedbackReporter.safeReportMessage(
            message = rawLookingMessage,
            metadata = metadata,
        )

        assertTrue(reportMessage.contains("category=upfront_fee_risk"))
        assertTrue(reportMessage.contains("risk_level=red"))
        assertTrue(reportMessage.contains("source_type=sms"))
        assertTrue(reportMessage.contains("reason_code=upfront_fee_with_income_promise"))
        assertFalse(reportMessage.contains("123456"))
        assertFalse(reportMessage.contains("ABCDE1234F"))
        assertFalse(reportMessage.contains(rawLookingMessage))
    }

    @Test
    fun `non detector feedback keeps existing generated report message`() {
        val generatedMessage = "This payment may disturb your daily planning."

        val reportMessage = AlertFeedbackReporter.safeReportMessage(
            message = generatedMessage,
            metadata = null,
        )

        assertEquals(generatedMessage, reportMessage)
    }

    @Test
    fun `overlay feedback maps useful and dismissive actions to pilot reaction logs`() {
        assertEquals(
            "overlay_reaction_useful",
            AlertFeedbackReporter.overlayReactionLogMessage("useful", "overlay_window"),
        )
        assertEquals(
            "overlay_reaction_irritating",
            AlertFeedbackReporter.overlayReactionLogMessage("not_useful", "overlay_window"),
        )
        assertEquals(
            "overlay_reaction_irritating",
            AlertFeedbackReporter.overlayReactionLogMessage("dismissed", "overlay"),
        )
        assertEquals(
            null,
            AlertFeedbackReporter.overlayReactionLogMessage("useful", "fullscreen_activity"),
        )
    }
}
