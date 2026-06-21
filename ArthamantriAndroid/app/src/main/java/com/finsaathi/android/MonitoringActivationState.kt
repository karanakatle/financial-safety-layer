package com.finsaathi.android

import android.content.Context
import com.finsaathi.android.core.AppConstants

internal enum class MonitoringStartBlocker {
    NONE,
    ONBOARDING,
    SMS,
    USAGE,
    OVERLAY,
    NOTIFICATIONS,
}

internal data class MonitoringActivationState(
    val onboardingStep: OnboardingStep,
    val permissionState: PermissionOnboardingState,
) {
    fun blocker(): MonitoringStartBlocker {
        return when {
            onboardingStep != OnboardingStep.COMPLETE -> MonitoringStartBlocker.ONBOARDING
            !permissionState.smsGranted -> MonitoringStartBlocker.SMS
            !permissionState.notificationsGranted -> MonitoringStartBlocker.NOTIFICATIONS
            !permissionState.usageGranted -> MonitoringStartBlocker.USAGE
            !permissionState.overlayGranted -> MonitoringStartBlocker.OVERLAY
            else -> MonitoringStartBlocker.NONE
        }
    }

    fun canStart(): Boolean = blocker() == MonitoringStartBlocker.NONE
}

internal enum class MonitoringProtectionStatus {
    STOPPED,
    PARTIAL,
    FULL,
}

internal data class MonitoringAccessState(
    val monitoringActive: Boolean,
    val permissionState: PermissionOnboardingState,
) {
    fun protectionStatus(): MonitoringProtectionStatus {
        return when {
            !monitoringActive -> MonitoringProtectionStatus.STOPPED
            permissionState.isComplete() -> MonitoringProtectionStatus.FULL
            else -> MonitoringProtectionStatus.PARTIAL
        }
    }

    fun canProcessBackgroundSignals(): Boolean {
        return protectionStatus() == MonitoringProtectionStatus.FULL
    }

    fun shouldStopBackgroundMonitoring(): Boolean {
        return monitoringActive && !permissionState.isComplete()
    }
}

internal object MonitoringAccessGate {
    fun isMonitoringActive(context: Context): Boolean {
        return context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .getBoolean(AppConstants.Prefs.KEY_MONITORING_ACTIVE, false)
    }
}
