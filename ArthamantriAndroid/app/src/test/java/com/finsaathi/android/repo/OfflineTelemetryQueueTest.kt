package com.finsaathi.android.repo

import com.finsaathi.android.model.LiteracyAlertFeedbackRequest
import org.junit.Assert.assertEquals
import org.junit.Test

class OfflineTelemetryQueueTest {
    @Test
    fun `alert feedback payload preserves detector metadata for offline replay`() {
        val request = LiteracyAlertFeedbackRequest(
            event_id = "evt-1",
            alert_id = "alert-1",
            participant_id = "participant-1",
            action = "useful",
            channel = "overlay_window",
            title = "High-risk money message",
            message = "category=upfront_fee_risk\nrisk_level=red\nsource_type=sms\nreason_code=upfront_fee",
            timestamp = "2026-06-20T10:00:00",
            category = "upfront_fee_risk",
            risk_level = "red",
            source_type = "sms",
            reason_code = "upfront_fee",
        )

        val payload = OfflineTelemetryQueue.alertFeedbackPayloadMapFor(request)
        val restored = OfflineTelemetryQueue.alertFeedbackRequestFromMap(payload)

        assertEquals("upfront_fee_risk", payload["category"])
        assertEquals("red", payload["risk_level"])
        assertEquals("sms", payload["source_type"])
        assertEquals("upfront_fee", payload["reason_code"])
        assertEquals(request, restored)
    }
}
