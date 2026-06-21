package com.arthamantri.android.notify

import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.FinancialRiskDetection
import com.arthamantri.android.core.FinancialRiskLevel

enum class FinancialRiskAlertRoute {
    NONE,
    PASSIVE_NOTIFICATION,
    INTERRUPTIVE_ALERT,
}

data class FinancialRiskAlertRoutingDecision(
    val route: FinancialRiskAlertRoute,
    val riskLevel: FinancialRiskLevel,
    val severity: String,
    val allowOverlay: Boolean,
    val pauseSeconds: Int,
) {
    val shouldShow: Boolean
        get() = route != FinancialRiskAlertRoute.NONE
}

object FinancialRiskAlertRouter {
    fun routeFor(detection: FinancialRiskDetection): FinancialRiskAlertRoutingDecision {
        return when (detection.riskLevel) {
            FinancialRiskLevel.GREEN -> FinancialRiskAlertRoutingDecision(
                route = FinancialRiskAlertRoute.NONE,
                riskLevel = FinancialRiskLevel.GREEN,
                severity = "soft",
                allowOverlay = false,
                pauseSeconds = 0,
            )
            FinancialRiskLevel.YELLOW -> FinancialRiskAlertRoutingDecision(
                route = FinancialRiskAlertRoute.PASSIVE_NOTIFICATION,
                riskLevel = FinancialRiskLevel.YELLOW,
                severity = "soft",
                allowOverlay = false,
                pauseSeconds = 0,
            )
            FinancialRiskLevel.RED -> FinancialRiskAlertRoutingDecision(
                route = FinancialRiskAlertRoute.INTERRUPTIVE_ALERT,
                riskLevel = FinancialRiskLevel.RED,
                severity = "hard",
                allowOverlay = true,
                pauseSeconds = AppConstants.Timing.PAYMENT_DECISION_PAUSE_SECONDS,
            )
        }
    }

    /**
     * Legacy alert severities map to the newer traffic-light policy as:
     * none/blank -> Green, soft/medium -> Yellow, hard -> Red.
     */
    fun riskLevelForLegacySeverity(severity: String?): FinancialRiskLevel {
        return when (severity?.trim()?.lowercase()) {
            null, "", "none", "green" -> FinancialRiskLevel.GREEN
            "hard", "red" -> FinancialRiskLevel.RED
            "soft", "medium", "yellow" -> FinancialRiskLevel.YELLOW
            else -> FinancialRiskLevel.YELLOW
        }
    }
}
