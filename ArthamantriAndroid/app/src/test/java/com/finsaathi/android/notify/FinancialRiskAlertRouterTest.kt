package com.finsaathi.android.notify

import com.finsaathi.android.core.AppConstants
import com.finsaathi.android.core.FinancialRiskCategory
import com.finsaathi.android.core.FinancialRiskDetection
import com.finsaathi.android.core.FinancialRiskLevel
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FinancialRiskAlertRouterTest {
    @Test
    fun `green risk stays silent`() {
        val decision = FinancialRiskAlertRouter.routeFor(
            detection(FinancialRiskLevel.GREEN),
        )

        assertEquals(FinancialRiskAlertRoute.NONE, decision.route)
        assertFalse(decision.shouldShow)
        assertFalse(decision.allowOverlay)
        assertEquals(0, decision.pauseSeconds)
    }

    @Test
    fun `yellow risk uses passive notification without overlay`() {
        val decision = FinancialRiskAlertRouter.routeFor(
            detection(FinancialRiskLevel.YELLOW),
        )

        assertEquals(FinancialRiskAlertRoute.PASSIVE_NOTIFICATION, decision.route)
        assertTrue(decision.shouldShow)
        assertEquals("soft", decision.severity)
        assertFalse(decision.allowOverlay)
        assertEquals(0, decision.pauseSeconds)
    }

    @Test
    fun `red risk uses interruptive alert with overlay enabled`() {
        val decision = FinancialRiskAlertRouter.routeFor(
            detection(FinancialRiskLevel.RED),
        )

        assertEquals(FinancialRiskAlertRoute.INTERRUPTIVE_ALERT, decision.route)
        assertTrue(decision.shouldShow)
        assertEquals("hard", decision.severity)
        assertTrue(decision.allowOverlay)
        assertEquals(AppConstants.Timing.PAYMENT_DECISION_PAUSE_SECONDS, decision.pauseSeconds)
    }

    @Test
    fun `legacy severities map to traffic light policy`() {
        assertEquals(FinancialRiskLevel.GREEN, FinancialRiskAlertRouter.riskLevelForLegacySeverity(null))
        assertEquals(FinancialRiskLevel.GREEN, FinancialRiskAlertRouter.riskLevelForLegacySeverity(""))
        assertEquals(FinancialRiskLevel.GREEN, FinancialRiskAlertRouter.riskLevelForLegacySeverity("none"))
        assertEquals(FinancialRiskLevel.YELLOW, FinancialRiskAlertRouter.riskLevelForLegacySeverity("soft"))
        assertEquals(FinancialRiskLevel.YELLOW, FinancialRiskAlertRouter.riskLevelForLegacySeverity("medium"))
        assertEquals(FinancialRiskLevel.RED, FinancialRiskAlertRouter.riskLevelForLegacySeverity("hard"))
    }

    private fun detection(level: FinancialRiskLevel): FinancialRiskDetection {
        return FinancialRiskDetection(
            riskLevel = level,
            category = FinancialRiskCategory.UPFRONT_FEE_RISK,
            reasonCode = "test",
        )
    }
}
